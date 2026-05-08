#!/usr/bin/env python3
"""
ComfyGramBot — ImageCreator 专属 Telegram Bot
直连 ComfyUI，无内容过滤。

新版：多步 Inline Keyboard 流程
  选模式 → 选 family → 选底模 → 多选 LoRA → 确认 → 生成

也保留旧版命令支持：/status /cancel /help /start
"""

import json
import os
import random
import sys
import time
import uuid
import shutil
import threading
import subprocess

# auto_mask available but not imported in main flow (no longer needed for unified i2i path)
import urllib.request   # kept for ComfyUI client calls only
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

# ── 配置 ────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TG_BOT_TOKEN environment variable not set")
TG_API      = f"https://api.telegram.org/bot{BOT_TOKEN}"

from telegram_http import TelegramClient
import dual_transfer
from types import SimpleNamespace
_tg_client = TelegramClient(TG_API, default_timeout=15.0)
COMFYUI_ENDPOINTS = [
    os.environ.get("COMFYUI_BASE", "").strip(),
    "http://127.0.0.1:8188",
    "http://localhost:8188",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8001",
    "http://localhost:8001",
]
COMFYUI_ENDPOINTS = [x for x in COMFYUI_ENDPOINTS if x]
ACTIVE_COMFYUI = None

WORKSPACE          = Path(os.environ.get("IMAGECREATOR_WORKSPACE", "./workspace"))
COMFYUI_BASE       = Path(os.environ.get("COMFYUI_BASE_DIR", "./ComfyUI"))
COMFYUI_INPUT      = COMFYUI_BASE / "input"
COMFYUI_OUTPUT     = COMFYUI_BASE / "output"
MEDIA_OUTPUT       = WORKSPACE / "media" / "output"
MEDIA_INPUT        = WORKSPACE / "media" / "input"
OUTPUT_ARCHIVE     = Path(os.environ.get("COMFYUI_OUTPUT_ARCHIVE", "./ComfyUI_output_archive"))
MATERIAL_REGISTRY_FILE = WORKSPACE / "material_registry.json"
LORA_REGISTRY_FILE = WORKSPACE / "lora_registry.json"  # kept for compat

# tmp files
OFFSET_FILE   = WORKSPACE / "tmp" / "comfygram_offset.json"
PENDING_FILE  = WORKSPACE / "tmp" / "comfygram_pending.json"
WAITING_FILE  = WORKSPACE / "tmp" / "comfygram_waiting.json"
TRAINING_FILE = WORKSPACE / "tmp" / "comfygram_training.json"
GEN_STATE_FILE = WORKSPACE / "tmp" / "gen_state.json"

POLL_INTERVAL  = 10
MAX_JOB_AGE    = 7200
WAITING_EXPIRE = 1800
TRAINING_EXPIRE = 3600
PAGE_SIZE = 20  # loras per page

# ── Family display names ─────────────────────────────────
FAMILY_CN = {"pvc": "手办", "2d": "2D动漫", "3d": "3D风格"}

# ── Preset prompt templates ──────────────────────────────
PRESET_TEMPLATES_FILE = WORKSPACE / "preset_prompt_templates.json"

def _load_preset_templates() -> list:
    if PRESET_TEMPLATES_FILE.exists():
        try:
            return json.loads(PRESET_TEMPLATES_FILE.read_text())
        except Exception:
            return []
    return []

PRESET_TEMPLATES = _load_preset_templates()

# ── Custom preset slots (10 fixed-size user-editable prompts) ───────
CUSTOM_PRESETS_FILE = WORKSPACE / "user_custom_prompts.json"
CUSTOM_PRESET_SLOTS = 10

def _load_custom_presets() -> list:
    """Always returns exactly CUSTOM_PRESET_SLOTS entries, each
    {id, title, positive}. Creates file with slot 1 seeded on first run."""
    default_slot1 = ("masterpiece, best quality, girl, kawaii, mature female, "
                     "ojousama, female, large breasts, nipples, areolae, "
                     "clitoris, shaved_pussy,")
    if not CUSTOM_PRESETS_FILE.exists():
        slots = [{"title": f"自定义 {i+1}", "positive": ""} for i in range(CUSTOM_PRESET_SLOTS)]
        slots[0]["positive"] = default_slot1
        CUSTOM_PRESETS_FILE.write_text(json.dumps({"slots": slots}, ensure_ascii=False, indent=2))
    try:
        slots = json.loads(CUSTOM_PRESETS_FILE.read_text()).get("slots", [])
    except Exception:
        slots = []
    out = []
    for i in range(CUSTOM_PRESET_SLOTS):
        s = slots[i] if i < len(slots) else {}
        out.append({
            "id":       f"custom_{i+1}",
            "title":    s.get("title") or f"自定义 {i+1}",
            "positive": s.get("positive", "") or "",
        })
    return out


def _save_custom_presets() -> None:
    data = {"slots": [{"title": p["title"], "positive": p["positive"]} for p in CUSTOM_PRESETS]}
    CUSTOM_PRESETS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _find_preset_by_id(preset_id: str):
    """Look up preset across regular + custom lists. Returns dict or None."""
    tpl = next((t for t in PRESET_TEMPLATES if t["id"] == preset_id), None)
    if tpl is None:
        tpl = next((t for t in CUSTOM_PRESETS if t["id"] == preset_id), None)
    return tpl


CUSTOM_PRESETS = _load_custom_presets()

# ── Curated prompt banks (自选预设：14 分类 tag 勾选，最多 30 个) ──
CURATED_BANKS_FILE = WORKSPACE / "curated_prompt_banks.json"
CURATED_PAGE_SIZE = 8
CURATED_MAX_SELECTION_FALLBACK = 30

def _load_curated_banks() -> dict:
    """Load curated banks JSON. Returns dict {max_selection, categories: [{id,cn_label,tags}]}."""
    if CURATED_BANKS_FILE.exists():
        try:
            data = json.loads(CURATED_BANKS_FILE.read_text())
            cats = data.get("categories", [])
            # sanity
            for c in cats:
                c.setdefault("tags", [])
            return {
                "max_selection": int(data.get("max_selection", CURATED_MAX_SELECTION_FALLBACK)),
                "categories": cats,
            }
        except Exception:
            pass
    return {"max_selection": CURATED_MAX_SELECTION_FALLBACK, "categories": []}


CURATED_BANKS = _load_curated_banks()


def _curated_category(cid: str):
    for c in CURATED_BANKS.get("categories", []):
        if c["id"] == cid:
            return c
    return None


def _tag_en(t) -> str:
    """Extract English tag text from either a legacy plain string or new {en,cn} dict."""
    if isinstance(t, dict):
        return t.get("en", "")
    return str(t)


def _tag_cn(t) -> str:
    """Extract Chinese button label; falls back to English if translation missing."""
    if isinstance(t, dict):
        return t.get("cn") or t.get("en", "")
    return str(t)


def _curated_resolve_selected(selected: list) -> list:
    """Convert state list of 'cid:idx' strings into actual ENGLISH tag strings
    (the form that goes into the final prompt). Preserves pick order."""
    out = []
    for key in selected:
        if ":" not in key:
            continue
        cid, idx_s = key.split(":", 1)
        try:
            idx = int(idx_s)
        except ValueError:
            continue
        cat = _curated_category(cid)
        if not cat or idx >= len(cat.get("tags", [])):
            continue
        out.append(_tag_en(cat["tags"][idx]))
    return out


# ── Prompt library ──────────────────────────────────────
PROMPT_LIBRARY_FILE = WORKSPACE / "prompt_library.json"

def _load_prompt_library() -> dict:
    if PROMPT_LIBRARY_FILE.exists():
        try:
            return json.loads(PROMPT_LIBRARY_FILE.read_text())
        except Exception:
            return {"version": 0, "categories": []}
    return {"version": 0, "categories": []}

PROMPT_LIBRARY = _load_prompt_library()

# ── Registry ─────────────────────────────────────────────
def load_registry() -> dict:
    return json.loads(MATERIAL_REGISTRY_FILE.read_text())

REG = load_registry()

def get_enabled_models(family: str) -> list:
    """Return list of (key, entry) for enabled models in family."""
    return [(k, v) for k, v in REG["models"].items()
            if v["family"] == family and v.get("telegram_enabled", True)]

def get_enabled_loras(family: str, mode: str) -> list:
    """Return list of (key, entry) for enabled loras in family that support mode."""
    loras_dict = REG.get("loras", {})
    result = []
    for k, v in loras_dict.items():
        if v.get("family") != family:
            continue
        if not v.get("telegram_enabled", True):
            continue
        supported = v.get("supported_modes", ["t2i", "i2i"])
        # video mode uses "i2v"; image mode uses "t2i" or "i2i"
        if mode == "video":
            if "i2v" in supported:
                result.append((k, v))
        else:
            if "t2i" in supported or "i2i" in supported:
                result.append((k, v))
    return result

# ── GEN_STATE (per user) ─────────────────────────────────
GEN_STATE: dict = {}

# ── Callback dedup (in-memory, prevents double-processing) ──
_SEEN_CB_IDS: set = set()
_MAX_SEEN_CB = 500

# ── Mode prompts (prepended, never overwrite original prompts) ──
MODE_PROMPTS = {
    # Text-to-image: quality boost
    "t2i": "masterpiece, best quality, amazing quality, very aesthetic, absurdres",
    # Image-to-image with character preservation: identity lock
    "i2i_light":  "same character, same face, same hair color, same pose, same expression, preserve identity, preserve facial features",
    "i2i_medium": "same character, same face, same hair color, same hairstyle, preserve identity, preserve facial features",
    "i2i_heavy":  "same character, same face, preserve identity",
}

# ── Intensity presets (character preservation vs style transfer) ──
INTENSITY_PRESETS = {
    "light": {
        "label": "🌿 轻度（角色保留优先）",
        "desc":  "最大程度保留角色脸、发色、姿势，风格迁移较弱",
        "denoise": 0.40,
        "mode_prompt_key": "i2i_light",
    },
    "medium": {
        "label": "⚖️ 中度（平衡）",
        "desc":  "角色保留与新风格平衡，推荐模式",
        "denoise": 0.60,
        "mode_prompt_key": "i2i_medium",
    },
    "heavy": {
        "label": "🔥 重度（风格更强）",
        "desc":  "新底模/LoRA 风格介入更强，仍尽量保留脸和头发",
        "denoise": 0.80,
        "mode_prompt_key": "i2i_heavy",
    },
}

# ── Update dedup (prevents reprocessing on offset reset) ────
_PROCESSED_UPDATE_IDS: set = set()
_MAX_PROCESSED_UPDATES = 1000

def _load_gen_state():
    global GEN_STATE
    if GEN_STATE_FILE.exists():
        try:
            GEN_STATE = json.loads(GEN_STATE_FILE.read_text())
            # keys are strings in JSON; convert user_id keys to int
            GEN_STATE = {int(k): v for k, v in GEN_STATE.items()}
        except Exception:
            GEN_STATE = {}

_last_state_save = 0.0

def _save_gen_state():
    global _last_state_save
    GEN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    GEN_STATE_FILE.write_text(json.dumps(
        {str(k): v for k, v in GEN_STATE.items()},
        indent=2, ensure_ascii=False))
    _last_state_save = time.time()

def get_state(user_id: int, chat_id: int) -> dict:
    if user_id not in GEN_STATE:
        GEN_STATE[user_id] = _default_state(chat_id)
    return GEN_STATE[user_id]

def save_state(user_id: int):
    _save_gen_state()

def _default_state(chat_id: int) -> dict:
    return {
        "step": "idle",
        "mode": "image",
        "family": "pvc",
        "model_key": "",
        "lora_keys": [],
        "user_prompt": "",
        "source_image_path": None,
        "last_seed": 0,
        "chat_id": chat_id,
        "last_menu_msg_id": None,
        "current_model_list": [],
        "current_lora_list": [],
        "awaiting_prompt_input": False,
        "lora_page": 0,
        "intensity": None,
        "lora_sub_family": None,       # pvc sub-menu: "pvc"/"2d"/"3d"
        "preset_template_id": None,    # selected preset template
        "custom_preset_edit_slot": None,  # slot_id currently being edited via await_custom_preset_input
        "curated_selected": [],        # list of "cid:idx" strings; order = pick order; cap = CURATED_BANKS.max_selection
        "curated_current_cat": None,   # currently-browsing curated category id
        "curated_page": 0,             # page within current curated category
        "preset_return_to": None,      # None | "confirm" — where to go after apply/done
        "last_tag_result": "",         # most recent WD14 tagger output string
        "flow": None,                  # "t2i" | "i2i" | "vid" | "dt" | "tag" | None
        "ai_suggestion_id": None,      # selected AI suggestion (0-3)
        "ai_suggestions_cache": None,  # cached AI suggestions for current config
        # ── 词库选择 ──
        "library_selected_ids": [],    # list of selected prompt_library item IDs
        "library_category_id": None,   # current browsing category
        "library_page": 0,             # pagination within category
        # ── 双图迁移专用（dt_* 前缀，全部由 dual_transfer 模块管理） ──
        **dual_transfer.default_dt_fields(),
    }

def reset_state(user_id: int, chat_id: int):
    GEN_STATE[user_id] = _default_state(chat_id)
    save_state(user_id)

# ── Telegram helpers ────────────────────────────────────
def _tg_get(method, params=None, timeout=15):
    return _tg_client.call(method, params, read_timeout=timeout) or {}


def _tg_post_json(method, data, timeout=15):
    return _tg_client.call(method, data, read_timeout=timeout) or {}


def register_bot_commands():
    """Register the bot's left-side command menu. Idempotent — Telegram
    replaces the whole command list with each call, safe to call on every start."""
    cmds = [
        {"command": "start",  "description": "打开主菜单"},
        {"command": "help",   "description": "显示帮助"},
        {"command": "status", "description": "查看排队任务"},
        {"command": "cancel", "description": "取消排队任务"},
    ]
    return _tg_post_json("setMyCommands", {"commands": cmds})


def send_text(chat_id, text):
    return _tg_post_json("sendMessage", {"chat_id": chat_id, "text": text})


def send_photo(chat_id, file_path, caption=""):
    """Upload photo via httpx multipart."""
    import mimetypes
    fname = Path(file_path).name
    mime = mimetypes.guess_type(fname)[0] or "image/png"
    data_fields = {"chat_id": str(chat_id)}
    if caption:
        data_fields["caption"] = caption
    try:
        with open(file_path, "rb") as f:
            resp = _tg_client.upload(
                "sendPhoto",
                files={"photo": (fname, f, mime)},
                data=data_fields,
                read_timeout=30.0,
            )
        if resp.get("ok"):
            print(f"[send_photo] OK msg_id={resp['result']['message_id']}", flush=True)
        else:
            print(f"[send_photo] FAIL: {resp}", flush=True)
        return resp
    except Exception as e:
        print(f"[send_photo] error: {e}", flush=True)
        return {}


def send_video(chat_id, file_path, caption=""):
    """Upload video via httpx multipart."""
    fname = Path(file_path).name
    data_fields = {"chat_id": str(chat_id)}
    if caption:
        data_fields["caption"] = caption
    try:
        with open(file_path, "rb") as f:
            resp = _tg_client.upload(
                "sendVideo",
                files={"video": (fname, f, "video/mp4")},
                data=data_fields,
                read_timeout=60.0,
            )
        if resp.get("ok"):
            print(f"[send_video] OK msg_id={resp['result']['message_id']}", flush=True)
        else:
            print(f"[send_video] FAIL: {resp}", flush=True)
        return resp
    except Exception as e:
        print(f"[send_video] error: {e}", flush=True)
        return {}


