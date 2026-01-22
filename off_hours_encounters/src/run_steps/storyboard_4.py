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
    scene = (sb3.get("scenes") or [{}])[0]

    scene_type = scene.get("scene_type", "adjacent")
    logic = scene.get("visual_logic", "")
    goal = scene.get("narrative_goal", "")

    return f"""
You are the Visual Executor.

TASK:
Write ONE single, cinematic visual sentence for ONE scene.

STRICT OUTPUT RULE:
- Output MUST be ONE plain sentence. No JSON. No labels. No quotes. No brackets.

IDENTITY RULES (NON-NEGOTIABLE):
- The protagonist is ALWAYS: {canon.get("character_canon", {}).get("adult_1", "adult_1")}
- The entity is ALWAYS: {canon.get("entity_canon", {}).get("entity_1", "entity_1")}
- DO NOT merge them. The protagonist never becomes the entity.

ENTITY APPEARANCE RULE:
- Only show the entity’s BODY if the Logic clearly indicates it is physically present.
- If Logic does NOT clearly indicate entity presence, you may only imply it indirectly
  (shadow, disturbed object, ominous empty space, camera glitch), but no full entity body.

SAFETY / CONTENT RULES (HARD BAN):
- No nudity. No lingerie. No cleavage focus. No sexual framing.
- All people are fully clothed in normal, modest clothing.
- No explicit body parts, no exposed breasts, no nude silhouettes.

VARIETY RULE:
- Avoid repeating the same framing. Choose a distinct shot style:
  (wide establishing, over-the-shoulder, extreme close-up, low angle, high angle, hallway depth shot,
   POV handheld, macro prop detail, silhouette through doorway).

SCENE CONTEXT:
Chapter: {target_idx}
Scene type: {scene_type}
Narrative goal: {goal}
Logic: {logic}

Write the sentence now:
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