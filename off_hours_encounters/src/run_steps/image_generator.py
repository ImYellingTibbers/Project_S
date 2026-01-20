from __future__ import annotations

import json
import os
import sys
import time
import random
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
    "ominous, oppressive atmosphere, "
    "deep shadow dominance, limited visibility, "
    "dense fog or haze obscuring distance, "
    "isolated subject or silhouette within the frame, "
    "strong negative space, "
    "threat implied but not shown, "
    "psychological horror tone, "
    "moody cinematic lighting, uneven illumination, "
    "silhouettes emphasized over detail, "
    "grim, unsettling composition, "
    "single cinematic frame, one shot only, no panels, no split frame, "
    "no collage, no triptych, no film strip, no storyboard layout"
)

NEGATIVE_PROMPT = (
    "anime, cartoon, chibi, "
    "bright cheerful lighting, "
    "neon colors, oversaturated colors, "
    "extreme HDR, glowing outlines, "
    "fantasy magic effects, supernatural glow, "
    "cgi, plastic skin, video game graphics, "
    "fisheye lens, ultra wide distortion, "
    "dutch angle, tilted horizon, "
    "impossible geometry, warped architecture, "
    "low resolution, jpeg artifacts, compression artifacts, "
    "motion blur, streaking, smear, "
    "extra people, crowd, "
    "duplicate heads, extra limbs, missing limbs, "
    "malformed hands, distorted anatomy, "
    "text, watermark, logo, subtitles, captions, "
    "UI elements, branded signage, readable labels, "
    "graphic gore, exposed organs, torture, dismemberment, "
    "multiple frames, split screen, diptych, triptych, collage, "
    "storyboard, comic panel, film strip, contact sheet, montage"
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
    visual_canon = load_json(run / "visual_canon.json")
    CHARACTER_CANON = visual_canon["character_description"]
    STYLE_CANON = visual_canon["style"]
    run_id = image_plan["run_id"]
    seed = random.randint(100000, 1000000)

    images_dir = run / "images"
    images_dir.mkdir(exist_ok=True)

    workflows = {
        "scenes": load_json(ROOT / "src/image_generation/horror_shorts_txt2img_beat_workflow.json"),
    }

    
    # ---- Pass 1: scenes
    for scene in image_plan["scenes"]:
        scene_index = scene["scene_index"]

        out_name = f"scene_{scene_index:03d}"

        wf = patch_prompt(
            workflows["scenes"],
            positive=(
                f"{CHARACTER_CANON}. "
                f"{STYLE_CANON}. "
                f"{HORROR_VISUAL_BIAS}. "
                f"{scene['image_prompt_body']}"
            ),
            negative=NEGATIVE_PROMPT,
            seed=seed + scene_index * 1000,
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
