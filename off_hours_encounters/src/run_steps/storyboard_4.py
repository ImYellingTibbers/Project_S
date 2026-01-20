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

SCHEMA_NAME = "storyboard_4"

def build_prompt(script_text: str, sb3: Dict[str, Any], canon: Dict[str, Any]) -> str:
    return f"""
You are the Visual Executor. Your goal is to write the final descriptions for every scene in a horror short. 

CRITICAL INSTRUCTION: HARD-INJECTION OF CANON
You must never use placeholder names like "the protagonist" or "the entity" alone. You must physically describe them in EVERY scene using the exact traits provided in the VISUAL CANON. This ensures the image generator maintains visual consistency.

INPUTS:
1. SCRIPT: {script_text}
2. STORYBOARD_3 (The Narrative Logic): {sb3}
3. VISUAL CANON (The Physical Truth): {canon}

EXECUTION RULES:
- If a scene involves a character (e.g., adult_1), you MUST describe their physical features (age, hair, clothing) in that scene's description.
- If a scene takes place in a location (e.g., location_1), you MUST describe the environmental details (lighting, furniture, atmosphere) from the canon.
- Detail level: High. Describe the texture, the lighting contrast, and the specific movement.
- Tone: Cinematic, dark, viral horror.

RETURN FORMAT:
{{
  "final_chapters": [
    {{
      "chapter_index": 0,
      "scenes": [
        {{
          "scene_type": "anchor/adjacent",
          "description": "The final physical description. Example: 'A white adult male in his 40s with short brown hair, wearing a plain shirt [adult_1], sits in a dimly lit room with peeling wallpaper [location_1]...'"
        }}
      ]
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
    sb3 = read_json(run_folder / "storyboard_3.json")
    canon = read_json(run_folder / "visual_canon.json")

    script_text = script_json.get("script", "")

    # Final execution call
    resp = call_llm(build_prompt(script_text, sb3, canon))
    payload = extract_json_from_llm(resp)

    out: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "final_chapters": payload.get("final_chapters", []),
    }

    write_json(run_folder / "storyboard_4.json", out)
    print(f"[SUCCESS] storyboard_4.json (Hard-Injected) saved | run={args.run_id}")

if __name__ == "__main__":
    main()