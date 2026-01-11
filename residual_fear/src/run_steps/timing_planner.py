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
    
    def _collapse_to_beats(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_id: Dict[int, Dict[str, Any]] = {}
        rank = {"light": 0, "normal": 1, "heavy": 2}
        for r in rows:
            beat_id = r.get("beat_id")
            if not isinstance(beat_id, int):
                raise RuntimeError(f"Invalid beat_id in image_plan: {beat_id}")

            scope = r.get("timing_scope") or {}
            line_index = scope.get("line_index")
            start_line = scope.get("start_line")
            end_line = scope.get("end_line")

            if isinstance(line_index, int):
                sl = el = line_index
            else:
                if not isinstance(start_line, int) or not isinstance(end_line, int):
                    raise RuntimeError(
                        f"beat_id {beat_id}: timing_scope must include start_line/end_line (or line_index)"
                    )
                sl, el = start_line, end_line

            aw = r.get("attention_weight", "normal")
            if aw not in rank:
                aw = "normal"

            if beat_id not in by_id:
                by_id[beat_id] = {
                    "beat_id": beat_id,
                    "timing_scope": {"start_line": sl, "end_line": el},
                    "attention_weight": aw,
                }
            else:
                ts = by_id[beat_id]["timing_scope"]
                ts["start_line"] = min(int(ts["start_line"]), int(sl))
                ts["end_line"] = max(int(ts["end_line"]), int(el))
                prev = by_id[beat_id].get("attention_weight", "normal")
                by_id[beat_id]["attention_weight"] = aw if rank[aw] > rank.get(prev, 1) else prev

        return [by_id[k] for k in sorted(by_id.keys())]

    beats = _collapse_to_beats(beats)

    beats_have_explicit_timing = all(
        isinstance(b.get("timing"), dict)
        and "start" in b["timing"]
        and "end" in b["timing"]
        for b in beats
    )

    timing = vo.get("timing", {})
    lines = timing.get("lines")
    if not isinstance(lines, list):
        raise RuntimeError("vo.json missing timing.lines")

    # FINAL full.wav duration (absolute truth for end alignment)
    full_duration = timing.get("full_duration_seconds")
    spoken_duration = timing.get("total_duration_seconds")
    if not isinstance(full_duration, (int, float)):
        raise RuntimeError(
            "vo.json missing timing.full_duration_seconds (required)"
        )
    timed_beats: List[Dict[str, Any]] = []
    if not beats_have_explicit_timing:
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

            if not isinstance(beat_id, int):
                raise RuntimeError("Beat missing valid beat_id")

            timing_scope = beat.get("timing_scope")
            if not timing_scope:
                raise RuntimeError(f"beat_id {beat_id}: missing timing_scope")

            # Backward + forward compatible handling
            if "line_index" in timing_scope:
                line_indices = [timing_scope["line_index"]]
            elif "start_line" in timing_scope and "end_line" in timing_scope:
                line_indices = list(
                    range(
                        int(timing_scope["start_line"]),
                        int(timing_scope["end_line"]) + 1
                    )
                )
            else:
                raise RuntimeError(
                    f"beat_id {beat_id}: timing_scope must contain line_index OR start_line/end_line"
                )

            weight = 1.0
            if beat.get("attention_weight") == "light":
                weight = 0.6
            elif beat.get("attention_weight") == "heavy":
                weight = 1.6

            for s_idx in line_indices:
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

        for s_idx in sorted(sentence_map.keys()):
            s = sentence_map[s_idx]
            s_start = s["start"]
            s_end = s["end"]
            s_duration = s_end - s_start

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

                key = b["beat_id"]

                r = beat_time_ranges.setdefault(
                    key,
                    {
                        "beat_id": b["beat_id"],
                        "start": b_start,
                        "end": b_end,
                    }
                )

                r["start"] = min(r["start"], b_start)
                r["end"] = max(r["end"], b_end)


                cursor = b_end

        for _, r in beat_time_ranges.items():
            start = r["start"]
            end = r["end"]

            entry = {
                "beat_id": r["beat_id"],
                "start_time_seconds": round(start, 6),
                "end_time_seconds": round(end, 6),
                "duration_seconds": round(end - start, 6),
            }

            timed_beats.append(entry)


        timed_beats.sort(key=lambda b: b["start_time_seconds"])
        # ---- Clamp non-final images so only the last image may extend ----
        if timed_beats:
            for i in range(len(timed_beats) - 1):
                timed_beats[i]["end_time_seconds"] = min(
                    timed_beats[i]["end_time_seconds"],
                    timed_beats[i + 1]["start_time_seconds"]
                )
                timed_beats[i]["duration_seconds"] = round(
                    timed_beats[i]["end_time_seconds"]
                    - timed_beats[i]["start_time_seconds"],
                    6
                )

        # -------- Sanity check: visuals must span spoken VO --------
        if timed_beats:
            last_end = float(timed_beats[-1]["end_time_seconds"])
            if last_end < (float(spoken_duration) * 0.98):
                raise RuntimeError(
                    "Timing plan does not span spoken VO duration. "
                    f"last_end={last_end:.3f}s, spoken_duration={float(spoken_duration):.3f}s. "
                    "This usually means storyboard/image_plan missed late script lines."
                )

            # ---- Extend final image to cover post-VO audio tail ----
            if full_duration and last_end < float(full_duration):
                timed_beats[-1]["end_time_seconds"] = round(float(full_duration), 6)
                timed_beats[-1]["duration_seconds"] = round(
                    timed_beats[-1]["end_time_seconds"]
                    - timed_beats[-1]["start_time_seconds"],
                    6
                )

    if beats_have_explicit_timing:
        # ---- Clamp non-final images so only the last image may extend ----
        if timed_beats:
            for i in range(len(timed_beats) - 1):
                timed_beats[i]["end_time_seconds"] = min(
                    timed_beats[i]["end_time_seconds"],
                    timed_beats[i + 1]["start_time_seconds"]
                )
                timed_beats[i]["duration_seconds"] = round(
                    timed_beats[i]["end_time_seconds"]
                    - timed_beats[i]["start_time_seconds"],
                    6
                )
        for b in beats:
            timing = b["timing"]

            start = float(timing["start"])
            end = float(timing["end"])

            entry = {
                "beat_id": b["beat_id"],
                "start_time_seconds": round(start, 6),
                "end_time_seconds": round(end, 6),
                "duration_seconds": round(end - start, 6),
            }

            timed_beats.append(entry)

        timed_beats.sort(key=lambda x: x["start_time_seconds"])
        # ---- Ensure only the FINAL microbeat can be extended ----
        if timed_beats:
            for i in range(len(timed_beats) - 1):
                # Clamp all non-final images to their calculated span
                timed_beats[i]["end_time_seconds"] = min(
                    timed_beats[i]["end_time_seconds"],
                    timed_beats[i + 1]["start_time_seconds"]
                )
                timed_beats[i]["duration_seconds"] = round(
                    timed_beats[i]["end_time_seconds"]
                    - timed_beats[i]["start_time_seconds"],
                    6
                )

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
        "scale_factor": 1.0,
        "beats": timed_beats,
    }

    out_path = run_dir / "timing_plan.json"
    write_json(out_path, output)

    if beats_have_explicit_timing:
        print(f"Wrote {out_path} (explicit timing)")
    else:
        print(f"Wrote {out_path} (vo-aligned timing)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
