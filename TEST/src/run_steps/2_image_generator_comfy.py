import os
import json
import time
import random
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Ensure required dependencies are installed
def _ensure_import(pkg: str, import_name: Optional[str] = None):
    name = import_name or pkg
    try:
        return __import__(name)
    except ImportError:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        return __import__(name)

requests = _ensure_import("requests")
websocket = _ensure_import("websocket-client", "websocket")

# --- CONFIGURATION ---
ROOT = Path(__file__).resolve().parent.parent.parent 
RUNS_DIR = ROOT / "runs"
WORKFLOW_PATH = ROOT / "src/image_generation/horror_shorts_txt2img_beat_workflow.json"

@dataclass
class ComfyConfig:
    base_url: str = os.getenv("COMFY_URL", "http://127.0.0.1:8188")
    client_id: str = os.getenv("COMFY_CLIENT_ID", "horror_gen_client")

# STYLIZED HORROR CONSTANTS
NEGATIVE_PROMPT = (
    "woman, female, girl, feminine, lady, child, "
    "photorealistic, photo, DSLR, studio lighting, fashion photography, "
    "hyperreal skin, skin pores, symmetrical face, beauty lighting, "
    "romantic, sensual, explicit gore, sexualized pose, intimate framing, "
    "shirtless male, bare torso, erotic, nsfw, fetish, nudity, "
    "bright cheerful lighting, neon colors, oversaturated, "
    "cgi, unreal engine, glossy 3d, plastic skin, "
    "text, watermark, logo, caption, multiple frames, split screen, "
    "abstract, conceptual, symbolic, surreal, dreamlike, artistic interpretation"
)

STYLE_PREFIX = (
    "dark cinematic horror frame, muted colors, realistic lighting, "
    "film still, shallow depth of field, heavy shadows, grain, "
    "natural textures, no illustration, no painterly style"
)

# --- COMFYUI HELPERS ---
def get_latest_run():
    if not RUNS_DIR.exists(): return None
    folders = [f for f in RUNS_DIR.iterdir() if f.is_dir() and f.name.startswith("run_")]
    return max(folders, key=os.path.getmtime) if folders else None

def patch_workflow(wf: dict, prompt: str, seed: int, filename: str) -> dict:
    """Targets specific node IDs: 92 (Positive), 50 (Negative), 55 (KSampler)"""
    wf = json.loads(json.dumps(wf))
    if "92" in wf: wf["92"]["inputs"]["text"] = f"{STYLE_PREFIX}, {prompt}"
    if "50" in wf: wf["50"]["inputs"]["text"] = NEGATIVE_PROMPT
    if "55" in wf:
        wf["55"]["inputs"]["seed"] = seed
        wf["55"]["inputs"]["cfg"] = 8.0
    if "57" in wf: wf["57"]["inputs"]["filename_prefix"] = filename
    return wf

def queue_prompt(cfg: ComfyConfig, prompt: dict) -> str:
    r = requests.post(f"{cfg.base_url}/prompt", json={"prompt": prompt, "client_id": cfg.client_id})
    r.raise_for_status()
    return r.json()["prompt_id"]

def wait_for_completion(cfg: ComfyConfig, pid: str):
    ws_url = cfg.base_url.replace("http", "ws") + f"/ws?clientId={cfg.client_id}"
    ws = websocket.WebSocket()
    ws.connect(ws_url)
    try:
        while True:
            msg = ws.recv()
            data = json.loads(msg)
            if data.get("type") == "executing" and data["data"].get("node") is None:
                return
    finally:
        ws.close()

def download_image(cfg: ComfyConfig, pid: str) -> bytes:
    history = requests.get(f"{cfg.base_url}/history/{pid}").json()[pid]
    for node_output in history.get("outputs", {}).values():
        if "images" in node_output:
            info = node_output["images"][0]
            r = requests.get(f"{cfg.base_url}/view", params={
                "filename": info["filename"], 
                "subfolder": info.get("subfolder", ""), 
                "type": info.get("type", "output")
            })
            return r.content
    raise RuntimeError("No image found in history")

# --- MAIN EXECUTION ---
def generate_images():
    cfg = ComfyConfig()
    run_folder = get_latest_run()
    
    if not run_folder or not (run_folder / "script.json").exists():
        print("❌ Error: Valid run folder or script.json not found.")
        return
    
    img_dir = run_folder / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    # Load project data and workflow
    with open(run_folder / "script.json", "r") as f:
        data = json.load(f)
    with open(WORKFLOW_PATH, "r") as f:
        base_workflow = json.load(f)

    segments = data.get("segments", [])
    print(f"🚀 Starting ComfyUI Generation for {len(segments)} segments...")

    for i, segment in enumerate(segments):
        raw_prompt = segment['image_prompt']
        out_name = f"image_{i+1:03d}"
        seed = 777000 + (i * 37)

        print(f"🎨 Rendering {out_name}.png...", end=" ", flush=True)
        
        wf = patch_workflow(base_workflow, raw_prompt, seed, f"renders/{run_folder.name}/{out_name}")

        try:
            pid = queue_prompt(cfg, wf)
            wait_for_completion(cfg, pid)
            img_data = download_image(cfg, pid)
            
            output_path = img_dir / f"{out_name}.png"
            output_path.write_bytes(img_data)
            print("✅ [SAVED]")

        except Exception as e:
            print(f"❌ [ERROR]: {e}")

    print(f"\n📁 Batch complete! Images saved to: {img_dir}")

if __name__ == "__main__":
    generate_images()