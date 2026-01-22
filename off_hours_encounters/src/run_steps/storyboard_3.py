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

def enforce_scene_counts(sb3_payload: Dict[str, Any], sb2: Dict[str, Any]) -> Dict[str, Any]:
    """Force storyboard_3 expanded_chapters to exactly match storyboard_2 scene counts."""
    target_counts = {c["chapter_index"]: c["scene_count"] for c in sb2.get("chapters", [])}

    expanded = sb3_payload.get("expanded_chapters", [])
    expanded_by_idx = {c["chapter_index"]: c for c in expanded}

    # Ensure all chapters exist
    for chap_idx, target in target_counts.items():
        if chap_idx not in expanded_by_idx:
            expanded_by_idx[chap_idx] = {"chapter_index": chap_idx, "scenes": []}

        scenes = expanded_by_idx[chap_idx].get("scenes", [])
        if scenes is None:
            scenes = []
            expanded_by_idx[chap_idx]["scenes"] = scenes

        # Ensure at least one anchor exists
        has_anchor = any(s.get("scene_type") == "anchor" for s in scenes)
        if scenes and not has_anchor:
            mid = len(scenes) // 2
            scenes[mid]["scene_type"] = "anchor"

        # Trim if too many (keep anchor + early/late context)
        if len(scenes) > target:
            anchors = [s for s in scenes if s.get("scene_type") == "anchor"]
            non_anchors = [s for s in scenes if s.get("scene_type") != "anchor"]

            kept = []
            if anchors:
                kept.append(anchors[0])

            # Keep from beginning then end
            remaining = target - len(kept)
            front_take = max(0, remaining // 2)
            back_take = remaining - front_take

            kept.extend(non_anchors[:front_take])
            if back_take > 0:
                kept.extend(non_anchors[-back_take:])

            expanded_by_idx[chap_idx]["scenes"] = kept[:target]

        # Pad if too few
        while len(expanded_by_idx[chap_idx]["scenes"]) < target:
            i = len(expanded_by_idx[chap_idx]["scenes"])
            expanded_by_idx[chap_idx]["scenes"].append({
                "scene_type": "adjacent",
                "narrative_goal": "Bridge pacing with a supporting cutaway that maintains tension.",
                "visual_logic": (
                    "A grounded, non-repeating cutaway detail that supports the moment: "
                    "hands, door hardware, hallway depth, phone screen glow, shadows, clutter, "
                    "footsteps, appliance light, or a tight close-up on a prop."
                )
            })

    # Return chapters in order
    fixed = sorted(expanded_by_idx.values(), key=lambda x: x["chapter_index"])
    sb3_payload["expanded_chapters"] = fixed
    return sb3_payload


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
    chapters_map = sb2.get("chapters", [])
    
    all_expanded_chapters = []

    print(f"[*] Starting chunked processing for {len(chapters_map)} chapters...")

    for chapter in chapters_map:
        c_idx = chapter["chapter_index"]
        target_count = chapter["scene_count"]
        purpose = chapter["chapter_purpose"]
        
        print(f"[>] Processing Chapter {c_idx} ({target_count} scenes)...")

        # Refined prompt just for this chapter
        chapter_prompt = f"""
        You are a Horror Narrative Architect.
        
        TASK:
        Generate the visual logic for Chapter {c_idx} only.
        Chapter Purpose: {purpose}
        Target Number of Scenes: {target_count}
        
        INPUTS:
        - FULL SCRIPT: {script_text}
        - ANCHOR MOMENTS: {sb1}
        
        RETURN FORMAT (JSON ONLY):
        {{
          "chapter_index": {c_idx},
          "scenes": [
            {{
              "scene_type": "anchor or adjacent",
              "narrative_goal": "One sentence goal",
              "visual_logic": "One sentence visual description"
            }}
          ]
        }}
        """

        # Call LLM for this specific chunk
        resp = call_llm(chapter_prompt.strip())
        chapter_payload = extract_json_from_llm(resp)
        
        # Add to our collection
        all_expanded_chapters.append(chapter_payload)

    # Reconstruct the final payload
    payload = {
        "expanded_chapters": all_expanded_chapters
    }

    # Enforce counts (your existing function works great here as a safety net)
    payload = enforce_scene_counts(payload, sb2)

    out: Dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "expanded_chapters": payload.get("expanded_chapters", []),
    }

    write_json(run_folder / "storyboard_3.json", out)
    print(f"[SUCCESS] storyboard_3.json (Thinking Layer) saved | run={args.run_id}")


    write_json(run_folder / "storyboard_3.json", out)
    print(f"[SUCCESS] storyboard_3.json (Thinking Layer) saved | run={args.run_id}")

if __name__ == "__main__":
    main()