def send_menu(chat_id, text: str, keyboard: list) -> dict:
    """发送带 Inline Keyboard 的消息，返回整个响应"""
    return _tg_post_json("sendMessage", {
        "chat_id":      chat_id,
        "text":         text,
        "reply_markup": {"inline_keyboard": keyboard},
    })


def edit_menu(chat_id, message_id: int, text: str, keyboard=None):
    """编辑已有菜单消息"""
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if keyboard is not None:
        data["reply_markup"] = {"inline_keyboard": keyboard}
    else:
        data["reply_markup"] = {"inline_keyboard": []}
    resp = _tg_post_json("editMessageText", data)
    # Telegram returns 400 "message is not modified" when content is identical.
    # Treat this as a no-op success so callers don't fall back to send_menu.
    if not resp.get("ok") and "not modified" in str(resp.get("description", "")).lower():
        return {"ok": True, "_not_modified": True}
    return resp


def answer_callback(callback_query_id: str, text: str = ""):
    return _tg_post_json("answerCallbackQuery",
                         {"callback_query_id": callback_query_id, "text": text})


def download_telegram_file(file_id) -> Path:
    """Download a Telegram file to media/input/, return local path."""
    info = _tg_get("getFile", {"file_id": file_id})
    file_path = info.get("result", {}).get("file_path")
    if not file_path:
        raise RuntimeError(f"Cannot get file_path for file_id={file_id}")
    ext = Path(file_path).suffix or ".jpg"
    local_name = f"tg_{uuid.uuid4().hex[:8]}{ext}"
    local_path = MEDIA_INPUT / local_name
    MEDIA_INPUT.mkdir(parents=True, exist_ok=True)
    data = _tg_client.download_file(file_path, read_timeout=20.0)
    if data is None:
        raise RuntimeError(f"Download failed for file_path={file_path}")
    local_path.write_bytes(data)
    print(f"[download] {file_id} → {local_path}", flush=True)
    return local_path


# ── Offset / pending persistence ────────────────────────
def load_offset():
    if OFFSET_FILE.exists():
        try:
            return json.loads(OFFSET_FILE.read_text()).get("offset", 0)
        except Exception:
            pass
    return 0


def save_offset(offset):
    OFFSET_FILE.write_text(json.dumps({"offset": offset}))


def load_pending():
    if PENDING_FILE.exists():
        try:
            return json.loads(PENDING_FILE.read_text())
        except Exception:
            pass
    return {}


def save_pending(pending):
    PENDING_FILE.write_text(json.dumps(pending, indent=2))


# ── Training mode state (kept for compat) ───────────────
def load_training() -> dict:
    if TRAINING_FILE.exists():
        try:
            return json.loads(TRAINING_FILE.read_text())
        except Exception:
            pass
    return {}

def save_training(training: dict):
    TRAINING_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRAINING_FILE.write_text(json.dumps(training, indent=2, ensure_ascii=False))

def get_training_style(chat_id: int):
    training = load_training()
    entry = training.get(str(chat_id))
    if not entry:
        return None
    if time.time() - entry.get("started_at", 0) > TRAINING_EXPIRE:
        training.pop(str(chat_id), None)
        save_training(training)
        return None
    return entry.get("style_name")

def set_training_style(chat_id: int, style_name: str):
    training = load_training()
    training[str(chat_id)] = {"style_name": style_name, "started_at": time.time()}
    save_training(training)

def clear_training_style(chat_id: int):
    training = load_training()
    training.pop(str(chat_id), None)
    save_training(training)


# ── ComfyUI helpers ──────────────────────────────────────
_comfyui_alive_cache = 0.0  # timestamp of last successful check

def comfyui_alive():
    global ACTIVE_COMFYUI, _comfyui_alive_cache
    # Cache: skip re-check if verified within last 30s
    if ACTIVE_COMFYUI and time.time() - _comfyui_alive_cache < 30:
        return True
    for base in ([ACTIVE_COMFYUI] if ACTIVE_COMFYUI else []) + COMFYUI_ENDPOINTS:
        if not base:
            continue
        try:
            with urllib.request.urlopen(base + "/system_stats", timeout=3) as r:
                if r.status == 200:
                    ACTIVE_COMFYUI = base
                    _comfyui_alive_cache = time.time()
                    return True
        except Exception:
            continue
    return False


def _comfyui_base():
    if ACTIVE_COMFYUI:
        return ACTIVE_COMFYUI
    if comfyui_alive():
        return ACTIVE_COMFYUI
    raise RuntimeError(f"ComfyUI offline: {COMFYUI_ENDPOINTS}")


def comfyui_get(path):
    try:
        base = _comfyui_base()
        with urllib.request.urlopen(base + path, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        if comfyui_alive():
            with urllib.request.urlopen(ACTIVE_COMFYUI + path, timeout=10) as r:
                return json.loads(r.read())
        raise


def _resize_image(image_path: Path, max_dim: int = 1024) -> Path:
    try:
        from PIL import Image as PILImage
        img = PILImage.open(image_path)
        w, h = img.size
        if max(w, h) <= max_dim:
            return image_path
        ratio = max_dim / max(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), PILImage.LANCZOS)
        out = image_path.parent / f"rs_{image_path.name}"
        img.save(out)
        print(f"[resize] {w}x{h} → {new_w}x{new_h}: {out.name}", flush=True)
        return out
    except Exception as e:
        print(f"[resize] skipped: {e}", flush=True)
        return image_path


# ── Prompt building ──────────────────────────────────────
def build_merged_prompt(state: dict, mode_prompt: str = "") -> tuple:
    """Returns (positive, negative) merged from mode + registry + user prompt.

    Final positive order:
        mode_prompt → family_default_prompt → model_default_prompt
        → lora_default_prompt(s) → user_prompt

    Original prompts from txt files (model/lora default_prompt) are never modified.
    mode_prompt is prepended as an additional layer.
    """
    reg = REG
    family = state.get("family", "")
    model_key = state.get("model_key", "")
    lora_keys = state.get("lora_keys", [])
    user_prompt = state.get("user_prompt", "")

    family_def = reg.get("family_defaults", {}).get(family, {})

    parts = []

    # 1. Mode prompt (quality / character-lock, never in original txt)
    if mode_prompt:
        parts.append(mode_prompt)

    # 2. Family default prompt (from registry)
    base = family_def.get("default_prompt", "")
    if base:
        parts.append(base)

    # 3. Model default prompt (from txt — untouched)
    if model_key and model_key in reg.get("models", {}):
        model_entry = reg["models"][model_key]
        m_prompt = model_entry.get("default_prompt", "")
        if m_prompt:
            parts.append(m_prompt)

    # 4. LoRA default prompts (from txt — untouched)
    for lk in lora_keys:
        if lk in reg.get("loras", {}):
            lora_entry = reg["loras"][lk]
            lp = lora_entry.get("default_prompt", "")
            if lp:
                parts.append(lp)

    # 5. Preset template prompt (from preset_prompt_templates.json)
    preset_id = state.get("preset_template_id")
    if preset_id:
        tpl = _find_preset_by_id(preset_id)
        if tpl and tpl.get("positive"):
            parts.append(tpl["positive"])

    # 6. AI suggestion prompt (from cached suggestion)
    ai_idx = state.get("ai_suggestion_id")
    ai_cache = state.get("ai_suggestions_cache")
    if ai_idx is not None and ai_cache and 0 <= ai_idx < len(ai_cache):
        ai_pos = ai_cache[ai_idx].get("positive", "")
        if ai_pos:
            parts.append(ai_pos)

    # 7. User prompt (typed in Telegram)
    if user_prompt:
        parts.append(user_prompt)

    # 8. Prompt library positive (selected items from prompt_library.json)
    lib_ids = state.get("library_selected_ids", [])
    if lib_ids:
        lib_id_set = set(lib_ids)
        for cat in PROMPT_LIBRARY.get("categories", []):
            for it in cat.get("items", []):
                if it["id"] in lib_id_set and it.get("positive"):
                    parts.append(it["positive"])

    # 9. Curated-bank selected tags (自选预设 — 14-分类 tag 勾选)
    curated_sel = state.get("curated_selected") or []
    if curated_sel:
        tags = _curated_resolve_selected(curated_sel)
        if tags:
            parts.append(", ".join(tags))

    positive = ", ".join(p.strip().strip(",") for p in parts if p.strip())

    # Negative
    neg_parts = []
    family_neg = family_def.get("default_negative_prompt", "")
    if family_neg:
        neg_parts.append(family_neg)

    if model_key and model_key in reg.get("models", {}):
        m_neg = reg["models"][model_key].get("default_negative_prompt", "")
        if m_neg:
            neg_parts.append(m_neg)

    for lk in lora_keys:
        if lk in reg.get("loras", {}):
            ln = reg["loras"][lk].get("default_negative_prompt", "")
            if ln:
                neg_parts.append(ln)

    # Preset template negative
    if preset_id:
        tpl = _find_preset_by_id(preset_id)
        if tpl and tpl.get("negative"):
            neg_parts.append(tpl["negative"])

    # AI suggestion negative
    if ai_idx is not None and ai_cache and 0 <= ai_idx < len(ai_cache):
        ai_neg = ai_cache[ai_idx].get("negative", "")
        if ai_neg:
            neg_parts.append(ai_neg)

    # 9. Prompt library negative (selected items)
    if lib_ids:
        lib_id_set = set(lib_ids)
        for cat in PROMPT_LIBRARY.get("categories", []):
            for it in cat.get("items", []):
                if it["id"] in lib_id_set and it.get("negative"):
                    neg_parts.append(it["negative"])

    seen = set()
    neg_terms = []
    for part in neg_parts:
        for term in part.split(","):
            t = term.strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                neg_terms.append(t)
    negative = ", ".join(neg_terms)

    return positive, negative


# ── AI suggestion generator ─────────────────────────────

_AI_NORMAL = {
    "pvc": {
        "conservative": {
            "title": "🛡 保留角色·手办精修",
            "positive": "masterpiece, best quality, same character, same face, same hair, same outfit, pvc figure, high quality sculpt, sharp detail, studio lighting, clean background, product photography, glossy finish, precise proportions, faithful recreation, beautiful detailed eyes, accurate colors, smooth surface, professional rendering, display quality, collector grade, absurdres, highres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, different character, face change, style change, distorted",
        },
        "stylistic": {
            "title": "🎨 风格强化·极致手办",
            "positive": "masterpiece, best quality, exquisite pvc figure, dramatic studio lighting, gradient_background, iridescent surface, metallic accents, dynamic pose, action figure quality, premium finish, ray tracing, subsurface scattering, pearlescent material, detailed base, artistic composition, dramatic shadows, color contrast, magazine cover quality, gallery display, absurdres, highres, extremely detailed CG unity 8k wallpaper",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, flat lighting, dull, plain background, static pose, cheap quality",
        },
        "clothing": {
            "title": "👗 服装细节·华丽着装",
            "positive": "masterpiece, best quality, detailed clothing, intricate fabric texture, lace, ribbon, layered outfit, flowing dress, pleated_skirt, ornate accessories, jewelry, hair_ornament, thighhighs, shoe details, clothing wrinkles, fabric sheen, embroidery, frills, corset details, costume design, fashion illustration quality, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, simple clothing, flat texture, shapeless, generic outfit, costume error, clipping",
        },
        "cinematic": {
            "title": "🎬 光影构图·电影镜头",
            "positive": "masterpiece, best quality, cinematic composition, dramatic rim lighting, volumetric light, depth of field, bokeh background, golden ratio, low angle shot, backlighting, spotlight, atmospheric fog, lens flare, reflective floor, chiaroscuro, professional photography, editorial style, dusk, moonlight, absurdres, highres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, flat lighting, centered composition, boring angle, no depth, plain background, snapshot",
        },
    },
    "2d": {
        "conservative": {
            "title": "🛡 保留角色·忠实还原",
            "positive": "masterpiece, best quality, same character, same face, same hair color, same hairstyle, consistent art style, accurate proportions, detailed lineart, clean coloring, beautiful detailed eyes, character reference match, canonical outfit, precise features, matching expression, correct accessories, identity preserved, high fidelity, absurdres, highres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, different character, off-model, wrong colors, style inconsistency",
        },
        "stylistic": {
            "title": "🎨 画风极致·二次元顶级",
            "positive": "masterpiece, best quality, exceptional anime illustration, vibrant colors, dynamic lighting, detailed shading, cel shading, beautiful lineart, pixiv top ranking, trending illustration, complementary colors, light particles, chromatic aberration, detailed hair strands, sparkling eyes, rim light glow, artistic composition, visual impact, game_cg, absurdres, extremely detailed CG unity 8k wallpaper",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, amateur art, flat coloring, dull colors, rough lines, muddy colors",
        },
        "clothing": {
            "title": "👗 精致衣装·二次元时尚",
            "positive": "masterpiece, best quality, detailed anime clothing, intricate costume design, layered outfit, flowing fabric, lace, ribbon, ornate accessories, serafuku, japanese_clothes, kimono, pleated_skirt, thighhighs, elbow gloves, boots, hair_ornament, earrings, necklace, frills, gothic_lolita, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, simple outfit, plain clothing, flat fabric, generic uniform, costume error, shapeless clothing",
        },
        "cinematic": {
            "title": "🎬 构图光影·动画电影",
            "positive": "masterpiece, best quality, anime movie quality, Makoto Shinkai style lighting, dramatic sky, volumetric clouds, golden hour, backlighting, God rays, lens flare, atmospheric depth, panoramic composition, weather effects, wind effect, falling petals, scattered light, reflections in water, dramatic perspective, scenery, dusk, stars, absurdres, highres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, flat background, no atmosphere, static composition, boring sky, generic background, no depth",
        },
    },
    "3d": {
        "conservative": {
            "title": "🛡 保留角色·写实精修",
            "positive": "masterpiece, best quality, same person, same face, same features, same hair, photorealistic, consistent identity, detailed skin texture, accurate proportions, natural pose, realistic lighting, professional portrait, identity preservation, natural expression, DSLR quality, sharp focus, true to reference, high fidelity rendering, absurdres, highres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, different person, face swap, cartoon, anime, uncanny valley, plastic skin",
        },
        "stylistic": {
            "title": "🎨 极致写实·大片质感",
            "positive": "masterpiece, best quality, hyperrealistic, 8K resolution, octane render, ray tracing, global illumination, subsurface scattering, photorealistic skin, detailed pores, volumetric lighting, HDR photography, professional color grading, dramatic composition, fashion editorial, studio strobe lighting, beauty dish, specular highlights, premium render, absurdres, extremely detailed CG unity 8k wallpaper",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, cartoon, anime, drawing, flat, airbrushed, uncanny, cheap quality",
        },
        "clothing": {
            "title": "👗 服装质感·写实穿搭",
            "positive": "masterpiece, best quality, detailed clothing texture, realistic fabric, silk sheen, leather texture, lace fabric, velvet material, chiffon transparency, clothing wrinkles, natural draping, fashion photography, outfit coordination, jewelry, high heels, belt, necklace, earrings, high fashion quality, absurdres, highres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, flat texture, generic clothing, shapeless, costume, floating clothes, clipping error",
        },
        "cinematic": {
            "title": "🎬 电影镜头·光影大师",
            "positive": "masterpiece, best quality, cinematic photography, film lighting, anamorphic bokeh, depth of field, dramatic shadows, rim lighting, colored gels, atmospheric haze, wet floor reflections, neon signs, city lights, golden hour warmth, blue hour mood, backlit silhouette, lens flare, professional cinematography, night, rain, absurdres, highres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, flat lighting, no depth, boring angle, plain background, snapshot quality, no atmosphere",
        },
    },
}

