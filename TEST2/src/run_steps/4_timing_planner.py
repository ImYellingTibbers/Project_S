import json
import sys
import os
import re
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

        chunks = script.get("chunks", [])
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
        expected_images = sum(len(c.get("image_prompts", [])) for c in chunks)
        if expected_images != len(images):
            raise RuntimeError(
                f"Image count mismatch: chunks expect {expected_images}, "
                f"but found {len(images)} images"
            )

        # ---------------- PROMPT-LOCKED SENTENCE TIMING ----------------
        timed_beats = []
        beat_index = 0
        image_cursor = 0
        vo_idx = 0

        for chunk in chunks:
            prompts = chunk.get("image_prompts", [])
            if not prompts:
                continue

            # Consume VO sentences until we cover this chunk's script text
            collected = []
            script_words = len(chunk["script_text"].split())

            words_accum = 0
            start_time = None
            end_time = None

            while vo_idx < len(sentences) and words_accum < script_words:
                sent = sentences[vo_idx]
                sent_words = len(sent["text"].split())

                if start_time is None:
                    start_time = float(sent["start"])

                end_time = float(sent["end"])
                words_accum += sent_words
                collected.append(sent)
                vo_idx += 1

            if start_time is None or end_time is None:
                raise RuntimeError(
                    f"Failed to assign VO time span for chunk {chunk['chunk_index']}"
                )

            span_dur = end_time - start_time
            if span_dur <= 0:
                raise RuntimeError(
                    f"Invalid VO span for chunk {chunk['chunk_index']}"
                )

            per_image = span_dur / len(prompts)
            cursor = start_time

            for _ in prompts:
                start = cursor
                end = min(start + per_image, end_time)

                timed_beats.append({
                    "segment_index": beat_index,
                    "chunk_index": chunk["chunk_index"],
                    "start_time": round(start, 3),
                    "end_time": round(end, 3),
                    "image_file": images[image_cursor],
                    "sentence_text": " ".join(s["text"] for s in collected)
                })

                cursor = end
                image_cursor += 1
                beat_index += 1


        # Hard validation
        if timed_beats:
            final_end = timed_beats[-1]["end_time"]
            if abs(final_end - total_duration) > 0.01:
                print(
                    f"⚠️ Drift detected: images end at {final_end:.2f}s "
                    f"but VO is {total_duration:.2f}s"
                )

        output = {
            "schema": SCHEMA_NAME,
            "created_at": utc_now_iso(),
            "meta": {
                "total_duration": total_duration,
                "total_chunks": len(chunks),
                "total_beats": len(timed_beats),
                "timing_mode": "sentence_aligned",
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
