"""
src/run_steps/canon_creator.py

STAGE: CANON CREATOR (CONSISTENT VISUAL WORLD)
----------------------------------------------
Inputs:
  - runs/<run_id>/script.json
  - runs/<run_id>/storyboard_1.json

Output:
  - runs/<run_id>/visual_canon.json

Purpose:
  - Create JUST ENOUGH canon detail for consistent image generation:
    characters, entity, locations, props, and style.
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
from src.run_steps._common_utils import utc_now_iso, read_json, write_json, get_script_text, extract_json_from_llm, find_latest_run_folder

SCHEMA_NAME = "visual_canon"
SCHEMA_VERSION = "2.0"


def build_prompt(script_text: str, storyboard_1: Dict[str, Any]) -> str:
    must_see = storyboard_1.get("must_see_moments", [])
    recurring = storyboard_1.get("recurring_ids", {})

    return """
You are creating VISUAL_CANON: the consistent visual world for image generation.

Inputs:
- The full script
- A list of must-see macro moments and recurring canonical IDs

Rules (STRICT):
- Output JSON ONLY. No commentary.
- Use ONLY canonical IDs that appear in storyboard_1 (must_see_moments + recurring_ids).
- Keep canon descriptions short but specific (2-4 sentences each).
- Avoid mirrors / reflections as key visual requirements.
- Disambiguate entity vs prop:
  - entity_1 is the supernatural presence (shadow / silhouette / partial limb).
  - cursed objects are PROPS (e.g., prop_box_1), not entities.
- style_canon.global_style_prompt must be a single line describing the consistent art style.

Return JSON with EXACT shape (you may include MORE keys inside each *_canon dict as needed):
{
  "roles": ["adult_1", "entity_1"],
  "character_canon": {
    "adult_1": "Short consistent description.",
    "entity_1": "Short consistent description."
  },
  "location_canon": {
    "location_apartment_1": "Short consistent description."
  },
  "prop_canon": {
    "prop_box_1": "Short consistent description."
  },
  "style_canon": {
    "global_style_prompt": "One line style prompt for ALL images.",
    "format": "vertical 9:16"
  }
}

STORYBOARD_1:
{
  "must_see_moments": {must_see},
  "recurring_ids": {recurring}
}

SCRIPT:
{script_text}
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

    script_path = run_folder / "script.json"
    sb1_path = run_folder / "storyboard_1.json"

    script_json = read_json(script_path)
    script_text = get_script_text(script_json)
    if not script_text:
        raise RuntimeError("script.json missing script text")

    sb1 = read_json(sb1_path)

    resp = call_llm(build_prompt(script_text, sb1))
    payload = extract_json_from_llm(resp)

    out: Dict[str, Any] = {
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "roles": payload["roles"],
        "character_canon": payload["character_canon"],
        "location_canon": payload.get("location_canon", {}),
        "prop_canon": payload.get("prop_canon", {}),
        "style_canon": payload.get("style_canon", {}),
    }

    write_json(run_folder / "visual_canon.json", out)
    print(f"[SUCCESS] visual_canon.json saved | run={args.run_id}")


if __name__ == "__main__":
    main()
