from __future__ import annotations

import os
import time
import random
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List

from openai import OpenAI

from _common_utils import (
    utc_now_iso,
    read_json,
    write_json,
    get_script_text,
    extract_json_from_llm,
    find_latest_run_folder,
)

load_dotenv()

# -------------------------
# Config
# -------------------------

MODEL = "gpt-4o-mini"
SCENES_MIN = 10
SCENES_MAX = 15
BATCH_SIZE = 5
MAX_RETRIES_PER_BATCH = 3

RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -------------------------
# OpenAI helper
# -------------------------

def call_llm(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    resp = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    output_text = resp.output_text
    return extract_json_from_llm(output_text)


# -------------------------
# Phase 1 — Canon
# -------------------------

def generate_canon(script_text: str) -> Dict[str, Any]:
    return {
        "canon": [
            {
                "id": "c1",
                "type": "character",
                "description": "__PROTAGONIST__"
            },
            {
                "id": "c2",
                "type": "entity",
                "description": ""  # filled by LLM next
            }
        ]
    }


def generate_protagonist_description() -> str:
    hair = random.choice([
        "short brown hair",
        "short dark hair",
        "short light brown hair"
    ])

    beard = random.choice([
        "clean-shaven",
        "short beard"
    ])

    age = random.choice([
        "late 20s",
        "mid 30s",
        "early 40s"
    ])

    clothing = random.choice([
        "casual clothing",
        "plain t-shirt and jeans",
        "dark casual clothing"
    ])

    hat = random.choice([
        "",
        "wearing a baseball cap"
    ])

    parts = [
        "adult white male",
        age,
        hair,
        beard,
        clothing,
        hat
    ]

    return ", ".join(p for p in parts if p)



# -------------------------
# Phase 2 — Scenes
# -------------------------

def generate_scene_batch(
    script_text: str,
    canon: List[Dict[str, Any]],
    start_index: int,
    count: int,
    total_target: int,
    sentence_texts: List[str],
) -> Dict[str, Any]:
    system = (
        "You are a master horror film director and storyboard artist.\n"
        "You provide precise visual instructions that must be logically consistent.\n"
        "Output ONLY valid JSON."
    )
    
    total_lines = len(sentence_texts)
    batch_start_line = int((start_index / total_target) * total_lines)
    batch_end_line = int(((start_index + count) / total_target) * total_lines) - 1
    batch_end_line = max(batch_start_line, min(batch_end_line, total_lines - 1))

    user = f"""
TASK: Create EXACTLY {count} visual scenes for the script segments provided.

STRICT RULES:
1. **script_sentence**: Provide the EXACT sentence from the script.
2. **script_anchor**: Provide the line index (0-indexed).
3. **visible_canon_ids**: 
   - ["c1"] = Protagonist is visible.
   - ["c2"] = Entity is visible.
   - [] = Environment/objects only. No people allowed.
4. **Variety**: At least {max(1, count // 2)} scenes MUST be environment-only (visible_canon_ids: []).
5. **Visual Consistency**: The `visual_description` MUST NOT mention a character or entity unless their ID is in `visible_canon_ids`. 

LOGIC CHECK:
- If `visible_canon_ids` is [], DO NOT describe a person, hands, eyes, or faces. Focus on objects and rooms.
- If `visible_canon_ids` is ["c1"], you MUST describe the man (c1), but you MUST NOT describe the entity (c2).
- If both are present, use ["c1", "c2"].

ALLOWED RANGE (Lines {batch_start_line} to {batch_end_line}):
{chr(10).join(f"{i}: {sentence_texts[i]}" for i in range(batch_start_line, batch_end_line + 1))}

FULL CONTEXT:
{script_text}

JSON FORMAT:
{{
  "scenes": [
    {{
      "scene_index": null,
      "script_anchor": {{ "line_index": 0 }},
      "script_sentence": "...",
      "visible_canon_ids": ["c1"],
      "visual_description": "..."
    }}
  ]
}}
"""
    return call_llm(system, user)

# -------------------------
# Validation
# -------------------------

def batch_is_valid(
    batch: Dict[str, Any],
    canon_ids: set[str],
    *,
    expected_count: int,
) -> bool:
    scenes = batch.get("scenes", [])
    if not scenes or len(scenes) > BATCH_SIZE:
        return False

    # must match requested count exactly (prevents silent under-generation)
    if len(scenes) != expected_count:
        return False

    for s in scenes:
        desc = s.get("visual_description", "")
        lower = desc.lower()
        banned = ("woman", "women", "female", "girl", "girls", "child", "children", "teen", "teenage", "pregnant")
        if any(w in lower for w in banned):
            return False
        ids = s.get("visible_canon_ids", [])

        for cid in ids:
            if cid not in canon_ids:
                return False

        if desc.count(",") > 8:
            return False

    return True


def inject_canon_descriptions(
    scenes: List[Dict[str, Any]],
    canon: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    canon_map = {c["id"]: c["description"] for c in canon}

    for scene in scenes:
        injected = []
        for cid in scene.get("visible_canon_ids", []):
            injected.append(f"{cid}: {canon_map[cid]}")
        scene["canon_descriptions"] = injected

    return scenes


# -------------------------
# Main
# -------------------------

def main() -> None:
    run_dir = find_latest_run_folder(RUNS_DIR)
    script_path = run_dir / "script.json"

    script_json = read_json(script_path)
    script_text = get_script_text(script_json)
    if not script_text:
        raise RuntimeError("Script text not found or empty")
    
    # ---- VO sentence map for anchoring
    vo_path = run_dir / "vo.json"
    if not vo_path.exists():
        raise RuntimeError("vo.json not found; required for script_anchor sentence indices")

    vo_json = read_json(vo_path)
    sentences = vo_json.get("timing", {}).get("sentences", [])
    if not isinstance(sentences, list) or not sentences:
        raise RuntimeError("vo.json missing timing.sentences")

    sentence_texts = [s.get("text", "").strip() for s in sentences]
    if any(not t for t in sentence_texts):
        raise RuntimeError("vo.json timing.sentences has empty text entries")


    # ---- Canon
    canon_obj = generate_canon(script_text)
    canon = canon_obj["canon"]

    # Fill protagonist deterministically
    canon[0]["description"] = generate_protagonist_description()

    # Ask LLM ONLY for entity description
    entity_prompt = f"""
    From the script below, describe the ENTITY visually.

    Rules:
    - short
    - visually suggestive
    - incomplete
    - suitable for partial or shadowed appearances

    Script:
    \"\"\"
    {script_text}
    \"\"\"

    Return JSON only in this shape:
    {{
    "description": "..."
    }}
    """

    entity_desc = call_llm(
        "You describe a horror entity for image generation.",
        entity_prompt
    )["description"]

    canon[1]["description"] = (
        "Non-human presence. Only partial physical intrusion allowed. No full body, no face, no hands unless explicitly required by the scene. A vertical distortion in shadow, suggesting an inhuman mass just beyond visibility. Limbs are never fully seen; only indirect occlusion, warped silhouettes, or pressure against space. "
        "No full body, no face, no hands unless explicitly required by the scene. "
        f"{entity_desc}".strip()
    )

    canon_ids = {c["id"] for c in canon}

    write_json(
        run_dir / "canon.json",
        {
            "schema": "visual_canon_v1",
            "created_at": utc_now_iso(),
            "canon": canon,
        },
    )

    # ---- Scene count
    total_scenes = SCENES_MAX
    scenes: List[Dict[str, Any]] = []

    index = 0
    while index < total_scenes:
        batch_size = min(BATCH_SIZE, total_scenes - index)
        
        max_attempts = 3 # Define this at the top or here
        for attempt in range(max_attempts):
            batch = generate_scene_batch(
                script_text=script_text,
                canon=canon,
                start_index=index,
                count=batch_size,
                total_target=total_scenes,
                sentence_texts=sentence_texts,
            )
            # Check if batch is valid before processing
            if batch_is_valid(batch, canon_ids, expected_count=batch_size):
                for i, scene in enumerate(batch["scenes"]):
                    scene["scene_index"] = index + i
                scenes.extend(batch["scenes"])
                break
            if attempt == max_attempts - 1:
                raise RuntimeError(f"Batch {index}-{index+batch_size-1} failed validation")

            time.sleep(1)

        index += batch_size
        
    if len(scenes) < SCENES_MIN:
        raise RuntimeError(
            f"Only generated {len(scenes)} scenes, below minimum {SCENES_MIN}"
        )

    scenes = inject_canon_descriptions(scenes, canon)

    write_json(
        run_dir / "visual_scenes.json",
        {
            "schema": "visual_scenes_v1",
            "created_at": utc_now_iso(),
            "scenes": scenes,
        },
    )


if __name__ == "__main__":
    main()
