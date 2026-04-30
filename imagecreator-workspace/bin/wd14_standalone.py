#!/usr/bin/env python3
"""Standalone WD14 tagger — does NOT depend on ComfyUI runtime.

Usage:
    python3 wd14_standalone.py <image_path> [--model MODEL] [--threshold 0.35]

Reuses the model files shipped by the ComfyUI-WD14-Tagger node
(/Users/leo/Documents/ComfyUI/custom_nodes/ComfyUI-WD14-Tagger/models/).
Downloads from HuggingFace on first use (~300MB).

Prints the resulting comma-separated tags to stdout.
"""

import argparse
import csv
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

DEFAULT_MODEL = "wd-v1-4-moat-tagger-v2"
MODELS_DIR = Path(
    "/Users/leo/Documents/ComfyUI/custom_nodes/ComfyUI-WD14-Tagger/models"
)
HF_BASE = "https://huggingface.co/SmilingWolf"


def ensure_model(model_name: str) -> tuple[Path, Path]:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    onnx = MODELS_DIR / f"{model_name}.onnx"
    tags_csv = MODELS_DIR / f"{model_name}.csv"
    if not onnx.exists():
        print(f"[wd14] downloading {model_name}/model.onnx ...", file=sys.stderr, flush=True)
        urllib.request.urlretrieve(
            f"{HF_BASE}/{model_name}/resolve/main/model.onnx", onnx
        )
    if not tags_csv.exists():
        print(f"[wd14] downloading {model_name}/selected_tags.csv ...", file=sys.stderr, flush=True)
        urllib.request.urlretrieve(
            f"{HF_BASE}/{model_name}/resolve/main/selected_tags.csv", tags_csv
        )
    return onnx, tags_csv


def tag_image(
    image_path: Path,
    model_name: str = DEFAULT_MODEL,
    threshold: float = 0.35,
    character_threshold: float = 0.85,
    replace_underscore: bool = True,
    trailing_comma: bool = False,
    exclude_tags: str = "",
) -> str:
    onnx_path, csv_path = ensure_model(model_name)

    image = Image.open(str(image_path)).convert("RGB")

    providers = [
        p for p in ("CoreMLExecutionProvider", "CPUExecutionProvider")
        if p in ort.get_available_providers()
    ]
    session = ort.InferenceSession(str(onnx_path), providers=providers)

    inp = session.get_inputs()[0]
    side = inp.shape[1]
    ratio = float(side) / max(image.size)
    new_size = tuple(int(x * ratio) for x in image.size)
    image = image.resize(new_size, Image.LANCZOS)
    square = Image.new("RGB", (side, side), (255, 255, 255))
    square.paste(image, ((side - new_size[0]) // 2, (side - new_size[1]) // 2))
    arr = np.array(square).astype(np.float32)
    arr = arr[:, :, ::-1]  # RGB -> BGR
    arr = np.expand_dims(arr, 0)

    tags: list[str] = []
    general_index: int | None = None
    character_index: int | None = None
    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if general_index is None and row[2] == "0":
                general_index = reader.line_num - 2
            elif character_index is None and row[2] == "4":
                character_index = reader.line_num - 2
            name = row[1].replace("_", " ") if replace_underscore else row[1]
            tags.append(name)

    label = session.get_outputs()[0].name
    probs = session.run([label], {inp.name: arr})[0]
    paired = list(zip(tags, probs[0]))

    if general_index is None:
        general_index = 0
    if character_index is None:
        character_index = len(paired)

    general = [item for item in paired[general_index:character_index] if item[1] > threshold]
    character = [item for item in paired[character_index:] if item[1] > character_threshold]

    picked = character + general
    remove = {s.strip() for s in exclude_tags.lower().split(",") if s.strip()}
    picked = [t for t in picked if t[0] not in remove]

    if trailing_comma:
        return "".join(
            item[0].replace("(", "\\(").replace(")", "\\)") + ", " for item in picked
        )
    return ", ".join(
        item[0].replace("(", "\\(").replace(")", "\\)") for item in picked
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="Path to input image (jpg/png/webp)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--threshold", type=float, default=0.35)
    ap.add_argument("--character-threshold", type=float, default=0.85)
    ap.add_argument("--no-replace-underscore", action="store_true")
    ap.add_argument("--trailing-comma", action="store_true")
    ap.add_argument("--exclude-tags", default="")
    args = ap.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"image not found: {image_path}", file=sys.stderr)
        return 2
    try:
        result = tag_image(
            image_path,
            model_name=args.model,
            threshold=args.threshold,
            character_threshold=args.character_threshold,
            replace_underscore=not args.no_replace_underscore,
            trailing_comma=args.trailing_comma,
            exclude_tags=args.exclude_tags,
        )
    except Exception as e:
        print(f"[wd14] error: {e}", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
