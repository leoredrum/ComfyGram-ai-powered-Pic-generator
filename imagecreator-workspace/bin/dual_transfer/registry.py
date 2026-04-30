"""加载 bin/dual_transfer/registry.json。"""

import json
from pathlib import Path

_REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"
_CACHE = None


def load_registry() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(_REGISTRY_PATH.read_text())
    return _CACHE


def get_track(track: str) -> dict | None:
    reg = load_registry()
    return reg.get("tracks", {}).get(track)