_AI_R18 = {
    "pvc": {
        "sensual_pose": {
            "title": "🔥 色气体位·挑逗姿势",
            "positive": "masterpiece, best quality, nsfw, sensual pose, arched_back, spread legs, top-down_bottom-up, bent_over, on_stomach, straddling, seductive smile, naughty_face, looking at viewer, large breasts, nipples, areolae, cleavage, navel, bare_shoulders, thigh gap, cameltoe, sweat, light blush, pvc figure, glossy surface, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, standing straight, boring pose, fully clothed",
        },
        "lingerie_fetish": {
            "title": "👙 情趣内衣·恋物诱惑",
            "positive": "masterpiece, best quality, nsfw, sexy lingerie, lace, transparent underwear, garter belt, garter straps, black thighhighs, fishnet thighhighs, string_panties, thong, no bra, bra, side-tie_panties, ribbon_choker, collar, leash, high heels, breasts, nipples visible through fabric, cameltoe, naughty_face, pvc figure, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, casual clothing, full coverage, plain underwear",
        },
        "explicit_act": {
            "title": "💦 直球行为·显式场景",
            "positive": "masterpiece, best quality, nsfw, sex, nude, pussy, breasts, nipples, cum, cum_inside, ejaculation, penetration, insertion, missionary, cowgirl_position, doggystyle, girl_on_top, ahegao, saliva, tongue out, spread legs, pussy_juice, female_ejaculation, sweat, endured_face, pvc figure, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, clothed, no nudity, mild",
        },
        "bondage_play": {
            "title": "⛓ 束缚调教·支配臣服",
            "positive": "masterpiece, best quality, nsfw, shibari, bondage, bdsm, rope, bound_wrists, bound_arms, crotch_rope, spreader_bar, suspension, hogtie, ballgag, ring_gag, blindfold, collar, leash, nipple_torture, nipple_pull, slave, spanked, wooden_horse, anal_beads, egg_vibrator, vibrator, endured_face, ahegao, tears, nude, breasts, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, consensual vanilla, happy scene, casual",
        },
    },
    "2d": {
        "sensual_pose": {
            "title": "🔥 色气体位·动漫诱惑",
            "positive": "masterpiece, best quality, nsfw, sensual pose, arched_back, spread legs, top-down_bottom-up, bent_over, straddling, all_fours, seductive smile, naughty_face, ahegao, looking at viewer, beautiful detailed eyes, large breasts, nipples, areolae, navel, bare_shoulders, thigh gap, cameltoe, light blush, shiny wet skin, sweat, anime style, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, standing straight, boring pose, fully clothed",
        },
        "lingerie_fetish": {
            "title": "👙 情趣衣装·二次元恋物",
            "positive": "masterpiece, best quality, nsfw, sexy lingerie, transparent underwear, lace, serafuku, school uniform, skirt lift, shirt lift, no_panties, panties, striped_panties, garter belt, black thighhighs, fishnet pantyhose, bikini, sling bikini, maid, naked ribbon, no bra, breasts, nipples, cleavage, off_shoulder, bare_shoulders, naughty_face, blush, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, full coverage, casual clothing, armor",
        },
        "explicit_act": {
            "title": "💦 直球行为·显式场景",
            "positive": "masterpiece, best quality, nsfw, sex, nude, pussy, breasts, nipples, oral, fellatio, deepthroat, paizuri, cum, cum_inside, cum_on_breast, ejaculation, penetration, fingering, missionary, cowgirl_position, doggystyle, 69, spitroast, ahegao, saliva, tongue out, pussy_juice, female_ejaculation, tears, endured_face, beautiful detailed eyes, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, clothed, no nudity, mild",
        },
        "bondage_play": {
            "title": "⛓ 束缚调教·二次元SM",
            "positive": "masterpiece, best quality, nsfw, shibari, bondage, bdsm, rope, bound_wrists, bound_arms, crotch_rope, suspension, frogtie, ballgag, panty_gag, blindfold, collar, leash, nipple_pull, nipple_piercing, slave, humiliation, body_writing, egg_vibrator, vibrator, anal_beads, endured_face, ahegao, tears, blush, nude, breasts, beautiful detailed eyes, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, happy vanilla, casual, fully clothed",
        },
    },
    "3d": {
        "sensual_pose": {
            "title": "🔥 色气体位·写实挑逗",
            "positive": "masterpiece, best quality, nsfw, sensual pose, arched_back, spread legs, bent_over, straddling, on_stomach, seductive smile, naughty_face, looking at viewer, large breasts, nipples, areolae, navel, bare_shoulders, thigh gap, cameltoe, detailed skin texture, sweat, light blush, oiled skin, photorealistic, professional glamour photography, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, cartoon, anime, standing straight, boring pose, fully clothed",
        },
        "lingerie_fetish": {
            "title": "👙 情趣内衣·写实恋物",
            "positive": "masterpiece, best quality, nsfw, sexy lingerie, lace, transparent underwear, garter belt, garter straps, black thighhighs, fishnet pantyhose, string_panties, thong, bustier, chemise, no bra, high heels, breasts, nipples visible through fabric, cameltoe, naughty_face, detailed skin texture, photorealistic, mature female, oiled skin, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, cartoon, anime, casual clothing, full coverage",
        },
        "explicit_act": {
            "title": "💦 直球行为·写实场景",
            "positive": "masterpiece, best quality, nsfw, sex, nude, pussy, breasts, nipples, oral, fellatio, paizuri, handjob, cum, cum_inside, ejaculation, penetration, missionary, cowgirl_position, doggystyle, girl_on_top, ahegao, saliva, pussy_juice, female_ejaculation, detailed skin texture, sweat, photorealistic, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, cartoon, anime, clothed, no nudity",
        },
        "bondage_play": {
            "title": "⛓ 束缚调教·写实SM",
            "positive": "masterpiece, best quality, nsfw, shibari, bondage, bdsm, rope, bound_wrists, bound_arms, crotch_rope, spreader_bar, suspension, hogtie, ballgag, ring_gag, blindfold, collar, leash, nipple_torture, slave, spanked, anal_beads, egg_vibrator, hitachi_magic_wand, endured_face, tears, nude, breasts, detailed skin texture, photorealistic, absurdres",
            "negative": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, censored, mosaic, cartoon, anime, happy vanilla, casual",
        },
    },
}

def generate_ai_suggestions(state: dict, category: str = "normal") -> list:
    """Generate 4 context-aware prompt suggestions based on current state and category."""
    family = state.get("family", "pvc")
    if category == "r18":
        base = _AI_R18.get(family, _AI_R18["pvc"])
        keys = ("sensual_pose", "lingerie_fetish", "explicit_act", "bondage_play")
    else:
        base = _AI_NORMAL.get(family, _AI_NORMAL["pvc"])
        keys = ("conservative", "stylistic", "clothing", "cinematic")

    suggestions = []
    for key in keys:
        sug = dict(base[key])
        suggestions.append(sug)

    return suggestions


# ── Menu keyboard builders ───────────────────────────────

def build_mode_keyboard() -> list:
    return [
        [{"text": "📝 t2i 文生图", "callback_data": "m:t2i"}],
        [{"text": "🖼 i2i 图生图", "callback_data": "m:i2i"}],
        [{"text": "🔀 双图合并",   "callback_data": "m:dt"}],
        [{"text": "🎬 生成视频",   "callback_data": "m:vid"}],
        [{"text": "🔍 图转提示词", "callback_data": "m:tag"}],
    ]


def build_post_photo_keyboard() -> list:
    """After user sends a raw photo, only i2i and video can consume it."""
    return [
        [{"text": "🖼 i2i 图生图", "callback_data": "m:i2i"}],
        [{"text": "🎬 生成视频",   "callback_data": "m:vid"}],
    ]


def build_family_keyboard() -> list:
    return [
        [{"text": "🧸 手办",   "callback_data": "f:pvc"},
         {"text": "🌸 2D动漫", "callback_data": "f:2d"},
         {"text": "🌐 3D风格", "callback_data": "f:3d"}],
        [{"text": "← 返回",    "callback_data": "chm:"}],
    ]


def build_model_keyboard(family: str) -> list:
    models = get_enabled_models(family)
    rows = []
    row = []
    for idx, (key, entry) in enumerate(models):
        label = entry.get("display_name_cn", key.split("/")[-1])
        btn = {"text": label, "callback_data": f"mdl:{idx}"}
        if len(models) <= 3:
            row.append(btn)
        else:
            rows.append([btn])
    if row:
        rows.append(row)
    rows.append([{"text": "← 返回", "callback_data": "f:" + family}])
    rows.append([{"text": "🧹 重置本轮选择", "callback_data": "rst:"}])
    return rows


def build_lora_keyboard(state: dict) -> list:
    family = state["family"]
    mode = state["mode"]
    selected = state.get("lora_keys", [])
    page = state.get("lora_page", 0)
    lora_list = state.get("current_lora_list", [])

    total = len(lora_list)
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_loras = lora_list[start:end]

    rows = []
    for idx_in_page, lk in enumerate(page_loras):
        abs_idx = start + idx_in_page
        entry = REG.get("loras", {}).get(lk, {})
        display = entry.get("display_name_cn", lk.split("/")[-1])
        if lk in selected:
            label = f"✅ {display}"
        else:
            label = display
        rows.append([{"text": label, "callback_data": f"l:{abs_idx}"}])

    # Pagination row
    nav_row = []
    if page > 0:
        nav_row.append({"text": "◀ 上页", "callback_data": f"lp:{page-1}"})
    if end < total:
        nav_row.append({"text": "▶ 下页", "callback_data": f"lp:{page+1}"})
    if nav_row:
        rows.append(nav_row)

    n_sel = len(selected)
    rows.append([
        {"text": f"✅ 完成选择（{n_sel}个）", "callback_data": "ld:"},
        {"text": "🗑 清空",                  "callback_data": "lc:"},
    ])
    # PVC sub-family mode: back to category menu instead of model
    if state.get("lora_sub_family"):
        rows.append([{"text": "← 返回分类", "callback_data": "lbcat:"}])
    else:
        rows.append([{"text": "← 返回上一级", "callback_data": "lb:"}])
    rows.append([{"text": "🧹 重置本轮选择", "callback_data": "rst:"}])
    return rows


def build_lora_category_keyboard() -> list:
    """Build LoRA sub-family category keyboard for pvc family."""
    return [
        [{"text": "🧸 手办LoRA", "callback_data": "lcat:pvc"}],
        [{"text": "🌸 2D LoRA",  "callback_data": "lcat:2d"}],
        [{"text": "🌐 3D LoRA",  "callback_data": "lcat:3d"}],
        [{"text": f"✅ 完成选择", "callback_data": "ld:"}],
        [{"text": "← 返回上一级", "callback_data": "lb:"}],
    ]


def build_preset_category_keyboard() -> list:
    """Build preset category picker: normal vs r18."""
    return [
        [{"text": "📝 正常预设", "callback_data": "ptcat:normal"}],
        [{"text": "🔞 R18预设",  "callback_data": "ptcat:r18"}],
        [{"text": "跳过", "callback_data": "ptsk:"}],
        [{"text": "← 返回", "callback_data": "ptbk:"}],
    ]


def build_preset_template_keyboard(family: str, category: str) -> list:
    """Build preset prompt template keyboard filtered by family and category."""
    rows = []
    for tpl in PRESET_TEMPLATES:
        if family in tpl.get("families", []) and tpl.get("category") == category:
            rows.append([{"text": tpl["title"], "callback_data": f"pt:{tpl['id']}"}])
    rows.append([{"text": "← 返回分类", "callback_data": "ptml:"}])
    return rows


def build_ai_category_keyboard() -> list:
    """Build AI suggestion category picker: normal vs r18."""
    return [
        [{"text": "🤖 正常AI推荐", "callback_data": "aicat:normal"}],
        [{"text": "🔞 R18 AI推荐", "callback_data": "aicat:r18"}],
        [{"text": "跳过", "callback_data": "aisk:"}],
        [{"text": "← 返回", "callback_data": "aibk:"}],
    ]


def build_ai_suggestion_keyboard(suggestions: list) -> list:
    """Build AI suggestion keyboard from 4 generated suggestions."""
    rows = []
    for i, sug in enumerate(suggestions):
        rows.append([{"text": sug["title"], "callback_data": f"ai:{i}"}])
    rows.append([{"text": "← 返回分类", "callback_data": "aiml:"}])
    return rows


# ── Prompt library keyboards ────────────────────────────
LIBRARY_PAGE_SIZE = 6

def build_library_category_keyboard(state: dict) -> list:
    """Build prompt library category list."""
    sel_count = len(state.get("library_selected_ids", []))
    rows = []
    for cat in PROMPT_LIBRARY.get("categories", []):
        # Count how many items from this category are selected
        cat_ids = {it["id"] for it in cat.get("items", [])}
        cat_sel = len(cat_ids & set(state.get("library_selected_ids", [])))
        label = cat["title"]
        if cat_sel:
            label += f" ({cat_sel}✓)"
        rows.append([{"text": label, "callback_data": f"plcat:{cat['id']}"}])
    # Bottom row
    if sel_count:
        rows.append([{"text": f"✅ 完成选择（已选{sel_count}项）", "callback_data": "pldone:"}])
        rows.append([{"text": "🗑 清空词库选择", "callback_data": "plclr:"}])
    else:
        rows.append([{"text": "跳过", "callback_data": "plsk:"}])
    rows.append([{"text": "← 返回", "callback_data": "plbk:"}])
    return rows


