import json
import time
import requests
import subprocess
from sys import path
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import COMFY_URL, RUNS_DIR

# =====================
# CONFIG
# =====================

WORKFLOW_PATH = Path("src/image_generation/horror_shorts_i2v_workflow_v2.json")

# Class types used in your workflow JSON
CLASS_LATENT = "Wan22ImageToVideoLatent"
CLASS_LOAD_IMAGE = "LoadImage"
CLASS_POS_CLIP = "CLIPTextEncode"
CLASS_KSAMPLER = "KSampler"
CLASS_SAVE_VIDEO = "SaveVideo"

# =====================
# HELPERS
# =====================

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def queue_prompt(workflow: dict) -> str:
    r = requests.post(
        f"{COMFY_URL}/prompt",
        json={
            "prompt": workflow,
            # extra_pnginfo isn't required for execution; safe to omit workflow metadata here.
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["prompt_id"]

def wait_for_completion(prompt_id: str, poll_s: float = 0.5) -> dict:
    # Minimal polling approach (consistent with your existing style)
    while True:
        r = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=60)
        if r.status_code == 200:
            data = r.json()
            if prompt_id in data:
                return data[prompt_id]
        time.sleep(poll_s)

def fetch_file(file_meta: dict) -> bytes:
    r = requests.get(
        f"{COMFY_URL}/view",
        params={
            "filename": file_meta["filename"],
            "subfolder": file_meta.get("subfolder", ""),
            "type": file_meta.get("type", "output"),
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.content

def extract_last_frame_ffmpeg(video_path: Path, out_path: Path) -> None:
    """
    Grab a frame near the end reliably. Using -sseof avoids "last frame" expression issues.
    """
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-sseof", "-0.05",       # seek to ~last 50ms
            "-i", str(video_path),
            "-vframes", "1",
            str(out_path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

def find_first_node_id_by_class(workflow: dict, class_name: str) -> str:
    for node_id, node in workflow.items():
        if node.get("class_type") == class_name:
            return node_id
    raise RuntimeError(f"Node with class_type '{class_name}' not found")

def find_positive_clip_node_id(workflow: dict) -> str:
    """
    Your workflow has two CLIPTextEncode nodes:
      - title contains 'Positive Prompt' for node 6
      - title contains 'Negative Prompt' for node 7
    We select by _meta.title to avoid guessing IDs. :contentReference[oaicite:5]{index=5}
    """
    for node_id, node in workflow.items():
        if node.get("class_type") == CLASS_POS_CLIP:
            title = (node.get("_meta", {}) or {}).get("title", "")
            if "Positive" in title:
                return node_id
    # Fallback: first CLIPTextEncode if titles were stripped
    return find_first_node_id_by_class(workflow, CLASS_POS_CLIP)

def extract_mp4_from_history_block(history_block: dict) -> dict:
    """
    SaveVideo outputs are usually under `videos`, not `images`.
    We search several common keys to be robust.
    """
    outputs = history_block.get("outputs", {})
    for out in outputs.values():
        if not isinstance(out, dict):
            continue

        for key in ("videos", "gifs", "images", "files"):
            items = out.get(key)
            if isinstance(items, list):
                for f in items:
                    fn = f.get("filename", "")
                    if isinstance(fn, str) and fn.lower().endswith(".mp4"):
                        return f
    raise RuntimeError(f"No mp4 output found. Output blocks keys: {[list(v.keys()) for v in outputs.values() if isinstance(v, dict)]}")

def latest_run_dir() -> Path:
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    if not runs:
        raise RuntimeError("No run folders found in runs/")
    return runs[-1]


def upload_input_image(path: Path, subfolder: str) -> str:
    with path.open("rb") as f:
        r = requests.post(
            f"{COMFY_URL}/upload/image",
            files={"image": (path.name, f, "image/png")},
            data={"subfolder": subfolder, "type": "input", "overwrite": "true"},
            timeout=120,
        )
    r.raise_for_status()
    return f"{subfolder}/{path.name}".replace("\\", "/")


# =====================
# MAIN
# =====================

def run_i2v(run_dir: Path) -> None:
    images_dir = run_dir / "images"
    out_dir = run_dir / "i2v"
    out_dir.mkdir(exist_ok=True)

    image_plan = load_json(run_dir / "image_plan.json")

    for beat in image_plan["beats"]:
        workflow = load_json(WORKFLOW_PATH)

        beat_id = int(beat["beat_id"])
        prompt = (beat.get("i2v_prompt_body") or "").strip()
        if not prompt:
            raise RuntimeError(f"beat_id {beat_id}: missing i2v_prompt_body")

        image_path = images_dir / f"beat_{beat_id:03d}.png"
        if not image_path.exists():
            raise RuntimeError(f"Missing image: {image_path}")

        print(f"[i2v] Beat {beat_id}: {prompt}")

        # --- Patch start image used by Wan22ImageToVideoLatent
        latent_id = find_first_node_id_by_class(workflow, CLASS_LATENT)
        start_image_ref = workflow[latent_id]["inputs"]["start_image"]  # e.g. ["56", 0] :contentReference[oaicite:7]{index=7}
        load_image_id = start_image_ref[0]
        unique_subfolder = f"project_s/{image_plan['run_id']}/i2v"
        uploaded_path = upload_input_image(image_path, unique_subfolder)
        workflow[load_image_id]["inputs"]["image"] = uploaded_path

        # --- Patch positive prompt text
        pos_id = find_positive_clip_node_id(workflow)
        workflow[pos_id]["inputs"]["text"] = prompt

        # --- Patch SaveVideo filename prefix
        save_id = find_first_node_id_by_class(workflow, CLASS_SAVE_VIDEO)
        workflow[save_id]["inputs"]["filename_prefix"] = f"video/beat_{beat_id:03d}"

        # --- Patch seed
        ksampler_id = find_first_node_id_by_class(workflow, CLASS_KSAMPLER)
        workflow[ksampler_id]["inputs"]["seed"] = int(time.time() * 1000) % (2**32)

        # --- Run
        prompt_id = queue_prompt(workflow)
        history_block = wait_for_completion(prompt_id)

        # --- Find mp4 output (SaveVideo -> videos)
        video_meta = extract_mp4_from_history_block(history_block)
        video_bytes = fetch_file(video_meta)

        video_out = out_dir / f"beat_{beat_id:03d}.mp4"
        video_out.write_bytes(video_bytes)

        last_frame_out = out_dir / f"beat_{beat_id:03d}_last.png"
        extract_last_frame_ffmpeg(video_out, last_frame_out)

        print(f"[i2v] Saved {video_out.name}")

    print("[i2v] COMPLETE")

if __name__ == "__main__":
    run_i2v(latest_run_dir())
