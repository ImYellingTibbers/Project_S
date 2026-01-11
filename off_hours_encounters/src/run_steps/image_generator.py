from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import random

from face_gate import FaceGate, gate_images

# ----------------------------
# Optional dependency bootstrap
# ----------------------------
def _ensure_import(pkg: str, import_name: Optional[str] = None):
    name = import_name or pkg
    try:
        return __import__(name)
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        return __import__(name)


requests = _ensure_import("requests")
websocket = _ensure_import("websocket-client", "websocket")

# ----------------------------
# Paths / Config
# ----------------------------
ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"

@dataclass
class ComfyConfig:
    base_url: str = os.getenv("COMFY_URL", "http://127.0.0.1:8188")
    client_id: str = os.getenv("COMFY_CLIENT_ID", "project_s_image_generator")
    input_subfolder_root: str = os.getenv("COMFY_INPUT_SUBFOLDER_ROOT", "project_s")

# ----------------------------
# Constants
# ----------------------------
ID_MATCH_POSITIVE = (
    "same person as reference image, "
    "preserve original scene and composition, "
    "preserve lighting and camera angle, "
    "preserve clothing and body proportions, "
    "subtle correction only, "
    "photorealistic, "
    "natural skin texture, "
    "no beautification"
)

ID_MATCH_NEGATIVE = (
    "different person, face mismatch, identity change, face swap,"
    "incorrect face, altered identity,"
    "beauty retouching, model-like appearance, idealized features,"
    "plastic skin, overly smooth skin, airbrushed face,"
    "exaggerated facial features, stylized face, cartoon face,"
    "cgi face, digital face,"
    "distorted face, warped face, melted face,"
    "duplicated face, asymmetrical eyes,"
    "misaligned pupils, extra eyes, extra ears,"
    "blurry face, low detail face, out of focus face"
)

# ----------------------------
# Helpers
# ----------------------------
def latest_run_dir() -> Path:
    return sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())[-1]

def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(p: Path, d: dict):
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")

def stable_seed(run_id: str | None, run_dir: Path | None = None) -> int:
    """
    Generate a stable numeric seed.
    Priority:
    1) run_id string (preferred)
    2) run_dir name
    3) hard fallback
    """
    source = None

    if isinstance(run_id, str) and run_id:
        source = run_id
    elif run_dir is not None:
        source = run_dir.name
    else:
        source = "fallback"

    try:
        return int(source.split("__")[0].replace("_", ""))
    except Exception:
        return sum(ord(c) for c in source) * 1000


