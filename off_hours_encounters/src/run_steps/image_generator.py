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

# Note: HORROR_VISUAL_BIAS is now largely handled by the Prompt Generator LLM, 
# but we keep this as a safety fallback or global negative reinforcement.
NEGATIVE_PROMPT = (
    "anime, cartoon, chibi, bright cheerful lighting, neon colors, "
    "oversaturated, cgi, plastic skin, distorted anatomy, text, watermark, "
    "multiple frames, split screen, storyboard, comic panel"
)

# ----------------------------
# Helpers
# ----------------------------
def latest_run_dir() -> Path:
    # Get the most recent folder in /runs
    return sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()])[-1]

def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

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
    return r.json()[pid] # Accessing the specific prompt ID history

def extract_image(history: dict) -> dict:
    for node_id, node_output in history.get("outputs", {}).items():
        if "images" in node_output:
            return node_output["images"][0]
    raise RuntimeError("No image found in workflow output")

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

def patch_prompt(wf: dict, *, positive: str, negative: str, seed: int, filename: str) -> dict:
    wf = json.loads(json.dumps(wf))
    for node in wf.values():
        if node.get("class_type") == "CLIPTextEncode":
            title = node.get("_meta", {}).get("title", "").upper()
            if "NEGATIVE" in title:
                node["inputs"]["text"] = negative
            else:
                # The prompt generator now builds the full string, so we pass it directly
                node["inputs"]["text"] = positive
        if node.get("class_type") in ["KSampler", "KSamplerAdvanced"]:
            seed_key = "seed" if node["class_type"] == "KSampler" else "noise_seed"
            node["inputs"][seed_key] = seed
        if node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = filename
    return wf

# ----------------------------
# Main
# ----------------------------
def main():
    cfg = ComfyConfig()
    run = latest_run_dir()
    
    # NEW: Load the final compiled prompts (28+ scenes)
    prompt_artifact = load_json(run / "final_image_prompts.json")
    run_id = prompt_artifact.get("run_id")
    seed = random.randint(100000, 1000000)

    images_dir = run / "images"
    images_dir.mkdir(exist_ok=True)

    # Load workflow template
    workflow_path = ROOT / "src/image_generation/horror_shorts_txt2img_beat_workflow.json"
    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow not found at {workflow_path}")
    
    base_workflow = load_json(workflow_path)

    print(f"[*] Starting Image Generation for Run: {run_id}")

    global_scene_counter = 0
    
    # NEW: Iterate through Chapters and Nested Prompts
    for chapter in prompt_artifact.get("chapters", []):
        chapter_idx = chapter.get("chapter_index")
        
        for prompt_obj in chapter.get("prompts", []):
            # The prompt is already pre-compiled with Style and Canon by image_prompt_generator.py
            full_prompt_text = prompt_obj.get("prompt")
            
            # Formatted name for alphabetical sorting in editors: scene_000.png
            out_name = f"scene_{global_scene_counter:03d}_ch{chapter_idx}"

            print(f"[+] Processing: {out_name}...")

            wf = patch_prompt(
                base_workflow,
                positive=full_prompt_text,
                negative=NEGATIVE_PROMPT,
                seed=seed + (global_scene_counter * 13),
                filename=f"project_s/{run_id}/{out_name}"
            )

            try:
                pid = queue_prompt(cfg, wf)
                wait_for_completion(cfg, pid)
                
                # Fetch and save locally to the run folder
                history = get_history(cfg, pid)
                img_info = extract_image(history)
                img_data = download_image(cfg, img_info)
                
                img_path = images_dir / f"{out_name}.png"
                img_path.write_bytes(img_data)
                
                print(f"    [OK] Saved to {img_path.name}")
            except Exception as e:
                print(f"    [ERROR] Failed scene {global_scene_counter}: {e}")
            
            global_scene_counter += 1

    print(f"\n[SUCCESS] Generated {global_scene_counter} images for video production.")

if __name__ == "__main__":
    main()