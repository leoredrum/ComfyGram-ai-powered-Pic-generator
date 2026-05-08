#!/usr/bin/env python3
"""Convert diffusion_model weights in a safetensors checkpoint from fp16 to bf16.

This fixes NaN overflow on MPS (Apple Silicon) for certain Illustrious/NoobAI
models whose UNet weights produce intermediate values exceeding fp16 range.

bf16 has 8 exponent bits (vs 5 for fp16), giving a dynamic range of ~3.4e38
(vs ~65504 for fp16), which prevents overflow during inference.

Only diffusion_model weights are converted; CLIP and VAE remain in fp16.
"""
import argparse
import shutil
import sys
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file


def convert(src: Path, dst: Path, *, unet_only: bool = True):
    print(f"Loading {src} ...")
    tensors = load_file(str(src))

    converted = 0
    total = len(tensors)
    new_tensors = {}

    for key, tensor in tensors.items():
        if tensor.dtype == torch.float16 and (
            not unet_only or key.startswith("model.diffusion_model.")
        ):
            new_tensors[key] = tensor.to(torch.bfloat16)
            converted += 1
        else:
            new_tensors[key] = tensor

    print(f"Converted {converted}/{total} tensors from fp16 → bf16")
    print(f"Saving to {dst} ...")
    save_file(new_tensors, str(dst))
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path, help="Source safetensors file")
    parser.add_argument("--dst", type=Path, default=None,
                        help="Destination file (default: overwrite src after backup)")
    parser.add_argument("--all-weights", action="store_true",
                        help="Convert ALL fp16 weights, not just diffusion_model")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip creating .fp16.bak backup")
    args = parser.parse_args()

    if not args.src.exists():
        print(f"ERROR: {args.src} not found", file=sys.stderr)
        sys.exit(1)

    dst = args.dst or args.src

    if dst == args.src and not args.no_backup:
        bak = args.src.with_suffix(".fp16.bak.safetensors")
        if not bak.exists():
            print(f"Backing up original → {bak.name}")
            shutil.copy2(args.src, bak)
        else:
            print(f"Backup already exists: {bak.name}")

    # Write to temp file first, then rename (atomic-ish)
    tmp = dst.with_suffix(".tmp.safetensors")
    try:
        convert(args.src, tmp, unet_only=not args.all_weights)
        tmp.rename(dst)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
