import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import RUNS_DIR, SCHEMA_VERSION


SCHEMA_NAME = "timing_planner"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_run_folder() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError("runs/ folder not found")
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    if not runs:
        raise RuntimeError("No run folders found")
    return runs[-1]


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> int:
    run_dir = find_latest_run_folder()

    image_plan = read_json(run_dir / "image_plan.json")
    vo = read_json(run_dir / "vo.json")

    beats = image_plan.get("beats")
    if not isinstance(beats, list):
        raise RuntimeError("image_plan.json missing 'beats' list")

    timing = vo.get("timing", {})
    lines = timing.get("lines")
    if not isinstance(lines, list):
        raise RuntimeError("vo.json missing timing.lines")

    # FINAL full.wav duration (absolute truth for end alignment)
    full_duration = timing.get("full_duration_seconds")
    if not isinstance(full_duration, (int, float)):
        raise RuntimeError(
            "vo.json missing timing.full_duration_seconds (required)"
        )

    # ------------------------------------------------------------
    # Build sentence timing map
    # ------------------------------------------------------------
    sentence_map: Dict[int, Dict[str, Any]] = {}
    for row in lines:
        idx = row.get("line_index")
        if isinstance(idx, int):
            sentence_map[idx] = {
                "start": float(row["start_time_seconds"]),
                "end": float(row["end_time_seconds"]),
                "beats": []  # will hold weighted beat refs
            }

    if not sentence_map:
        raise RuntimeError("No usable sentence timing found in vo.json")

    # ------------------------------------------------------------
    # Assign beats to sentences with fractional weights
    # ------------------------------------------------------------
    for beat in beats:
        beat_id = beat.get("beat_id")
        script_lines = beat.get("script_lines")

        if not isinstance(beat_id, int):
            raise RuntimeError("Beat missing valid beat_id")

        if (
            not isinstance(script_lines, list)
            or not script_lines
            or len(script_lines) > 2
            or not all(isinstance(x, int) for x in script_lines)
        ):
            raise RuntimeError(
                f"beat_id {beat_id}: script_lines must be [sentence] or [sentence1, sentence2]"
            )

        weight = 1.0 / len(script_lines)

        for s_idx in script_lines:
            if s_idx not in sentence_map:
                raise RuntimeError(
                    f"beat_id {beat_id}: sentence {s_idx} not found in VO timing"
                )

            sentence_map[s_idx]["beats"].append({
                "beat_id": beat_id,
                "weight": weight
            })

    # ------------------------------------------------------------
    # Allocate time per sentence using weighted beats
    # ------------------------------------------------------------
    beat_time_ranges: Dict[int, Dict[str, float]] = {}
    sentence_total_duration = 0.0

    for s_idx in sorted(sentence_map.keys()):
        s = sentence_map[s_idx]
        s_start = s["start"]
        s_end = s["end"]
        s_duration = s_end - s_start
        sentence_total_duration += s_duration

        if not s["beats"]:
            continue

        total_weight = sum(b["weight"] for b in s["beats"])
        if total_weight <= 0:
            continue

        unit = s_duration / total_weight
        cursor = s_start

        for b in s["beats"]:
            b_start = cursor
            b_end = cursor + (unit * b["weight"])

            r = beat_time_ranges.setdefault(
                b["beat_id"],
                {"start": b_start, "end": b_end}
            )

            r["start"] = min(r["start"], b_start)
            r["end"] = max(r["end"], b_end)

            cursor = b_end

    if sentence_total_duration <= 0:
        raise RuntimeError("Computed sentence duration is invalid")

    # ------------------------------------------------------------
    # Global normalization to match final VO duration
    # ------------------------------------------------------------
    scale = full_duration / sentence_total_duration

    timed_beats: List[Dict[str, Any]] = []
    for beat_id, r in beat_time_ranges.items():
        start = r["start"] * scale
        end = r["end"] * scale

        timed_beats.append({
            "beat_id": beat_id,
            "start_time_seconds": round(start, 6),
            "end_time_seconds": round(end, 6),
            "duration_seconds": round(end - start, 6),
            "image_file": f"images/beat_{beat_id:03d}.png",
        })

    timed_beats.sort(key=lambda b: b["start_time_seconds"])

    artifacts = vo.get("artifacts", {})
    audio_source = artifacts.get("full_wav") or artifacts.get(
        "combined_wav", "vo/full.wav"
    )

    output = {
        "schema": {
            "name": SCHEMA_NAME,
            "version": SCHEMA_VERSION,
        },
        "run_id": image_plan.get("run_id") or vo.get("run_id"),
        "created_at": utc_now_iso(),
        "audio_source": audio_source,
        "scale_factor": round(scale, 8),
        "beats": timed_beats,
    }

    out_path = run_dir / "timing_plan.json"
    write_json(out_path, output)
    print(f"Wrote {out_path} (scale={scale:.6f})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
