"""dual_transfer — 双图迁移独立 feature。

设计原则：
- 与普通生图 / 图生图 / i2v 链路完全隔离，不共享 prompt builder / submit 逻辑。
- state 字段统一 dt_ 前缀；回调前缀 dt:；任务 ID 前缀 dt-{track}-。
- 仅复用 tg_bot 提供的底层服务（send_text / save_state / comfyui_alive 等），
  通过 Host 协议显式注入，避免循环 import。
"""

from .state import DT_FIELDS, default_dt_fields, reset_dt, assert_clean
from .registry import load_registry, get_track
from .prompt import build_dt_prompt, IDENTITY_LOCK
from .menu import show_track_entry, handle_dt_callback, on_photo
from .pipeline import submit_dt_job

__all__ = [
    "DT_FIELDS",
    "default_dt_fields",
    "reset_dt",
    "assert_clean",
    "load_registry",
    "get_track",
    "build_dt_prompt",
    "IDENTITY_LOCK",
    "show_track_entry",
    "handle_dt_callback",
    "on_photo",
    "submit_dt_job",
]
