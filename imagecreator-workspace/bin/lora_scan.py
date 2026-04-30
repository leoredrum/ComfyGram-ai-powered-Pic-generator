#!/usr/bin/env python3
"""
lora_scan.py — Scan /Users/leo/Downloads/lora and report LoRA metadata.

Usage:
  python3 bin/lora_scan.py              # print report
  python3 bin/lora_scan.py --check      # check Flux LoRAs only
  python3 bin/lora_scan.py --registry   # print current registry summary

Does NOT modify registry.json automatically — edits are manual.
"""

import argparse
import json
import os
import struct
from pathlib import Path

LORA_ROOT = Path("/Users/leo/Downloads/lora")
REGISTRY_FILE = Path("/Users/leo/Agents/imagecreator-workspace/lora_registry.json")


def peek_header(path: Path, max_bytes: int = 4096) -> str:
    """Read first max_bytes of safetensors header as text."""
    try:
        with open(path, "rb") as f:
            length_bytes = f.read(8)
            if len(length_bytes) < 8:
                return ""
            header_length = struct.unpack("<Q", length_bytes)[0]
            if header_length > 20_000_000:
                return "[header_too_large]"
            data = f.read(min(header_length, max_bytes))
            return data.decode("utf-8", errors="replace")
    except Exception as e:
        return f"[error: {e}]"


def infer_base_model(path: Path) -> str:
    """Best-effort base model inference from safetensors header."""
    header = peek_header(path)
    if not header:
        return "UNKNOWN"

    h = header.lower()

    # Explicit metadata markers
    if "flux" in h:
        return "Flux"
    if "wan" in h and ("i2v" in h or "t2v" in h or "video" in h):
        return "WAN"
    if "modelspec.architecture" in h and "xl" in h:
        return "SDXL"
    if "sd_xl" in h or "sdxl" in h:
        return "SDXL"
    if "stable-diffusion-xl" in h:
        return "SDXL"
    if '"modelspec.resolution":"1024x1024"' in h.replace(" ", ""):
        return "SDXL_or_Flux"

    # Diffusion model key names (Flux-specific)
    if "diffusion_model.transformer_blocks" in h:
        return "Flux"
    if "net.blocks." in h and "adaln" in h:
        return "WAN_or_other_DiT"

    # CLIP dimension indicators
    if '"shape":[' in h:
        # SD1.5 text encoder uses dim 768
        if any(f'"shape":[{d},768]' in h for d in ["16", "32", "64", "128", "256"]):
            return "SD1.5"
        # SDXL uses 1280 or 2048
        if any(f'"shape":[{d},1280]' in h for d in ["32", "64", "128"]):
            return "SDXL"
        if any(f'"shape":[{d},2048]' in h for d in ["32", "64", "128"]):
            return "SDXL"

    # Training metadata markers
    if "ss_base_model_version" in h:
        if "sd_v1" in h:
            return "SD1.5"
        if "sdxl" in h:
            return "SDXL"
    if "ss_v2" in h and '"false"' in h:
        return "SD1.5_likely"
    if "ss_sd_model_name" in h:
        if "v1-5" in h or "v1.5" in h or "anything" in h or "chillout" in h or "majicmix" in h:
            return "SD1.5"

    # Resolution hints
    if '"512, 512"' in h or '"resolution": "(512' in h or "512x512" in h:
        return "SD1.5_likely(res512)"
    if '"1024, 1024"' in h or '"resolution": "(1024' in h or "1024x1024" in h:
        return "SDXL_or_Flux_likely"

    # Full model markers (not LoRAs)
    if "cond_stage_model.transformer" in h or "conditioner.embedders" in h:
        return "FULL_MODEL_NOT_LORA"

    return "UNKNOWN"


def scan_loras() -> list:
    """Return list of dicts with metadata for all .safetensors files."""
    results = []
    if not LORA_ROOT.exists():
        print(f"[error] LORA_ROOT not found: {LORA_ROOT}")
        return results

    for cat_dir in sorted(LORA_ROOT.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith("."):
            continue
        cat_key = cat_dir.name

        for f in sorted(cat_dir.iterdir()):
            if f.suffix.lower() != ".safetensors":
                continue
            if f.name.startswith(".") or f.name.startswith("_"):
                continue

            size_mb = f.stat().st_size // (1024 * 1024)
            base_model = infer_base_model(f)
            comfyui_name = f"{cat_key}/{f.name}"

            results.append({
                "category": cat_key,
                "name": f.stem,
                "filename": f.name,
                "comfyui_name": comfyui_name,
                "path": str(f),
                "size_mb": size_mb,
                "base_model": base_model,
            })
    return results


def print_report(loras: list):
    """Print a summary table of all LoRAs."""
    print(f"\n{'='*80}")
    print(f"LoRA Scan Report — {LORA_ROOT}")
    print(f"{'='*80}")
    print(f"{'Category':<12} {'Name':<26} {'MB':>5}  {'Base Model'}")
    print(f"{'-'*80}")

    current_cat = None
    for l in loras:
        if l["category"] != current_cat:
            current_cat = l["category"]
            print()
        size_warn = " ⚠️ LARGE" if l["size_mb"] > 500 else ""
        print(f"{l['category']:<12} {l['name']:<26} {l['size_mb']:>5}  {l['base_model']}{size_warn}")

    print(f"\nTotal: {len(loras)} LoRAs across {len({l['category'] for l in loras})} categories")


def print_flux_only(loras: list):
    """Print only Flux-compatible LoRAs."""
    flux = [l for l in loras if "Flux" in l["base_model"]]
    print(f"\nFlux-compatible LoRAs ({len(flux)}):")
    for l in flux:
        print(f"  {l['comfyui_name']} ({l['size_mb']}MB)")


def print_registry_summary():
    """Print current registry telegram_enabled status."""
    if not REGISTRY_FILE.exists():
        print("Registry not found.")
        return
    reg = json.loads(REGISTRY_FILE.read_text())
    print(f"\nRegistry summary — {REGISTRY_FILE}")
    for cat_key, cat in reg.get("categories", {}).items():
        enabled_loras = [
            k for k, v in cat.get("loras", {}).items()
            if not k.startswith("_") and isinstance(v, dict) and v.get("telegram_enabled")
        ]
        cat_label = cat.get("category_display_name", cat_key)
        status = "✅ ENABLED" if cat.get("telegram_enabled") else "  disabled"
        print(f"  {status}  {cat_label} ({cat_key}): {len(enabled_loras)} enabled LoRA(s)")
        for lk in enabled_loras:
            lora = cat["loras"][lk]
            print(f"           → {lora.get('lora_display_name', lk)} [{lora.get('tier','?')}] "
                  f"{lora.get('file_size_mb','?')}MB {lora.get('base_model_compatibility','?')}")


def main():
    parser = argparse.ArgumentParser(description="Scan LoRA directory")
    parser.add_argument("--check",    action="store_true", help="Show Flux-compatible LoRAs only")
    parser.add_argument("--registry", action="store_true", help="Show registry enabled status")
    args = parser.parse_args()

    if args.registry:
        print_registry_summary()
        return

    loras = scan_loras()

    if args.check:
        print_flux_only(loras)
    else:
        print_report(loras)


if __name__ == "__main__":
    main()
