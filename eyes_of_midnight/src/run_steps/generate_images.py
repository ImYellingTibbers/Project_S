from __future__ import annotations

import os
import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

import requests
import websocket
from dotenv import load_dotenv

# ============================================================
# Project bootstrap
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.start_comfyui import start as start_comfyui

load_dotenv()

# ============================================================
# Environment
# ============================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "google/gemma-3-27b-it"

COMFY_URL = os.getenv("COMFY_URL", "http://127.0.0.1:8188")
COMFY_CLIENT_ID = os.getenv("COMFY_CLIENT_ID", "key_image_gen")

ROOT = PROJECT_ROOT
RUNS_DIR = ROOT / "runs"
WORKFLOW_PATH = ROOT / "src/image_generation/horror_shorts_txt2img_beat_workflow.json"

# ============================================================
# ComfyUI style constraints (shared)
# ============================================================

NEGATIVE_PROMPT = (
    "faces, people, person, human figure, body, silhouette, "
    "monsters, creatures, ghosts, demons, entities, "
    "dramatic action, motion blur, cinematic lighting, "
    "stylized horror, exaggerated fear, "
    "cgi, unreal engine, 3d render, plastic texture, "
    "text, watermark, logo, caption, "
    "ruins, abandoned, decay, debris, rubble, post apocalyptic"
)

STYLE_PREFIX = (
    "photorealistic nighttime photograph, real-world location, "
    "quiet residential or urban environment, "
    "empty but clearly intended for people, "
    "streetlights, porch lights, traffic signals, or interior lamps as the only light sources, "
    "deep shadows swallowing detail, limited visibility, "
    "cool muted color tones, low saturation, "
    "natural grain, slight sensor noise, realistic exposure, "
    "human eye-level viewpoint, standing perspective, "
    "static composition, no motion, no action, "
    "documentary realism, uncinematic, unstylized, "
    "uneasy calm, lingering tension, something feels wrong but nothing is happening"
)

THUMBNAIL_STYLE_PREFIX = (
    "photorealistic nighttime photograph, "
    "strong visual contrast, high readability at small size, "
    "one dominant subject or area of focus, "
    "heavy surrounding darkness, "
    "streetlight glow, window light, or doorway light cutting through darkness, "
    "suggested human presence through distant silhouette or shadow only, "
    "no visible faces, no detail confirmation, "
    "quiet but threatening atmosphere, "
    "simple composition, bold shapes, negative space, "
    "feels like witnessing something you should not be seeing"
)

# ============================================================
# OpenRouter helper
# ============================================================

def call_llm(messages, temperature=0.4, max_tokens=800, require_json=True) -> str:
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if require_json:
        payload["response_format"] = {"type": "json_object"}

    r = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    if not content:
        raise RuntimeError("LLM returned empty content")
    return content.strip()

# ============================================================
# Run discovery
# ============================================================

def get_latest_run_with_script() -> Path:
    candidates = []
    for d in RUNS_DIR.iterdir():
        if not d.is_dir():
            continue
        script = d / "script" / "full_script.txt"
        if script.exists():
            candidates.append(d)
    if not candidates:
        raise RuntimeError("No run folder with full_script.txt found")
    return max(candidates, key=lambda p: p.stat().st_mtime)

# ============================================================
# Prompt generation
# ============================================================