def build_library_items_keyboard(state: dict, category_id: str) -> list:
    """Build paginated item list for a library category with multi-select."""
    cat = next((c for c in PROMPT_LIBRARY.get("categories", []) if c["id"] == category_id), None)
    if not cat:
        return [[{"text": "← 返回分类", "callback_data": "plml:"}]]
    items = cat.get("items", [])
    page = state.get("library_page", 0)
    total_pages = max(1, (len(items) + LIBRARY_PAGE_SIZE - 1) // LIBRARY_PAGE_SIZE)
    page = min(page, total_pages - 1)
    start = page * LIBRARY_PAGE_SIZE
    page_items = items[start:start + LIBRARY_PAGE_SIZE]
    selected = set(state.get("library_selected_ids", []))

    rows = []
    for it in page_items:
        check = "☑️ " if it["id"] in selected else ""
        rows.append([{"text": f"{check}{it['label']}", "callback_data": f"pli:{it['id']}"}])

    # Pagination
    nav = []
    if page > 0:
        nav.append({"text": "◀ 上页", "callback_data": f"plpg:{page - 1}"})
    nav.append({"text": f"{page + 1}/{total_pages}", "callback_data": "noop:"})
    if page < total_pages - 1:
        nav.append({"text": "下页 ▶", "callback_data": f"plpg:{page + 1}"})
    if nav:
        rows.append(nav)

    sel_count = len(selected)
    if sel_count:
        rows.append([{"text": f"✅ 完成（已选{sel_count}项）", "callback_data": "pldone:"}])
    rows.append([{"text": "← 返回分类", "callback_data": "plml:"}])
    return rows


def build_confirm_keyboard(state: dict = None) -> list:
    rows = [
        [{"text": "🚀 开始生成",   "callback_data": "gen:"}],
        [{"text": "🔄 换底模",     "callback_data": "chm:"},
         {"text": "🎭 换LoRA",     "callback_data": "chl:"}],
        [{"text": "✏️ 修改提示词", "callback_data": "ap:"}],
        [{"text": "📝 预设模板",   "callback_data": "ptml:"},
         {"text": "🤖 AI推荐",    "callback_data": "aiml:"}],
        [{"text": "📚 词库选择",   "callback_data": "plml:"}],
    ]
    # Show current selections if any
    if state:
        indicators = []
        if state.get("preset_template_id"):
            tpl = _find_preset_by_id(state["preset_template_id"])
            if tpl:
                indicators.append(f"📝{tpl['title']}")
        if state.get("ai_suggestion_id") is not None and state.get("ai_suggestions_cache"):
            idx = state["ai_suggestion_id"]
            cache = state["ai_suggestions_cache"]
            if 0 <= idx < len(cache):
                indicators.append(f"🤖{cache[idx]['title']}")
        lib_count = len(state.get("library_selected_ids", []))
        if lib_count:
            indicators.append(f"📚词库{lib_count}项")
        if indicators:
            clear_row = [{"text": f"🗑 清除增强（{'｜'.join(indicators)}）", "callback_data": "clrp:"}]
            rows.append(clear_row)
    return rows


def build_intensity_keyboard() -> list:
    return [
        [{"text": "🌿 轻度（角色保留优先）", "callback_data": "int:light"}],
        [{"text": "⚖️ 中度（平衡·推荐）",   "callback_data": "int:medium"}],
        [{"text": "🔥 重度（风格更强）",     "callback_data": "int:heavy"}],
        [{"text": "← 返回选LoRA",           "callback_data": "chl:"}],
    ]


def build_result_keyboard(has_source_image: bool = False, is_image_mode: bool = True) -> list:
    row1 = [{"text": "🎲 再来一张", "callback_data": "re:"},
            {"text": "✏️ 加提示词", "callback_data": "ap:"}]
    if is_image_mode:
        row1.append({"text": "🔢 批量再来", "callback_data": "qty:"})
    rows = [
        row1,
        [{"text": "🎭 换LoRA",   "callback_data": "chl:"},
         {"text": "🔄 换底模",   "callback_data": "chm:"}],
    ]
    if has_source_image:
        rows.append([{"text": "🎚 换强度", "callback_data": "chi:"},
                     {"text": "🧹 清空",   "callback_data": "rst:"}])
    else:
        rows.append([{"text": "🧹 清空", "callback_data": "rst:"}])
    return rows


# ── Screen text builders ─────────────────────────────────

def mode_text(has_source_image: bool = False) -> str:
    if has_source_image:
        return "选择操作：\n\n已上传原图，可进入 i2i 或生视频"
    return "选择操作："


def family_text() -> str:
    return "选择风格大类："


def model_text(state: dict) -> str:
    family = state["family"]
    family_cn = FAMILY_CN.get(family, family)
    models = get_enabled_models(family)
    return f"选择底模 [{family_cn}]：\n共 {len(models)} 个可用底模"


def lora_text(state: dict) -> str:
    family = state["family"]
    sub = state.get("lora_sub_family")
    if sub:
        sub_cn = FAMILY_CN.get(sub, sub)
        label = f"手办·{sub_cn} LoRA"
    else:
        label = FAMILY_CN.get(family, family)
    n = len(state.get("lora_keys", []))
    return f"选择 LoRA [{label}]（已选 {n}/8）："


def confirm_text(state: dict) -> str:
    mode_label = "图片" if state["mode"] == "image" else "视频"
    family_cn = FAMILY_CN.get(state["family"], state["family"])

    model_key = state.get("model_key", "")
    if state["mode"] == "video":
        model_label = "WAN 视频模型（固定）"
    elif model_key and model_key in REG.get("models", {}):
        model_label = REG["models"][model_key].get("display_name_cn", model_key.split("/")[-1])
    else:
        model_label = "（未选择）"

    lora_keys = state.get("lora_keys", [])
    if lora_keys:
        lora_names = []
        for lk in lora_keys:
            entry = REG.get("loras", {}).get(lk, {})
            lora_names.append(entry.get("display_name_cn", lk.split("/")[-1]))
        lora_label = "、".join(lora_names)
    else:
        lora_label = "未选择"

    prompt_label = "已填写" if state.get("user_prompt", "").strip() else "未填写"

    # LoRA: append count when multiple
    if lora_keys and len(lora_keys) > 1:
        lora_label += f"（{len(lora_keys)}个）"

    lines = [
        "📋 确认生成\n",
        f"{mode_label}｜{family_cn}",
        f"底模：{model_label}",
        f"LoRA：{lora_label}",
    ]

    if state.get("source_image_path"):
        intensity = state.get("intensity", "medium")
        intensity_short = {"light": "轻度", "medium": "中度", "heavy": "重度"}.get(intensity, "中度")
        lines.append(f"原图：已上传")
        lines.append(f"强度：{intensity_short}")

    lines.append(f"提示词：{prompt_label}")

    # Preset template indicator
    tpl_id = state.get("preset_template_id")
    if tpl_id:
        tpl = _find_preset_by_id(tpl_id)
        if tpl:
            lines.append(f"预设模板：{tpl['title']}")
    # AI suggestion indicator
    ai_idx = state.get("ai_suggestion_id")
    ai_cache = state.get("ai_suggestions_cache")
    if ai_idx is not None and ai_cache and 0 <= ai_idx < len(ai_cache):
        lines.append(f"AI推荐：{ai_cache[ai_idx]['title']}")

    # Prompt library indicator
    lib_ids = state.get("library_selected_ids", [])
    if lib_ids:
        # Collect selected item labels
        lib_labels = []
        lib_id_set = set(lib_ids)
        for cat in PROMPT_LIBRARY.get("categories", []):
            for it in cat.get("items", []):
                if it["id"] in lib_id_set:
                    lib_labels.append(it["label"])
        if lib_labels:
            preview = "、".join(lib_labels[:5])
            if len(lib_labels) > 5:
                preview += f"…等{len(lib_labels)}项"
            lines.append(f"词库：{preview}")

    return "\n".join(lines)


# ── Flow helpers ─────────────────────────────────────────

def show_mode_menu(user_id: int, state: dict, edit_msg_id=None):
    chat_id = state["chat_id"]
    state["step"] = "select_mode"
    save_state(user_id)
    has_img = bool(state.get("source_image_path"))
    kb = build_mode_keyboard()
    text = mode_text(has_img)
    if edit_msg_id:
        resp = edit_menu(chat_id, edit_msg_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = edit_msg_id
        else:
            # edit failed (stale msg id / foreign sender / too old): fall back to send_menu
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_intensity_menu(user_id: int, state: dict):
    chat_id = state["chat_id"]
    state["step"] = "select_intensity"
    save_state(user_id)
    text = "选择保留强度：\n\n🌿 轻度 → 最大保留角色，风格迁移弱\n⚖️ 中度 → 平衡（推荐）\n🔥 重度 → 风格介入更强，角色可能微漂"
    kb = build_intensity_keyboard()
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_family_menu(user_id: int, state: dict):
    chat_id = state["chat_id"]
    state["step"] = "select_family"
    save_state(user_id)
    kb = build_family_keyboard()
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, family_text(), kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, family_text(), kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, family_text(), kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_model_menu(user_id: int, state: dict):
    chat_id = state["chat_id"]
    family = state["family"]
    models = get_enabled_models(family)
    state["current_model_list"] = [k for k, _ in models]
    state["step"] = "select_model"
    save_state(user_id)

    if not models:
        msg_id = state.get("last_menu_msg_id")
        text = f"❌ 当前 {FAMILY_CN.get(family, family)} 没有可用底模"
        kb = [[{"text": "← 返回", "callback_data": f"f:{family}"}]]
        if msg_id:
            edit_menu(chat_id, msg_id, text, kb)
        else:
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
        save_state(user_id)
        return

    kb = build_model_keyboard(family)
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, model_text(state), kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, model_text(state), kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, model_text(state), kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_lora_category_menu(user_id: int, state: dict):
    """Show LoRA sub-category menu (手办/2D/3D). Reachable from any
    base-model family — LoRA banks are decoupled from the base family."""
    chat_id = state["chat_id"]
    state["step"] = "select_lora_category"
    state["lora_sub_family"] = None
    save_state(user_id)

    n = len(state.get("lora_keys", []))
    fam_cn = FAMILY_CN.get(state.get("family", ""), state.get("family", ""))
    text = f"选择 LoRA 分类 [底模:{fam_cn}]（已选 {n}/8）："
    kb = build_lora_category_keyboard()
    # Update count on done button
    kb[3] = [{"text": f"✅ 完成选择（{n}个）", "callback_data": "ld:"}]
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_lora_menu(user_id: int, state: dict):
    chat_id = state["chat_id"]
    family = state["family"]
    mode = state["mode"]

    # All families: show LoRA sub-category menu first (sub_family: pvc/2d/3d)
    # so user can mix any LoRA bank regardless of base-model family.
    if not state.get("lora_sub_family"):
        show_lora_category_menu(user_id, state)
        return

    # Load loras from sub_family if set, otherwise from family
    lora_family = state.get("lora_sub_family") or family
    loras = get_enabled_loras(lora_family, mode)
    state["current_lora_list"] = [k for k, _ in loras]
    state["step"] = "select_lora"
    if "lora_page" not in state:
        state["lora_page"] = 0
    save_state(user_id)

    if not loras:
        if mode == "video":
            text = f"此 family 暂无视频 LoRA，可跳过直接生成"
        else:
            text = "暂无可用 LoRA，可直接跳过"
        kb = [
            [{"text": "跳过，直接生成", "callback_data": "ld:"}],
            [{"text": "← 返回",           "callback_data": "lb:"}],
        ]
        msg_id = state.get("last_menu_msg_id")
        if msg_id:
            resp = edit_menu(chat_id, msg_id, text, kb)
            if not resp.get("ok"):
                resp = send_menu(chat_id, text, kb)
                if resp.get("ok"):
                    state["last_menu_msg_id"] = resp["result"]["message_id"]
        else:
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
        save_state(user_id)
        return

    kb = build_lora_keyboard(state)
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, lora_text(state), kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, lora_text(state), kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, lora_text(state), kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_confirm_menu(user_id: int, state: dict):
    chat_id = state["chat_id"]
    state["step"] = "confirm"
    save_state(user_id)
    kb = build_confirm_keyboard(state)
    msg_id = state.get("last_menu_msg_id")
    text = confirm_text(state)
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_t2i_preset_category(user_id: int, state: dict):
    """t2i 入口第一步：选预设分类 (normal / r18)。
    不走现有的 show_preset_template_menu，因为那是 confirm 菜单里可选项；
    这里是强制入口（t2i 必须先选一个预设才能进 family/model）。
    """
    chat_id = state["chat_id"]
    state["step"] = "t2i_preset_category"
    save_state(user_id)
    kb = [
        [{"text": "🛠 自定义预设", "callback_data": "t2ic:custom"}],
        [{"text": "📝 正常预设",   "callback_data": "t2ic:normal"}],
        [{"text": "🔞 R18预设",    "callback_data": "t2ic:r18"}],
        [{"text": "← 返回主菜单",  "callback_data": "chm:"}],
    ]
    text = "📝 t2i 文生图\n\n选择预设 prompt 分类："
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_t2i_preset_list(user_id: int, state: dict, category: str):
    """t2i 入口第二步：在选定分类下列出全部 preset（不按 family 过滤，
    因为此时还没选 family）。选中后进 family_menu。"""
    chat_id = state["chat_id"]
    state["step"] = "t2i_preset_select"
    save_state(user_id)
    rows = []
    for tpl in PRESET_TEMPLATES:
        if tpl.get("category") == category:
            rows.append([{"text": tpl["title"], "callback_data": f"t2ip:{tpl['id']}"}])
    rows.append([{"text": "← 返回分类", "callback_data": "m:t2i"}])
    rows.append([{"text": "← 返回主菜单", "callback_data": "chm:"}])
    cat_label = "正常" if category == "normal" else "R18"
    text = f"📝 t2i / {cat_label} 预设\n\n选择一个预设 prompt："
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, rows)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, rows)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, rows)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def _goto_after_preset_apply(user_id: int, state: dict):
    """After a preset (normal/r18/custom/curated) has been applied, jump to
    either the family menu (fresh t2i flow) or the confirm menu (append-prompt
    flow invoked by 'ap:' after a generation)."""
    where = state.get("preset_return_to")
    if where == "confirm":
        state["preset_return_to"] = None
        save_state(user_id)
        show_confirm_menu(user_id, state)
    else:
        show_family_menu(user_id, state)


