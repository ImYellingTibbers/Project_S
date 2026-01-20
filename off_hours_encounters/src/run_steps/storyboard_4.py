"""
src/run_steps/storyboard_4.py

STAGE: STORYBOARD_4 (FINAL SCENES PER CHAPTER)
----------------------------------------------
Inputs:
  - runs/<run_id>/storyboard_1.json
  - runs/<run_id>/storyboard_2.json
  - runs/<run_id>/storyboard_3.json
  - runs/<run_id>/visual_canon.json

Output:
  - runs/<run_id>/storyboard_4.json

Purpose:
  - Create the final per-scene list for each chapter.
  - One LLM call per chapter.
  - Every scene must reference canonical IDs (characters/locations/props).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from sys import path as sys_path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys_path:
    sys_path.insert(0, str(ROOT))

from src.llm.qwen_instruct_llm import call_llm
from src.run_steps._common_utils import utc_now_iso, read_json, write_json, extract_json_from_llm, find_latest_run_folder

SCHEMA_NAME = "storyboard_4"
SCHEMA_VERSION = "2.0"


def build_prompt_for_chapter(
    chapter: Dict[str, Any],
    chapter_plan: Dict[str, Any],
    sb1: Dict[str, Any],
    canon: Dict[str, Any],
) -> str:
    must_see = sb1.get("must_see_moments", [])
    recurring = sb1.get("recurring_ids", {})

    chapter_index = int(chapter.get("chapter_index", 0))
    scene_count = int(chapter.get("scene_count", 1))
    arc_label = str(chapter.get("arc_label", "")).strip()

    char_ids = list((canon.get("character_canon") or {}).keys())
    loc_ids = list((canon.get("location_canon") or {}).keys())
    prop_ids = list((canon.get("prop_canon") or {}).keys())

    return """
You are creating STORYBOARD_4: FINAL SCENES for ONE chapter of a vertical horror short.

Rules (STRICT):
- Output JSON ONLY. No commentary.
- Create EXACTLY {scene_count} scenes.
- One still frame per scene_description (not a montage).
- DO NOT invent new canonical IDs. Use ONLY the provided canon IDs.
- Every scene_description MUST reference canonical IDs (adult_1, entity_1, location_..., prop_...).
- Avoid mirrors / reflections. Do not make reflections a key story beat.
- Respect must-see moments:
  - Ensure the chapter's major_event_summary is clearly represented by at least ONE scene.

Entity visibility rules:
- If the chapter's linked must-see moment says entity_visibility_rule = "none": do NOT include entity_1 in any scene.
- If "glimpse": entity_1 may appear only as a partial limb / silhouette / shadow.
- If "full": entity_1 can be shown fully, but keep it monetization-safe (no gore).

Return JSON with EXACT shape:
{
  "scenes": [
    {
      "scene_in_chapter": 0,
      "scene_role": "setup | clue | big_scene | reaction | aftermath",
      "characters_present": ["adult_1"],
      "location_ids": ["location_apartment_1"],
      "prop_ids": ["prop_window_1"],
      "scene_description": "1-2 sentences describing the still frame. Include canonical IDs."
    }
  ]
}

Chapter:
{
  "chapter_index": {chapter_index},
  "arc_label": "{arc_label}",
  "scene_count": {scene_count},
  "major_event_summary": "{str(chapter.get('major_event_summary','')).strip()}",
  "moment_indices": {chapter.get("moment_indices", [])}
}

Chapter plan (from storyboard_3):
{chapter_plan}

Storyboard_1 must_see_moments:
{must_see}

Recurring IDs:
{recurring}

Available canon IDs:
characters: {char_ids}
locations: {loc_ids}
props: {prop_ids}
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, default=None)
    args = parser.parse_args()

    RUNS_DIR = ROOT / "runs"

    if args.run_id:
        run_folder = RUNS_DIR / args.run_id
    else:
        run_folder = find_latest_run_folder(RUNS_DIR)

    sb1 = read_json(run_folder / "storyboard_1.json")
    sb2 = read_json(run_folder / "storyboard_2.json")
    sb3 = read_json(run_folder / "storyboard_3.json")
    canon = read_json(run_folder / "visual_canon.json")

    chapters: List[Dict[str, Any]] = sb2.get("chapters", [])
    plans: List[Dict[str, Any]] = sb3.get("chapters", [])

    out_chapters: List[Dict[str, Any]] = []
    global_scene_index = 0

    for ch in chapters:
        cidx = int(ch.get("chapter_index", 0))
        plan = next((p for p in plans if int(p.get("chapter_index", -1)) == cidx), {})

        resp = call_llm(build_prompt_for_chapter(ch, plan, sb1, canon))
        payload = extract_json_from_llm(resp)

        scenes = payload["scenes"]
        for s in scenes:
            s["chapter_index"] = cidx
            s["global_scene_index"] = global_scene_index
            global_scene_index += 1

        out_chapters.append(
            {
                "chapter_index": cidx,
                "arc_label": ch.get("arc_label", ""),
                "scene_count": ch.get("scene_count", 0),
                "scenes": scenes,
            }
        )

    out: Dict[str, Any] = {
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "total_scenes": global_scene_index,
        "chapters": out_chapters,
    }

    write_json(run_folder / "storyboard_4.json", out)
    print(f"[SUCCESS] storyboard_4.json saved | total_scenes={global_scene_index} | run={args.run_id}")


if __name__ == "__main__":
    main()
