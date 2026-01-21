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
    target_idx = sb3.get("chapter_index", "UNKNOWN")
    
    return f"""
You are the Visual Executor. 
TASK: Create a single, highly descriptive visual sentence for Chapter {target_idx}.

STRICT OUTPUT RULE:
- Your response MUST be a single string of text. 
- DO NOT use JSON, DO NOT use curly braces {{}}, and DO NOT use labels like "Description:".
- If you return anything other than a plain sentence, the system will crash.

CONTENT HIERARCHY:
1. IF OBJECT: Focus on 3 specific textures. (Example: "A macro shot of [Texture A], [Texture B], and [Texture C] on the [Object].")
2. IF CHARACTER: Describe 1 physical action and 1 facial emotion. (Example: "The [Character] [Action] while looking [Emotion].")
3. IF ENVIRONMENT: Describe the lighting and the furthest visible point.

STRICT NEGATIVE CONSTRAINTS:
- Do NOT use the words "No humans," "Canon," "Shot type," or "Logic" in your sentence.
- Do NOT describe more than one distinct moment.

INPUTS:
- Logic: {sb3}
- Canon: {canon}

(Write the sentence now):
""".strip()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, default=None)
    args = parser.parse_args()

    RUNS_DIR = ROOT / "runs"
    run_folder = RUNS_DIR / args.run_id if args.run_id else find_latest_run_folder(RUNS_DIR)

    # Load necessary files
    script_json = read_json(run_folder / "script.json")
    script_text = script_json.get("script", "")
    sb3 = read_json(run_folder / "storyboard_3.json")
    canon = read_json(run_folder / "visual_canon.json")
    
    all_final_chapters = []

    # Sort chapters to maintain narrative order
    chapters = sorted(sb3.get("expanded_chapters", []), key=lambda x: x['chapter_index'])

    for chapter in chapters:
        c_idx = chapter.get("chapter_index")
        current_chapter_scenes = []
        
        for s_idx, scene_logic in enumerate(chapter.get("scenes", [])):
            print(f"[*] Processing Chapter {c_idx} | Scene {s_idx}...")
            
            single_scene_sb3 = {
                "chapter_index": c_idx,
                "scenes": [scene_logic] 
            }
            
            # 1. Call LLM
            resp = call_llm(build_prompt(script_text, single_scene_sb3, canon))
            
            # 2. HYBRID PARSING LOGIC
            # This prevents the "LLM did not return a JSON object" crash
            try:
                # Try parsing as JSON first
                payload = extract_json_from_llm(resp)
                # Dig through the expected structure
                gen_desc = payload["final_chapters"][0]["scenes"][0]["description"]
            except Exception:
                # Fallback: Treat the raw response as the description string
                # Strip quotes in case the LLM wrapped the sentence in them
                gen_desc = resp.strip().strip('"').strip("'")
            
            # 3. Create a standardized scene object
            gen_scene = {
                "scene_type": scene_logic.get("scene_type", "adjacent"),
                "description": gen_desc
            }
            current_chapter_scenes.append(gen_scene)
        
        # Rebuild chapter object
        all_final_chapters.append({
            "chapter_index": c_idx,
            "scenes": current_chapter_scenes
        })

    # Prepare final output
    out: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "final_chapters": all_final_chapters
    }
    
    write_json(run_folder / "storyboard_4.json", out)
    
    total_scenes = sum(len(c["scenes"]) for c in all_final_chapters)
    print(f"[SUCCESS] storyboard_4.json saved with {total_scenes} total scenes across {len(all_final_chapters)} chapters.")

if __name__ == "__main__":
    main()