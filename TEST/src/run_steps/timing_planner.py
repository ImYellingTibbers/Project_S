import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

# --- Constants & Utilities ---
SCHEMA_NAME = "timing_planner_v2"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

# ---------------------------------------------------------
# Timing Logic
# ---------------------------------------------------------

def main():
    # 1. Setup paths (Assumes standard project structure)
    # Using relative discovery to find the latest run folder
    runs_dir = Path(__file__).resolve().parents[2] / "runs"
    run_folders = sorted([d for d in runs_dir.iterdir() if d.is_dir()])
    if not run_folders:
        print("No run folders found.")
        return 1
    run_dir = run_folders[-1]

    # 2. Load Artifacts
    vo = read_json(run_dir / "vo.json")
    scenes_data = read_json(run_dir / "visual_scenes.json")
    
    timing = vo.get("timing", {})
    vo_sentences = timing.get("sentences", []) # New vo.json structure
    full_duration = timing.get("full_duration_seconds", 0)
    scenes = scenes_data.get("scenes", [])

    if not vo_sentences or not scenes:
        print("Required data missing from vo.json or visual_scenes.json")
        return 1

    # 3. Build a map of sentence index -> timestamps
    # This allows us to look up exactly when line 5 starts and ends
    sentence_map = {
        s["index"]: {"start": s["start"], "end": s["end"]}
        for s in vo_sentences
    }

    # 4. Group scenes by their script_anchor line_index
    # Some lines may have 1 image, others 2, some 0.
    from collections import defaultdict
    line_to_scenes = defaultdict(list)
    for s in scenes:
        l_idx = s["script_anchor"]["line_index"]
        line_to_scenes[l_idx].append(s)

    timed_output_beats = []

    # 5. Distribute time based on sentence duration
    # We iterate through the sentences found in the VO timing
    for s_idx in sorted(sentence_map.keys()):
        s_time = sentence_map[s_idx]
        assigned_scenes = line_to_scenes.get(s_idx, [])

        if not assigned_scenes:
            # If no scene was generated for this line, the previous scene 
            # should continue. We handle this by stretching the previous beat later.
            continue

        # Split the sentence duration equally among its assigned images
        count = len(assigned_scenes)
        duration_per_image = (s_time["end"] - s_time["start"]) / count
        
        for i, scene in enumerate(assigned_scenes):
            start_t = s_time["start"] + (i * duration_per_image)
            end_t = start_t + duration_per_image

            timed_output_beats.append({
                "scene_index": scene["scene_index"],
                "line_index": s_idx,
                "start_time_seconds": round(start_t, 4),
                "end_time_seconds": round(end_t, 4),
                "duration_seconds": round(duration_per_image, 4)
            })

    # 6. Final Polishing & Gap Filling
    if not timed_output_beats:
        print("No beats were timed.")
        return 1

    # Ensure there are no gaps between images
    for i in range(len(timed_output_beats) - 1):
        timed_output_beats[i]["end_time_seconds"] = timed_output_beats[i+1]["start_time_seconds"]
        timed_output_beats[i]["duration_seconds"] = round(
            timed_output_beats[i]["end_time_seconds"] - timed_output_beats[i]["start_time_seconds"], 4
        )

    # Force first image to start at 0.0
    timed_output_beats[0]["start_time_seconds"] = 0.0
    timed_output_beats[0]["duration_seconds"] = round(
        timed_output_beats[0]["end_time_seconds"], 4
    )

    # Force last image to end at full audio duration
    if full_duration > timed_output_beats[-1]["end_time_seconds"]:
        timed_output_beats[-1]["end_time_seconds"] = full_duration
        timed_output_beats[-1]["duration_seconds"] = round(
            full_duration - timed_output_beats[-1]["start_time_seconds"], 4
        )

    # 7. Write output
    final_plan = {
        "schema": SCHEMA_NAME,
        "created_at": utc_now_iso(),
        "total_images": len(timed_output_beats),
        "full_duration_seconds": full_duration,
        "beats": timed_output_beats
    }

    write_json(run_dir / "timing_plan.json", final_plan)
    print(f"[SUCCESS] Timing plan created with {len(timed_output_beats)} beats in {run_dir.name}")

if __name__ == "__main__":
    sys.exit(main())