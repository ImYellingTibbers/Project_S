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
RUNS_DIR = Path(__file__).resolve().parents[2] / "runs"
TARGET_IMAGE_COUNT = 15

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------
# Phase 1 — Canon Generation
# -------------------------
def call_llm(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    output_text = resp.choices[0].message.content
    return extract_json_from_llm(output_text)


def generate_protagonist_description() -> str:
    hair = random.choice(["short brown hair", "short dark hair", "short light brown hair"])
    beard = random.choice(["clean-shaven", "short beard"])
    age = random.choice(["late 20s", "mid 30s", "early 40s"])
    clothing = random.choice(["casual clothing", "plain t-shirt and jeans", "dark casual clothing"])
    parts = ["adult white male", age, hair, beard, clothing]
    return ", ".join(p for p in parts if p)


# -------------------------
# Phase 2 — Narration → Literal Image Slice
# -------------------------
def generate_scene_for_beat(
    full_script: str,
    beat_index: int,
    window_text: str,
    start_line: int,
    end_line: int,
    canon_ids: set[str],
    previous_description: str,
) -> Dict[str, Any]:

    forced_shot = "close-up, low angle"

    if beat_index <= 4:
        pacing_rule = "NO ENTITY. Show only normal objects or space altered by the narration."
        forced_visible_ids = ["c1"]
    elif 5 <= beat_index <= 9:
        pacing_rule = "ENTITY ONLY AS PARTIAL: shadow, limb, or distortion. No full body."
        forced_visible_ids = ["c1"]
    else:
        pacing_rule = "ENTITY FULLY ALLOWED IN FRAME."
        forced_visible_ids = ["c1", "c2"]

    system = (
        "You are a visual extraction engine, not a storyteller.\n"
        "Your task is to SELECT ONE PHYSICAL OBJECT OR BODY PART explicitly mentioned "
        "or unavoidably implied by the narration, and depict ONLY that.\n"
        "If the narration mentions sound, show the DEVICE that captures it.\n"
        "If the narration mentions presence, show a PHYSICAL EFFECT (indentation, wrinkle, vibration).\n"
        "Never depict entities, figures, faces, breath, or silhouettes unless the narration explicitly names them.\n"
        "No abstraction. No symbolism. No atmosphere-only frames.\n"
        "Return JSON only."
    )

    user = f"""
NARRATION CHUNK (USE DIRECTLY):
\"{window_text}\"

PREVIOUS FRAME SUBJECT (do not repeat):
\"{previous_description if previous_description else "None"}\"

PACING RULE:
{pacing_rule}

OUTPUT JSON (STRICT):
{{
  "visible_canon_ids": ["__AUTO__"],
  "frame_subject": "short literal noun phrase (≤12 words)",
  "frame_action": "single visible action or state (≤18 words)",
  "camera": "{forced_shot}",
  "mood": "one or two words",
  "literal_sd_prompt": "single comma-separated prompt describing exactly what is visible"
}}

RULES FOR literal_sd_prompt:
- Include camera/framing terms (cropped, partial, foreground, edge of frame)
- No illustration, poster, vector, comic language
- No skeletons, skulls, bones
- Must be grounded in the narration chunk
"""

    try:
        data = call_llm(system, user)
        # FORCE CAMERA INTO THE SD PROMPT
        if data.get("literal_sd_prompt"):
            data["literal_sd_prompt"] = (
                f"{forced_shot}, "
                f"{data['literal_sd_prompt']}"
            )
        
        # HARD FILTER — BAN NON-LITERAL VISUALS
        ILLEGAL_TERMS = [
            "figure", "entity", "presence", "silhouette", "breath",
            "looming", "watching", "standing over", "shadowy"
        ]

        prompt = data.get("literal_sd_prompt", "").lower()
        for term in ILLEGAL_TERMS:
            if term in prompt:
                raise ValueError(
                    f"Illegal abstract term '{term}' in literal_sd_prompt: {prompt}"
                )
        
        # HARD BAN EARLY-REVEAL LANGUAGE
        if beat_index < 10:
            banned_terms = ["face", "mouth", "head", "figure", "eyes", "breath"]
            prompt = data.get("literal_sd_prompt", "").lower()
            for term in banned_terms:
                if term in prompt:
                    data["literal_sd_prompt"] = data["literal_sd_prompt"].replace(term, "shadow")

        data["visible_canon_ids"] = forced_visible_ids
        data["camera"] = forced_shot
        data["script_anchor"] = {"start_line": start_line, "end_line": end_line}
        data["segment_text"] = window_text

        data.setdefault("frame_subject", "")
        data.setdefault("frame_action", "")
        data.setdefault("mood", "uneasy")
        data.setdefault("literal_sd_prompt", "")

        return data

    except Exception as e:
        print(f"Error on beat {beat_index}: {e}")
        return {}


# -------------------------
# Main Logic
# -------------------------
def main() -> None:
    run_dir = find_latest_run_folder(RUNS_DIR)
    script_json = read_json(run_dir / "script.json")
    script_text = get_script_text(script_json)

    vo_json = read_json(run_dir / "vo.json")
    sentences = vo_json.get("timing", {}).get("sentences", [])
    sentence_texts = [s.get("text", "").strip() for s in sentences]

    c1_desc = generate_protagonist_description()
    entity_prompt = f"Describe the horror entity based on this script: {script_text}. Return JSON."
    entity_desc = call_llm(
        "Horror Concept Artist. Return JSON only.", entity_prompt
    ).get("description", "A contorted shadow with elongated limbs.")

    canon = [
        {"id": "c1", "type": "character", "description": c1_desc},
        {"id": "c2", "type": "entity", "description": entity_desc},
    ]
    write_json(run_dir / "canon.json", {"canon": canon})

    total_sentences = len(sentence_texts)
    all_scenes: List[Dict[str, Any]] = []
    last_subject = ""

    print(f"[*] Generating {TARGET_IMAGE_COUNT} narration-anchored image beats...")

    for i in range(TARGET_IMAGE_COUNT):
        start_idx = int((i / TARGET_IMAGE_COUNT) * total_sentences)
        end_idx = int(((i + 1) / TARGET_IMAGE_COUNT) * total_sentences)
        if i == TARGET_IMAGE_COUNT - 1:
            end_idx = total_sentences

        window_text = " ".join(sentence_texts[start_idx:end_idx]).strip()

        scene_data = generate_scene_for_beat(
            script_text,
            i,
            window_text,
            start_idx,
            end_idx - 1,
            {"c1", "c2"},
            last_subject,
        )

        if scene_data:
            last_subject = scene_data.get("frame_subject", last_subject)
            all_scenes.append(scene_data)

        time.sleep(0.2)

    write_json(
        run_dir / "visual_scenes.json",
        {
            "schema": "visual_scenes_v7_literal_from_narration",
            "total_images": len(all_scenes),
            "scenes": all_scenes,
        },
    )
    print(f"[SUCCESS] {len(all_scenes)} scenes generated.")

if __name__ == "__main__":
    main()