# ----------------------------
# ComfyUI plumbing
# ----------------------------
def queue_prompt(cfg: ComfyConfig, prompt: dict) -> str:
    r = requests.post(
        f"{cfg.base_url}/prompt",
        json={"prompt": prompt, "client_id": cfg.client_id},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["prompt_id"]

def wait_for_completion(cfg: ComfyConfig, pid: str, timeout: int = 1200):
    ws_url = cfg.base_url.replace("http", "ws") + f"/ws?clientId={cfg.client_id}"
    ws = websocket.WebSocket()
    ws.settimeout(5)
    ws.connect(ws_url)
    start = time.time()

    try:
        while time.time() - start < timeout:
            try:
                msg = ws.recv()
                data = json.loads(msg)
                if data.get("type") == "executing" and data["data"].get("node") is None:
                    return
            except Exception:
                continue
        raise TimeoutError(pid)
    finally:
        ws.close()

def get_history(cfg: ComfyConfig, pid: str) -> dict:
    r = requests.get(f"{cfg.base_url}/history/{pid}", timeout=60)
    r.raise_for_status()
    return r.json()

def extract_image(history: dict) -> dict:
    for block in history.values():
        for out in block.get("outputs", {}).values():
            if isinstance(out, dict) and out.get("images"):
                return out["images"][0]
    raise RuntimeError("No image found")

def download_image(cfg: ComfyConfig, info: dict) -> bytes:
    r = requests.get(
        f"{cfg.base_url}/view",
        params={
            "filename": info["filename"],
            "subfolder": info.get("subfolder", ""),
            "type": info.get("type", "output"),
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.content

def upload_input_image(cfg: ComfyConfig, path: Path, subfolder: str) -> str:
    with path.open("rb") as f:
        r = requests.post(
            f"{cfg.base_url}/upload/image",
            files={"image": (path.name, f, "image/png")},
            data={"subfolder": subfolder, "type": "input", "overwrite": "true"},
            timeout=120,
        )
    r.raise_for_status()
    return f"{subfolder}/{path.name}".replace("\\", "/")

# ----------------------------
# Workflow patching
# ----------------------------
def patch_prompt(wf: dict, *, positive: str, negative: Optional[str], seed: int, filename: str) -> dict:
    wf = json.loads(json.dumps(wf))
    for node in wf.values():
        if node.get("class_type") == "CLIPTextEncode":
            text = node["inputs"].get("text", "")
            if "NEGATIVE" in node.get("_meta", {}).get("title", "") and negative:
                node["inputs"]["text"] = negative
            elif "POSITIVE" in node.get("_meta", {}).get("title", ""):
                node["inputs"]["text"] = positive
        if node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = seed
        elif node.get("class_type") == "KSamplerAdvanced":
            node["inputs"]["noise_seed"] = seed
        if node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = filename
    return wf

def patch_loadimage(wf: dict, image_path: str) -> dict:
    wf = json.loads(json.dumps(wf))
    for node in wf.values():
        if node.get("class_type") == "LoadImage":
            if "Beat" in node.get("_meta", {}).get("title", ""):
                node["inputs"]["image"] = image_path
    return wf

# ----------------------------
# Main
# ----------------------------
def main():
    cfg = ComfyConfig()
    run = latest_run_dir()
    image_plan = load_json(run / "image_plan.json")
    run_id = image_plan["run_id"]
    canon_seed = random.randint(0, 2**32 - 1)
    print(f"canon seed: {canon_seed}")
    image_plan["canon"]["seed"] = canon_seed
    save_json(run / "image_plan.json", image_plan)
    seed0 = stable_seed(run_id, run)

    images_dir = run / "images"
    images_dir.mkdir(exist_ok=True)

    workflows = {
        "canon": load_json(ROOT / "src/image_generation/horror_shorts_txt2img_canon.json"),
        "beats": load_json(ROOT / "src/image_generation/horror_shorts_txt2img_beat_workflow.json"),
        "id_match": load_json(ROOT / "src/image_generation/horror_shorts_img2img_ID_match_workflow.json"),
    }

    # ---- Canon
    canon_wf = patch_prompt(
        workflows["canon"],
        positive=image_plan["canon"]["image_prompt_body"],
        negative=None,
        seed=canon_seed,
        filename="project_s/canon",
    )
    pid = queue_prompt(cfg, canon_wf)
    wait_for_completion(cfg, pid)
    canon_info = extract_image(get_history(cfg, pid))
    canon_path = images_dir / "canon.png"
    canon_path.write_bytes(download_image(cfg, canon_info))
    
    # ---- Pass 1: Beats
    face_gate = FaceGate()
    protagonist_images = []
    for beat in image_plan["beats"]:
        fname = f"beat_{beat['beat_id']:03d}"
        is_p = beat["protagonist_visible"]
        out_name = f"{fname}{'_p' if is_p else ''}"

        wf = patch_prompt(
            workflows["beats"],
            positive=beat["image_prompt_body"],
            negative=None,
            seed=seed0 + beat["beat_id"],
            filename=f"project_s/{out_name}",
        )

        pid = queue_prompt(cfg, wf)
        wait_for_completion(cfg, pid)
        info = extract_image(get_history(cfg, pid))
        img_path = images_dir / f"{out_name}.png"
        img_path.write_bytes(download_image(cfg, info))

        if is_p:
            protagonist_images.append(img_path)

    # ---- Gate + Pass 2
    gate_results = gate_images(face_gate, protagonist_images)

    for img_path, result in gate_results.items():
        final_path = img_path.with_name(img_path.name.replace("_p", ""))

        if not result.should_refine:
            img_path.rename(final_path)
            continue

        unique_subfolder = f"{cfg.input_subfolder_root}/{run_id}/{img_path.stem}"

        uploaded_path = upload_input_image(
            cfg,
            img_path,
            subfolder=unique_subfolder
        )


        wf = patch_loadimage(workflows["id_match"], uploaded_path)
        wf = patch_prompt(
            wf,
            positive=ID_MATCH_POSITIVE,
            negative=ID_MATCH_NEGATIVE,
            seed=seed0,
            filename=f"project_s/{final_path.stem}",
        )

        pid = queue_prompt(cfg, wf)
        wait_for_completion(cfg, pid)
        info = extract_image(get_history(cfg, pid))
        final_path.write_bytes(download_image(cfg, info))
        img_path.unlink()

    print("Image generation complete.")

if __name__ == "__main__":
    main()
