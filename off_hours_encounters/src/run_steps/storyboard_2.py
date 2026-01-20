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
    # CALCULATION: For a ~100s script, we want a cut every 3-4 seconds.
    # 100 / 3.5 = ~28 scenes. 
    target_total_scenes = 28 
    
    return f"""
You are a master structural pacing architect for YouTube Shorts. 

Your goal is to take a 100-second horror script and break it into a high-retention pacing map.

CRITICAL PACING RULE:
To keep viewers engaged, we need frequent visual cuts. For this 100-second script, you MUST distribute exactly {target_total_scenes} scenes across the narrative. 

INPUTS:
1. SCRIPT: {script_text}
2. STORYBOARD_1 (Major Anchors): {storyboard_1}

YOUR TASK:
1. Divide the script into Chapters based on the {len(storyboard_1['scenes'])} Anchor Scenes in Storyboard_1.
2. Assign a 'scene_count' to each chapter. 
3. The total sum of all 'scene_count' values MUST be exactly {target_total_scenes}.
4. Most chapters should have 5-7 scenes to ensure the visual moves every 3 seconds.

STRICT RULES:
- Do not describe visuals.
- Do not add camera angles.
- Only output the numerical structure and the purpose of the chapter.

RETURN FORMAT:
{{
  "chapters": [
    {{
      "chapter_index": 0,
      "source_scene_index": 0,
      "chapter_purpose": "Intro: Establishing the cursed cabinet",
      "scene_count": 6
    }}
  ]
}}
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

    # The prompt now forces the LLM to aim for ~28 scenes total
    resp = call_llm(build_prompt(script_text, storyboard_1))
    payload = extract_json_from_llm(resp)

    out: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "total_target_scenes": 28,
        "chapters": payload.get("chapters", []),
    }

    write_json(run_folder / "storyboard_2.json", out)
    print(f"[SUCCESS] storyboard_2.json (High-Retention Pacing) saved | run={args.run_id}")

if __name__ == "__main__":
    main()