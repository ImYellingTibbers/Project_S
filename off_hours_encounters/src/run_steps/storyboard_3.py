"""
src/run_steps/storyboard_3.py

STAGE: STORYBOARD_3 (THINKING + EXPLANATION PER CHAPTER)
--------------------------------------------------------
Inputs:
  - runs/<run_id>/storyboard_1.json
  - runs/<run_id>/storyboard_2.json
  - runs/<run_id>/visual_canon.json

Output:
  - runs/<run_id>/storyboard_3.json

Purpose:
  - For each chapter, identify:
    - the BIG scene (must-see shot)
    - adjacent scene ideas around it (setup/reaction/clues)
  - This is a planning artifact, not final scenes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from sys import path as sys_path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys_path:
    sys_path.insert(0, str(ROOT))

from src.llm.qwen_instruct_llm import call_llm
from src.run_steps._common_utils import utc_now_iso, read_json, write_json, extract_json_from_llm, find_latest_run_folder

SCHEMA_NAME = "storyboard_3"
SCHEMA_VERSION = "2.0"


def build_prompt(sb1: Dict[str, Any], sb2: Dict[str, Any], canon: Dict[str, Any]) -> str:
    must_see = sb1.get("must_see_moments", [])
    chapters = sb2.get("chapters", [])
    recurring = sb1.get("recurring_ids", {})
    return """
You are creating STORYBOARD_3: a "thinking" plan per chapter for a vertical horror short.

Goal:
- For EACH chapter from storyboard_2, define the BIG SCENE (the key still frame).
- Then define adjacent scene ideas that support it (setup/clue/reaction/aftermath).

Rules (STRICT):
- Output JSON ONLY. No commentary.
- Create exactly ONE plan object per chapter in storyboard_2.
- Preserve chapter_index, arc_label, and scene_count from storyboard_2.
- Every description MUST reference canonical IDs (adult_1, entity_1, location_..., prop_...).
- Adjacent scene idea count MUST equal (scene_count - 1).
- Do NOT output a final scene list (that is storyboard_4). This is planning only.

Return JSON with EXACT shape:
{
  "chapters": [
    {
      "chapter_index": 0,
      "arc_label": "HOOK",
      "scene_count": 3,
      "big_scene_description": "1-2 sentences describing the key still frame.",
      "adjacent_scene_ideas": [
        {
          "scene_role": "setup | clue | reaction | aftermath",
          "idea": "1 sentence describing a supporting still frame."
        }
      ]
    }
  ]
}

must_see_moments:
{must_see}

recurring_ids:
{recurring}

chapters (scene budgets):
{chapters}

visual_canon keys available:
characters: {list((canon.get("character_canon") or {}).keys())}
locations: {list((canon.get("location_canon") or {}).keys())}
props: {list((canon.get("prop_canon") or {}).keys())}
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
    canon = read_json(run_folder / "visual_canon.json")

    resp = call_llm(build_prompt(sb1, sb2, canon))
    payload = extract_json_from_llm(resp)

    out: Dict[str, Any] = {
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "chapters": payload["chapters"],
    }

    write_json(run_folder / "storyboard_3.json", out)
    print(f"[SUCCESS] storyboard_3.json saved | run={args.run_id}")


if __name__ == "__main__":
    main()
