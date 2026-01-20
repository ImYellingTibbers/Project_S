from __future__ import annotations

import argparse
from pathlib import Path
from sys import path as sys_path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys_path:
    sys_path.insert(0, str(ROOT))

from src.llm.qwen_instruct_llm import call_llm
from src.run_steps._common_utils import (
    utc_now_iso,
    read_json,
    write_json,
    extract_json_from_llm,
    find_latest_run_folder,
)

SCHEMA_NAME = "storyboard_2"


def build_prompt(script_text: str, storyboard_1: Dict[str, Any]) -> str:
    return f"""
You are a master storyboard creator for a YouTube Shorts channel that specializes in confessional horror shorts.

Your job is to create storyboard step 2.

You are given a script and a storyboard_1. Storyboard_1 already defines the major visual moments that must exist in the video. For this step, your task is to turn each storyboard_1 scene into a chapter that represents a section of the visual narrative.

Each chapter exists only to determine pacing. Chapters do not add new story events and do not invent new visuals. They simply decide how many short scenes should exist within that chapter.

Assume that one visual scene lasts between 2 and 5 seconds. Use the length and pacing of the script to determine how many total scenes are needed for the entire video, then distribute those scenes across the chapters. Every chapter must contain at least two scenes, and some chapters may contain more depending on how much visual material can reasonably be derived from the corresponding storyboard_1 scene.

Use the storyboard_1 scenes as guidance for how dense or sparse each chapter should be, but do not describe visuals, camera angles, styles, or consistency. This step is purely structural.

Your output should only list the chapters, their index, which storyboard_1 scene they came from, a short functional description of the chapter’s purpose, and how many scenes belong to that chapter.

RETURN FORMAT:
{{
  "chapters": [
    {{
      "chapter_index": 0,
      "source_scene_index": 0,
      "chapter_purpose": "Short functional purpose",
      "scene_count": 3
    }}
  ]
}}

SCRIPT:
{script_text}

STORYBOARD_1:
{storyboard_1}
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, default=None)
    args = parser.parse_args()

    RUNS_DIR = ROOT / "runs"
    run_folder = RUNS_DIR / args.run_id if args.run_id else find_latest_run_folder(RUNS_DIR)

    script_json = read_json(run_folder / "script.json")
    storyboard_1 = read_json(run_folder / "storyboard_1.json")

    script_text = script_json.get("script", "")
    if not script_text:
        raise RuntimeError("script.json missing script text")

    resp = call_llm(build_prompt(script_text, storyboard_1))
    payload = extract_json_from_llm(resp)

    out: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "chapters": payload.get("chapters", []),
    }

    write_json(run_folder / "storyboard_2.json", out)
    print(f"[SUCCESS] storyboard_2.json saved | run={args.run_id}")


if __name__ == "__main__":
    main()
