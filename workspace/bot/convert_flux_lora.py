#!/usr/bin/env python3
"""
Flux LoRA 格式转换工具 — 适配 ComfyUI

问题背景：
  某些 Flux LoRA 训练器（如部分 kohya/diffusers 方案）输出键名带 'diffusion_model.' 前缀，
  如: diffusion_model.transformer_blocks.0.attn.add_k_proj.lora_A.weight
  ComfyUI 的 key_map 只识别不带该前缀的版本（DiffSynth 格式）：
  如: transformer_blocks.0.attn.add_k_proj.lora_A.weight
  导致所有键报 "lora key not loaded"，LoRA 实际未生效。

修复：strip 'diffusion_model.' 前缀即可，无需修改权重数值。

用法：
  python3 convert_flux_lora.py input.safetensors
  python3 convert_flux_lora.py input.safetensors --out /path/to/output.safetensors
  python3 convert_flux_lora.py *.safetensors          # 批量
  python3 convert_flux_lora.py --check input.safetensors  # 只检测，不转换
"""

import argparse
import sys
from pathlib import Path

STRIP_PREFIX = "diffusion_model."


def _load_safetensors():
    try:
        import safetensors.torch as st
        return st
    except ImportError:
        # Try venv
        import subprocess, importlib
        import os
        comfyui_base = os.environ.get("COMFYUI_BASE_DIR", "./ComfyUI")
        venv_py = f"{comfyui_base}/.venv/bin/python3"
        print(f"[warn] safetensors not in current env, re-running via {venv_py}", file=sys.stderr)
        result = subprocess.run([venv_py, __file__] + sys.argv[1:])
        sys.exit(result.returncode)


def detect(path: Path) -> dict:
    """Return info about whether the file needs conversion."""
    st = _load_safetensors()
    tensors = st.load_file(str(path))
    total = len(tensors)
    needs_strip = [k for k in tensors if k.startswith(STRIP_PREFIX)]
    other = total - len(needs_strip)
    return {
        "path": path,
        "total_keys": total,
        "needs_strip": len(needs_strip),
        "other_keys": other,
        "should_convert": len(needs_strip) > 0,
    }


def convert(src: Path, dst: Path, dry_run: bool = False) -> dict:
    """Convert src → dst by stripping STRIP_PREFIX. Returns stats."""
    st = _load_safetensors()

    print(f"[load] {src}")
    tensors = st.load_file(str(src))
    total = len(tensors)

    renamed = {}
    converted = 0
    kept = 0
    for k, v in tensors.items():
        if k.startswith(STRIP_PREFIX):
            renamed[k[len(STRIP_PREFIX):]] = v
            converted += 1
        else:
            renamed[k] = v
            kept += 1

    stats = {
        "src": src,
        "dst": dst,
        "total": total,
        "converted": converted,
        "kept_as_is": kept,
    }

    if dry_run:
        print(f"[dry-run] would convert {converted}/{total} keys, kept {kept}")
        return stats

    if dst.exists():
        print(f"[skip] {dst} already exists — use --force to overwrite")
        stats["skipped"] = True
        return stats

    print(f"[save] {dst} ({converted} keys renamed, {kept} kept)")
    st.save_file(renamed, str(dst))

    src_mb = src.stat().st_size / 1024 / 1024
    dst_mb = dst.stat().st_size / 1024 / 1024
    print(f"[done] {src_mb:.1f}MB → {dst_mb:.1f}MB")
    stats["skipped"] = False
    return stats


def main():
    parser = argparse.ArgumentParser(description="Convert Flux LoRA for ComfyUI (strip diffusion_model. prefix)")
    parser.add_argument("inputs", nargs="+", help="Input .safetensors file(s)")
    parser.add_argument("--out", help="Output path (only valid for single input)")
    parser.add_argument("--suffix", default="_comfyui", help="Suffix for output file (default: _comfyui)")
    parser.add_argument("--check", action="store_true", help="Detect only, do not convert")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files")
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen, don't write")
    args = parser.parse_args()

    inputs = [Path(p) for p in args.inputs]

    if args.check:
        for src in inputs:
            if not src.exists():
                print(f"[missing] {src}")
                continue
            info = detect(src)
            status = "NEEDS_CONVERT" if info["should_convert"] else "OK"
            print(f"[{status}] {src.name}: {info['needs_strip']}/{info['total_keys']} keys have '{STRIP_PREFIX}' prefix")
        return

    if args.out and len(inputs) > 1:
        print("[error] --out can only be used with a single input file", file=sys.stderr)
        sys.exit(1)

    results = []
    for src in inputs:
        if not src.exists():
            print(f"[missing] {src}")
            continue

        if args.out:
            dst = Path(args.out)
        else:
            dst = src.with_name(src.stem + args.suffix + src.suffix)

        if src == dst:
            print(f"[error] src and dst are the same file: {src}", file=sys.stderr)
            continue

        if dst.exists() and not args.force and not args.dry_run:
            print(f"[skip] {dst.name} already exists")
            continue

        stats = convert(src, dst, dry_run=args.dry_run)
        results.append(stats)

    if results:
        print()
        print("=== Summary ===")
        for r in results:
            skipped = r.get("skipped", False)
            tag = "SKIPPED" if skipped else "CONVERTED"
            print(f"[{tag}] {r['src'].name} → {r['dst'].name}: {r['converted']} keys renamed")


if __name__ == "__main__":
    main()
