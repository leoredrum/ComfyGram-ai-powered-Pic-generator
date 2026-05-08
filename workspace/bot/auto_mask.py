#!/usr/bin/env python3
"""Auto-generate clothing mask using Segformer semantic segmentation.

Labels from mattmdjaga/segformer_b2_clothes:
  0: Background, 1: Hat, 2: Hair, 3: Sunglasses, 4: Upper-clothes,
  5: Skirt, 6: Pants, 7: Dress, 8: Belt, 9: Left-shoe, 10: Right-shoe,
  11: Face, 12: Left-leg, 13: Right-leg, 14: Left-arm, 15: Right-arm,
  16: Bag, 17: Scarf

Clothing labels (white in mask): 4, 5, 6, 7, 8, 17
Protected labels (black in mask): 0, 1, 2, 3, 9, 10, 11, 12, 13, 14, 15, 16
"""
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageFilter

MODEL_NAME = "mattmdjaga/segformer_b2_clothes"
CLOTHING_LABELS = {4, 5, 6, 7, 8, 17}  # upper-clothes, skirt, pants, dress, belt, scarf

_processor = None
_model = None


def _load_model():
    global _processor, _model
    if _model is not None:
        return
    from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
    _processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
    _model = AutoModelForSemanticSegmentation.from_pretrained(MODEL_NAME)
    _model.eval()


def generate_clothing_mask(image_path: str, output_path: str | None = None,
                           feather_px: int = 5) -> str:
    """Generate a binary mask where clothing = white, everything else = black.

    Args:
        image_path: Path to source image.
        output_path: Where to save mask. Default: <image_path>_automask.png
        feather_px: Gaussian blur radius for soft edges.

    Returns:
        Path to saved mask image.
    """
    _load_model()

    img = Image.open(image_path).convert("RGB")
    orig_size = img.size  # (W, H)

    inputs = _processor(images=img, return_tensors="pt")
    with torch.no_grad():
        outputs = _model(**inputs)

    # Upsample logits to original image size
    logits = outputs.logits  # (1, num_labels, H', W')
    upsampled = torch.nn.functional.interpolate(
        logits, size=(orig_size[1], orig_size[0]),  # (H, W)
        mode="bilinear", align_corners=False,
    )
    seg = upsampled.argmax(dim=1).squeeze().cpu().numpy()  # (H, W)

    # Build binary mask: clothing = 255, rest = 0
    mask = np.zeros_like(seg, dtype=np.uint8)
    for label_id in CLOTHING_LABELS:
        mask[seg == label_id] = 255

    mask_img = Image.fromarray(mask, mode="L")

    # Feather edges
    if feather_px > 0:
        mask_img = mask_img.filter(ImageFilter.GaussianBlur(feather_px))
        # Re-threshold to keep mostly binary with soft edges
        arr = np.array(mask_img)
        arr = np.where(arr > 30, 255, 0).astype(np.uint8)
        mask_img = Image.fromarray(arr, mode="L")

    if output_path is None:
        p = Path(image_path)
        output_path = str(p.with_stem(p.stem + "_automask"))

    mask_img.save(output_path)
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <image_path> [output_path]")
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    result = generate_clothing_mask(src, dst)
    print(f"Mask saved: {result}")
