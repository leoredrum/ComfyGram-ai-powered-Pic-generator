#!/usr/bin/env python3
"""Scan material directory and rebuild material_registry.json"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(os.environ.get("IMAGECREATOR_WORKSPACE", "./workspace"))
MATERIAL_ROOT = Path(os.environ.get("MATERIAL_ROOT_DIR", "./material"))
REGISTRY_PATH = WORKSPACE / "material_registry.json"
OVERRIDES_PATH = WORKSPACE / "material_registry_overrides.json"

# Family directory mapping
MODEL_FAMILY_DIRS = {
    "pvc": MATERIAL_ROOT / "model" / "pvc",
    "2d": MATERIAL_ROOT / "model" / "2d",
    "3d": MATERIAL_ROOT / "model" / "3d",
}
LORA_FAMILY_DIRS = {
    "pvc": MATERIAL_ROOT / "lora" / "pvc",
    "2d": MATERIAL_ROOT / "lora" / "2d",
    "3d": MATERIAL_ROOT / "lora" / "3d",
}
LORA_ORPHAN_DIR = MATERIAL_ROOT / "lora"
LORA_NON_ORPHAN_NAMES = {"pvc", "2d", "3d"}

# ComfyUI path prefixes for models
MODEL_COMFYUI_PREFIX = {
    "pvc": "pvc",
    "2d": "2d",
    "3d": "3d",
}
# ComfyUI path prefixes for loras
LORA_COMFYUI_PREFIX = {
    "pvc": "pvc",
    "2d": "2d",
    "3d": "3d",
}

DISPLAY_NAME_OVERRIDES = {
    # Figure models
    "Deng_PVC_XL_Mix2": "邓版手办XL",
    "PVC_STYLE": "PVC写实",
    "[PVC Style Model] MiaoMiao Dollie": "喵喵娃娃",
    "[PVC Style Model]Movable figure model Pony": "活动手办P",
    "[PVC Style Model]Movable figure model XL": "活动手办XL",
    "[PVC Style Model]Movable figure model": "活动手办",
    "欧派的手办定制(PVC model)": "欧派手办",
    # 2D models
    "One obsession Branch（Mature.NoobAi.Vpred）": "执念成熟",
    "Ultimate Hentai Anime RX - ( T-Rex ) - Anime ScreenShot -  CHECKPOINT - Illustrious XL  - by YeiyeiArt": "T-Rex色漫",
    "WAI-illustrious-SDXL": "WAI插画",
    # 3D models
    "Asian Realism By Stable Yogi (PONY)": "亚裔写实P",
    "Big Lust": "大欲写实",
    "Moody Porn Mix": "暗调色情",
    "PornMaster-色情大师": "色情大师",
    # Figure LoRAs
    "Figure Anime Style": "手办动漫",
    "Figure creation": "手办生成",
    "Qwen Edit Figure Maker By Aldniki": "Qwen手办",
    "[PonyXL + Illustrious] Concept - Anime Figures": "动漫手办",
    "figure_photo_style": "手办摄影",
    # Orphan figure LoRAs
    "PVC Figurerizer Lora Edition": "PVC化",
    "PVC figure SDXL": "PVC手办XL",
    "PVC-chiwu": "PVC赤武",
    "Pvc_NSFW_TENTACLES": "触手手办",
    # 2D LoRAs
    "'90 anime style": "90年代风",
    "(ILXL) Hug From Behind-emphasize breasts  後ろからハグ": "后拥挤胸",
    "(ILXL) Kankaku Shadan Trap  感覚遮断落とし穴": "感觉遮断",
    "(ILXL) Reverse Fellatio  逆さフェラ": "逆向口爱",
    "(wan 2.2 experimental) WAN General NSFW model": "WAN色情",
    "90's Retro  Illustrious  NoobAI Style Lora": "复古90风",
    "90's anime melancholy illustriousXLZImageTurboFluxChroma": "忧郁动漫",
    "All Fours From Below - Concept": "四肢俯视",
    "Breast Expansion WAN 2.2 i2v": "胸扩视频",
    "Cowgirl Position Sex Non-POV  Third Person": "骑乘体位",
    "Cum Pool - Concept": "精液池",
    "Cupless bra & Crotchless Panties": "露乳内衣",
    "Deep Penetration  LoRA": "深入插入",
    "Dripping Pussy Juice From Behind - Concept - COMMISSION": "后视汁液",
    "FUCKED SILLY - Lewd Details Enchancer v2.0  Extreme Sex  IllustriousXL NoobAI Pony XL": "极端性爱",
    "Fondled": "爱抚",
    "Full Nelson - Concept": "抱起体位",
    "Group Sex  Orgy Scene LoRA - High-Quality Group Scene": "群交场景",
    "Hentai Comic Random Generator (FULL COLOR) Pony  IL XL  フルカラーエロ漫画ランダムジェネレーター": "全彩色漫",
    "Hentai Studio Quality illustriousXLZImageTurbo": "高质色漫",
    "Hucow Milking ZIMWan2.1FluxPonySDXL": "奶牛榨乳",
    "Illustrious Style Pack": "画风包",
    "Imminent Penetration - Concept": "临入时刻",
    "JAV HARD BDSM Generator (bondage wall ) Pony  IL XL  拘束少女快楽拷問 アダルト ビデオ ジェネレーター": "拘束凌辱",
    "Kissing Penis - Concept": "亲吻阳具",
    "Lactation SD1.5Pontillustrious": "泌乳",
    "Loose Tank Top": "宽松背心",
    "Mating Press From Above - Concept": "翻折俯视",
    "Mating Press From Side - Concept": "翻折侧视",
    "Micro Panties  Goofy Ai": "微型内裤",
    "Milking machine": "榨乳机",
    "NSFW Bunnysuit": "兔女郎",
    "Nipple and clitoris chain (Illustrious concept)": "乳蒂链",
    "Nuru Massage (Illustrious)": "泥滑按摩",
    "Oily bodystocking -- SDXL and Pony": "油光连体",
    "On Side Missionary - Concept - COMMISSION": "侧卧传教",
    "One-piece swimsuit pull  LoRA": "连体泳衣",
    "POV Missionary-Raised Legs  LoRA": "主视传教",
    "POV Paizuri-Twisted Breasts  LoRA": "主视乳交",
    "Painted clothes (IL+Pony)": "彩绘衣物",
    "Partially Submerged POV - Concept": "半浸主视",
    "Pet Play - Concept": "宠物扮演",
    "Pov sex looking down [Updated] (Missionary + doggy style + mating press)": "俯视主视",
    "Pressed Missionary (Feet on Chest) Multi-Views, Plus Cowgirl!": "压腿传教",
    "Pussy sandwich": "夹阴",
    "Random NSFW Poses - Concept": "随机姿势",
    "Retro Anisthetic Style  Illustrious": "复古美学",
    "Reverse Fellatio - Concept": "逆向口爱2",
    "Sagging Breasts": "下垂乳",
    "Slingshot swimsuit [SD1.5PonyIllustrious]": "弹弓泳衣",
    "Sweaty  Steamy  Musky (Illustrious)": "汗湿蒸腾",
    "T-Rex Studio V2 NEW!!- Hentai +18 -  STYLE  PONY XL  Illustrious XL  - COMMISSION - by YeiyeiArt": "T-Rex画风",
    "Taretiti (sagging breasts)  垂れ乳": "垂乳",
    "Tomonori Kogawa Style  70's,80's,90's style": "古川风格",
    "Too Deep  Too Rough": "暴力深插",
    "Undressing - Concept": "脱衣概念",
    "Wilhelmina - Browndust2  ブラウンダスト2 - ウィルヘルミナ[Pony,Illustrious]": "威廉娜",
    "X-ray glasses": "透视眼镜",
    "[Illustrious-XL] Nipple LORA for ADetailer  ADetailer用の乳首LORA": "乳头细化",
    "[concept]dildo under clothes xl": "衣下情趣",
    "multiple pussy": "多重阴部",
    "plastic bag　ビニール袋": "塑料袋",
    "shiny wet skin": "湿润光肤",
    "だいしゅきホールドleg lock": "爱意夹腿",
    "まんぐり返しfolded pose(XL,ill,pony)": "折叠体位",
    "ヴィーナスビキニVenus bikini(pony)": "女神泳装",
    "クリトリスジュエリーclitoris jewelry(XL,ILL,pony)": "阴蒂装饰",
    "クロスビキニcross bikini": "交叉泳装",
    "セクシーランジェリーsexy lingerie(SD,ILL,pony)": "性感内衣",
    "バンドエイドbandaid": "创可贴",
    "ハーネスharness(SD,XL,pony)": "束缚绳",
    "フィンガリングfingering": "手指爱抚",
    "ポールダンスpole dancing": "钢管舞",
    "マン汁pussy juice": "爱液",
    "メイドビキニmaid bikini(XL,ILL,pony)": "女仆泳装",
    "ローションプレイlotion play(XL,ill,pony)": "乳液嬉戏",
    "乳首責めnipple pull(ill,pony)": "乳首责",
    "二穴責めdouble insertion(ILL,pony)": "双穴责",
    "仕込みローター vibrator under clothes(ILL,pony)": "衣下震动",
    "使用済みコンドームused condom(ill,pony)": "用过避孕套",
    "温泉onsen(XL,ill,pony)": "温泉场景",
    "潮吹き female ejaculation": "女性潮吹",
    "縛りshibari(SD,XL,ILL,pony)": "绑缚",
    "脱ぎかけclothes pull(ill,pony)": "脱衣进行",
    "裂けた服torn clothes(ill,pony)": "破衣",
    "裸リボンnaked ribbon(SD,XL,ill,pony)": "裸身彩带",
    "透明バニーガールtransparent bunny girl(XL,pony)": "透明兔女郎",
    "顔面騎乗位Face Sitting": "骑脸",
    "食い込みWedgie(XL,pony)": "陷入内裤",
    "駅弁suspended congress": "驿便体位",
    # 3D LoRAs
    "A Queen's Breasts  Z-image Turbo + Flux + Pony + ILL": "女王乳房",
    "Breast Expansion WAN 2.2 i2v": "胸扩视频3D",
    "Breast Squeeze and Lactation (Milk spray, milking) WAN 2.1 i2vt2v model": "挤乳喷射",
    "Coco's Sexy Clothing Collection CoCo最爱的性感服装合集": "Coco性感装",
    "Fondled": "爱抚3D",
    "Hip swayAss shaking dance Wan 2.2 I2V": "臀部摇摆",
    "Hucow Milking ZIMWan2.1FluxPonySDXL": "奶牛榨乳3D",
    "JellyHips - Hun  Wan Video Lora - K3NK": "果冻臀",
    "MCNL (Multi Concept NSFW Lora) [Qwen Image]": "多概念色",
    "Nude Art": "裸体艺术",
    "OB拍立得人像摄影 Instant camera portrait photography": "拍立得像",
    "PhotoReal BetterNudes  NSFW": "真实裸体",
    "Qwen-image_NSFW_Adv.1": "Qwen色图",
    "Real Pussy - Peach": "真实私处",
    "Standing Doggystyle (breast & hand movement enhanced) WAN2.1 i2v": "站立后入",
    "Turbo Pussy Z": "速射私处",
    "Wan 2.2 Massage tits by MQ Lab": "乳房按摩",
    "Wan2.2 - Korean Women": "韩国女性",
    "better nipples and pussy": "细化私处",
    "娜乌斯嘉nwsj_realistic": "娜乌斯嘉",
}

FAMILY_DEFAULTS = {
    "pvc": {
        "recommended_params": {
            "steps": 25,
            "cfg": 7,
            "sampler": "euler",
            "scheduler": "karras",
            "width": 1024,
            "height": 1024,
            "clip_skip": 2,
        },
        "default_prompt": "pvc figure, 1girl, white background, high quality",
        "default_negative_prompt": "blurry, bad anatomy, ugly, watermark, low quality, deformed",
    },
    "2d": {
        "recommended_params": {
            "steps": 25,
            "cfg": 5,
            "sampler": "euler",
            "scheduler": "karras",
            "width": 1024,
            "height": 1024,
            "clip_skip": 1,
        },
        "default_prompt": "1girl, anime style, high quality, detailed",
        "default_negative_prompt": "blurry, bad anatomy, ugly, watermark, low quality, deformed, worst quality",
    },
    "3d": {
        "recommended_params": {
            "steps": 25,
            "cfg": 7,
            "sampler": "dpmpp_2m",
            "scheduler": "karras",
            "width": 1024,
            "height": 1024,
            "clip_skip": 2,
        },
        "default_prompt": "1girl, realistic, high quality, detailed",
        "default_negative_prompt": "blurry, bad anatomy, ugly, watermark, cartoon, anime",
    },
}

# Folders known to use ZImageTurbo (incompatible with telegram)
ZIMT_DISABLED = {"Moody Porn Mix"}


def find_main_model_file(folder: Path) -> Path | None:
    """Find the main .safetensors file in a folder, skipping embeddings."""
    safetensors = [f for f in folder.iterdir() if f.suffix == ".safetensors"]
    if not safetensors:
        return None

    # Filter out embedding files
    embedding_patterns = ["-neg", "_neg", "_negative", "positives", "_pos"]

    def is_embedding(p: Path) -> bool:
        fname_low = p.name.lower()
        return any(pat in fname_low for pat in embedding_patterns)

    candidates = [f for f in safetensors if not is_embedding(f)]

    if not candidates:
        # All are embeddings — fall back to all
        candidates = safetensors

    if len(candidates) == 1:
        return candidates[0]

    # Multiple candidates: pick the largest
    return max(candidates, key=lambda p: p.stat().st_size)


def detect_arch(folder_name: str, filename: str, txt_content: str) -> str:
    """Detect model architecture from folder name, filename, and txt content."""
    txt_low = txt_content.lower()
    fname_low = filename.lower()
    folder_low = folder_name.lower()

    # Check txt content first (Base Model lines and keywords)
    if "wan video" in txt_low or "wan2" in txt_low or "wan 2" in txt_low:
        return "wan"
    if "sd 1.5" in txt_low or "sd1.5" in txt_low:
        return "sd15"
    if "illustrious" in txt_low and "noob" in txt_low:
        return "noob"
    if "illustrious" in txt_low:
        return "illustrious"
    if "noobai" in txt_low or "noob ai" in txt_low:
        return "noob"
    if "pony" in txt_low or "pdxl" in txt_low:
        return "pony"
    if "zimagetu" in txt_low or "zit" in fname_low or "zimageturbo" in txt_low.replace(" ", ""):
        return "zimt"
    if "sdxl" in txt_low or "sdxl" in fname_low:
        return "sdxl"

    # Filename hints
    if "_il" in fname_low or "ilv" in fname_low:
        return "illustrious"
    if "pony" in fname_low or "pony" in folder_low:
        return "pony"
    if "_xl" in fname_low or "xl" in fname_low:
        return "sdxl"

    return "sdxl"  # default


def is_wan_lora(folder_name: str) -> bool:
    """Check if a LoRA folder name indicates WAN architecture."""
    wan_keywords = ["WAN", "Wan", "wan", "i2v", "I2V", "t2v"]
    for kw in wan_keywords:
        if kw in folder_name:
            return True
    return False


def parse_txt(txt_path: Path) -> dict:
    """Parse the info txt file and extract useful metadata."""
    result = {
        "base_model": "",
        "strength": None,
        "trigger_words": [],
        "recommended_params": {},
        "default_prompt": "",
        "notes": "",
    }

    if not txt_path.exists():
        return result

    try:
        content = txt_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return result

    result["notes"] = content[:800]

    lines = content.splitlines()

    # Extract base model
    for i, line in enumerate(lines):
        if line.strip() == "Base Model":
            # Look for next non-empty line
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip():
                    result["base_model"] = lines[j].strip()
                    break
            break
        if re.match(r"Base Model\s*:", line, re.IGNORECASE):
            result["base_model"] = re.sub(r"Base Model\s*:\s*", "", line, flags=re.IGNORECASE).strip()
            break

    # Extract strength/weight
    for line in lines:
        m = re.search(r"(?:Strength|Weight)\s*[:\s]+([0-9.]+)", line, re.IGNORECASE)
        if m:
            try:
                result["strength"] = float(m.group(1))
            except ValueError:
                pass
            break

    # Extract trigger words
    trigger_section = False
    trigger_lines = []
    for i, line in enumerate(lines):
        if re.search(r"Trigger\s+Words?", line, re.IGNORECASE):
            trigger_section = True
            continue
        if trigger_section:
            stripped = line.strip()
            if stripped:
                # Stop if we hit another section header
                if re.match(r"^(Hash|AIR|Type|Stats|Published|Base Model|Usage Tips|Training|Reviews|Details)\s*$", stripped):
                    break
                trigger_lines.append(stripped)
                if len(trigger_lines) >= 3:
                    break

    if trigger_lines:
        result["trigger_words"] = trigger_lines

    # Extract recommended params
    params = {}
    for line in lines:
        # CFG
        m = re.search(r"CFG\s*[:\s]+([0-9.~\-]+)", line, re.IGNORECASE)
        if m and "cfg" not in params:
            val_str = m.group(1).strip()
            # Handle ranges like "2~4" or "5-7"
            range_m = re.match(r"([0-9.]+)\s*[~\-]\s*([0-9.]+)", val_str)
            if range_m:
                try:
                    params["cfg"] = (float(range_m.group(1)) + float(range_m.group(2))) / 2
                except ValueError:
                    pass
            else:
                try:
                    params["cfg"] = float(val_str)
                except ValueError:
                    pass

        # Steps
        m = re.search(r"Steps\s*[:\s]+([0-9]+)", line, re.IGNORECASE)
        if m and "steps" not in params:
            try:
                params["steps"] = int(m.group(1))
            except ValueError:
                pass

        # Sampler
        m = re.search(r"Sampler\s*[:\s]+(.+)", line, re.IGNORECASE)
        if m and "sampler" not in params:
            params["sampler"] = m.group(1).strip()

        # Clip skip
        m = re.search(r"Clip\s*Skip\s*[:\s]+([0-9]+)", line, re.IGNORECASE)
        if m and "clip_skip" not in params:
            try:
                params["clip_skip"] = int(m.group(1))
            except ValueError:
                pass

    result["recommended_params"] = params

    # Extract default_prompt from trigger words (strip lora tag)
    if result["trigger_words"]:
        first_trigger = result["trigger_words"][0]
        # Remove <lora:...> tags
        cleaned = re.sub(r"<lora:[^>]+>", "", first_trigger).strip().strip(",").strip()
        result["default_prompt"] = cleaned

    return result


def generate_display_name(folder_name: str, family: str, arch: str) -> str:
    """Generate a Chinese display name for a folder."""
    if folder_name in DISPLAY_NAME_OVERRIDES:
        return DISPLAY_NAME_OVERRIDES[folder_name]

    # Keyword fallback: try to extract meaningful CN name from folder name
    # Check for common keywords
    fname_low = folder_name.lower()

    # Architecture suffix
    arch_suffix = ""
    if arch == "pony":
        arch_suffix = "P"
    elif arch == "illustrious":
        arch_suffix = "IL"
    elif arch == "noob":
        arch_suffix = "N"
    elif arch == "wan":
        arch_suffix = "W"
    elif arch == "sd15":
        arch_suffix = "15"

    # Family prefix hints
    if family == "pvc":
        prefix = "手办"
    elif family == "2d":
        prefix = "二次元"
    else:
        prefix = "写实"

    # Try to use first meaningful word from folder name (strip brackets, special chars)
    clean = re.sub(r"[\[\]()（）{}]", " ", folder_name)
    # Remove arch keywords
    clean = re.sub(r"\b(SDXL|XL|Pony|Illustrious|NoobAI|SD1\.5|SD 1\.5|LoRA|Lora|LORA|Concept|WAN|Wan|I2V|i2v)\b", "", clean, flags=re.IGNORECASE)
    clean = clean.strip(" -_,.")

    # Take first token (up to 10 chars)
    tokens = [t for t in re.split(r"[\s\-_]+", clean) if t and len(t) > 1]
    if tokens:
        short = tokens[0][:10]
        return f"{short}{arch_suffix}"

    return f"{prefix}{arch_suffix}" if arch_suffix else prefix


def read_name_txt(folder: Path) -> str | None:
    """Read name.txt from folder, return stripped content or None if missing/empty."""
    name_file = folder / "name.txt"
    if not name_file.exists():
        return None
    try:
        content = name_file.read_text(encoding="utf-8", errors="replace").strip()
        return content if content else None
    except Exception:
        return None


def scan_models() -> dict:
    """Scan all model directories and return model entries."""
    models = {}

    for family, family_dir in MODEL_FAMILY_DIRS.items():
        if not family_dir.exists():
            print(f"WARNING: Model family dir not found: {family_dir}")
            continue

        for folder in sorted(family_dir.iterdir()):
            if not folder.is_dir():
                continue

            folder_name = folder.name
            main_file = find_main_model_file(folder)

            if main_file is None:
                print(f"WARNING: No .safetensors found in {folder}")
                continue

            txt_path = folder / "新建 文本文档.txt"
            txt_info = parse_txt(txt_path)

            arch = detect_arch(folder_name, main_file.name, txt_info["notes"])

            # supported_modes
            if arch == "wan":
                supported_modes = ["i2v"]
            else:
                supported_modes = ["t2i", "i2i"]

            # telegram_enabled
            telegram_enabled = True
            if arch == "sd15":
                telegram_enabled = False
            if folder_name in ZIMT_DISABLED:
                telegram_enabled = False

            # display name: name.txt > override > generated
            name_txt_val = read_name_txt(folder)
            if name_txt_val:
                display_name_cn = name_txt_val
            else:
                display_name_cn = generate_display_name(folder_name, family, arch)

            # ComfyUI model path
            comfyui_prefix = MODEL_COMFYUI_PREFIX[family]
            comfyui_model_name = f"{comfyui_prefix}/{folder_name}/{main_file.name}"

            key = f"{family}/{folder_name}"

            rec_params = txt_info["recommended_params"]

            # Illustrious / NoobAI models require clip_skip>=2 (layer 11
            # of CLIP-L is untrained and may contain NaN weights).
            if arch in ("illustrious", "noob") and "clip_skip" not in rec_params:
                rec_params["clip_skip"] = 2
                print(f"[auto-fix] {folder_name}: detected as {arch}, default clip_skip=2 applied")

            models[key] = {
                "asset_type": "model",
                "family": family,
                "source_dir": str(folder),
                "asset_folder_name": folder_name,
                "original_name": folder_name,
                "display_name_cn": display_name_cn,
                "model_file": main_file.name,
                "comfyui_model_name": comfyui_model_name,
                "info_txt_path": str(txt_path) if txt_path.exists() else "",
                "file_format": "safetensors",
                "likely_architecture": arch,
                "supported_modes": supported_modes,
                "default_prompt": txt_info["default_prompt"],
                "default_negative_prompt": "",
                "recommended_params": rec_params,
                "telegram_enabled": telegram_enabled,
                "notes": txt_info["notes"],
            }

    return models


def scan_loras() -> dict:
    """Scan all lora directories and return lora entries."""
    loras = {}

    # Scan family lora dirs
    for family, family_dir in LORA_FAMILY_DIRS.items():
        if not family_dir.exists():
            print(f"WARNING: LoRA family dir not found: {family_dir}")
            continue

        for folder in sorted(family_dir.iterdir()):
            if not folder.is_dir():
                continue

            folder_name = folder.name
            main_file = find_main_model_file(folder)

            if main_file is None:
                print(f"WARNING: No .safetensors found in {folder}")
                continue

            txt_path = folder / "新建 文本文档.txt"
            txt_info = parse_txt(txt_path)

            # For lora3d, check if WAN
            if family == "3d" and is_wan_lora(folder_name):
                arch = "wan"
            else:
                arch = detect_arch(folder_name, main_file.name, txt_info["notes"])

            # supported_modes
            if arch == "wan":
                supported_modes = ["i2v"]
            else:
                supported_modes = ["t2i", "i2i"]

            # telegram_enabled: WAN loras are enabled (video mode)
            telegram_enabled = True
            if arch == "sd15":
                telegram_enabled = False

            # recommended_strength
            if txt_info["strength"] is not None:
                recommended_strength = txt_info["strength"]
            elif family == "pvc":
                recommended_strength = 1.0
            else:
                recommended_strength = 0.8

            # display name: name.txt > override > generated
            name_txt_val = read_name_txt(folder)
            if name_txt_val:
                display_name_cn = name_txt_val
            else:
                display_name_cn = generate_display_name(folder_name, family, arch)

            # ComfyUI lora path
            comfyui_prefix = LORA_COMFYUI_PREFIX[family]
            comfyui_lora_name = f"{comfyui_prefix}/{folder_name}/{main_file.name}"

            key = f"{family}/{folder_name}"

            loras[key] = {
                "asset_type": "lora",
                "family": family,
                "source_dir": str(folder),
                "asset_folder_name": folder_name,
                "original_name": folder_name,
                "display_name_cn": display_name_cn,
                "lora_file": main_file.name,
                "comfyui_lora_name": comfyui_lora_name,
                "info_txt_path": str(txt_path) if txt_path.exists() else "",
                "file_format": "safetensors",
                "likely_architecture": arch,
                "supported_modes": supported_modes,
                "default_prompt": txt_info["default_prompt"],
                "default_negative_prompt": "",
                "recommended_strength": recommended_strength,
                "telegram_enabled": telegram_enabled,
                "notes": txt_info["notes"],
            }

    # Scan orphan loras (direct children of lora/ that are not lorafigure/lora2d/lora3d)
    if LORA_ORPHAN_DIR.exists():
        for folder in sorted(LORA_ORPHAN_DIR.iterdir()):
            if not folder.is_dir():
                continue
            if folder.name in LORA_NON_ORPHAN_NAMES:
                continue

            folder_name = folder.name
            family = "pvc"  # orphan loras are all pvc family

            main_file = find_main_model_file(folder)

            if main_file is None:
                print(f"WARNING: No .safetensors found in orphan lora {folder}")
                continue

            txt_path = folder / "新建 文本文档.txt"
            txt_info = parse_txt(txt_path)

            arch = detect_arch(folder_name, main_file.name, txt_info["notes"])

            if arch == "wan":
                supported_modes = ["i2v"]
            else:
                supported_modes = ["t2i", "i2i"]

            telegram_enabled = True
            if arch == "sd15":
                telegram_enabled = False

            if txt_info["strength"] is not None:
                recommended_strength = txt_info["strength"]
            else:
                recommended_strength = 1.0  # pvc default

            # display name: name.txt > override > generated
            name_txt_val = read_name_txt(folder)
            if name_txt_val:
                display_name_cn = name_txt_val
            else:
                display_name_cn = generate_display_name(folder_name, family, arch)

            # Orphan loras use a special prefix
            comfyui_lora_name = f"pvc_orphan/{folder_name}/{main_file.name}"

            key = f"{family}/{folder_name}"

            loras[key] = {
                "asset_type": "lora",
                "family": family,
                "source_dir": str(folder),
                "asset_folder_name": folder_name,
                "original_name": folder_name,
                "display_name_cn": display_name_cn,
                "lora_file": main_file.name,
                "comfyui_lora_name": comfyui_lora_name,
                "info_txt_path": str(txt_path) if txt_path.exists() else "",
                "file_format": "safetensors",
                "likely_architecture": arch,
                "supported_modes": supported_modes,
                "default_prompt": txt_info["default_prompt"],
                "default_negative_prompt": "",
                "recommended_strength": recommended_strength,
                "telegram_enabled": telegram_enabled,
                "notes": txt_info["notes"],
            }

    return loras


def main():
    # Load manual overrides file if present
    overrides = {}
    if OVERRIDES_PATH.exists():
        try:
            overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"WARNING: Could not load overrides file: {e}")

    registry = {
        "_meta": {
            "generated": datetime.now().isoformat(),
            "material_root": str(MATERIAL_ROOT),
            "version": 1,
        },
        "family_defaults": FAMILY_DEFAULTS,
        "models": scan_models(),
        "loras": scan_loras(),
    }

    # Apply overrides (overrides can set display_name_cn, telegram_enabled, etc. per key)
    for key, ovr in overrides.get("models", {}).items():
        if key in registry["models"]:
            registry["models"][key].update(ovr)
        else:
            print(f"WARNING: Override key '{key}' not found in models")

    for key, ovr in overrides.get("loras", {}).items():
        if key in registry["loras"]:
            registry["loras"][key].update(ovr)
        else:
            print(f"WARNING: Override key '{key}' not found in loras")

    REGISTRY_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Print summary
    models = registry["models"]
    loras = registry["loras"]
    print(f"\nScanned: {len(models)} models, {len(loras)} LoRAs")
    for fam in ["pvc", "2d", "3d"]:
        m_count = sum(1 for v in models.values() if v["family"] == fam)
        l_count = sum(1 for v in loras.values() if v["family"] == fam)
        disabled_count = sum(
            1
            for v in {**models, **loras}.values()
            if v["family"] == fam and not v.get("telegram_enabled", True)
        )
        print(f"  {fam}: {m_count} models, {l_count} LoRAs ({disabled_count} disabled)")
    print(f"\nWritten to {REGISTRY_PATH}")


if __name__ == "__main__":
    main()
