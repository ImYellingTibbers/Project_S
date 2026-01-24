import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# --- CONFIGURATION ---
ROOT = Path("/home/jcpix/projects/Project_S/TEST")
RUNS_DIR = ROOT / "runs"
SCHEMA_NAME = "timing_planner_v3_consistent"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def find_latest_run_folder() -> Path:
    runs = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir() and p.name.startswith("run_")])
    if not runs:
        raise RuntimeError(f"No run folders found in {RUNS_DIR}")
    return runs[-1]

def main():
    try:
        run_dir = find_latest_run_folder()
        print(f"📍 Planning timing for: {run_dir.name}")

        script_data = read_json(run_dir / "script.json")
        vo_data = read_json(run_dir / "vo.json")

        vo_sentences = vo_data.get("alignment", {}).get("sentences", [])
        full_duration = vo_data.get("total_duration", 0)
        script_segments = script_data.get("segments", [])

        if not vo_sentences or not script_segments:
            raise RuntimeError("Missing essential data in vo.json or script.json")
        
        timed_beats = []
        
        for i, vo_seg in enumerate(vo_sentences):
            if i >= len(script_segments):
                break
            start_t = vo_seg["start"]
            end_t = vo_seg["end"]

            timed_beats.append({
                "segment_index": i,
                "text": vo_seg["text"],
                "start_time": round(float(start_t), 3),
                "end_time": round(float(end_t), 3),
                "image_prompt": script_segments[i].get("image_prompt", "")
            })
            
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