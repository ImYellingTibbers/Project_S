from __future__ import annotations

import json
import os
import sys
import time
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List

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
    client_id: str = os.getenv("COMFY_CLIENT_ID", "project_s_generator")

# STRENGTHENED NEGATIVE PROMPT
NEGATIVE_PROMPT = (
    "woman, female, girl, feminine, lady, child, "
    "photorealistic, photo, DSLR, studio lighting, fashion photography, "
    "hyperreal skin, skin pores, symmetrical face, beauty lighting, "
    "romantic, sensual, explicit gore, sexualized pose, intimate framing, "
    "shirtless male, bare torso, erotic, nsfw, fetish, nudity, "
    "bright cheerful lighting, neon colors, oversaturated, "
    "cgi, unreal engine, glossy 3d, plastic skin, "
    "text, watermark, logo, caption, multiple frames, split screen,abstract, conceptual, symbolic, surreal, dreamlike, artistic interpretation, metaphorical, fantasy creature"
)

STYLE_PREFIX = (
    "dark cinematic horror frame, muted colors, realistic lighting, "
    "film still, shallow depth of field, heavy shadows, grain, "
    "natural textures, no illustration, no painterly style"
)

# ----------------------------
# ComfyUI Helpers
# ----------------------------
def latest_run_dir() -> Path:
    return sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()])[-1]

def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def patch_prompt(wf: dict, *, positive: str, negative: str, seed: int, filename: str) -> dict:
    """
    CRITICAL FIX: Targets specific node IDs 92 (Positive) and 50 (Negative) 
    to prevent the script from patching the wrong text boxes.
    """
    wf = json.loads(json.dumps(wf))
    
    # Patch Positive Prompt (Node 92)
    if "92" in wf:
        wf["92"]["inputs"]["text"] = positive
    
    # Patch Negative Prompt (Node 50)
    if "50" in wf:
        wf["50"]["inputs"]["text"] = negative
        
    # Patch KSampler (Node 55)
    if "55" in wf:
        wf["55"]["inputs"]["seed"] = seed
        # Ensure CFG is high enough for detail
        wf["55"]["inputs"]["cfg"] = 8.0
        
    # Patch SaveImage (Node 57)
    if "57" in wf:
        wf["57"]["inputs"]["filename_prefix"] = filename
        
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

def get_history(cfg: ComfyConfig, pid: str) -> dict:
    r = requests.get(f"{cfg.base_url}/history/{pid}")
    return r.json()[pid]

def extract_image(history: dict) -> dict:
    for node_output in history.get("outputs", {}).values():
        if "images" in node_output:
            return node_output["images"][0]
    raise RuntimeError("No image found")

def download_image(cfg: ComfyConfig, info: dict) -> bytes:
    r = requests.get(f"{cfg.base_url}/view", params={"filename": info["filename"], "subfolder": info.get("subfolder", ""), "type": info.get("type", "output")})
    return r.content

# ----------------------------
# Main Execution Logic
# ----------------------------
def main():
    cfg = ComfyConfig()
    run = latest_run_dir()
    
    scenes_path = run / "visual_scenes.json"
    canon_path = run / "canon.json"

    if not scenes_path.exists():
        print(f"[!] Error: {scenes_path} not found.")
        return

    scenes_data = load_json(scenes_path)
    scenes = scenes_data.get("scenes", [])
    
    canon_data = load_json(canon_path)
    # Extract monster and man details
    canon_map = {c["id"]: c["description"] for c in canon_data.get("canon", [])}

    images_dir = run / "images"
    images_dir.mkdir(exist_ok=True)

    workflow_path = ROOT / "src/image_generation/horror_shorts_txt2img_beat_workflow.json"
    base_workflow = load_json(workflow_path)

    print(f"[*] Starting Image Generation for {len(scenes)} beats...")

    for idx, scene in enumerate(scenes):
        visible_ids = scene.get("visible_canon_ids", [])
        
        # 1. ADDITIVE CHARACTER ASSEMBLY
        # This allows both Man (c1) and Monster (c2) to be in the prompt simultaneously
        subjects = []
        if "c1" in visible_ids:
            subjects.append(canon_map.get('c1', 'adult male'))
        if "c2" in visible_ids:
            # We add a high weight to the entity to make sure it overcomes the background
            subjects.append(canon_map.get('c2', 'contorted presence'))
            
        character_block = ", ".join(subjects) if subjects else "empty dark room"
        if "c2" in visible_ids and "c1" in visible_ids:
            character_block += ", entity positioned far behind the man, partially obscured"

        # 2. HIERARCHY ASSEMBLY (Monster/Man -> Scene Action -> Environment)
        prompt_parts = [
            scene.get("literal_sd_prompt", ""),
        ]

        if "c2" in visible_ids:
            prompt_parts.append(character_block)

        prompt_parts.append(STYLE_PREFIX)
    
        prompt_text = ", ".join(prompt_parts)
        out_name = f"scene_{idx:03d}"
        base_seed = 777000
        current_seed = base_seed + idx * 37

        print(f"    [+] Rendering {out_name} with Entity Weighting...")

        wf = patch_prompt(
            base_workflow,
            positive=prompt_text,
            negative=NEGATIVE_PROMPT,
            seed=current_seed,
            filename=f"project_s/{run.name}/{out_name}"
        )

        try:
            pid = queue_prompt(cfg, wf)
            wait_for_completion(cfg, pid)
            
            history = get_history(cfg, pid)
            img_info = extract_image(history)
            img_data = download_image(cfg, img_info)

            out_path = images_dir / f"{out_name}.png"
            out_path.write_bytes(img_data)
            print(f"        [OK] Saved to {out_path.name}")
            
        except Exception as e:
            print(f"        [ERROR] Beat {idx} failed: {e}")

    print(f"\n[SUCCESS] Render complete. Images located in {images_dir}")

if __name__ == "__main__":
    main()