import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# ---------------- CONFIG ----------------
ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"
SCHEMA_NAME = "timing_planner_v4_time_partitioned"

IMAGE_EXTS = {".png", ".jpg", ".jpeg"}

# ---------------- UTILS ----------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

# ---------------- DISCOVERY ----------------
def find_latest_run_folder() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError(f"Directory NOT FOUND: {RUNS_DIR}")

    candidates = []
    for f in RUNS_DIR.iterdir():
        if not f.is_dir():
            continue
        if (f / "vo.json").exists() and (f / "script_with_prompts.json").exists():
            candidates.append(f)

    if not candidates:
        raise RuntimeError("No valid runs found")

    return max(candidates, key=os.path.getmtime)

def get_sorted_image_files(run_dir: Path) -> list[str]:
    img_dir = run_dir / "img"
    if not img_dir.exists():
        raise RuntimeError(f"Missing img dir: {img_dir}")

    images = sorted(f.name for f in img_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS)
    if not images:
        raise RuntimeError("No images found in img directory")

    return images

# ---------------- MAIN ----------------
def main():
    try:
        run_dir = find_latest_run_folder()
        print(f"📍 Planning timing for: {run_dir.name}")

        script = read_json(run_dir / "script_with_prompts.json")
        vo = read_json(run_dir / "vo.json")

        chunks = script.get("image_prompt_chunks", [])
        sentences = vo.get("alignment", {}).get("sentences", [])
        total_duration = float(vo.get("total_duration", 0))

        if not chunks:
            raise RuntimeError("No image_prompt_chunks found")
        if not sentences:
            raise RuntimeError("No VO sentences found")
        if total_duration <= 0:
            raise RuntimeError("Invalid total VO duration")

        images = get_sorted_image_files(run_dir)

        # Validate image counts
        expected_images = sum(len(c.get("images", [])) for c in chunks)
        if expected_images != len(images):
            raise RuntimeError(
                f"Image count mismatch: chunks expect {expected_images}, "
                f"but found {len(images)} images"
            )

        num_chunks = len(chunks)
        chunk_window = total_duration / num_chunks

        timed_beats = []
        image_cursor = 0
        beat_index = 0

        for chunk_index, chunk in enumerate(chunks):
            expected = len(chunk["images"])
            chunk_start_time = chunk_index * chunk_window
            chunk_end_time = (chunk_index + 1) * chunk_window

            # Sentences whose midpoint falls in this chunk window
            chunk_sentences = []
            for s in sentences:
                mid = (float(s["start"]) + float(s["end"])) / 2
                if chunk_start_time <= mid < chunk_end_time:
                    chunk_sentences.append(s)

            # Fallback safety (never fail hard)
            if not chunk_sentences:
                chunk_sentences = [
                    s for s in sentences
                    if s["start"] >= chunk_start_time and s["start"] < chunk_end_time
                ]

            if not chunk_sentences:
                raise RuntimeError(f"No VO coverage for chunk {chunk_index}")

            start = min(float(s["start"]) for s in chunk_sentences)
            end = max(float(s["end"]) for s in chunk_sentences)
            duration = end - start

            per_image = duration / expected

            chunk_images = images[image_cursor:image_cursor + expected]
            image_cursor += expected

            for i, img in enumerate(chunk_images):
                timed_beats.append({
                    "segment_index": beat_index,
                    "chunk_index": chunk_index,
                    "start_time": round(start + i * per_image, 3),
                    "end_time": round(start + (i + 1) * per_image, 3),
                    "image_file": img
                })
                beat_index += 1

        output = {
            "schema": SCHEMA_NAME,
            "created_at": utc_now_iso(),
            "meta": {
                "total_duration": total_duration,
                "total_chunks": num_chunks,
                "total_beats": len(timed_beats)
            },
            "beats": timed_beats
        }

        out_path = run_dir / "timing_plan.json"
        write_json(out_path, output)

        print(f"✅ SUCCESS: {len(timed_beats)} beats written ({total_duration}s)")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
