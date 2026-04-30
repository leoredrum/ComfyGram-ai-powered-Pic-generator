"""dual_transfer 菜单 + 回调处理。

回调前缀 dt:，禁止与普通菜单的 m: / tf: / mdl: / l: 等重叠。

子回调命名：
  dt:back        返回主菜单（清 dt_*）
  dt:tk:<track>  选轨道（pose / outfit）
  dt:chgtk       回到选轨道
  dt:go          确认提交
"""

from pathlib import Path

from .registry import get_track, load_registry
from .state import reset_dt


def _kb_back() -> list:
    return [[{"text": "← 返回", "callback_data": "dt:back"}]]


def _push_menu(host, state: dict, text: str, kb: list) -> None:
    chat_id = state["chat_id"]
    msg_id = state.get("last_menu_msg_id")
    if msg_id:
        resp = host.edit_menu(chat_id, msg_id, text, kb)
        if resp.get("ok"):
            return
    resp = host.send_menu(chat_id, text, kb)
    if resp.get("ok"):
        state["last_menu_msg_id"] = resp["result"]["message_id"]


# ── 入口 ──────────────────────────────────────────────────

def show_track_entry(host, user_id: int, state: dict) -> None:
    """从主菜单选择 "🔀 双图迁移" 后的第一个落点：选轨道。"""
    state["mode"] = "dual_transfer"
    state["step"] = "dual_transfer_flow"
    reset_dt(state)
    host.save_state(user_id)
    _show_track_menu(host, user_id, state)


def _show_track_menu(host, user_id: int, state: dict) -> None:
    state["dt_step"] = "select_track"
    host.save_state(user_id)
    reg = load_registry()
    rows = []
    for track_id, track in reg.get("tracks", {}).items():
        rows.append([{
            "text": track["display_cn"],
            "callback_data": f"dt:tk:{track_id}",
        }])
    rows.append([{"text": "← 返回主菜单", "callback_data": "dt:back"}])
    text = "🔀 双图迁移\n\n选择迁移轨道："
    _push_menu(host, state, text, rows)


def _show_await_a(host, user_id: int, state: dict) -> None:
    state["dt_step"] = "await_a"
    host.save_state(user_id)
    track = get_track(state.get("dt_track")) or {}
    text = (
        f"🔀 双图迁移 — {track.get('display_cn', '')}\n\n"
        "请发送 A 图（角色图）\n这张图的角色 identity 会被锁定到结果中"
    )
    _push_menu(host, state, text, _kb_back())


def _show_await_b(host, user_id: int, state: dict) -> None:
    state["dt_step"] = "await_b"
    host.save_state(user_id)
    track = state.get("dt_track")
    if track == "pose":
        hint = "B 图（姿势参考）：会用 DWPose 抽骨架"
    elif track == "outfit":
        hint = "B 图（服装参考）：仅取衣物风格/颜色"
    else:
        hint = "B 图（条件源）"
    text = f"✅ A 图已保存\n\n请发送 B 图\n{hint}"
    _push_menu(host, state, text, _kb_back())


def _show_confirm(host, user_id: int, state: dict) -> None:
    state["dt_step"] = "confirm"
    host.save_state(user_id)
    track = get_track(state.get("dt_track")) or {}
    img_a = Path(state["dt_image_a"]).name if state.get("dt_image_a") else "未设置"
    img_b = Path(state["dt_image_b"]).name if state.get("dt_image_b") else "未设置"
    text = (
        f"🔀 双图迁移 — 确认\n\n"
        f"轨道：{track.get('display_cn', '')}\n"
        f"A 图（角色）：{img_a}\n"
        f"B 图（条件）：{img_b}\n\n"
        f"确认后将提交 ComfyUI 生成"
    )
    rows = [
        [{"text": "✅ 确认生成", "callback_data": "dt:go"}],
        [{"text": "🔄 换轨道", "callback_data": "dt:chgtk"}],
        [{"text": "← 返回主菜单", "callback_data": "dt:back"}],
    ]
    _push_menu(host, state, text, rows)


# ── 回调分发 ──────────────────────────────────────────────

def handle_dt_callback(host, user_id: int, state: dict, sub: str, msg_id) -> None:
    """sub 是 "dt:" 前缀去掉后的部分，例如 "tk:pose" / "go" / "back"。"""
    if sub == "back":
        reset_dt(state)
        state["mode"] = "image"
        host.save_state(user_id)
        host.show_mode_menu(user_id, state, edit_msg_id=msg_id)
        return

    if sub == "chgtk":
        reset_dt(state)
        host.save_state(user_id)
        _show_track_menu(host, user_id, state)
        return

    if sub.startswith("tk:"):
        track_id = sub[3:]
        track = get_track(track_id)
        if track is None:
            host.send_text(state["chat_id"], "❌ 未知轨道")
            return
        if track.get("status") != "active":
            wip = track.get("wip_message", "该轨道开发中")
            host.send_text(state["chat_id"], f"🚧 {wip}")
            return
        state["dt_track"] = track_id
        host.save_state(user_id)
        _show_await_a(host, user_id, state)
        return

    if sub == "go":
        from .pipeline import submit_dt_job
        submit_dt_job(host, user_id, state)
        return


# ── 图片上传分发 ──────────────────────────────────────────

def on_photo(host, user_id: int, state: dict, downloaded_path: str, caption: str) -> bool:
    """tg_bot 在 step=='dual_transfer_flow' 时把图片喂进来。返回 True 表示已处理。"""
    if state.get("step") != "dual_transfer_flow":
        return False
    ts = state.get("dt_step")
    if ts == "await_a":
        state["dt_image_a"] = downloaded_path
        if caption:
            state["dt_user_prompt"] = caption
        host.save_state(user_id)
        _show_await_b(host, user_id, state)
        return True
    if ts == "await_b":
        state["dt_image_b"] = downloaded_path
        if caption:
            cur = (state.get("dt_user_prompt") or "").strip()
            state["dt_user_prompt"] = f"{cur}, {caption}".strip(", ") if cur else caption
        host.save_state(user_id)
        _show_confirm(host, user_id, state)
        return True
    host.send_text(state["chat_id"], "当前步骤不需要图片，请按菜单操作。")
    return True
