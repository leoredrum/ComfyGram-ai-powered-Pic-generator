"""dual_transfer 专属 prompt 构造。

- 不引用 preset_prompt_templates / prompt_library / lora 风格串
- pose 轨道用强身份锁定串；outfit 留待 Step 2
"""

IDENTITY_LOCK = (
    "same character, same identity, same face, same eyes, "
    "same hair color, same hairstyle, preserve facial features, "
    "high quality, detailed, masterpiece"
)

_TRACK_BASE = {
    "pose": IDENTITY_LOCK,
    # outfit 轨道 Stage 1 不上线；保留 key 让 caller 不会 KeyError
    "outfit": IDENTITY_LOCK + ", same outfit, same clothing",
}


def build_dt_prompt(track: str, user_prompt: str | None) -> str:
    base = _TRACK_BASE.get(track, IDENTITY_LOCK)
    user_prompt = (user_prompt or "").strip()
    if user_prompt:
        return f"{base}, {user_prompt}"
    return base
