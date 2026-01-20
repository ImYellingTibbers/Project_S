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

SCHEMA_NAME = "storyboard_1"

def build_prompt(script_text: str) -> str:
    return f"""
You are a lead Cinematographer for a viral horror YouTube channel. 
Your task is to identify the 6 most visually distinct "Anchor Moments" from this script.

An Anchor Moment is a scene that defines a major turning point or a high-scare moment in the story. 

GUIDELINES:
1. Spread the moments evenly across the entire script (Intro, Rising Tension, Climax, Aftermath).
2. Each moment should be visually unique from the others (e.g., don't pick two scenes of a person just standing in a room).
3. Focus on objects, entities, and atmospheric changes that represent the core of the horror.

RETURN FORMAT:
{{
  "scenes": [
    {{
      "scene_index": 0,
      "moment_title": "The Discovery",
      "description": "A detailed summary of the primary visual event."
    }}
  ]
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

    script_path = run_folder / "script.json"
    script_json = read_json(script_path)
    script_text = get_script_text(script_json)

    if not script_text:
        raise RuntimeError("script.json missing script text")

    # We now use the improved "Cinematographer" prompt
    resp = call_llm(build_prompt(script_text))
    payload = extract_json_from_llm(resp)

    out: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "scenes": payload.get("scenes", []),
    }

    write_json(run_folder / "storyboard_1.json", out)
    print(f"[SUCCESS] storyboard_1.json (Anchor Moments) saved | run={args.run_id}")

if __name__ == "__main__":
    main()