def generate_image_prompts(script_text: str) -> Dict[str, str]:
    system = (
        "You are analyzing a full confessional horror narration script.\n\n"
        "This is realistic, first-person horror.\n"
        "No supernatural elements. No monsters. No fantasy.\n\n"
        "You must FIRST determine the dominant real-world setting that emotionally defines the entire story.\n"
        "This is the place the listener subconsciously associates with the fear.\n\n"
        "Then generate image prompts using these rules.\n\n"
        "OUTPUT STRICT JSON ONLY with exactly three fields:\n"
        "- background_prompt\n"
        "- thumbnail_prompt_a\n"
        "- thumbnail_prompt_b\n\n"
        "BACKGROUND PROMPT RULES:\n"
        "- One real location only\n"
        "- Empty of people, but clearly human-built\n"
        "- Nighttime or near-darkness\n"
        "- Ordinary, believable place\n"
        "- Designed to sit behind narration for long duration\n\n"
        "THUMBNAIL PROMPT RULES:\n"
        "- Thumbnails are marketing images, not story scenes\n"
        "- Each thumbnail must present a visual question\n"
        "- Focus on isolation, distance, or being watched\n"
        "- Use roads, windows, doorways, alleys, or streetlights\n"
        "- Strong contrast and immediate clarity\n"
        "- No text, no faces, no explicit threat"
    )

    user = (
        "Here is the full narration script.\n"
        "You must analyze the entire script before deciding anything.\n\n"
        f"{script_text}\n\n"
        "Determine the dominant setting and psychological tension.\n"
        "Then generate the prompts."
    )

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.45,
        max_tokens=700,
        require_json=True,
    )

    data = json.loads(raw)

    for key in ("background_prompt", "thumbnail_prompt_a", "thumbnail_prompt_b"):
        if key not in data or not data[key].strip():
            raise RuntimeError(f"Missing required prompt: {key}")

    return {
        "background": data["background_prompt"].strip(),
        "thumbnail_a": data["thumbnail_prompt_a"].strip(),
        "thumbnail_b": data["thumbnail_prompt_b"].strip(),
    }

# ============================================================
# ComfyUI helpers
# ============================================================

@dataclass
class ComfyConfig:
    base_url: str = COMFY_URL
    client_id: str = COMFY_CLIENT_ID

def patch_workflow(workflow: dict, prompt: str, seed: int, filename_prefix: str) -> dict:
    wf = json.loads(json.dumps(workflow))
    style = STYLE_PREFIX
    if "thumbnail" in filename_prefix:
        style = THUMBNAIL_STYLE_PREFIX

    wf["92"]["inputs"]["text"] = f"{style}, {prompt}"
    wf["50"]["inputs"]["text"] = NEGATIVE_PROMPT
    wf["55"]["inputs"]["seed"] = seed
    wf["55"]["inputs"]["cfg"] = 8.0
    wf["57"]["inputs"]["filename_prefix"] = filename_prefix
    return wf

def queue_prompt(cfg: ComfyConfig, prompt: dict) -> str:
    r = requests.post(
        f"{cfg.base_url}/prompt",
        json={"prompt": prompt, "client_id": cfg.client_id},
    )
    r.raise_for_status()
    return r.json()["prompt_id"]

def wait_for_completion(cfg: ComfyConfig, pid: str):
    ws_url = cfg.base_url.replace("http", "ws") + f"/ws?clientId={cfg.client_id}"
    ws = websocket.WebSocket()
    ws.connect(ws_url)
    try:
        while True:
            msg = json.loads(ws.recv())
            if msg.get("type") == "executing" and msg["data"].get("node") is None:
                return
    finally:
        ws.close()

def download_image(cfg: ComfyConfig, pid: str) -> bytes:
    history = requests.get(f"{cfg.base_url}/history/{pid}").json()[pid]
    for out in history.get("outputs", {}).values():
        if "images" in out:
            img = out["images"][0]
            r = requests.get(
                f"{cfg.base_url}/view",
                params={
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                },
            )
            return r.content
    raise RuntimeError("No image found in ComfyUI output")

# ============================================================
# Main execution
# ============================================================

def main():
    start_comfyui()
    cfg = ComfyConfig()

    run_dir = get_latest_run_with_script()
    script_path = run_dir / "script" / "full_script.txt"
    script_text = script_path.read_text(encoding="utf-8").strip()

    print(f"[IMG] Using run: {run_dir.name}", flush=True)

    prompts = generate_image_prompts(script_text)

    img_dir = run_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    with open(WORKFLOW_PATH, "r") as f:
        base_workflow = json.load(f)

    jobs = [
        ("background_img", prompts["background"], 910001),
        ("thumbnail_a", prompts["thumbnail_a"], 910101),
        ("thumbnail_b", prompts["thumbnail_b"], 910201),
    ]

    for name, prompt, seed in jobs:
        print(f"[IMG] Rendering {name}.png", flush=True)
        wf = patch_workflow(
            base_workflow,
            prompt,
            seed,
            f"renders/{run_dir.name}/{name}",
        )
        pid = queue_prompt(cfg, wf)
        wait_for_completion(cfg, pid)
        img = download_image(cfg, pid)
        (img_dir / f"{name}.png").write_bytes(img)

    print("[IMG] Key images generated successfully.", flush=True)

if __name__ == "__main__":
    main()
