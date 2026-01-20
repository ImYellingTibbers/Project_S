"""
src/run_steps/visual_canon.py

STAGE: VISUAL CANON (SIMPLE, DETERMINISTIC)
------------------------------------------
Inputs:
  - runs/<run_id>/script.json
  - runs/<run_id>/storyboard_1.json

Output:
  - runs/<run_id>/visual_canon.json

Purpose:
  - Identify characters, locations, and entity
  - Keep descriptions minimal and reusable
  - Style is handled OUTSIDE the LLM
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
from src.run_steps._common_utils import (
    utc_now_iso,
    read_json,
    write_json,
    get_script_text,
    extract_json_from_llm,
    find_latest_run_folder,
)

SCHEMA_NAME = "visual_canon"
SCHEMA_VERSION = "4.0"

# HARD CODED CHARACTER BASE (NOT LLM)
BASE_CHARACTER_DESCRIPTION = (
    "White adult male, age 30s–50s, short brown or dark hair, "
    "wearing a plain shirt and jeans, average build, slightly tired appearance."
)


def build_prompt(script_text: str, storyboard_1: Dict[str, Any]) -> str:
    return f"""
You are helping create a visual story for a viral YouTube Shorts horror channel.

Your job is to read the script and pull out the recurring visual elements that need to stay consistent for AI image generation.

Start by identifying any recurring human characters in the story. Assign them simple IDs like adult_1, adult_2 if there is more than one. Do not over-describe characters — just enough detail to keep them visually consistent across images.

Next, identify the main locations that appear more than once in the story. Describe each location as a place only, focusing on physical traits like size, layout, lighting, furniture, and general condition. Do not include actions, events, people, animals, or emotions in location descriptions.

Then, identify any recurring physical objects that matter visually across the story. Describe only what the object looks like on the outside. Do not describe contents, symbols, writing, or story-specific evidence.

Finally, identify the supernatural entity or presence that is stalking, haunting, or threatening the character. This description can be more detailed than the others, but it should still avoid very specific anatomy or a clearly defined face. Think eerie, partial, or obscured.

All descriptions should be visual, concrete, and usable for AI image generation. Keep them general enough to avoid breaking consistency, but specific enough to produce similar images each time. Each description should be one sentence.

Do not describe scenes, actions, pacing, or emotions. Do not invent elements that are not clearly implied by the script.

Return JSON only in the following format:

{{
  "characters": ["adult_1"],
  "entity": {{
    "entity_1": "One sentence visual description."
  }},
  "locations": {{
    "location_1": "One sentence physical description."
  }},
  "objects": {{
    "object_1": "One sentence physical description."
  }}
}}

SCRIPT:
{script_text}
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, default=None)
    args = parser.parse_args()

    RUNS_DIR = ROOT / "runs"
    run_folder = RUNS_DIR / args.run_id if args.run_id else find_latest_run_folder(RUNS_DIR)

    script_json = read_json(run_folder / "script.json")
    script_text = get_script_text(script_json)
    if not script_text:
        raise RuntimeError("script.json missing script text")

    resp = call_llm(build_prompt(script_text, {}))
    payload = extract_json_from_llm(resp)

    # BUILD CANON DETERMINISTICALLY
    character_canon = {
        char_id: BASE_CHARACTER_DESCRIPTION
        for char_id in payload.get("characters", [])
    }

    out: Dict[str, Any] = {
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "character_canon": character_canon,
        "entity_canon": payload.get("entity", {}),
        "location_canon": payload.get("locations", {}),
    }

    write_json(run_folder / "visual_canon.json", out)
    print(f"[SUCCESS] visual_canon.json saved | run={args.run_id}")


if __name__ == "__main__":
    main()
