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
    extract_json_from_llm,
    find_latest_run_folder,
)

SCHEMA_NAME = "storyboard_3"

def build_prompt(script_text: str, sb1: Dict[str, Any], sb2: Dict[str, Any]) -> str:
    return f"""
You are the Narrative Architect for a horror YouTube Shorts channel. 
Your task is "Step 3: Logical Scene Expansion."

INPUTS:
1. SCRIPT: The full story text.
2. STORYBOARD_1: The mandatory visual "anchor" moments.
3. STORYBOARD_2: The pacing structure (Chapters and Scene Counts).

YOUR TASK:
For each chapter defined in STORYBOARD_2, you must brainstorm the specific logic for the required number of scenes. 
One scene in each chapter should be the "Anchor Scene" (the big moment from SB1), and the other scenes should be "Adjacent Scenes" that build tension, show reactions, or provide environmental context.

THINKING GUIDELINES:
- If a chapter has 3 scenes and contains an anchor like "Entity taps on window," your logic might be:
    - Scene 1 (Adjacent): Character is scrolling on their phone, oblivious.
    - Scene 2 (Anchor): A pale hand presses against the glass.
    - Scene 3 (Adjacent): Extreme close-up of the character's eyes widening in the dark.
- Ensure the narrative flow makes sense between scenes.
- Focus on "What is happening" and "Why it matters." Do not write final image prompts yet.

RETURN FORMAT:
{{
  "expanded_chapters": [
    {{
      "chapter_index": 0,
      "scenes": [
        {{
          "scene_type": "anchor/adjacent",
          "narrative_goal": "Why this scene exists (e.g., build dread)",
          "visual_logic": "Detailed explanation of what we see and how it connects to the previous shot."
        }}
      ]
    }}
  ]
}}

SCRIPT:
{script_text}

STORYBOARD_1:
{sb1}

STORYBOARD_2:
{sb2}
""".strip()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, default=None)
    args = parser.parse_args()

    RUNS_DIR = ROOT / "runs"
    run_folder = RUNS_DIR / args.run_id if args.run_id else find_latest_run_folder(RUNS_DIR)

    # Load artifacts from previous steps
    script_json = read_json(run_folder / "script.json")
    sb1 = read_json(run_folder / "storyboard_1.json")
    sb2 = read_json(run_folder / "storyboard_2.json")

    script_text = script_json.get("script", "")
    if not script_text:
        raise RuntimeError("script.json missing script text")

    # Call LLM for narrative "thinking"
    resp = call_llm(build_prompt(script_text, sb1, sb2))
    payload = extract_json_from_llm(resp)

    out: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "expanded_chapters": payload.get("expanded_chapters", []),
    }

    write_json(run_folder / "storyboard_3.json", out)
    print(f"[SUCCESS] storyboard_3.json (Thinking Layer) saved | run={args.run_id}")

if __name__ == "__main__":
    main()