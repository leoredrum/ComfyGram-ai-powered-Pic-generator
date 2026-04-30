"""dual_transfer 提交逻辑。与普通 submit_gen_job 完全分离。"""

import json
import random
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from .prompt import build_dt_prompt
from .registry import get_track
from .state import reset_dt


def submit_dt_job(host, user_id: int, state: dict) -> None:
    chat_id = state["chat_id"]

    track_id = state.get("dt_track")
    track = get_track(track_id) if track_id else None
    if not track or track.get("status") != "active":
        host.send_text(chat_id, "❌ 未选择有效轨道")
        return

    img_a = state.get("dt_image_a")
    img_b = state.get("dt_image_b")
    if not img_a or not Path(img_a).exists():
        host.send_text(chat_id, "❌ A 图（角色）缺失，请重新上传。")
        return
    if not img_b or not Path(img_b).exists():
        host.send_text(chat_id, "❌ B 图（条件）缺失，请重新上传。")
        return

    if not host.comfyui_alive():
        host.send_text(chat_id, "❌ ComfyUI 离线，请先启动。")
        return

    state["step"] = "generating"
    host.save_state(user_id)

    msg_id = state.get("last_menu_msg_id")
    notice = f"⏳ 双图迁移生成中（{track.get('display_cn', track_id)}），请稍候..."
    if msg_id:
        host.edit_menu(chat_id, msg_id, notice, [])
    else:
        host.send_text(chat_id, notice)

    workflow_id = track["workflow_id"]
    prompt = build_dt_prompt(track_id, state.get("dt_user_prompt"))

    seed = random.randint(1, 2**32 - 1)
    state["last_seed"] = seed
    host.save_state(user_id)

    img_a = str(host.resize_image(Path(img_a), 1024))
    img_b = str(host.resize_image(Path(img_b), 1024))

    task_prefix = track.get("task_prefix", f"dt-{track_id}")
    task_id = f"{task_prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
    inbox_payload = {
        "task_id": task_id,
        "workflow": workflow_id,
        "params": {
            "prompt": prompt,
            "negative_prompt": "blurry, bad anatomy, deformed, watermark, low quality, ugly",
            "seed": seed,
            "width": 1024,
            "height": 1024,
            "steps": 28,
            "face_image_path": img_a,
            "body_image_path": img_b,
            "mode": "dual_transfer",
            "track": track_id,
        },
    }

    inbox_path = host.workspace / "inbox" / f"{task_id}.json"
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text(json.dumps(inbox_payload, indent=2, ensure_ascii=False))

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(host.workspace / "bin" / "comfyui_client.py"),
                "--task", str(inbox_path),
                "--submit-only",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        host.send_text(chat_id, "❌ ComfyUI 提交超时，请稍后重试。")
        state["step"] = "dual_transfer_flow"
        state["dt_step"] = "confirm"
        host.save_state(user_id)
        return

    prompt_id = None
    for line in result.stdout.splitlines():
        if "[submit] prompt_id=" in line:
            prompt_id = line.split("=", 1)[1].strip()
            break

    if not prompt_id:
        detail = (
            f"submit failed: returncode={result.returncode}\n"
            f"stdout_tail={result.stdout[-1000:] if result.stdout else ''}\n"
            f"stderr_tail={result.stderr[-1000:] if result.stderr else ''}"
        )
        print(f"[dt][submit_dt_job] {detail}", flush=True)
        host.send_text(chat_id, f"❌ 提交失败:\n{detail}")
        state["step"] = "dual_transfer_flow"
        state["dt_step"] = "confirm"
        host.save_state(user_id)
        return

    pending = host.load_pending()
    pending[prompt_id] = {
        "task_id": task_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "prompt_id": prompt_id,
        "workflow": workflow_id,
        "submitted_at": time.time(),
        "source_image": img_a,
        "mode": "dual_transfer",
        "track": track_id,
    }
    host.save_pending(pending)

    host.send_text(chat_id, f"✅ 已提交！prompt_id={prompt_id}\n等待 ComfyUI 完成...")

    # 提交完成后清掉 dt 状态，回到 idle，确保普通生图入口干净。
    reset_dt(state)
    state["step"] = "idle"
    state["mode"] = "image"
    host.save_state(user_id)
