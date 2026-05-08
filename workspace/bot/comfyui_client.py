#!/usr/bin/env python3
"""
ComfyUI API client for imagecreator agent.
Usage: python3 comfyui_client.py --task /path/to/task.json
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
import shutil
import uuid
from pathlib import Path

WORKSPACE = Path(os.environ.get("IMAGECREATOR_WORKSPACE", "./workspace"))
COMFYUI_BASE = Path(os.environ.get("COMFYUI_BASE_DIR", "./ComfyUI"))
MATERIAL_REGISTRY_FILE = WORKSPACE / "material_registry.json"
_MATERIAL_REG = None

def get_material_reg():
    global _MATERIAL_REG
    if _MATERIAL_REG is None:
        _MATERIAL_REG = json.loads(MATERIAL_REGISTRY_FILE.read_text())
    return _MATERIAL_REG

DEFAULT_ENDPOINTS = [
    "http://127.0.0.1:8188",
    "http://localhost:8188",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8001",
    "http://localhost:8001",
]
ENV_ENDPOINT = os.environ.get("COMFYUI_BASE", "").strip()
COMFYUI_ENDPOINTS = ([ENV_ENDPOINT] if ENV_ENDPOINT else []) + DEFAULT_ENDPOINTS
ACTIVE_COMFYUI_BASE = None
WORKFLOWS_DIR = WORKSPACE / "workflows"
OUTBOX_DIR   = WORKSPACE / "outbox"
OUTPUT_DIR   = WORKSPACE / "media" / "output"
INPUT_DIR    = WORKSPACE / "media" / "input"
COMFYUI_INPUT = COMFYUI_BASE / "input"
COMFYUI_OUTPUT = COMFYUI_BASE / "output"

WORKFLOW_MAP = {
    "i2v":            "wan_i2v_api.json",
    "i2i":            "flux_i2i_api.json",
    "i2i_undress":    "flux_i2i_undress_api.json",   # legacy: Flux canny+ipa regen
    "i2v_undress":    "wan_i2v_undress_api.json",
    "i2i_figure":     "flux_i2i_figure_api.json",
    "t2i":            "flux_t2i_api.json",
    "t2i_figure":     "flux_t2i_api.json",    # reuses t2i workflow, prompt differs
    "i2i_style":      "flux_i2i_style_api.json",
    "i2i_portrait":   "flux_i2i_portrait_api.json",
    "i2i_colorgrade": "flux_i2i_colorgrade_api.json",
    "i2i_watermark":  "flux_i2i_watermark_api.json",
    "train_lora":     "lora_train_api.json",
    "sdxl_multi_lora": "__dynamic__",  # built dynamically by build_sdxl_workflow()
    "i2i_outfit_mask": "flux_i2i_ipadapter_mask_api.json",  # mask-based outfit swap (face+body+mask inputs)
    "dual_transfer_pose": "dual_transfer_pose_api.json",    # 双图迁移 / pose 轨道: A角色(PuLID) + B动作(DWPose+Union CN)
}

TIMEOUTS = {
    "i2v":            3600,   # 1 hour for WAN video
    "i2i":            900,    # Flux i2i on MPS ~5-10 min
    "i2i_undress":    1200,   # Flux canny+ipa regen (legacy)
    "i2v_undress":    3600,   # Wan 2.1 i2v + undress LoRA (~same as i2v)
    "i2i_figure":     1200,
    "i2i_portrait":   1200,   # IP-Adapter + ControlNet
    "i2i_colorgrade": 900,
    "t2i":            900,
    "t2i_figure":     900,
    "i2i_style":      900,
    "i2i_watermark":  900,
    "train_lora":     7200,
    "sdxl_multi_lora": 1200,
    "i2i_outfit_mask": 1200,
    "dual_transfer_pose": 1800,   # PuLID + DWPose + Union ControlNet
}

def _candidate_bases():
    seen = set()
    if ACTIVE_COMFYUI_BASE:
        seen.add(ACTIVE_COMFYUI_BASE)
        yield ACTIVE_COMFYUI_BASE
    for base in COMFYUI_ENDPOINTS:
        if base and base not in seen:
            seen.add(base)
            yield base


def api_get(path):
    global ACTIVE_COMFYUI_BASE
    last_err = None
    for base in _candidate_bases():
        url = f"{base}{path}"
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                ACTIVE_COMFYUI_BASE = base
                return json.loads(r.read())
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"ComfyUI unreachable on all endpoints: {COMFYUI_ENDPOINTS}; last_error={last_err}")


def api_post(path, data):
    global ACTIVE_COMFYUI_BASE
    body = json.dumps(data).encode()
    last_err = None
    for base in _candidate_bases():
        url = f"{base}{path}"
        req = urllib.request.Request(url, data=body,
                                      headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                ACTIVE_COMFYUI_BASE = base
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            # HTTP error (4xx/5xx) means ComfyUI is reachable but rejected the request
            ACTIVE_COMFYUI_BASE = base
            raise RuntimeError(f"ComfyUI rejected request ({e.code}): {e.read().decode()[:400]}")
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"ComfyUI unreachable on all endpoints: {COMFYUI_ENDPOINTS}; last_error={last_err}")


def check_online():
    try:
        api_get("/system_stats")
        return True
    except Exception:
        return False


MAX_INPUT_PIXELS = 1024  # max pixels on long edge for VAE encoding on MPS


def resize_image_if_needed(src: Path) -> Path:
    """Resize image to MAX_INPUT_PIXELS on the long edge if larger. Returns path to use."""
    try:
        result = subprocess.run(
            ["sips", "--getProperty", "pixelWidth", "--getProperty", "pixelHeight", str(src)],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().splitlines()
        width = height = 0
        for line in lines:
            if "pixelWidth:" in line:
                width = int(line.split(":")[1].strip())
            if "pixelHeight:" in line:
                height = int(line.split(":")[1].strip())
        if width <= 0 or height <= 0 or max(width, height) <= MAX_INPUT_PIXELS:
            return src
        # Resize needed
        scale_factor = MAX_INPUT_PIXELS / max(width, height)
        new_w = int(width * scale_factor)
        new_h = int(height * scale_factor)
        suffix = src.suffix or ".jpg"
        tmp = Path(tempfile.mktemp(suffix=suffix, prefix="ic_resized_"))
        subprocess.run(
            ["sips", "-z", str(new_h), str(new_w), str(src), "--out", str(tmp)],
            capture_output=True, timeout=30
        )
        print(f"[client] resized {width}x{height} → {new_w}x{new_h}: {tmp}", file=sys.stderr)
        return tmp
    except Exception as e:
        print(f"[client] resize warning: {e} — using original", file=sys.stderr)
        return src


def upload_image(image_path: str) -> str:
    """Copy image (resizing if needed) to ComfyUI input dir, return filename."""
    src = Path(image_path)
    if not src.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")
    src = resize_image_if_needed(src)
    dest = COMFYUI_INPUT / src.name
    # Skip copy if already in ComfyUI input dir (same file)
    try:
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
    except Exception:
        shutil.copy2(str(src), str(dest))
    return src.name


def prepare_mask_image(mask_path: str) -> str:
    """Convert mask to PNG, binarize (pure black/white), and apply slight edge feathering.
    Returns path to processed mask file. Falls back to original on error."""
    try:
        from PIL import Image as PILImage, ImageFilter
        import tempfile

        img = PILImage.open(mask_path).convert("L")  # grayscale

        # Binarize: threshold at 128 → pure black/white, eliminates JPEG gray fringe
        img = img.point(lambda p: 255 if p >= 128 else 0)

        # Slight feathering: blur the binary edge by 1px then re-threshold at 64
        # This softens the hard cutout without smearing the mask region
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        img = img.point(lambda p: 255 if p >= 64 else 0)

        out_path = Path(tempfile.mktemp(suffix="_mask.png"))
        img.save(out_path, format="PNG")
        print(f"[client] mask prepared (binarized+feathered): {out_path.name}", file=sys.stderr)
        return str(out_path)
    except Exception as e:
        print(f"[client] mask prepare skipped ({e}), using original", file=sys.stderr)
        return mask_path


def inject_params(workflow: dict, params: dict) -> dict:
    """Inject task params into API-format workflow nodes.
    Strips any non-node metadata keys (e.g. _comment, _models) before returning."""
    # Deep copy, keeping only valid ComfyUI nodes (dicts with class_type)
    wf = {k: json.loads(json.dumps(v))
          for k, v in workflow.items()
          if isinstance(v, dict) and "class_type" in v}

    image_file      = params.get("image_file")   # filename already in ComfyUI input
    prompt          = params.get("prompt")
    negative_prompt = params.get("negative_prompt")
    seed            = params.get("seed")
    width           = params.get("width")
    height          = params.get("height")
    steps           = params.get("steps")
    denoise         = params.get("denoise")
    num_frames      = params.get("num_frames")

    for node_id, node in wf.items():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        # LoadImage — single-image workflows use image_file; multi-image workflows
        # detect FACE/BODY placeholder markers and inject the correct file.
        if class_type == "LoadImage":
            cur = str(inputs.get("image", "")).upper()
            face_f = params.get("face_image_file")
            body_f = params.get("body_image_file")
            if face_f and "FACE" in cur:
                inputs["image"] = face_f
            elif body_f and "BODY" in cur:
                inputs["image"] = body_f
            elif image_file and "FACE" not in cur and "BODY" not in cur:
                inputs["image"] = image_file

        # LoadImageMask — inject mask filename (multi-image outfit workflows)
        if class_type == "LoadImageMask":
            mask_f = params.get("mask_image_file")
            if mask_f:
                inputs["image"] = mask_f

        # WanVideoTextEncode — inject prompts
        if class_type == "WanVideoTextEncode":
            if prompt:
                inputs["positive_prompt"] = prompt
            if negative_prompt:
                inputs["negative_prompt"] = negative_prompt

        # WanVideoSampler — inject seed, steps
        if class_type == "WanVideoSampler":
            if seed is not None:
                inputs["seed"] = seed
            if steps is not None:
                inputs["steps"] = steps

        # WanVideoImageToVideoEncode — inject num_frames
        if class_type == "WanVideoImageToVideoEncode" and num_frames is not None:
            inputs["num_frames"] = num_frames

        # Flux — CLIPTextEncode (positive prompt only; i2i workflows have 1 node)
        if class_type == "CLIPTextEncode" and prompt:
            inputs["text"] = prompt

        # Flux — CLIPTextEncodeFlux (style transfer positive/negative)
        # Distinguish by placeholder text in template: "NEGATIVE" → negative node
        if class_type == "CLIPTextEncodeFlux":
            current_text = inputs.get("clip_l", "") or inputs.get("t5xxl", "")
            is_negative = "NEGATIVE" in str(current_text).upper()
            if is_negative and negative_prompt:
                inputs["clip_l"] = negative_prompt
                inputs["t5xxl"] = negative_prompt
            elif not is_negative and prompt:
                inputs["clip_l"] = prompt
                inputs["t5xxl"] = prompt

        # Flux — EmptySD3LatentImage / EmptyLatentImage (size)
        if class_type in ("EmptySD3LatentImage", "EmptyLatentImage"):
            if width:  inputs["width"]  = width
            if height: inputs["height"] = height

        # Flux — ModelSamplingFlux (size)
        if class_type == "ModelSamplingFlux":
            if width:  inputs["width"]  = width
            if height: inputs["height"] = height

        # Flux — RandomNoise (seed)
        if class_type == "RandomNoise" and seed is not None:
            inputs["noise_seed"] = seed

        # Flux — BasicScheduler (steps, denoise)
        if class_type == "BasicScheduler":
            if steps is not None:
                inputs["steps"] = steps
            if denoise is not None:
                inputs["denoise"] = denoise

        # XLabs — XlabsSampler (steps + seed + i2i strength)
        if class_type == "XlabsSampler":
            if steps is not None:
                inputs["steps"] = steps          # fix: was wrongly using "num_steps"
            if seed is not None:
                inputs["noise_seed"] = seed
            i2i_str = params.get("image_to_image_strength")
            if i2i_str is not None:
                inputs["image_to_image_strength"] = float(i2i_str)

        # KSampler — inject seed (used by SVD and other non-Flux workflows)
        if class_type == "KSampler":
            if seed is not None:
                inputs["seed"] = seed

        # ApplyFluxIPAdapter — inject ip_scale (used by ip_t2i_lora and i2i_figure_lora)
        if class_type == "ApplyFluxIPAdapter":
            ip_scale = params.get("ip_scale")
            if ip_scale is not None:
                inputs["ip_scale"] = float(ip_scale)

        # ApplyPulidFlux — inject pulid_weight (used by dual_transfer_pose)
        if class_type == "ApplyPulidFlux":
            pulid_weight = params.get("pulid_weight")
            if pulid_weight is not None:
                inputs["weight"] = float(pulid_weight)

        # ControlNetApplyAdvanced — inject controlnet strength (used by dual_transfer_pose)
        if class_type == "ControlNetApplyAdvanced":
            cn_strength = params.get("cn_strength")
            if cn_strength is not None:
                inputs["strength"] = float(cn_strength)

        # LoraLoaderModelOnly — inject LoRA filename and strength for Flux LoRA workflows
        if class_type == "LoraLoaderModelOnly":
            lora_name = params.get("lora_name")
            lora_strength = params.get("lora_strength")
            if lora_name:
                inputs["lora_name"] = lora_name
            if lora_strength is not None:
                inputs["strength_model"] = float(lora_strength)

    return wf


_SAMPLER_NORM = {
    # WebUI / civitai display names → ComfyUI internal names
    "euler a":            "euler_ancestral",
    "euler_a":            "euler_ancestral",
    "euler":              "euler",
    "dpm++ 2m karras":    "dpmpp_2m",       # karras = scheduler, handled separately
    "dpm++ 2m":           "dpmpp_2m",
    "dpm++ 2m sde":       "dpmpp_2m_sde",
    "dpm++ 2m sde karras":"dpmpp_2m_sde",
    "dpm++ 2m exponential":"dpmpp_2m",
    "dpm++ sde":          "dpmpp_sde",
    "dpm++ sde karras":   "dpmpp_sde",
    "dpm++ 2s a":         "dpmpp_2s_ancestral",
    "dpm2":               "dpm_2",
    "dpm2 a":             "dpm_2_ancestral",
    "lms":                "lms",
    "heun":               "heun",
    "ddim":               "ddim",
    "ddpm":               "ddpm",
    "uni_pc":             "uni_pc",
    "lcm":                "lcm",
}

def _norm_sampler(raw: str) -> str:
    """Normalize a WebUI/civitai sampler display name to a ComfyUI internal name."""
    key = raw.strip().lower().split(",")[0].strip()  # take first if comma-separated
    return _SAMPLER_NORM.get(key, "euler")  # default euler if unknown


def build_sdxl_workflow(task_params: dict) -> dict:
    """
    Build a ComfyUI workflow JSON for SDXL/Illustrious/Pony with N chained LoRAs.

    task_params keys:
    - model_key: str  (registry key like "figure/Deng_PVC_XL_Mix2")
    - lora_keys: list  (registry keys for LoRAs, in order)
    - prompt: str
    - negative_prompt: str
    - seed: int
    - width: int (default 1024)
    - height: int (default 1024)
    - steps: int (default 25)
    - cfg: float (default 7)
    - sampler: str (default "euler")
    - scheduler: str (default "karras")
    - clip_skip: int (default 2)
    - source_image: str | None  (path to input image, for i2i; None = t2i)
    - denoise: float (default 0.8 for i2i, 1.0 for t2i)
    """
    reg = get_material_reg()

    model_entry = reg["models"][task_params["model_key"]]
    lora_keys = task_params.get("lora_keys", [])

    checkpoint_name = model_entry["comfyui_model_name"]

    prompt = task_params.get("prompt", "1girl, high quality")
    negative = task_params.get("negative_prompt", "blurry, bad anatomy, watermark")
    seed = task_params.get("seed", 42)
    width = task_params.get("width", 1024)
    height = task_params.get("height", 1024)
    steps = task_params.get("steps", 25)
    cfg = task_params.get("cfg", 7.0)
    sampler = _norm_sampler(task_params.get("sampler", "euler"))
    scheduler = task_params.get("scheduler", "karras")
    clip_skip = task_params.get("clip_skip", 2)
    source_image = task_params.get("image_path") or task_params.get("source_image")  # None = t2i
    denoise = task_params.get("denoise", 0.8 if source_image else 1.0)

    # Node ID allocation:
    # 1: CheckpointLoaderSimple
    # 2: CLIPSetLastLayer (clip_skip)
    # 3: CLIPTextEncode (positive)
    # 4: CLIPTextEncode (negative)
    # 5: KSampler
    # 6: VAEDecode
    # 7: SaveImage
    # 8: EmptyLatentImage (t2i) OR LoadImage (i2i)
    # 9: VAEEncode (only for i2i)
    # 10+: LoraLoader nodes (one per lora, chained)
    # 20,22: IPAdapterUnifiedLoader/IPAdapterAdvanced (disabled — needs OpenCLIP ViT-H-14)

    # LoRA node IDs start at 10
    lora_node_start = 10

    nodes = {}

    # Node 1: Load checkpoint
    nodes["1"] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": checkpoint_name}
    }

    # Build LoRA chain: 10, 11, 12, ... up to 10+N-1
    # Each LoraLoader takes (model, clip) from previous node
    # First LoRA takes model/clip from node 1 (checkpoint)
    # Subsequent ones chain from previous LoRA

    prev_model_ref = ["1", 0]  # output 0 = model from CheckpointLoaderSimple
    prev_clip_ref  = ["1", 1]  # output 1 = clip from CheckpointLoaderSimple

    for i, lk in enumerate(lora_keys[:8]):  # max 8
        lora_entry = reg["loras"][lk]
        lora_name = lora_entry["comfyui_lora_name"]
        strength = lora_entry.get("recommended_strength", 1.0)
        node_id = str(lora_node_start + i)
        nodes[node_id] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": prev_model_ref,
                "clip": prev_clip_ref,
                "lora_name": lora_name,
                "strength_model": strength,
                "strength_clip": strength,
            }
        }
        prev_model_ref = [node_id, 0]  # output 0 = model from LoraLoader
        prev_clip_ref  = [node_id, 1]  # output 1 = clip from LoraLoader

    # Node 2: CLIPSetLastLayer (clip skip)
    nodes["2"] = {
        "class_type": "CLIPSetLastLayer",
        "inputs": {
            "clip": prev_clip_ref,
            "stop_at_clip_layer": -clip_skip
        }
    }

    # Node 3: positive conditioning
    nodes["3"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["2", 0],
            "text": prompt
        }
    }

    # Node 4: negative conditioning
    nodes["4"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["2", 0],
            "text": negative
        }
    }

    # IP-Adapter face preservation is disabled until CLIP-ViT-H-14-laion2B-s32B-b79K
    # (OpenCLIP format) is available. The current clip_vision_h.safetensors is a
    # Flux-specific ViT-H encoder with incompatible key format.
    final_model_ref = prev_model_ref

    if source_image:
        # i2i: load image, encode to latent
        # Node 8: LoadImage
        nodes["8"] = {
            "class_type": "LoadImage",
            "inputs": {"image": Path(source_image).name}
        }
        # Node 9: VAEEncode
        nodes["9"] = {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["8", 0],
                "vae": ["1", 2]  # output 2 = VAE from CheckpointLoaderSimple
            }
        }
        latent_ref = ["9", 0]
    else:
        # t2i: empty latent
        nodes["8"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        }
        latent_ref = ["8", 0]

    # Node 5: KSampler
    nodes["5"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": final_model_ref,
            "positive": ["3", 0],
            "negative": ["4", 0],
            "latent_image": latent_ref,
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": denoise,
        }
    }

    # Node 6: VAEDecode
    nodes["6"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["5", 0],
            "vae": ["1", 2]
        }
    }

    # Node 7: SaveImage
    nodes["7"] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["6", 0],
            "filename_prefix": "sdxl_gen"
        }
    }

    return nodes


def submit_workflow(workflow: dict) -> str:
    """Submit workflow to ComfyUI, return prompt_id."""
    result = api_post("/prompt", {"prompt": workflow})
    prompt_id = result.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI rejected workflow: {result}")
    return prompt_id


def poll_until_done(prompt_id: str, timeout: int, poll_interval: int = 10) -> dict:
    """Poll queue and history until task completes or times out."""
    deadline = time.time() + timeout
    consecutive_failures = 0
    MAX_FAILURES = 3

    while time.time() < deadline:
        try:
            queue = api_get("/queue")
            consecutive_failures = 0  # reset on success
            running = [i[1] for i in queue.get("queue_running", [])]
            pending = [i[1] for i in queue.get("queue_pending", [])]
            if prompt_id not in running and prompt_id not in pending:
                history = api_get(f"/history/{prompt_id}")
                if history:
                    return history.get(prompt_id, {})
        except Exception as e:
            consecutive_failures += 1
            print(f"[poll] warning: {e}", file=sys.stderr)
            if consecutive_failures >= MAX_FAILURES:
                raise RuntimeError(
                    f"ComfyUI unreachable after {MAX_FAILURES} attempts — task {prompt_id} lost"
                )

        elapsed = int(time.time() - (deadline - timeout))
        print(f"[poll] {prompt_id[:8]}... running ({elapsed}s elapsed)", file=sys.stderr)
        # Also print to stdout to prevent exec no-output-timeout
        print(f"[poll] running {elapsed}s", flush=True)
        time.sleep(poll_interval)

    raise TimeoutError(f"Task {prompt_id} timed out after {timeout}s")


def collect_outputs(history: dict) -> list:
    """Extract output file paths from ComfyUI history."""
    outputs = []
    for node_id, node_output in history.get("outputs", {}).items():
        for key in ("images", "gifs", "videos"):
            for item in node_output.get(key, []):
                fname = item.get("filename")
                subdir = item.get("subfolder", "")
                ftype  = item.get("type", "output")
                root = COMFYUI_OUTPUT
                if ftype == "temp":
                    root = COMFYUI_BASE / "temp"
                elif ftype == "input":
                    root = COMFYUI_INPUT
                src = root / subdir / fname if subdir else root / fname
                if src.exists():
                    dest = OUTPUT_DIR / fname
                    shutil.copy2(src, dest)
                    outputs.append(str(dest))
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Path to task JSON")
    parser.add_argument("--submit-only", action="store_true",
                        help="Submit job and exit immediately (no polling)")
    parser.add_argument("--poll", metavar="PROMPT_ID",
                        help="Poll for a previously submitted prompt_id (max 60s), then exit")
    args = parser.parse_args()

    task_path = Path(args.task)
    with open(task_path) as f:
        task = json.load(f)

    task_id   = task.get("task_id", f"ic-{uuid.uuid4().hex[:8]}")
    workflow_id = task.get("workflow", "i2v")
    params    = task.get("params", {})

    result = {
        "task_id": task_id,
        "workflow": workflow_id,
        "status": "error",
        "outputs": [],
        "error": None,
    }

    outbox_path = OUTBOX_DIR / f"{task_id}.json"

    # --poll mode: poll for a previously submitted prompt_id (max 60s) then exit
    if args.poll:
        prompt_id = args.poll
        result["prompt_id"] = prompt_id
        try:
            history = poll_until_done(prompt_id, timeout=60)
            outputs = collect_outputs(history)
            result["status"] = "completed"
            result["outputs"] = outputs
            print(f"[client] done: {outputs}", file=sys.stderr)
        except TimeoutError:
            result["status"] = "pending"
            result["error"] = f"still running after 60s (re-poll with --poll {prompt_id})"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        finally:
            with open(outbox_path, "w") as f:
                json.dump(result, f, indent=2)
            print(json.dumps(result))
        return

    try:
        # 1. Check ComfyUI online
        if not check_online():
            result["error"] = f"ComfyUI offline (unreachable endpoints: {COMFYUI_ENDPOINTS})"
            return

        # 2. Load / build workflow
        if workflow_id == "sdxl_multi_lora":
            # Build workflow dynamically from registry
            # model_key / lora_keys live in params (the "params" sub-dict)
            workflow = build_sdxl_workflow(params)
            # Upload source image if present (for i2i)
            source_image = params.get("image_path") or params.get("source_image")
            if source_image:
                upload_image(source_image)
                print(f"[client] uploaded source image: {source_image}", file=sys.stderr)
        else:
            wf_file = WORKFLOWS_DIR / WORKFLOW_MAP.get(workflow_id, f"{workflow_id}.json")
            if not wf_file.exists():
                result["error"] = f"Workflow not found: {wf_file}"
                return

            with open(wf_file) as f:
                workflow_raw = json.load(f)

            # 3. Upload image if provided (single-image workflows)
            image_path = params.get("image_path")
            if image_path:
                image_file = upload_image(image_path)
                params["image_file"] = image_file
                print(f"[client] uploaded image: {image_file}", file=sys.stderr)

            # 3b. Multi-image workflows: upload face/body/mask separately
            # mask_image_path gets binarized + feathered before upload to fix JPEG gray fringe
            for _src_key, _dst_key in (
                ("face_image_path", "face_image_file"),
                ("body_image_path", "body_image_file"),
                ("mask_image_path", "mask_image_file"),
            ):
                _val = params.get(_src_key)
                if _val:
                    if _src_key == "mask_image_path":
                        _val = prepare_mask_image(_val)
                    _uploaded = upload_image(_val)
                    params[_dst_key] = _uploaded
                    print(f"[client] uploaded {_src_key}: {_uploaded}", file=sys.stderr)

            # 4. Inject params into workflow
            workflow = inject_params(workflow_raw, params)

        # 5. Submit to ComfyUI
        prompt_id = submit_workflow(workflow)
        result["prompt_id"] = prompt_id
        result["status"] = "submitted"
        print(f"[client] submitted: {prompt_id}", file=sys.stderr)
        print(f"[submit] prompt_id={prompt_id}", flush=True)

        if args.submit_only:
            # Exit after submit, caller will poll with --poll <prompt_id>
            return

        # 6. Poll until done (full blocking mode)
        timeout = TIMEOUTS.get(workflow_id, 900)
        history = poll_until_done(prompt_id, timeout)

        # 7. Collect outputs
        outputs = collect_outputs(history)
        if not outputs:
            status = history.get("status", {})
            if status.get("status_str") == "error":
                for msg in status.get("messages", []):
                    if isinstance(msg, list) and len(msg) >= 2 and msg[0] == "execution_error":
                        detail = msg[1]
                        node = detail.get("node_id", "?")
                        ntype = detail.get("node_type", "?")
                        emsg = detail.get("exception_message", "unknown error").strip()
                        raise RuntimeError(f"ComfyUI execution_error node={node} type={ntype}: {emsg}")
            raise RuntimeError("ComfyUI completed but no output files were found in history outputs")
        result["status"] = "completed"
        result["outputs"] = outputs
        print(f"[client] done: {outputs}", file=sys.stderr)

    except TimeoutError as e:
        result["status"] = "timeout"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    finally:
        with open(outbox_path, "w") as f:
            json.dump(result, f, indent=2)
        print(json.dumps(result))


if __name__ == "__main__":
    main()
