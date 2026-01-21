import argparse
import re
from pathlib import Path
from sys import path as sys_path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys_path:
    sys_path.insert(0, str(ROOT))

from src.run_steps._common_utils import (
    utc_now_iso,
    read_json,
    write_json,
    find_latest_run_folder,
)

SCHEMA_NAME = "image_prompt_generator"

STYLE_PREFIX = "Cinematic horror film still, shot on 35mm lens, grainy texture, high contrast chiaroscuro lighting, eerie atmosphere, hyper-realistic, 8k resolution,"
STYLE_SUFFIX = "--ar 9:16 --v 6.0 --style raw"

def clean_description(text: str) -> str:
    """Removes technical tags, bracketed metadata, and extra whitespace."""
    # 1. Remove anything inside square brackets like [adult_1] or [character_canon]
    text = re.sub(r'\[.*?\]', '', text)
    
    # 2. Remove multiple spaces and fix punctuation gaps caused by stripping
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace(" .", ".").replace(" ,", ",")
    
    return text

def compile_prompt(description: str) -> str:
    """Combines the cleaned description with global style markers."""
    cleaned = clean_description(description)
    return f"{STYLE_PREFIX} {cleaned} {STYLE_SUFFIX}"

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, default=None)
    args = parser.parse_args()

    RUNS_DIR = ROOT / "runs"
    run_folder = RUNS_DIR / args.run_id if args.run_id else find_latest_run_folder(RUNS_DIR)

    sb4 = read_json(run_folder / "storyboard_4.json")
    
    final_prompts = []

    for chapter in sb4.get("final_chapters", []):
        chapter_prompts = []
        for scene in chapter.get("scenes", []):
            description = scene.get("description", "")
            if isinstance(description, dict):
                description = " ".join([str(v) for v in description.values()])

            formatted_prompt = compile_prompt(description)
            
            chapter_prompts.append({
                "scene_type": scene.get("scene_type"),
                "prompt": formatted_prompt
            })
        
        final_prompts.append({
            "chapter_index": chapter.get("chapter_index"),
            "prompts": chapter_prompts
        })

    out: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "style_applied": STYLE_PREFIX,
        "chapters": final_prompts,
    }

    write_json(run_folder / "final_image_prompts.json", out)
    print(f"[SUCCESS] final_image_prompts.json (Cleaned) saved.")

if __name__ == "__main__":
    main()