def show_t2i_custom_menu(user_id: int, state: dict):
    """t2i / 自定义预设子菜单：套用 / 修改 / 自选。"""
    chat_id = state["chat_id"]
    state["step"] = "t2i_preset_custom"
    save_state(user_id)
    sel_n = len(state.get("curated_selected") or [])
    apply_row = "✨ 套用自定义预设"
    edit_row  = "✏️ 修改自定义预设"
    curated_row = f"🎛 自选预设（已选 {sel_n}）" if sel_n else "🎛 自选预设"
    kb = [
        [{"text": apply_row,   "callback_data": "t2icu:apply"}],
        [{"text": edit_row,    "callback_data": "t2icu:edit"}],
        [{"text": curated_row, "callback_data": "t2icu:curated"}],
        [{"text": "← 返回分类", "callback_data": "m:t2i"}],
    ]
    text = "🛠 自定义预设\n\n选择操作："
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_t2i_curated_categories(user_id: int, state: dict):
    """自选预设：14 分类入口。"""
    chat_id = state["chat_id"]
    state["step"] = "t2i_curated_categories"
    state["curated_current_cat"] = None
    save_state(user_id)
    cats = CURATED_BANKS.get("categories", [])
    max_sel = CURATED_BANKS.get("max_selection", CURATED_MAX_SELECTION_FALLBACK)
    selected = state.get("curated_selected") or []
    # Count per-category selections for display hint.
    per_cat = {}
    for key in selected:
        if ":" in key:
            cid = key.split(":", 1)[0]
            per_cat[cid] = per_cat.get(cid, 0) + 1
    rows = []
    for c in cats:
        n = per_cat.get(c["id"], 0)
        label = f"{c['cn_label']} ({n})" if n else c["cn_label"]
        rows.append([{"text": label, "callback_data": f"tcrcat:{c['id']}"}])
    n_sel = len(selected)
    rows.append([
        {"text": f"✅ 完成（{n_sel}/{max_sel}）", "callback_data": "tcrdn:"},
        {"text": "🗑 清空",                     "callback_data": "tcrclr:"},
    ])
    rows.append([{"text": "← 返回自定义预设", "callback_data": "t2ic:custom"}])
    text = (
        f"🎛 自选预设\n\n"
        f"已选 {n_sel}/{max_sel} 个 tag。\n"
        f"点击分类进入勾选；跨分类可叠加。"
    )
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, rows)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, rows)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, rows)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_t2i_curated_tags(user_id: int, state: dict, cid: str, page: int = 0):
    """自选预设：某分类下的 tag 勾选列表，分页显示。"""
    chat_id = state["chat_id"]
    cat = _curated_category(cid)
    if cat is None:
        show_t2i_curated_categories(user_id, state)
        return
    state["step"] = "t2i_curated_tags"
    state["curated_current_cat"] = cid
    tags = cat.get("tags", [])
    total = len(tags)
    total_pages = max(1, (total + CURATED_PAGE_SIZE - 1) // CURATED_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    state["curated_page"] = page
    save_state(user_id)

    selected = state.get("curated_selected") or []
    selected_set = set(selected)
    max_sel = CURATED_BANKS.get("max_selection", CURATED_MAX_SELECTION_FALLBACK)
    n_sel = len(selected)

    start = page * CURATED_PAGE_SIZE
    end = min(start + CURATED_PAGE_SIZE, total)

    rows = []
    for idx in range(start, end):
        key = f"{cid}:{idx}"
        mark = "☑" if key in selected_set else "☐"
        tag_disp = _tag_cn(tags[idx])
        if len(tag_disp) > 48:
            tag_disp = tag_disp[:45] + "…"
        rows.append([{"text": f"{mark} {tag_disp}", "callback_data": f"tcrtog:{cid}:{idx}"}])

    # Pagination row
    nav = []
    if page > 0:
        nav.append({"text": "◀ 上页", "callback_data": f"tcrpg:{cid}:{page-1}"})
    nav.append({"text": f"{page+1}/{total_pages}", "callback_data": "noop:"})
    if page < total_pages - 1:
        nav.append({"text": "下页 ▶", "callback_data": f"tcrpg:{cid}:{page+1}"})
    rows.append(nav)

    rows.append([
        {"text": f"✅ 完成（{n_sel}/{max_sel}）", "callback_data": "tcrdn:"},
        {"text": "🗑 清空",                     "callback_data": "tcrclr:"},
    ])
    rows.append([{"text": "← 返回分类", "callback_data": "tcrbk:"}])

    text = (
        f"🎛 自选预设 / {cat['cn_label']}\n\n"
        f"共 {total} 个 tag，已选 {n_sel}/{max_sel}。\n"
        f"点击 tag 切换勾选；超过上限会提示。"
    )
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, rows)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, rows)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, rows)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_t2i_custom_slots(user_id: int, state: dict, purpose: str):
    """显示 10 个自定义槽位。purpose = 'apply' (套用) | 'edit' (修改)。"""
    chat_id = state["chat_id"]
    state["step"] = "t2i_preset_custom_slots"
    save_state(user_id)
    rows = []
    for p in CUSTOM_PRESETS:
        pos = p["positive"].strip()
        if pos:
            preview = pos[:24] + ("…" if len(pos) > 24 else "")
            label = f"{p['title']}: {preview}"
        else:
            label = f"{p['title']} (空)"
        cb = f"t2icp:{p['id']}" if purpose == "apply" else f"t2ice:{p['id']}"
        rows.append([{"text": label, "callback_data": cb}])
    rows.append([{"text": "← 返回自定义预设", "callback_data": "t2ic:custom"}])
    if purpose == "apply":
        text = "✨ 套用自定义预设\n\n点击槽位即选中（空槽位不可用）"
    else:
        text = "✏️ 修改自定义预设\n\n点击要修改的槽位，然后发送新的 prompt 文本"
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, rows)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, rows)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, rows)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_tagger_await(user_id: int, state: dict):
    """🔍 图转提示词 入口：等用户发图。photo handler 检测 step=='await_tagger_image'
    后会调 _run_wd14_tag 走 ComfyUI 的 /pysssss/wd14tagger/tag endpoint。"""
    chat_id = state["chat_id"]
    state["step"] = "await_tagger_image"
    save_state(user_id)
    text = (
        "🔍 图转提示词\n\n"
        "请发送一张图片（原图 / JPEG / PNG / WebP）。\n"
        "bot 会用 WD14 Tagger 跑出 danbooru-style tag，返回后你可以：\n"
        "  ✨ 直接套用生图\n"
        "  💾 存入自定义预设槽\n"
        "  🗑 丢弃\n\n"
        "⏳ 首次调用会自动下载模型（~300MB，1-2 分钟）。"
    )
    kb = [[{"text": "← 返回主菜单", "callback_data": "chm:"}]]
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def _run_wd14_tag(image_local_path: Path, timeout: int = 300) -> str:
    """Invoke bin/wd14_standalone.py in a subprocess (ComfyUI-independent;
    shares the model cache with the ComfyUI-WD14-Tagger node). Returns the
    tag string. Raises RuntimeError on failure."""
    src = Path(image_local_path)
    if not src.exists():
        raise RuntimeError(f"image not found: {image_local_path}")
    script = WORKSPACE / "bin" / "wd14_standalone.py"
    py = "./ComfyUI/.venv/bin/python3"
    try:
        result = subprocess.run(
            [py, str(script), str(src)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"WD14 timeout after {timeout}s (first run may need 1-2 min to download model)")
    if result.returncode != 0:
        err_tail = (result.stderr or "").strip()[-400:]
        raise RuntimeError(f"WD14 failed (rc={result.returncode}): {err_tail}")
    return (result.stdout or "").strip()


def _show_tagger_result_menu(user_id: int, state: dict, tags: str):
    """Show the action menu after tags are produced."""
    chat_id = state["chat_id"]
    state["last_tag_result"] = tags
    state["step"] = "tagger_result"
    save_state(user_id)
    # Truncate if huge for display
    disp = tags if len(tags) <= 800 else tags[:800] + "…"
    text = f"🔍 识别到的 tag：\n\n{disp}\n\n选择下一步："
    kb = [
        [{"text": "✨ 直接套用生图", "callback_data": "tg:apply"}],
        [{"text": "💾 存入自定义预设", "callback_data": "tg:save"}],
        [{"text": "🔁 另发一张再识别", "callback_data": "m:tag"}],
        [{"text": "🗑 丢弃",           "callback_data": "tg:drop"}],
    ]
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_i2i_await_source(user_id: int, state: dict):
    """i2i 入口：尚无 source_image，提示用户发送源图。设置 step 为
    await_i2i_source，photo handler 据此分发。"""
    chat_id = state["chat_id"]
    state["step"] = "await_i2i_source"
    state["flow"] = "i2i"
    save_state(user_id)
    text = "🖼 i2i 图生图\n\n请发送源图片（原图 / JPEG / PNG）。\n收到图片后会进入底模与 LoRA 选择。"
    kb = [[{"text": "← 返回主菜单", "callback_data": "chm:"}]]
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_preset_template_menu(user_id: int, state: dict):
    """Show preset category picker (normal / r18)."""
    chat_id = state["chat_id"]
    state["step"] = "select_preset"
    save_state(user_id)
    kb = build_preset_category_keyboard()
    cur = state.get("preset_template_id")
    cur_label = ""
    if cur:
        tpl = _find_preset_by_id(cur)
        if tpl:
            cur_label = f"\n当前已选：{tpl['title']}"
    text = f"📝 选择预设模板分类：{cur_label}"
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_preset_template_list(user_id: int, state: dict, category: str):
    """Show preset templates filtered by category and family."""
    chat_id = state["chat_id"]
    state["step"] = "select_preset"
    save_state(user_id)
    family = state["family"]
    kb = build_preset_template_keyboard(family, category)
    cat_label = "正常" if category == "normal" else "R18"
    text = f"📝 {cat_label}预设模板：\n\n选择后将叠加到生成提示词中"
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_ai_suggestion_menu(user_id: int, state: dict):
    """Show AI suggestion category picker (normal / r18)."""
    chat_id = state["chat_id"]
    state["step"] = "select_ai"
    save_state(user_id)
    kb = build_ai_category_keyboard()
    cur = state.get("ai_suggestion_id")
    cur_label = ""
    cache = state.get("ai_suggestions_cache")
    if cur is not None and cache and 0 <= cur < len(cache):
        cur_label = f"\n当前已选：{cache[cur]['title']}"
    text = f"🤖 选择 AI 推荐分类：{cur_label}"
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


def show_ai_suggestion_list(user_id: int, state: dict, category: str):
    """Show AI suggestions filtered by category."""
    chat_id = state["chat_id"]
    state["step"] = "select_ai"
    suggestions = generate_ai_suggestions(state, category)
    state["ai_suggestions_cache"] = suggestions
    save_state(user_id)
    kb = build_ai_suggestion_keyboard(suggestions)
    cat_label = "正常" if category == "normal" else "R18"
    text = f"🤖 {cat_label} AI 推荐（基于当前配置）：\n\n选择后将叠加到生成提示词中"
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = edit_menu(chat_id, msg_id, text, kb)
        if not resp.get("ok"):
            resp = send_menu(chat_id, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
    else:
        resp = send_menu(chat_id, text, kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
    save_state(user_id)


# ── 双图迁移：菜单 + 提交都搬到 bin/dual_transfer/ 模块；这里只剩 Host 桥接。─

def _build_dt_host():
    """构造 dual_transfer 模块所需的 Host 注入对象。所有跨模块调用都走这里。"""
    return SimpleNamespace(
        send_text=send_text,
        send_menu=send_menu,
        edit_menu=edit_menu,
        save_state=save_state,
        load_pending=load_pending,
        save_pending=save_pending,
        comfyui_alive=comfyui_alive,
        resize_image=_resize_image,
        show_mode_menu=show_mode_menu,
        workspace=WORKSPACE,
    )


_DT_HOST = None


def dt_host():
    global _DT_HOST
    if _DT_HOST is None:
        _DT_HOST = _build_dt_host()
    return _DT_HOST


# ── Generation submission ────────────────────────────────

def submit_gen_job(user_id: int, state: dict, batch_total: int = 1, batch_current: int = 1):
    chat_id = state["chat_id"]

    # ── 防护: 普通生成入口必须保证 dt_* 全清，杜绝 dual_transfer 残留 ──
    dual_transfer.assert_clean(state)

    if not comfyui_alive():
        send_text(chat_id, "❌ ComfyUI 离线，请先启动。")
        state["step"] = "confirm"
        save_state(user_id)
        return

    state["step"] = "generating"
    save_state(user_id)

    msg_id = state.get("last_menu_msg_id")
    if batch_total > 1:
        progress_text = f"⏳ 正在生成第 {batch_current}/{batch_total} 张..."
    else:
        progress_text = "⏳ 生成中，请稍候..."
    if batch_current == 1 and msg_id:
        edit_menu(chat_id, msg_id, progress_text, [])
    else:
        send_text(chat_id, progress_text)

    # Select mode_prompt based on whether this is t2i or i2i with intensity
    source_image = state.get("source_image_path")
    if source_image and Path(source_image).exists():
        intensity = state.get("intensity", "medium")
        ip = INTENSITY_PRESETS.get(intensity, INTENSITY_PRESETS["medium"])
        mode_prompt_key = ip["mode_prompt_key"]
    else:
        mode_prompt_key = "t2i"
    positive, negative = build_merged_prompt(state, mode_prompt=MODE_PROMPTS.get(mode_prompt_key, ""))
    seed = random.randint(1, 2**32 - 1)
    state["last_seed"] = seed
    save_state(user_id)

    family = state["family"]
    model_key = state.get("model_key", "")
    mode = state["mode"]
    lora_keys = state.get("lora_keys", [])
    source_image = state.get("source_image_path")

    # Get recommended params from family
    family_def = REG.get("family_defaults", {}).get(family, {})
    rec_params = dict(family_def.get("recommended_params", {}))

    # Override with model-specific params
    if model_key and model_key in REG.get("models", {}):
        model_rec = REG["models"][model_key].get("recommended_params", {})
        rec_params.update(model_rec)

    # Compute i2i denoise from intensity preset
    # LoRA recommended_denoise acts as a floor (some LoRAs need minimum denoise to work)
    intensity = state.get("intensity", "medium")
    ip = INTENSITY_PRESETS.get(intensity, INTENSITY_PRESETS["medium"])
    i2i_denoise = ip["denoise"]
    for lk in lora_keys:
        lora_entry = REG.get("loras", {}).get(lk, {})
        ld = lora_entry.get("recommended_denoise")
        if ld is not None and float(ld) > i2i_denoise:
            i2i_denoise = float(ld)

    workflow = "i2v" if mode == "video" else "sdxl_multi_lora"

    task = {
        "workflow": workflow,
        "model_key": model_key,
        "lora_keys": lora_keys,
        "prompt": positive,
        "negative_prompt": negative,
        "seed": seed,
        "width":  rec_params.get("width", 1024),
        "height": rec_params.get("height", 1024),
        "steps":  rec_params.get("steps", 25),
        "cfg":    rec_params.get("cfg", 7),
        "sampler": rec_params.get("sampler", "euler"),
        "scheduler": rec_params.get("scheduler", "karras"),
        "clip_skip": rec_params.get("clip_skip", 2),
        "source_image": None,
        "denoise": 1.0,    # default t2i; overridden below when source image present
        "mode": mode,
    }

    if source_image and Path(source_image).exists():
        resized = _resize_image(Path(source_image), 1024)
        task["source_image"] = str(resized)
        task["denoise"] = i2i_denoise

    task_id = f"ic-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
    task_file = WORKSPACE / "tmp" / f"gen_task_{uuid.uuid4().hex[:8]}.json"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text(json.dumps(task, indent=2, ensure_ascii=False))

    # Also write to inbox for comfyui_client compatibility
    inbox_payload = {"task_id": task_id, "workflow": workflow, "params": {
        "prompt": positive,
        "negative_prompt": negative,
        "seed": seed,
        "model_key": model_key,
        "lora_keys": lora_keys,
        "width":  task["width"],
        "height": task["height"],
        "steps":  task["steps"],
        "cfg":    task["cfg"],
        "sampler": task["sampler"],
        "scheduler": task["scheduler"],
        "clip_skip": task["clip_skip"],
        "mode": mode,
    }}
    if task["source_image"]:
        inbox_payload["params"]["image_path"] = task["source_image"]
        inbox_payload["params"]["denoise"] = task["denoise"]

    inbox_path = WORKSPACE / "inbox" / f"{task_id}.json"
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text(json.dumps(inbox_payload, indent=2, ensure_ascii=False))

    try:
        result = subprocess.run(
            [sys.executable,
             str(WORKSPACE / "bin" / "comfyui_client.py"),
             "--task", str(inbox_path),
             "--submit-only"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=30
        )
    except subprocess.TimeoutExpired:
        send_text(chat_id, "❌ ComfyUI 提交超时，请稍后重试。")
        state["step"] = "confirm"
        save_state(user_id)
        return

    prompt_id = None
    for line in result.stdout.splitlines():
        if "[submit] prompt_id=" in line:
            prompt_id = line.split("=", 1)[1].strip()
            break

    if not prompt_id:
        # 1. Try to extract structured error from comfyui_client stdout JSON
        structured_error = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and obj.get("error"):
                    structured_error = str(obj["error"])
                    break
            except Exception:
                pass

        # 2. Filter stderr: skip pure info lines, keep error lines
        stderr_useful = [
            ln for ln in result.stderr.splitlines()
            if ln.strip()
            and not ln.startswith("[client] uploaded")
            and not ln.startswith("[client] resized")
        ]
        stderr_summary = "\n".join(stderr_useful[:8])

        # 3. Build final error message
        parts = ["❌ 提交失败"]
        if structured_error:
            parts.append(f"错误：{structured_error[:300]}")
        if stderr_summary:
            parts.append(f"日志：{stderr_summary[:300]}")
        if not structured_error and not stderr_summary:
            # Fallback: show raw stdout
            parts.append(result.stdout[:400] or "(无输出)")
        send_text(chat_id, "\n".join(parts))
        state["step"] = "confirm"
        save_state(user_id)
        return

    print(f"[gen] {task_id} → prompt_id={prompt_id} mode={mode} family={family}", flush=True)

    pending = load_pending()
    pending[prompt_id] = {
        "chat_id":      chat_id,
        "user_id":      user_id,
        "task_id":      task_id,
        "workflow":     workflow,
        "prompt":       positive[:120],
        "submitted_at": time.time(),
        "gen_flow":     True,
        "source_image": bool(source_image and Path(source_image).exists()),
        "batch_total":   batch_total,
        "batch_current": batch_current,
        "batch_ok":      state.get("_batch_ok", 0),
        "batch_fail":    state.get("_batch_fail", 0),
    }
    save_pending(pending)


def _submit_batch_next(user_id: int, state: dict, batch_total: int, batch_current: int):
    """Submit the next job in a batch sequence (called from poller thread)."""
    try:
        submit_gen_job(user_id, state, batch_total=batch_total, batch_current=batch_current)
    except Exception as e:
        chat_id = state.get("chat_id")
        if chat_id:
            send_text(chat_id, f"❌ 批量生成第 {batch_current}/{batch_total} 张提交失败: {e}")
        state["step"] = "result"
        _save_gen_state()


# ── Callback handler ─────────────────────────────────────

def handle_callback(update):
    global _SEEN_CB_IDS
    cb      = update.get("callback_query", {})
    cb_id   = cb.get("id", "")
    data    = cb.get("data", "")
    user_id = cb["from"]["id"]
    msg     = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    msg_id  = msg.get("message_id")

    # Dedup: skip if this exact callback press was already processed
    if cb_id and cb_id in _SEEN_CB_IDS:
        answer_callback(cb_id)
        return
    if cb_id:
        _SEEN_CB_IDS.add(cb_id)
        if len(_SEEN_CB_IDS) > _MAX_SEEN_CB:
            _SEEN_CB_IDS.clear()
            _SEEN_CB_IDS.add(cb_id)

    if not chat_id:
        answer_callback(cb_id)
        return

    state = get_state(user_id, chat_id)
    # Keep track of the menu message we're interacting with
    if msg_id:
        state["last_menu_msg_id"] = msg_id

    # ── m: mode select ───────────────────────────────────
    if data.startswith("m:"):
        val = data[2:]
        if val == "dt":
            dual_transfer.show_track_entry(dt_host(), user_id, state)
        elif val == "t2i":
            # t2i: 清 source_image + 进 preset 分类选择
            state["mode"] = "image"
            state["flow"] = "t2i"
            state["source_image_path"] = None
            state["intensity"] = None
            state["lora_keys"] = []
            state["lora_page"] = 0
            state["preset_template_id"] = None
            state["preset_return_to"] = None   # fresh t2i → flow goes family/model/lora
            dual_transfer.assert_clean(state)
            show_t2i_preset_category(user_id, state)
        elif val == "i2i":
            # i2i: 必须有 source_image；没有就提示发图
            state["mode"] = "image"
            state["flow"] = "i2i"
            state["lora_keys"] = []
            state["lora_page"] = 0
            dual_transfer.assert_clean(state)
            if state.get("source_image_path"):
                show_family_menu(user_id, state)
            else:
                show_i2i_await_source(user_id, state)
        elif val == "vid":
            state["mode"] = "video"
            state["flow"] = "vid"
            state["lora_keys"] = []
            state["lora_page"] = 0
            dual_transfer.assert_clean(state)
            show_family_menu(user_id, state)
        elif val == "tag":
            # 🔍 图转提示词 — 等用户发图，走 WD14 tagger
            state["flow"] = "tag"
            state["step"] = "await_tagger_image"
            state["last_tag_result"] = ""
            dual_transfer.assert_clean(state)
            save_state(user_id)
            show_tagger_await(user_id, state)
        else:
            # 未知 mode，回主菜单
            show_mode_menu(user_id, state, edit_msg_id=msg_id)

    # ── t2ic: t2i preset category ────────────────────────
    elif data.startswith("t2ic:"):
        cat = data[5:]
        if cat == "custom":
            show_t2i_custom_menu(user_id, state)
        elif cat in ("normal", "r18"):
            show_t2i_preset_list(user_id, state, cat)
        answer_callback(cb_id)
        return

    # ── t2ip: t2i normal/r18 preset picked ─────────────────
    elif data.startswith("t2ip:"):
        tpl_id = data[5:]
        tpl = _find_preset_by_id(tpl_id)
        if tpl:
            state["preset_template_id"] = tpl_id
            save_state(user_id)
            answer_callback(cb_id, f"已选择：{tpl['title']}")
            _goto_after_preset_apply(user_id, state)
        else:
            answer_callback(cb_id, "模板不存在")
        return

    # ── t2icu: custom preset submenu (apply | edit | curated) ─
    elif data.startswith("t2icu:"):
        purpose = data[6:]
        if purpose in ("apply", "edit"):
            show_t2i_custom_slots(user_id, state, purpose)
        elif purpose == "curated":
            show_t2i_curated_categories(user_id, state)
        answer_callback(cb_id)
        return

    # ── tcrcat: curated category entry ─────────────────────
    elif data.startswith("tcrcat:"):
        cid = data[7:]
        show_t2i_curated_tags(user_id, state, cid, page=0)
        answer_callback(cb_id)
        return

    # ── tcrpg: curated page nav within current category ────
    elif data.startswith("tcrpg:"):
        rest = data[6:]
        if ":" in rest:
            cid, pg_s = rest.split(":", 1)
            try:
                pg = int(pg_s)
            except ValueError:
                pg = 0
            show_t2i_curated_tags(user_id, state, cid, page=pg)
        answer_callback(cb_id)
        return

    # ── tcrtog: toggle a curated tag ────────────────────────
    elif data.startswith("tcrtog:"):
        rest = data[7:]
        if ":" not in rest:
            answer_callback(cb_id)
            return
        cid, idx_s = rest.split(":", 1)
        try:
            idx = int(idx_s)
        except ValueError:
            answer_callback(cb_id)
            return
        cat = _curated_category(cid)
        if cat is None or idx >= len(cat.get("tags", [])):
            answer_callback(cb_id, "tag 不存在")
            return
        key = f"{cid}:{idx}"
        selected = state.setdefault("curated_selected", [])
        max_sel = CURATED_BANKS.get("max_selection", CURATED_MAX_SELECTION_FALLBACK)
        if key in selected:
            selected.remove(key)
            answer_callback(cb_id, "已取消")
        else:
            if len(selected) >= max_sel:
                answer_callback(cb_id, f"已达上限 {max_sel}")
                return
            selected.append(key)
            answer_callback(cb_id, f"已勾选 {len(selected)}/{max_sel}")
        save_state(user_id)
        # Refresh current page so the checkmark flips.
        cur_page = state.get("curated_page", 0)
        show_t2i_curated_tags(user_id, state, cid, page=cur_page)
        return

    # ── tcrbk: back from tag list to curated category list ──
    elif data == "tcrbk:":
        show_t2i_curated_categories(user_id, state)
        answer_callback(cb_id)
        return

    # ── tcrclr: clear all curated selections ────────────────
    elif data == "tcrclr:":
        state["curated_selected"] = []
        save_state(user_id)
        answer_callback(cb_id, "已清空自选 tag")
        # Stay on whatever view we were on
        if state.get("step") == "t2i_curated_tags" and state.get("curated_current_cat"):
            show_t2i_curated_tags(user_id, state, state["curated_current_cat"],
                                  page=state.get("curated_page", 0))
        else:
            show_t2i_curated_categories(user_id, state)
        return

    # ── tg: tagger result actions (apply / save / drop) ────
    elif data == "tg:apply":
        tags = state.get("last_tag_result") or ""
        if not tags:
            answer_callback(cb_id, "没有可套用的 tag")
            return
        state["user_prompt"] = tags
        state["last_tag_result"] = ""
        save_state(user_id)
        answer_callback(cb_id, "已套用，进入底模/LoRA 选择")
        _goto_after_preset_apply(user_id, state)
        return

    elif data == "tg:save":
        # show 10 custom slots so user can pick one to save the tag string into
        tags = state.get("last_tag_result") or ""
        if not tags:
            answer_callback(cb_id, "没有可保存的 tag")
            return
        answer_callback(cb_id)
        chat_id_local = state["chat_id"]
        rows = []
        for p in CUSTOM_PRESETS:
            pos = p["positive"].strip()
            lab = f"{p['title']} (占用)" if pos else f"{p['title']} (空)"
            rows.append([{"text": lab, "callback_data": f"tgsl:{p['id']}"}])
        rows.append([{"text": "← 返回",   "callback_data": "tg:back"}])
        text = "💾 选择保存到哪个自定义预设槽\n\n（选中会直接覆盖原内容）"
        msg_id_local = state.get("last_menu_msg_id")
        if msg_id_local:
            resp = edit_menu(chat_id_local, msg_id_local, text, rows)
            if not resp.get("ok"):
                resp = send_menu(chat_id_local, text, rows)
                if resp.get("ok"):
                    state["last_menu_msg_id"] = resp["result"]["message_id"]
        else:
            resp = send_menu(chat_id_local, text, rows)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
        save_state(user_id)
        return

    elif data.startswith("tgsl:"):
        slot_id = data[5:]
        tags = state.get("last_tag_result") or ""
        if not tags:
            answer_callback(cb_id, "没有可保存的 tag")
            return
        tpl = next((t for t in CUSTOM_PRESETS if t["id"] == slot_id), None)
        if tpl is None:
            answer_callback(cb_id, "槽位不存在")
            return
        tpl["positive"] = tags
        try:
            _save_custom_presets()
            answer_callback(cb_id, f"已保存到 {tpl['title']}")
            send_text(state["chat_id"], f"✅ 已保存到 [{tpl['title']}]")
        except Exception as e:
            answer_callback(cb_id)
            send_text(state["chat_id"], f"❌ 保存失败: {e}")
        state["last_tag_result"] = ""
        save_state(user_id)
        show_mode_menu(user_id, state)
        return

    elif data == "tg:back":
        # back from save-slot picker to the result menu
        tags = state.get("last_tag_result") or ""
        if tags:
            _show_tagger_result_menu(user_id, state, tags)
        else:
            show_mode_menu(user_id, state, edit_msg_id=msg_id)
        answer_callback(cb_id)
        return

    elif data == "tg:drop":
        state["last_tag_result"] = ""
        save_state(user_id)
        answer_callback(cb_id, "已丢弃")
        show_mode_menu(user_id, state, edit_msg_id=msg_id)
        return

    # ── tcrdn: done — apply selected curated tags and go forward ──
    elif data == "tcrdn:":
        selected = state.get("curated_selected") or []
        if not selected:
            answer_callback(cb_id, "尚未勾选任何 tag")
            return
        answer_callback(cb_id, f"已套用 {len(selected)} 个 tag")
        _goto_after_preset_apply(user_id, state)
        return

    # ── t2icp: custom preset slot apply ────────────────────
    elif data.startswith("t2icp:"):
        slot_id = data[6:]
        tpl = _find_preset_by_id(slot_id)
        if tpl is None or not tpl.get("positive"):
            answer_callback(cb_id, "该槽位为空")
            return
        state["preset_template_id"] = slot_id
        save_state(user_id)
        answer_callback(cb_id, f"已套用：{tpl['title']}")
        _goto_after_preset_apply(user_id, state)
        return

    # ── t2ice: custom preset slot edit ─────────────────────
    elif data.startswith("t2ice:"):
        slot_id = data[6:]
        tpl = _find_preset_by_id(slot_id)
        if tpl is None:
            answer_callback(cb_id, "槽位不存在")
            return
        state["custom_preset_edit_slot"] = slot_id
        state["step"] = "await_custom_preset_input"
        save_state(user_id)
        cur = tpl.get("positive", "")
        preview = f"\n当前内容：\n{cur}" if cur else "\n（当前为空）"
        text = (
            f"✏️ 编辑 [{tpl['title']}]{preview}\n\n"
            "请发送新的 prompt 文本作为消息保存（直接覆盖原内容）。\n"
            "发送 /cancel 取消编辑。"
        )
        chat_id_local = state["chat_id"]
        kb = [[{"text": "← 取消编辑", "callback_data": "t2icu:edit"}]]
        msg_id_local = state.get("last_menu_msg_id")
        if msg_id_local:
            resp = edit_menu(chat_id_local, msg_id_local, text, kb)
            if not resp.get("ok"):
                resp = send_menu(chat_id_local, text, kb)
                if resp.get("ok"):
                    state["last_menu_msg_id"] = resp["result"]["message_id"]
        else:
            resp = send_menu(chat_id_local, text, kb)
            if resp.get("ok"):
                state["last_menu_msg_id"] = resp["result"]["message_id"]
        save_state(user_id)
        answer_callback(cb_id)
        return

    # ── f: family select ─────────────────────────────────
    elif data.startswith("f:"):
        val = data[2:]
        if val in ("pvc", "2d", "3d"):
            state["family"] = val
            state["model_key"] = ""
            state["lora_keys"] = []
            state["lora_page"] = 0
            state["lora_sub_family"] = None
            state["preset_template_id"] = None
            state["ai_suggestion_id"] = None
            state["ai_suggestions_cache"] = None
            if state["mode"] == "video":
                # Skip model selection for video
                show_lora_menu(user_id, state)
            else:
                show_model_menu(user_id, state)
        else:
            # Unknown family: back to family menu
            show_family_menu(user_id, state)

    # ── mdl: model select ────────────────────────────────
    elif data.startswith("mdl:"):
        try:
            idx = int(data[4:])
        except ValueError:
            answer_callback(cb_id)
            return
        model_list = state.get("current_model_list", [])
        if 0 <= idx < len(model_list):
            state["model_key"] = model_list[idx]
            state["lora_keys"] = []
            state["lora_page"] = 0
            show_lora_menu(user_id, state)
        else:
            send_text(chat_id, "❌ 无效的底模序号，请重新选择。")

    # ── l: lora toggle ───────────────────────────────────
    elif data.startswith("l:"):
        try:
            idx = int(data[2:])
        except ValueError:
            answer_callback(cb_id)
            return
        lora_list = state.get("current_lora_list", [])
        if 0 <= idx < len(lora_list):
            lk = lora_list[idx]
            selected = state.get("lora_keys", [])
            if lk in selected:
                selected.remove(lk)
            else:
                if len(selected) >= 8:
                    answer_callback(cb_id, "最多只能选 8 个 LoRA")
                    return
                selected.append(lk)
            state["lora_keys"] = selected
            save_state(user_id)
            # Refresh lora keyboard in-place
            kb = build_lora_keyboard(state)
            msg_id_cur = state.get("last_menu_msg_id")
            if msg_id_cur:
                edit_menu(chat_id, msg_id_cur, lora_text(state), kb)
            answer_callback(cb_id)
            return

    # ── lp: lora page ────────────────────────────────────
    elif data.startswith("lp:"):
        try:
            page = int(data[3:])
        except ValueError:
            answer_callback(cb_id)
            return
        state["lora_page"] = page
        save_state(user_id)
        kb = build_lora_keyboard(state)
        msg_id_cur = state.get("last_menu_msg_id")
        if msg_id_cur:
            edit_menu(chat_id, msg_id_cur, lora_text(state), kb)
        answer_callback(cb_id)
        return

    # ── lcat: lora category select (pvc sub-menu) ─────────
    elif data.startswith("lcat:"):
        sub = data[5:]
        if sub in ("pvc", "2d", "3d"):
            state["lora_sub_family"] = sub
            state["lora_page"] = 0
            show_lora_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── lbcat: back to lora category menu ────────────────
    elif data == "lbcat:":
        state["lora_sub_family"] = None
        state["lora_page"] = 0
        show_lora_category_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── ld: lora done ────────────────────────────────────
    elif data == "ld:":
        if state.get("source_image_path"):
            show_intensity_menu(user_id, state)
        else:
            show_confirm_menu(user_id, state)

    # ── int: intensity selection ────────────────────────
    elif data.startswith("int:"):
        intensity = data[4:]
        if intensity in INTENSITY_PRESETS:
            state["intensity"] = intensity
            save_state(user_id)
            show_confirm_menu(user_id, state)

    # ── chi: change intensity ────────────────────────────
    elif data == "chi:":
        show_intensity_menu(user_id, state)

    # ── lc: lora clear ───────────────────────────────────
    elif data == "lc:":
        state["lora_keys"] = []
        save_state(user_id)
        kb = build_lora_keyboard(state)
        msg_id_cur = state.get("last_menu_msg_id")
        if msg_id_cur:
            edit_menu(chat_id, msg_id_cur, lora_text(state), kb)
        answer_callback(cb_id)
        return

    # ── lb: lora back ────────────────────────────────────
    elif data == "lb:":
        if state["mode"] == "video":
            show_family_menu(user_id, state)
        else:
            show_model_menu(user_id, state)

    # ── qty: change quantity ─────────────────────────────
    elif data == "qty:":
        if state.get("mode") != "image":
            answer_callback(cb_id, "视频模式不支持批量生成")
            return
        # Show quantity picker — user picks how many to batch generate
        qty_kb = [
            [{"text": str(i), "callback_data": f"qn:{i}"} for i in (2, 4, 8)],
            [{"text": str(i), "callback_data": f"qn:{i}"} for i in (10, 15, 20)],
            [{"text": "← 取消", "callback_data": "qbk:"}],
        ]
        msg_id_cur = state.get("last_menu_msg_id")
        if msg_id_cur:
            edit_menu(chat_id, msg_id_cur, "按同样配置再生成几张？", qty_kb)
        else:
            send_menu(chat_id, "按同样配置再生成几张？", qty_kb)
        answer_callback(cb_id)
        return

    # ── qn: quantity selected → start batch ──────────────
    elif data.startswith("qn:"):
        try:
            n = int(data[3:])
            n = max(2, min(20, n))
        except ValueError:
            answer_callback(cb_id)
            return
        answer_callback(cb_id)
        submit_gen_job(user_id, state, batch_total=n, batch_current=1)
        return

    # ── qbk: cancel batch, back to result ────────────────
    elif data == "qbk:":
        has_src = bool(state.get("source_image_path"))
        is_img = (state.get("mode") == "image")
        msg_id_cur = state.get("last_menu_msg_id")
        if msg_id_cur:
            edit_menu(chat_id, msg_id_cur, "✅ 已取消批量",
                      build_result_keyboard(has_src, is_img))
        answer_callback(cb_id)
        return

    # ── ptml: show preset template category menu ────────────
    elif data == "ptml:":
        show_preset_template_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── ptcat: select preset category (normal/r18) ──────────
    elif data.startswith("ptcat:"):
        cat = data[6:]
        if cat in ("normal", "r18"):
            show_preset_template_list(user_id, state, cat)
        answer_callback(cb_id)
        return

    # ── pt: select preset template ──────────────────────
    elif data.startswith("pt:"):
        tpl_id = data[3:]
        tpl = _find_preset_by_id(tpl_id)
        if tpl:
            state["preset_template_id"] = tpl_id
            save_state(user_id)
            answer_callback(cb_id, f"已选择：{tpl['title']}")
            show_confirm_menu(user_id, state)
        else:
            answer_callback(cb_id, "模板不存在")
        return

    # ── ptsk: skip preset template ──────────────────────
    elif data == "ptsk:":
        state["preset_template_id"] = None
        save_state(user_id)
        show_confirm_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── ptbk: back from preset to confirm ───────────────
    elif data == "ptbk:":
        show_confirm_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── aiml: show AI suggestion category menu ─────────────
    elif data == "aiml:":
        show_ai_suggestion_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── aicat: select AI category (normal/r18) ──────────
    elif data.startswith("aicat:"):
        cat = data[6:]
        if cat in ("normal", "r18"):
            show_ai_suggestion_list(user_id, state, cat)
        answer_callback(cb_id)
        return

    # ── ai: select AI suggestion ─────────────────────────
    elif data.startswith("ai:"):
        try:
            idx = int(data[3:])
        except ValueError:
            answer_callback(cb_id)
            return
        cache = state.get("ai_suggestions_cache", [])
        if 0 <= idx < len(cache):
            state["ai_suggestion_id"] = idx
            save_state(user_id)
            answer_callback(cb_id, f"已选择：{cache[idx]['title']}")
            show_confirm_menu(user_id, state)
        else:
            answer_callback(cb_id, "选项不存在")
        return

    # ── aisk: skip AI suggestion ─────────────────────────
    elif data == "aisk:":
        state["ai_suggestion_id"] = None
        save_state(user_id)
        show_confirm_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── aibk: back from AI to confirm ────────────────────
    elif data == "aibk:":
        show_confirm_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── plml: prompt library menu (show categories) ─────
    elif data == "plml:":
        state["step"] = "select_library"
        state["library_category_id"] = None
        state["library_page"] = 0
        save_state(user_id)
        kb = build_library_category_keyboard(state)
        sel_count = len(state.get("library_selected_ids", []))
        text = f"📚 词库选择（已选{sel_count}项）\n选择分类浏览词条：" if sel_count else "📚 词库选择\n选择分类浏览词条："
        edit_menu(chat_id, msg_id, text, kb)
        answer_callback(cb_id)
        return

    # ── plcat: enter a library category ───────────────
    elif data.startswith("plcat:"):
        cat_id = data[6:]
        state["library_category_id"] = cat_id
        state["library_page"] = 0
        save_state(user_id)
        cat = next((c for c in PROMPT_LIBRARY.get("categories", []) if c["id"] == cat_id), None)
        cat_title = cat["title"] if cat else cat_id
        sel_count = len(state.get("library_selected_ids", []))
        text = f"📚 {cat_title}（已选{sel_count}项）\n点击词条切换选中状态："
        kb = build_library_items_keyboard(state, cat_id)
        edit_menu(chat_id, msg_id, text, kb)
        answer_callback(cb_id)
        return

    # ── pli: toggle a library item ────────────────────
    elif data.startswith("pli:"):
        item_id = data[4:]
        selected = state.get("library_selected_ids", [])
        if item_id in selected:
            selected.remove(item_id)
        else:
            selected.append(item_id)
        state["library_selected_ids"] = selected
        save_state(user_id)
        cat_id = state.get("library_category_id", "")
        cat = next((c for c in PROMPT_LIBRARY.get("categories", []) if c["id"] == cat_id), None)
        cat_title = cat["title"] if cat else cat_id
        text = f"📚 {cat_title}（已选{len(selected)}项）\n点击词条切换选中状态："
        kb = build_library_items_keyboard(state, cat_id)
        edit_menu(chat_id, msg_id, text, kb)
        answer_callback(cb_id)
        return

    # ── plpg: library page navigation ─────────────────
    elif data.startswith("plpg:"):
        page = int(data[5:])
        state["library_page"] = page
        save_state(user_id)
        cat_id = state.get("library_category_id", "")
        cat = next((c for c in PROMPT_LIBRARY.get("categories", []) if c["id"] == cat_id), None)
        cat_title = cat["title"] if cat else cat_id
        sel_count = len(state.get("library_selected_ids", []))
        text = f"📚 {cat_title}（已选{sel_count}项）\n点击词条切换选中状态："
        kb = build_library_items_keyboard(state, cat_id)
        edit_menu(chat_id, msg_id, text, kb)
        answer_callback(cb_id)
        return

    # ── pldone: finish library selection ──────────────
    elif data == "pldone:":
        state["step"] = "confirm"
        state["library_category_id"] = None
        state["library_page"] = 0
        save_state(user_id)
        sel_count = len(state.get("library_selected_ids", []))
        answer_callback(cb_id, f"已选择{sel_count}个词库词条")
        show_confirm_menu(user_id, state)
        return

    # ── plclr: clear library selections ───────────────
    elif data == "plclr:":
        state["library_selected_ids"] = []
        save_state(user_id)
        answer_callback(cb_id, "已清空词库选择")
        kb = build_library_category_keyboard(state)
        edit_menu(chat_id, msg_id, "📚 词库选择\n选择分类浏览词条：", kb)
        return

    # ── plsk: skip library ────────────────────────────
    elif data == "plsk:":
        state["step"] = "confirm"
        save_state(user_id)
        show_confirm_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── plbk: back from library to confirm ────────────
    elif data == "plbk:":
        state["step"] = "confirm"
        state["library_category_id"] = None
        state["library_page"] = 0
        save_state(user_id)
        show_confirm_menu(user_id, state)
        answer_callback(cb_id)
        return

    # ── noop: do nothing (pagination label) ───────────
    elif data == "noop:":
        answer_callback(cb_id)
        return

    # ── clrp: clear preset + AI + library selections ──
    elif data == "clrp:":
        state["preset_template_id"] = None
        state["ai_suggestion_id"] = None
        state["ai_suggestions_cache"] = None
        state["library_selected_ids"] = []
        save_state(user_id)
        answer_callback(cb_id, "已清除增强提示词")
        show_confirm_menu(user_id, state)
        return

    # ── gen: start generation ────────────────────────────
    elif data == "gen:":
        submit_gen_job(user_id, state)

    # ── chm: change model (back to mode select) ──────────
    elif data == "chm:":
        state["model_key"] = ""
        state["lora_keys"] = []
        state["lora_page"] = 0
        show_mode_menu(user_id, state, edit_msg_id=msg_id)

    # ── chl: change lora ─────────────────────────────────
    elif data == "chl:":
        state["lora_keys"] = []
        state["lora_page"] = 0
        state["lora_sub_family"] = None
        show_lora_menu(user_id, state)

    # ── re: retry (same config, new seed) ────────────────
    elif data == "re:":
        state["step"] = "confirm"
        save_state(user_id)
        submit_gen_job(user_id, state)

    # ── ap: add/refine prompt ────────────────────────────
    elif data == "ap:":
        # Append prompt after a generation: route into the custom-preset
        # system (应用 / 修改 / 自选) and come back to the confirm menu
        # instead of the family menu when an apply completes.
        state["awaiting_prompt_input"] = False
        state["preset_return_to"] = "confirm"
        save_state(user_id)
        show_t2i_custom_menu(user_id, state)

    # ── dt: dual_transfer callbacks ─────────────────────
    elif data.startswith("dt:"):
        dual_transfer.handle_dt_callback(dt_host(), user_id, state, data[3:], msg_id)

    # ── bk: back shortcuts ───────────────────────────────
    elif data.startswith("bk:"):
        target = data[3:]
        if target == "l":
            show_lora_menu(user_id, state)
        elif target == "m":
            show_model_menu(user_id, state)
        else:
            show_mode_menu(user_id, state, edit_msg_id=msg_id)

    # ── rst: reset current session selection ─────────────
    elif data == "rst:":
        # Full wipe — including source image. The user is starting fresh.
        # If they want i2i again, they'll send a new image.
        saved_chat = state["chat_id"]
        GEN_STATE[user_id] = _default_state(saved_chat)
        save_state(user_id)
        answer_callback(cb_id)
        msg_id_cur = state.get("last_menu_msg_id")
        notice = "🧹 已重置本轮选择。\n重新发送图片或文字开始新一轮生成。"
        if msg_id_cur:
            edit_menu(chat_id, msg_id_cur, notice, [])
        else:
            send_text(chat_id, notice)
        return

    # Answer callback to remove spinner
    answer_callback(cb_id)
    save_state(user_id)


# ── Message handler ──────────────────────────────────────

HELP_TEXT = """\
🎨 ImageCreator Bot

/start 弹出主菜单，4 个入口：
📝 t2i 文生图 — 选预设 prompt → 选底模 → 选 LoRA → 生成
🖼 i2i 图生图 — 发送源图 → 选底模 → 选 LoRA → 生成
🔀 双图合并   — A 角色 + B 动作 / 服装
🎬 生成视频   — 源图 → 视频

也可以直接发图片，会弹出 🖼 i2i / 🎬 视频 两个入口。
纯文字消息会保存为 prompt 并弹出主菜单。

命令：
/start  — 显示主菜单
/help   — 显示此帮助
/status — 查看排队任务
/cancel — 取消排队任务
"""


def handle_message(msg):
    chat_id  = msg["chat"]["id"]
    user_id  = msg["from"]["id"]
    text     = (msg.get("text") or msg.get("caption") or "").strip()
    photos   = msg.get("photo")
    document = msg.get("document")

    # ── 自定义预设编辑模式拦截 ────────────────────────────
    # 在其他所有分发之前处理，以便 /cancel 在编辑模式下取消编辑
    # 而不是清空任务队列。
    state_peek = GEN_STATE.get(user_id)
    if state_peek and state_peek.get("step") == "await_custom_preset_input":
        state = get_state(user_id, chat_id)
        slot_id = state.get("custom_preset_edit_slot")
        if text == "/cancel":
            state["custom_preset_edit_slot"] = None
            state["step"] = "t2i_preset_custom"
            save_state(user_id)
            send_text(chat_id, "已取消编辑。")
            show_t2i_custom_menu(user_id, state)
            return
        if photos or document:
            send_text(chat_id, "⚠️ 编辑模式下请发送文字消息作为 prompt；或发送 /cancel 取消。")
            return
        if not text:
            return
        tpl = next((t for t in CUSTOM_PRESETS if t["id"] == slot_id), None)
        if tpl is None:
            state["custom_preset_edit_slot"] = None
            state["step"] = "t2i_preset_custom"
            save_state(user_id)
            send_text(chat_id, "❌ 槽位不存在，已退出编辑。")
            return
        tpl["positive"] = text
        try:
            _save_custom_presets()
            send_text(chat_id, f"✅ 已保存到 [{tpl['title']}]。")
        except Exception as e:
            send_text(chat_id, f"❌ 保存失败: {e}")
        state["custom_preset_edit_slot"] = None
        state["step"] = "t2i_preset_custom"
        save_state(user_id)
        show_t2i_custom_slots(user_id, state, "edit")
        return

    # /start → 主菜单；/help → 文字帮助
    if text == "/start":
        state = get_state(user_id, chat_id)
        # 清理任何遗留的上一轮 flow 临时状态（但保留 source_image 以便 i2i 快速路径）
        state["preset_template_id"] = None
        state["ai_suggestion_id"] = None
        state["ai_suggestions_cache"] = None
        dual_transfer.assert_clean(state)
        save_state(user_id)
        show_mode_menu(user_id, state)
        return
    if text in ("/help", "帮助", "help"):
        send_text(chat_id, HELP_TEXT)
        return

    # /status
    if text.lower() in ("/status", "状态", "队列"):
        pending = load_pending()
        mine = [(pid, j) for pid, j in pending.items() if j["chat_id"] == chat_id]
        if not mine:
            send_text(chat_id, "✅ 当前没有排队中的任务。")
        else:
            lines = [f"⏳ 排队中 {len(mine)} 个任务："]
            for pid, j in mine:
                elapsed = int(time.time() - j["submitted_at"])
                wf = j.get("workflow", "?")
                pr = j.get("prompt", "")[:40]
                lines.append(f"  • [{wf}] {pr}... ({elapsed}s)")
            send_text(chat_id, "\n".join(lines))
        return

    # /cancel
    if text.lower() in ("/cancel", "取消", "取消任务"):
        pending = load_pending()
        before = len(pending)
        pending = {pid: j for pid, j in pending.items() if j["chat_id"] != chat_id}
        removed = before - len(pending)
        save_pending(pending)
        if removed:
            send_text(chat_id, f"✅ 已从队列移除 {removed} 个任务。")
        else:
            send_text(chat_id, "没有可取消的任务。")
        return

    state = get_state(user_id, chat_id)
    has_photo = bool(photos or (document and document.get("mime_type", "").startswith("image/")))

    # ── Awaiting prompt input ────────────────────────────
    if state.get("awaiting_prompt_input") and text and not has_photo:
        state["awaiting_prompt_input"] = False
        existing = state.get("user_prompt", "")
        if existing:
            state["user_prompt"] = existing + ", " + text
        else:
            state["user_prompt"] = text
        save_state(user_id)
        # Go to confirm
        show_confirm_menu(user_id, state)
        return

    # ── 双图迁移: 拦截图片上传 ─────────────────────────────
    if has_photo and state.get("step") == "dual_transfer_flow":
        try:
            file_id = photos[-1]["file_id"] if photos else document["file_id"]
            downloaded = download_telegram_file(file_id)
        except Exception as e:
            send_text(chat_id, f"❌ 图片下载失败: {e}")
            return
        dual_transfer.on_photo(dt_host(), user_id, state, str(downloaded), text or "")
        return

    # ── Photo received ───────────────────────────────────
    if has_photo:
        try:
            file_id = photos[-1]["file_id"] if photos else document["file_id"]
            downloaded = download_telegram_file(file_id)
        except Exception as e:
            send_text(chat_id, f"❌ 图片下载失败: {e}")
            return

        state["source_image_path"] = str(downloaded)
        if text:
            state["user_prompt"] = text
        save_state(user_id)

        # i2i 入口已经预先声明 await_i2i_source：收到图直接进 family 菜单
        if state.get("step") == "await_i2i_source":
            state["flow"] = "i2i"
            state["mode"] = "image"
            save_state(user_id)
            send_text(chat_id, "✅ 图片已保存")
            show_family_menu(user_id, state)
            return

        # 🔍 图转提示词入口：收到图立即调 WD14 tagger
        if state.get("step") == "await_tagger_image":
            send_text(chat_id, "⏳ 识别中...（首次使用会下载模型，可能需要 1-2 分钟）")
            try:
                tags = _run_wd14_tag(downloaded)
            except Exception as e:
                send_text(chat_id, f"❌ 识别失败: {e}")
                state["step"] = "idle"
                save_state(user_id)
                return
            if not tags:
                send_text(chat_id, "⚠️ 未识别到任何 tag（阈值可能过高或图不含可识别内容）")
                state["step"] = "idle"
                save_state(user_id)
                return
            _show_tagger_result_menu(user_id, state, tags)
            return

        # 未声明入口时直接发图：只允许进 i2i / 生视频两种，不能直接进 t2i/dt
        send_text(chat_id, "✅ 图片已保存")
        kb = build_post_photo_keyboard()
        resp = send_menu(chat_id, "选择要做什么：\n🖼 i2i 图生图 / 🎬 生成视频", kb)
        if resp.get("ok"):
            state["last_menu_msg_id"] = resp["result"]["message_id"]
            save_state(user_id)
        return

    # ── Text message (no image attached) ──────────────────
    # Clear any leftover source image from a previous i2i round.
    # A text-only message is an explicit t2i intent — stale image paths
    # from earlier i2i sessions must not carry over.
    if text:
        if state.get("source_image_path"):
            state["source_image_path"] = None
            state["intensity"] = None
        state["user_prompt"] = text
        save_state(user_id)
        show_mode_menu(user_id, state)
        return

    send_text(chat_id, "请发送文字描述或图片。\n发 /help 查看功能。")


# ── Local archive save ───────────────────────────────────

def save_to_archive(file_path: str, media_type: str, job: dict, prompt_id: str,
                    tg_message_id=None, seq: int = 1) -> str | None:
    """Save generated file + JSON metadata to local archive. Returns archive path or None."""
    try:
        src = Path(file_path)
        if not src.exists():
            print(f"[archive] source file missing: {file_path}", flush=True)
            return None

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        ts = now.strftime("%Y%m%d_%H%M%S")

        # Resolve metadata from GEN_STATE
        user_id = job.get("user_id")
        st = GEN_STATE.get(int(user_id)) if user_id else None

        family = st.get("family", "unknown") if st else "unknown"
        model_key = st.get("model_key", "") if st else ""
        model_short = model_key.split("/")[-1] if model_key else "unknown"
        lora_keys = st.get("lora_keys", []) if st else []
        lora_short = "_".join(lk.split("/")[-1][:12] for lk in lora_keys) if lora_keys else "none"
        intensity = st.get("intensity") or "na"
        user_prompt = st.get("user_prompt", "") if st else ""
        mode = st.get("mode", "image") if st else ("video" if media_type != "images" else "image")
        has_source = bool(st.get("source_image_path")) if st else bool(job.get("source_image"))

        # sub type: image or video
        sub_type = "image" if media_type == "images" else "video"
        archive_dir = OUTPUT_ARCHIVE / sub_type / date_str
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Clean model_short for filename safety
        safe = lambda s: s.replace("/", "_").replace(" ", "_").replace(":", "_")[:30]
        base_name = f"{ts}_{safe(family)}_{safe(model_short)}_{safe(lora_short)}_{intensity}_{seq:02d}"
        ext = src.suffix or (".png" if sub_type == "image" else ".mp4")
        dest = archive_dir / f"{base_name}{ext}"
        shutil.copy2(src, dest)

        # Save companion JSON metadata
        meta = {
            "generated_at": now.isoformat(),
            "mode": mode,
            "family": family,
            "model": model_key,
            "lora_keys": lora_keys,
            "intensity": intensity,
            "user_prompt": user_prompt,
            "has_source_image": has_source,
            "prompt_id": prompt_id,
            "workflow": job.get("workflow", ""),
            "task_id": job.get("task_id", ""),
            "telegram_message_id": tg_message_id,
            "seq": seq,
        }
        meta_path = archive_dir / f"{base_name}.json"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

        print(f"[archive] saved {dest.name}", flush=True)
        return str(dest)
    except Exception as e:
        print(f"[archive] ERROR saving {file_path}: {e}", flush=True)
        return None


# ── Background result poller ─────────────────────────────

def result_poll_loop():
    while True:
        time.sleep(POLL_INTERVAL)
        try:
            _check_pending()
        except Exception as e:
            print(f"[poller] error: {e}", flush=True)


def _check_pending():
    pending = load_pending()
    if not pending:
        return

    now = time.time()
    changed = False

    for prompt_id, job in list(pending.items()):
        chat_id  = job["chat_id"]
        workflow = job.get("workflow", "?")
        prompt   = job.get("prompt", "")
        user_id  = job.get("user_id")
        gen_flow = job.get("gen_flow", False)

        # timeout
        if now - job["submitted_at"] > MAX_JOB_AGE:
            send_text(chat_id, f"⏰ 生成超时\nworkflow: {workflow}\nprompt: {prompt[:60]}")
            del pending[prompt_id]
            changed = True
            continue

        # check ComfyUI history
        try:
            history = comfyui_get(f"/history/{prompt_id}")
        except Exception:
            continue

        job_data = history.get(prompt_id, {})
        if not job_data:
            continue  # still running

        # collect outputs
        outputs = []
        seen_fnames = set()
        for node_output in job_data.get("outputs", {}).values():
            for key in ("images", "gifs", "videos"):
                for item in node_output.get(key, []):
                    fname     = item.get("filename", "")
                    subfolder = item.get("subfolder", "")
                    ftype     = item.get("type", "output")
                    if ftype != "output" or not fname:
                        continue
                    if fname in seen_fnames:
                        continue
                    seen_fnames.add(fname)
                    src = (COMFYUI_OUTPUT / subfolder / fname
                           if subfolder else COMFYUI_OUTPUT / fname)
                    if src.exists():
                        dest = MEDIA_OUTPUT / fname
                        MEDIA_OUTPUT.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dest)
                        outputs.append((str(dest), key))

        if not outputs:
            batch_total = job.get("batch_total", 1)
            batch_current = job.get("batch_current", 1)
            batch_label = f"（第 {batch_current}/{batch_total} 张）" if batch_total > 1 else ""

            status = job_data.get("status", {})
            if status.get("status_str") == "error":
                err_msg = "unknown"
                node = "?"
                ntype = "?"
                for status_msg in status.get("messages", []):
                    if isinstance(status_msg, list) and len(status_msg) >= 2 and status_msg[0] == "execution_error":
                        detail = status_msg[1]
                        node = detail.get("node_id", "?")
                        ntype = detail.get("node_type", "?")
                        err_msg = str(detail.get("exception_message", "unknown")).strip()
                        break
                send_text(chat_id,
                    f"❌ 生成失败{batch_label}\n"
                    f"workflow: {workflow}\n"
                    f"node: {node} ({ntype})\n"
                    f"error: {err_msg[:220]}")
            else:
                send_text(chat_id,
                    f"❌ 生成完成但无输出文件{batch_label}\n"
                    f"workflow: {workflow}\n"
                    f"status: {status.get('status_str', 'unknown')}")

            # Batch: continue with remaining even if one fails
            batch_ok   = job.get("batch_ok", 0)
            batch_fail = job.get("batch_fail", 0) + 1
            if batch_total > 1 and batch_current < batch_total and gen_flow and user_id:
                st = GEN_STATE.get(int(user_id))
                if st:
                    next_n = batch_current + 1
                    send_text(chat_id, f"⚠️ 第 {batch_current}/{batch_total} 张失败，跳过继续...")
                    st["_batch_ok"] = batch_ok
                    st["_batch_fail"] = batch_fail
                    _submit_batch_next(int(user_id), st, batch_total, next_n)
                    # Reload pending — same stale-dict fix as the success path
                    pending = load_pending()
                    pending.pop(prompt_id, None)
                    save_pending(pending)
                    changed = False
                    continue

            del pending[prompt_id]
            changed = True
            if gen_flow and user_id:
                st = GEN_STATE.get(int(user_id))
                if st:
                    st.pop("_batch_ok", None)
                    st.pop("_batch_fail", None)
                    st["step"] = "result"
                    _save_gen_state()
                    if batch_total > 1:
                        send_text(chat_id,
                            f"⚠️ 批量结束：完成 {batch_ok}/{batch_total} 张，失败 {batch_fail}/{batch_total} 张")
            continue

        # ── Batch tracking info ──
        batch_total = job.get("batch_total", 1)
        batch_current = job.get("batch_current", 1)
        batch_label = f"（{batch_current}/{batch_total}）" if batch_total > 1 else ""

        caption = f"✅ 生成完成！{batch_label}\n{prompt[:80]}{'...' if len(prompt) > 80 else ''}"

        # ── Send to Telegram + local archive ──
        tg_ok = True
        archive_ok = True
        for seq_i, (file_path, ftype) in enumerate(outputs, start=1):
            # Send to Telegram
            tg_msg_id = None
            try:
                if ftype == "images":
                    resp = send_photo(chat_id, file_path, caption)
                else:
                    resp = send_video(chat_id, file_path, caption)
                tg_msg_id = resp.get("result", {}).get("message_id") if resp else None
            except Exception as e:
                tg_ok = False
                send_text(chat_id, f"❌ Telegram 发送失败: {e}\n文件: {Path(file_path).name}")

            # Local archive save
            archive_path = save_to_archive(file_path, ftype, job, prompt_id,
                                           tg_message_id=tg_msg_id, seq=seq_i)
            if not archive_path:
                archive_ok = False

        # Log divergent results
        if tg_ok and not archive_ok:
            print(f"[warn] Telegram OK but local archive FAILED for {prompt_id[:8]}", flush=True)
        if not tg_ok and archive_ok:
            print(f"[warn] Local archive OK but Telegram FAILED for {prompt_id[:8]}", flush=True)

        # ── Batch: check if more to generate ──
        batch_ok   = job.get("batch_ok", 0) + 1
        batch_fail = job.get("batch_fail", 0)
        if batch_total > 1 and batch_current < batch_total and gen_flow and user_id:
            st = GEN_STATE.get(int(user_id))
            if st:
                st["_batch_ok"] = batch_ok
                st["_batch_fail"] = batch_fail
                # Submit next in batch
                _submit_batch_next(int(user_id), st, batch_total, batch_current + 1)
                # Reload pending from file — _submit_batch_next wrote the new
                # entry to disk; our in-memory dict is stale and would overwrite it.
                pending = load_pending()
                pending.pop(prompt_id, None)
                save_pending(pending)
                changed = False  # already saved
                continue

        # ── Send result keyboard (final or single) ──
        try:
            if gen_flow:
                has_src = bool(job.get("source_image"))
                st_mode = GEN_STATE.get(int(user_id), {}).get("mode", "image") if user_id else "image"
                is_img = (st_mode == "image")
                if batch_total > 1:
                    if batch_fail > 0:
                        summary = f"✅ 批量结束：完成 {batch_ok}/{batch_total} 张，失败 {batch_fail} 张"
                    else:
                        summary = f"✅ 本次完成 {batch_ok}/{batch_total} 张"
                    send_menu(chat_id, summary, build_result_keyboard(has_src, is_img))
                else:
                    send_menu(chat_id, "✅ 生成完成！", build_result_keyboard(has_src, is_img))
                if user_id:
                    st = GEN_STATE.get(int(user_id))
                    if st:
                        st.pop("_batch_ok", None)
                        st.pop("_batch_fail", None)
                        st["step"] = "result"
                        _save_gen_state()
            else:
                send_menu(chat_id, "🔁 同样参数重新生成一张？",
                          [[{"text": "🔄 再来一张", "callback_data": "re:"}]])
        except Exception:
            pass

        del pending[prompt_id]
        changed = True
        print(f"[delivered] {prompt_id[:8]} → chat {chat_id} ({len(outputs)} files)", flush=True)

    if changed:
        save_pending(pending)


# ── Main polling loop ─────────────────────────────────────
PID_FILE = WORKSPACE / "tmp" / "comfygram-bot.pid"


def _acquire_pid_lock():
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            import signal
            os.kill(old_pid, 0)
            print(f"[bot] already running (pid={old_pid}), exiting", flush=True)
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            pass
    PID_FILE.write_text(str(os.getpid()))


def _release_pid_lock():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def main():
    _acquire_pid_lock()
    import atexit
    atexit.register(_release_pid_lock)

    # Ensure dirs
    for d in [WORKSPACE / "tmp", WORKSPACE / "inbox", MEDIA_INPUT, MEDIA_OUTPUT, OUTPUT_ARCHIVE]:
        d.mkdir(parents=True, exist_ok=True)

    # Load persisted gen state
    _load_gen_state()

    bot_username = os.environ.get("TG_BOT_USERNAME", "ComfyGramBot")
    print(f"[bot] @{bot_username} starting... pid={os.getpid()}", flush=True)
    print(f"[bot] workspace: {WORKSPACE}", flush=True)
    print(f"[bot] registry: {len(REG.get('models',{}))} models, {len(REG.get('loras',{}))} loras", flush=True)

    # Register left-side menu commands (idempotent)
    try:
        register_bot_commands()
        print("[bot] setMyCommands registered: /start /help /status /cancel", flush=True)
    except Exception as e:
        print(f"[bot] setMyCommands failed: {e}", flush=True)

    # Start result poller thread
    t = threading.Thread(target=result_poll_loop, daemon=True)
    t.start()
    print(f"[bot] result poller started (interval={POLL_INTERVAL}s)", flush=True)

    offset = load_offset()
    print(f"[bot] polling from offset={offset}", flush=True)

    while True:
        try:
            resp = _tg_get("getUpdates", {
                "offset":          offset,
                "timeout":         30,
                "allowed_updates": json.dumps(["message", "callback_query"]),
            }, timeout=35)

            updates = resp.get("result", [])
            for update in updates:
                update_id = update["update_id"]
                offset    = update_id + 1

                # Global update dedup — prevents reprocessing if offset resets
                if update_id in _PROCESSED_UPDATE_IDS:
                    continue
                _PROCESSED_UPDATE_IDS.add(update_id)
                if len(_PROCESSED_UPDATE_IDS) > _MAX_PROCESSED_UPDATES:
                    _PROCESSED_UPDATE_IDS.clear()
                    _PROCESSED_UPDATE_IDS.add(update_id)

                cb  = update.get("callback_query")
                msg = update.get("message")

                if cb:
                    # Skip stale callbacks from messages older than 24 hours
                    cb_msg_time = cb.get("message", {}).get("date", 0)
                    if cb_msg_time and time.time() - cb_msg_time > 86400:
                        answer_callback(cb.get("id", ""))
                        continue
                    try:
                        handle_callback(update)
                    except Exception as e:
                        print(f"[handle_callback] error: {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                elif msg:
                    msg_time = msg.get("date", 0)
                    if time.time() - msg_time > 300:
                        continue
                    try:
                        handle_message(msg)
                    except Exception as e:
                        print(f"[handle_message] error: {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                        try:
                            send_text(msg["chat"]["id"], f"❌ 内部错误: {e}")
                        except Exception:
                            pass

            # Batch-save offset and state after processing all updates
            if updates:
                save_offset(offset)
                _save_gen_state()

        except KeyboardInterrupt:
            print("[bot] stopped", flush=True)
            break
        except Exception as e:
            print(f"[bot] polling error: {e}", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
