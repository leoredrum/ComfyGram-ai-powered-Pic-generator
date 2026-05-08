#!/usr/bin/env python3
"""
Convert a ComfyUI UI-format workflow JSON to API format.
Uses /object_info endpoint to resolve widget parameter names.

Usage: python3 export_api_workflow.py <input_ui.json> <output_api.json>
"""

import json
import sys
import urllib.request
from pathlib import Path

COMFYUI_BASE = "http://127.0.0.1:8000"

# ComfyUI primitive types that are rendered as widgets (not node connections)
WIDGET_TYPES = {"INT", "FLOAT", "STRING", "BOOLEAN"}

# Values that indicate a UI-only seed-control widget (not in node schema)
SEED_CONTROL_VALUES = {"fixed", "randomize", "increment", "control_before_generate"}

# Input names that trigger a following seed-control UI widget
SEED_INPUT_NAMES = {"seed", "noise_seed", "rand_seed", "batch_seed"}


def get_object_info(node_type: str) -> dict:
    url = f"{COMFYUI_BASE}/object_info/{urllib.request.quote(node_type)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
            return data.get(node_type, {})
    except Exception as e:
        print(f"  [warn] object_info failed for {node_type}: {e}", file=sys.stderr)
        return {}


def is_widget_type(type_def) -> bool:
    """Return True if this input should be a widget (value), not a link (connection)."""
    if isinstance(type_def, list):
        return True  # combo/dropdown
    if isinstance(type_def, str):
        return type_def in WIDGET_TYPES
    return False


def get_widget_names(schema: dict) -> list[str]:
    """
    Return ordered list of widget input names for a node type,
    based on its object_info schema.
    Widget inputs are those whose type is a primitive or combo.
    """
    names = []
    input_def = schema.get("input", {})
    # required first, then optional — same order ComfyUI uses
    for section in ("required", "optional"):
        for name, type_info in input_def.get(section, {}).items():
            tp = type_info[0] if type_info else None
            if is_widget_type(tp):
                names.append(name)
    return names


def ui_to_api(wf: dict) -> dict:
    # Build link map: link_id -> [src_node_id_str, src_slot_int]
    links: dict[int, list] = {}
    for link in wf.get("links", []):
        # [link_id, src_node_id, src_slot, dst_node_id, dst_slot, type]
        links[link[0]] = [str(link[1]), link[2]]

    # Cache object_info per node type
    schema_cache: dict[str, dict] = {}

    api_wf = {}
    for node in wf.get("nodes", []):
        node_id = str(node["id"])
        class_type = node.get("type", "")

        if class_type not in schema_cache:
            print(f"  fetching schema: {class_type}", file=sys.stderr)
            schema_cache[class_type] = get_object_info(class_type)

        schema = schema_cache[class_type]

        # Skip UI-only nodes (Note, PrimitiveNode, Reroute, etc.) — no schema
        if not schema:
            print(f"  skipping UI-only node: {class_type} (id={node_id})", file=sys.stderr)
            continue
        widget_names = get_widget_names(schema)

        inputs = {}

        # 1. Map linked inputs from node.inputs array
        linked_names = set()
        for inp in node.get("inputs", []):
            inp_name = inp.get("name", "")
            link_id = inp.get("link")
            if link_id is not None and link_id in links:
                inputs[inp_name] = links[link_id]
                linked_names.add(inp_name)

        # 2. Map widget values to names
        widget_values = node.get("widgets_values", [])
        if isinstance(widget_values, dict):
            # Already named — merge, links take priority
            for wname, val in widget_values.items():
                if wname not in linked_names:
                    inputs[wname] = val
        else:
            # Ordered list — schema order, index always advances even for linked widgets.
            # ComfyUI frontend injects extra "seed control" UI widgets (fixed/randomize/…)
            # immediately after any INT input named "seed*". These are not in the schema
            # but DO occupy a slot in widgets_values — skip them.
            wi = 0
            for wname in widget_names:
                if wi >= len(widget_values):
                    break
                if wname not in linked_names:
                    inputs[wname] = widget_values[wi]
                wi += 1  # always advance — linked widgets still occupy a slot
                # If this was a seed input, peek ahead and skip any seed-control token
                if wname in SEED_INPUT_NAMES:
                    if wi < len(widget_values) and widget_values[wi] in SEED_CONTROL_VALUES:
                        wi += 1  # skip the UI-only seed control value

        api_wf[node_id] = {
            "class_type": class_type,
            "_meta": {"title": node.get("title", class_type)},
            "inputs": inputs,
        }

    return api_wf


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_ui.json> <output_api.json>")
        sys.exit(1)

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    with open(src) as f:
        wf = json.load(f)

    if "nodes" not in wf:
        print("Input looks like API format already (no 'nodes' key). Aborting.")
        sys.exit(1)

    print(f"Converting {src.name} ({len(wf['nodes'])} nodes)...", file=sys.stderr)
    api_wf = ui_to_api(wf)

    with open(dst, "w") as f:
        json.dump(api_wf, f, indent=2)

    print(f"Written: {dst}", file=sys.stderr)
    print(json.dumps({"nodes": len(api_wf), "output": str(dst)}))


if __name__ == "__main__":
    main()
