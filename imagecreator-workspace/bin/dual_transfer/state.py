"""dual_transfer 专属 state 字段。

所有字段统一 dt_ 前缀，便于：
- assert_clean() 一行 grep 验证普通生图入口未被污染
- reset_dt() 集中清理，跨菜单 / submit 路径只调用一处
"""

DT_FIELDS = (
    "dt_track",        # "pose" | "outfit" | None
    "dt_image_a",      # A 图（角色锚点）路径
    "dt_image_b",      # B 图（条件源）路径
    "dt_step",         # "await_a" | "await_b" | "confirm" | None
    "dt_user_prompt",  # 用户追加的 prompt（与普通 user_prompt 完全分离）
)


def default_dt_fields() -> dict:
    return {f: None for f in DT_FIELDS}


def reset_dt(state: dict) -> None:
    """把所有 dt_* 字段清成 None。供菜单返回 / submit 完成 / 切换到普通模式时调用。"""
    for f in DT_FIELDS:
        state[f] = None


def assert_clean(state: dict) -> None:
    """普通生图入口必须先调用：确保不会把上一次双图迁移的状态带进 t2i/i2i。

    防御式清理而不是 raise——这样对老的 gen_state.json 也兼容。
    """
    reset_dt(state)
