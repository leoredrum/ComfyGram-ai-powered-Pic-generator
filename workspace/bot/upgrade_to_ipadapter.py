#!/usr/bin/env python3
"""
다운로드 완료 후 실행:
  python3 bin/upgrade_to_ipadapter.py

clip_vit_h14_laion2b.safetensors 가 올바른 포맷인지 확인 후,
flux_i2i_undress_api.json 을 IP-Adapter 버전으로 교체.
"""
import json, sys, os
from pathlib import Path

WORKSPACE = Path(os.environ.get("IMAGECREATOR_WORKSPACE", "./workspace"))
COMFYUI_BASE = Path(os.environ.get("COMFYUI_BASE_DIR", "./ComfyUI"))
CLIP_MODEL = COMFYUI_BASE / "models/clip_vision/clip_vit_h14_laion2b.safetensors"
WORKFLOW   = WORKSPACE / "workflows/flux_i2i_undress_api.json"

def verify_clip_format():
    try:
        import safetensors
        with safetensors.safe_open(str(CLIP_MODEL), framework="pt", device="cpu") as f:
            keys = set(f.keys())
        has_resblocks = any("resblocks" in k for k in keys)
        has_vision_model = any("vision_model.encoder" in k for k in keys)
        print(f"Keys total: {len(keys)}")
        print(f"Has resblocks format: {has_resblocks}")
        print(f"Has transformers format: {has_vision_model}")
        return has_resblocks or has_vision_model
    except Exception as e:
        print(f"Error reading model: {e}")
        return False

IPADAPTER_WORKFLOW = {
  "_comment": "Anime undress/outfit-change: XLabs IP-Adapter(0.85) + ControlNet Canny(0.45) + XlabsSampler. Requires clip_vit_h14_laion2b.safetensors.",
  "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-dev.safetensors", "weight_dtype": "default"}},
  "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "t5xxl_fp8_e4m3fn.safetensors", "clip_name2": "clip_l.safetensors", "type": "flux"}},
  "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
  "4": {"class_type": "LoadFluxIPAdapter", "inputs": {"ipadatper": "ip_adapter.safetensors", "clip_vision": "clip_vit_h14_laion2b.safetensors", "provider": "CPU"}},
  "5": {"class_type": "LoadFluxControlNet", "inputs": {"model_name": "flux-dev", "controlnet_path": "flux-canny-controlnet-v3.safetensors"}},
  "6": {"class_type": "LoadImage", "inputs": {"image": "input.jpg"}},
  "7": {"class_type": "ImageScale", "inputs": {"image": ["6", 0], "upscale_method": "lanczos", "width": 1024, "height": 1024, "crop": "center"}},
  "8": {"class_type": "ApplyFluxIPAdapter", "inputs": {"model": ["1", 0], "ip_adapter_flux": ["4", 0], "image": ["7", 0], "ip_scale": 0.85}},
  "9": {"class_type": "Canny", "inputs": {"image": ["7", 0], "low_threshold": 0.1, "high_threshold": 0.2}},
  "10": {"class_type": "ApplyFluxControlNet", "inputs": {"controlnet": ["5", 0], "image": ["9", 0], "strength": 0.45}},
  "11": {"class_type": "CLIPTextEncodeFlux", "inputs": {"clip": ["2", 0], "clip_l": "anime style illustration, 1girl, same character, nude, bare skin, no clothes, natural body, masterpiece, best quality, highly detailed", "t5xxl": "anime style illustration, 1girl, same character, nude, bare skin, no clothes, natural body, masterpiece, best quality, highly detailed", "guidance": 4.0}},
  "12": {"class_type": "CLIPTextEncodeFlux", "inputs": {"clip": ["2", 0], "clip_l": "NEGATIVE: clothing, fully clothed, different character, bad anatomy, extra limbs, deformed, low quality, blurry, ugly, watermark", "t5xxl": "NEGATIVE: clothing, fully clothed, different character, bad anatomy, extra limbs, deformed, low quality, blurry, ugly, watermark", "guidance": 4.0}},
  "13": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
  "14": {"class_type": "XlabsSampler", "inputs": {"model": ["8", 0], "conditioning": ["11", 0], "neg_conditioning": ["12", 0], "noise_seed": 42, "steps": 30, "timestep_to_start_cfg": 1, "true_gs": 4.0, "image_to_image_strength": 0.0, "denoise_strength": 1.0, "latent_image": ["13", 0], "controlnet_condition": ["10", 0]}},
  "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["3", 0]}},
  "16": {"class_type": "SaveImage", "inputs": {"images": ["15", 0], "filename_prefix": "flux_undress"}}
}

if __name__ == "__main__":
    if not CLIP_MODEL.exists():
        print(f"❌ 모델 없음: {CLIP_MODEL}")
        print("다운로드 먼저: laion/CLIP-ViT-H-14-laion2B-s32B-b79K/open_clip_model.safetensors")
        sys.exit(1)

    size_mb = CLIP_MODEL.stat().st_size // 1024 // 1024
    print(f"✓ 모델 존재: {size_mb}MB")

    if not verify_clip_format():
        print("❌ 포맷 불일치: resblocks 또는 vision_model 키 없음")
        sys.exit(1)

    print("✓ 포맷 OK — IP-Adapter workflow 배포")
    with open(WORKFLOW, "w") as f:
        json.dump(IPADAPTER_WORKFLOW, f, indent=2, ensure_ascii=False)
    print(f"✓ 배포 완료: {WORKFLOW}")
    print("Bot 재시작 필요 없음 (workflow JSON만 교체)")
