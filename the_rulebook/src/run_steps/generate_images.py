from __future__ import annotations

import os
import json
import sys
from pathlib import Path
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
    "minimalist composition, sparse environment, intentional emptiness, restrained detail, "
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
    
def extract_thumbnail_concepts(script_text: str) -> Dict[str, str]:
    system = (
        "You are extracting thumbnail concepts for a YouTube horror video.\n\n"
        "This is NOT story writing.\n"
        "This is marketing abstraction.\n\n"
        "Rules:\n"
        "- Ignore narrative order\n"
        "- Ignore specific scenes\n"
        "- Identify the SINGLE biggest implied threat\n"
        "- Identify the SINGLE most visually recognizable location\n"
        "- Generate short warning-style text that implies danger\n\n"
        "The result must be usable for a YouTube thumbnail.\n\n"
        "OUTPUT STRICT JSON ONLY:\n"
        "{\n"
        '  "location": "...",\n'
        '  "threat": "...",\n'
        '  "warning_text_a": "...",\n'
        '  "warning_text_b": "..."\n'
        "}"
    )

    user = (
        "Here is the full narration script.\n\n"
        f"{script_text}\n\n"
        "Extract thumbnail concepts.\n"
        "- Location must be a place, not a scene\n"
        "- Threat must be implied, not explained\n"
        "- Warning text must be 2–5 words, imperative or cautionary\n"
    )

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=300,
        require_json=True,
    )

    data = json.loads(raw)

    for key in ("location", "threat", "warning_text_a", "warning_text_b"):
        if key not in data or not data[key].strip():
            raise RuntimeError(f"Missing thumbnail concept field: {key}")

    return {
        "location": data["location"].strip(),
        "threat": data["threat"].strip(),
        "warning_a": data["warning_text_a"].strip(),
        "warning_b": data["warning_text_b"].strip(),
    }
    
def generate_chunk_background_prompt(
    chunk_id: int,
    chunk_text: str,
) -> str:
    system = (
        "You are generating a background image prompt for a chunk of a "
        "realistic, first-person confessional horror narration.\n\n"
        "This image will sit behind narration for several minutes.\n\n"
        "RULES:\n"
        "- No people or faces\n"
        "- No monsters or supernatural elements\n"
        "- No action or events\n"
        "- One real-world location only\n"
        "- One primary surface only (counter, street, hallway, desk, road)\n"
        "- At most 1–2 man-made objects total\n"
        "- No repeated objects\n"
        "- Large areas of empty space\n"
        "- Nighttime or very low light\n"
        "- Static, quiet, believable setting\n"
        "- Designed to support narration, not distract\n\n"
        "Output STRICT JSON ONLY:\n"
        "{ \"prompt\": \"...\" }"
    )

    user = (
        f"This is VISUAL CHUNK {chunk_id}.\n\n"
        "Analyze only the text below.\n\n"
        f"{chunk_text}\n\n"
        "Generate ONE background image prompt."
    )

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.35,
        max_tokens=300,
        require_json=True,
    )

    data = json.loads(raw)

    prompt = data.get("prompt", "").strip()
    if not prompt:
        raise RuntimeError(f"Empty prompt for chunk {chunk_id}")

    return prompt    

def generate_thumbnail_prompts_from_concepts(concepts: Dict[str, str]) -> Dict[str, str]:
    base = (
        "Dark, realistic nighttime photograph of {location}, "
        "heavily shadowed, minimal detail visible, "
        "one strong light source, extreme contrast, "
        "large areas of darkness and negative space, "
        "no visible people or faces, "
        "quiet but threatening atmosphere"
    )

    prompt_a = (
        base.format(location=concepts["location"])
        + f", implies danger related to {concepts['threat']}, "
        f"composition leaves space for bold text reading '{concepts['warning_a']}'"
    )

    prompt_b = (
        base.format(location=concepts["location"])
        + f", implies danger related to {concepts['threat']}, "
        f"composition leaves space for bold text reading '{concepts['warning_b']}'"
    )

    return {
        "thumbnail_a": prompt_a,
        "thumbnail_b": prompt_b,
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

    thumbnail_concepts = extract_thumbnail_concepts(script_text)
    thumbnail_prompts = generate_thumbnail_prompts_from_concepts(thumbnail_concepts)
    
    paragraph_index_path = run_dir / "script" / "paragraph_index.json"
    visual_chunks_path = run_dir / "script" / "visual_chunks.json"

    paragraph_index = json.loads(
        paragraph_index_path.read_text(encoding="utf-8")
    )["paragraphs"]

    visual_chunks = json.loads(
        visual_chunks_path.read_text(encoding="utf-8")
    )["chunks"]
    
    chunk_prompts = {}

    for chunk in visual_chunks:
        chunk_id = chunk["chunk_id"]
        texts = []

        for pid in chunk["paragraph_ids"]:
            if pid >= len(paragraph_index):
                raise RuntimeError(
                    f"Paragraph ID {pid} out of range for chunk {chunk_id}"
                )
            texts.append(paragraph_index[pid]["text"])

        chunk_text = "\n\n".join(texts)

        chunk_prompts[chunk_id] = generate_chunk_background_prompt(
            chunk_id=chunk_id,
            chunk_text=chunk_text,
        )


    img_dir = run_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)

    with open(WORKFLOW_PATH, "r") as f:
        base_workflow = json.load(f)

    jobs = []

    seed_base = 910000

    for chunk_id in sorted(chunk_prompts.keys()):
        prompt = chunk_prompts[chunk_id]
        name = f"chunk_{chunk_id:02d}"
        seed = seed_base + chunk_id * 100
        jobs.append((name, prompt, seed))

    jobs.extend([
        ("thumbnail_a", thumbnail_prompts["thumbnail_a"], 920101),
        ("thumbnail_b", thumbnail_prompts["thumbnail_b"], 920201),
    ])

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
