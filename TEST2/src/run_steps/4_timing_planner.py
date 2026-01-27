import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# --- CONFIGURATION ---
ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"
SCHEMA_NAME = "timing_planner_v3_consistent"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def find_latest_run_folder():
    if not RUNS_DIR.exists():
        raise RuntimeError(f"Directory NOT FOUND: {RUNS_DIR}")

    valid_runs = []

    for f in RUNS_DIR.iterdir():
        if not f.is_dir():
            continue

        vo_path = f / "vo.json"
        script_path = f / "script_with_prompts.json"

        if not vo_path.exists() or not script_path.exists():
            continue

        try:
            vo_data = json.loads(vo_path.read_text(encoding="utf-8"))
            sentences = vo_data.get("alignment", {}).get("sentences", [])
            if sentences:
                valid_runs.append(f)
        except Exception:
            continue

    if not valid_runs:
        raise RuntimeError("No runs found containing valid vo.json + script_with_prompts.json")

    return max(valid_runs, key=os.path.getmtime)

def normalize(text: str) -> set[str]:
    return set(
        w.strip(".,!?—'\"").lower()
        for w in text.split()
        if len(w) > 2
    )

def find_best_chunk(sentence_text: str, chunks: list[dict]) -> dict:
    sent_words = normalize(sentence_text)
    best = None
    best_score = 0

    for chunk in chunks:
        chunk_words = normalize(chunk["chunk_text"])
        score = len(sent_words & chunk_words)
        if score > best_score:
            best_score = score
            best = chunk

    return best


def main():
    try:
        run_dir = find_latest_run_folder()
        print(f"📍 Planning timing for: {run_dir.name}")

        script_data = read_json(run_dir / "script_with_prompts.json")
        vo_data = read_json(run_dir / "vo.json")

        vo_sentences = vo_data.get("alignment", {}).get("sentences", [])
        full_duration = vo_data.get("total_duration", 0)
        script_segments = script_data.get("image_prompt_chunks", [])

        if not vo_sentences or not script_segments:
            raise RuntimeError("Missing essential data in vo.json or script.json")
        
        timed_beats = []
        
        MAX_BEAT_DURATION = 6.0  # seconds

        timed_beats = []
        beat_index = 0

        for vo_seg in vo_sentences:
            start_t = float(vo_seg["start"])
            end_t = float(vo_seg["end"])
            duration = end_t - start_t

            chunk = find_best_chunk(vo_seg["text"], script_segments)

            images = chunk.get("images", []) if chunk else []
            image_prompt = images[0]["prompt"] if images else ""

            # Split long beats
            if duration > MAX_BEAT_DURATION and images:
                slices = max(1, int(duration // MAX_BEAT_DURATION))
                slice_len = duration / slices

                for s in range(slices):
                    timed_beats.append({
                        "segment_index": beat_index,
                        "text": vo_seg["text"],
                        "start_time": round(start_t + s * slice_len, 3),
                        "end_time": round(start_t + (s + 1) * slice_len, 3),
                        "image_prompt": images[s % len(images)]["prompt"]
                    })
                    beat_index += 1
            else:
                timed_beats.append({
                    "segment_index": beat_index,
                    "text": vo_seg["text"],
                    "start_time": round(start_t, 3),
                    "end_time": round(end_t, 3),
                    "image_prompt": image_prompt
                })
                beat_index += 1

        for i in range(len(timed_beats) - 1):
            timed_beats[i]["end_time"] = timed_beats[i+1]["start_time"]
        timed_beats[0]["start_time"] = 0.0
        if timed_beats[-1]["end_time"] < full_duration:
            timed_beats[-1]["end_time"] = round(full_duration, 3)

        final_plan = {
            "schema": SCHEMA_NAME,
            "created_at": utc_now_iso(),
            "meta": {
                "title": script_data.get("title", "Untitled"),
                "total_duration": full_duration,
                "total_beats": len(timed_beats)
            },
            "beats": timed_beats
        }

        output_path = run_dir / "timing_plan.json"
        write_json(output_path, final_plan)
        
        print(f"✅ SUCCESS: Timing plan saved. {len(timed_beats)} beats mapped over {full_duration}s.")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()