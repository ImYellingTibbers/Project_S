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

NEGATIVE_PROMPT = (
    "photorealistic, photo, DSLR, studio lighting, fashion photography, glamour lighting, "
    "hyperreal skin, skin pores, symmetrical face, beauty lighting, "
    "romantic, sensual, explicit gore, exposed organs, graphic anatomy, sexualized pose, intimate framing, "
    "shirtless male, bare torso, erotic, porn, nsfw, fetish, genitalia, nudity, breasts, nipples, "
    "bright cheerful lighting, neon colors, oversaturated, "
    "cgi, unreal engine, octane, glossy 3d, plastic skin, "
    "text, watermark, logo, caption, multiple frames, split screen, "
    "woman, women, female, girl, girls, child, children, teen, teenager, pregnant, "
)

STYLE_PREFIX = (
    "stylized horror illustration, painterly and cinematic, non-photoreal, "
    "silhouette-first composition, exaggerated contrast, deep crushing shadows, "
    "fog, darkness, and occlusion obscuring anatomy, "
    "imperfect proportions, suggestion over detail, "
    "faces partially obscured, facial features indistinct, identity not emphasized, "
    "graphic novel horror tone, unsettling negative space"
)

# ----------------------------
# Helpers
# ----------------------------
def latest_run_dir() -> Path:
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
    return r.json()[pid]

def extract_image(history: dict) -> dict:
    for node_output in history.get("outputs", {}).values():
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
                node["inputs"]["text"] = positive
        if node.get("class_type") in ["KSampler", "KSamplerAdvanced"]:
            key = "seed" if node["class_type"] == "KSampler" else "noise_seed"
            node["inputs"][key] = seed
        if node.get("class_type") == "SaveImage":
            node["inputs"]["filename_prefix"] = filename
    return wf

# ----------------------------
# Main
# ----------------------------
def main():
    cfg = ComfyConfig()
    run = latest_run_dir()

    scenes_path = run / "visual_scenes.json"
    canon_path = run / "canon.json"

    if not scenes_path.exists():
        raise FileNotFoundError("visual_scenes.json not found in latest run")

    scenes_data = load_json(scenes_path)
    scenes = scenes_data.get("scenes", [])
    
    canon_map = {}
    if canon_path.exists():
        canon_data = load_json(canon_path)
        canon_map = {c["id"]: c["description"] for c in canon_data.get("canon", [])}

    c1_desc = canon_map.get("c1", "adult white male, mid 30s, short dark hair, short beard, dark casual clothing")
    c2_desc = canon_map.get("c2", "non-human presence, partial intrusion only, no full body, no face")

    seed_base = random.randint(100_000, 1_000_000)

    images_dir = run / "images"
    images_dir.mkdir(exist_ok=True)

    workflow_path = ROOT / "src/image_generation/horror_shorts_txt2img_beat_workflow.json"
    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow not found at {workflow_path}")

    base_workflow = load_json(workflow_path)

    print(f"[*] Generating {len(scenes)} images for run: {run.name}")

    for idx, scene in enumerate(scenes):
        visible_ids = scene.get("visible_canon_ids", [])
        
        # 1. Start with the style
        prompt_parts = [STYLE_PREFIX]

        # 2. Add Protagonist (c1) description ONLY if requested
        if "c1" in visible_ids:
            # We add the character description from our canon map
            prompt_parts.append(f"Subject: {canon_map.get('c1', 'adult male protagonist')}. The character is visible in the frame.")
        else:
            prompt_parts.append("No people visible, empty scene, architectural or object focus.")

        # 3. Add Entity (c2) description ONLY if requested
        if "c2" in visible_ids:
            prompt_parts.append(f"Presence: {canon_map.get('c2', 'shrouded entity')}")

        # 4. Add the specific visual description from the LLM
        prompt_parts.append(f"Visual: {scene['visual_description']}")

        # Join everything into the final string
        prompt_text = ", ".join(prompt_parts)

        out_name = f"scene_{idx:03d}"
        print(f"[+] Rendering {out_name} | IDs: {visible_ids}")

        wf = patch_prompt(
            base_workflow,
            positive=prompt_text,
            negative=NEGATIVE_PROMPT,
            seed=seed_base + (idx * 31),
            filename=f"project_s/{run.name}/{out_name}",
        )

        try:
            pid = queue_prompt(cfg, wf)
            wait_for_completion(cfg, pid)

            history = get_history(cfg, pid)
            img_info = extract_image(history)
            img_data = download_image(cfg, img_info)

            out_path = images_dir / f"{out_name}.png"
            out_path.write_bytes(img_data)

            print(f"    [OK] {out_path.name}")
        except Exception as e:
            print(f"    [ERROR] Scene {idx}: {e}")

    print(f"\n[SUCCESS] Image generation complete.")

if __name__ == "__main__":
    main()
