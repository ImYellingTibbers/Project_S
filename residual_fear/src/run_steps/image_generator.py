from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
    
    
HORROR_VISUAL_BIAS = (
    "ominous, unsettling, oppressive atmosphere, "
    "low visibility, heavy shadow, harsh contrast, "
    "claustrophobic framing, obscured details, "
    "threat implied but not shown, "
    "psychological horror, cinematic lighting, "
    "grain, noise, imperfect, uncomfortable composition"
)

NEGATIVE_PROMPT = (
    "cgi, 3d render, illustration, painting, anime, cartoon, "
    "stylized, concept art, graphic novel, "
    "painterly, oil painting, watercolor, "
    "neon lighting, fantasy lighting, supernatural glow, "
    "heavy color grading, extreme HDR, "
    "fisheye lens, ultra wide distortion, dutch angle, "
    "impossible geometry, warped architecture, "
    "blur, low resolution, noise, motion blur, "
    "jpeg artifacts, compression artifacts, "
    "people, humans, person, body, face, head, "
    "hands, fingers, limbs, silhouettes, "
    "reflections, mirrors, "
    "text, watermark, logo, subtitles, captions, "
    "UI elements, branded signage, readable labels, "
    "graphic gore, dismemberment, exposed organs, "
    "blood spray, torture"
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

# ----------------------------
# Main
# ----------------------------
def main():
    cfg = ComfyConfig()
    run = latest_run_dir()
    image_plan = load_json(run / "image_plan.json")
    run_id = image_plan["run_id"]
    seed0 = stable_seed(run_id, run)

    images_dir = run / "images"
    images_dir.mkdir(exist_ok=True)

    workflows = {
        "beats": load_json(ROOT / "src/image_generation/horror_shorts_txt2img_beat_workflow.json"),
    }

    
    # ---- Pass 1: Beats
    for beat in image_plan["beats"]:
        beat_id = beat["beat_id"]

        if beat.get("unit_type") == "microbeat":
            micro_id = beat["microbeat_id"]
            out_name = f"beat_{beat_id:03d}_micro_{micro_id:03d}"
        else:
            out_name = f"beat_{beat_id:03d}"

        wf = patch_prompt(
            workflows["beats"],
            positive=f"{HORROR_VISUAL_BIAS}. {beat['image_prompt_body']}",
            negative=NEGATIVE_PROMPT,
            seed=seed0 + beat_id * 1000 + (beat.get("microbeat_id", 0)),
            filename=f"project_s/{out_name}",
        )

        pid = queue_prompt(cfg, wf)
        wait_for_completion(cfg, pid)
        info = extract_image(get_history(cfg, pid))
        img_path = images_dir / f"{out_name}.png"
        img_path.write_bytes(download_image(cfg, info))

    print("Image generation complete.")

if __name__ == "__main__":
    main()
