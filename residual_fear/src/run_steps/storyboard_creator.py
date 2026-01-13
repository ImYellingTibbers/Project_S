import json
import random
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.config import RUNS_DIR, PROJECT_VERSION
from src.llm.qwen_instruct_llm import call_llm


# -------------------------------------------------
# Utilities
# -------------------------------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_run_folder() -> Path:
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    if not runs:
        raise RuntimeError("No run folders found")
    return runs[-1]


def stable_seed(run_folder: Path) -> int:
    h = hashlib.sha256(run_folder.name.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def extract_sentences(script_text: str) -> List[str]:
    # Preserve narration order exactly
    sentences = []
    for block in script_text.split("\n"):
        block = block.strip()
        if block:
            sentences.append(block)
    return sentences


def extract_json(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError("LLM did not return JSON")
    return json.loads(text[start:end + 1])


# -------------------------------------------------
# Canon Generation (Character + Style ONLY)
# -------------------------------------------------

CHARACTER_POOL = {
    "age": ["late 20s", "early 30s", "mid 30s"],
    "build": ["average height with a heavy build", "tall and broad-shouldered"],
    "skin": ["fair white skin with faint under-eye shadows"],
    "hair": ["short dark brown hair, slightly unkempt"],
    "facial_hair": ["short trimmed beard", "light stubble"],
    "eyes": ["wide, alert eyes that look exhausted"],
    "expression": ["tight-jawed and anxious"],
    "clothing": ["dark canvas work jacket", "faded black t-shirt"],
    "detail": ["slight nervous sweat at the hairline"]
}

STYLE_BASE = (
    "Stylistic realism, cinematic horror, deep shadows, "
    "muted desaturated colors, heavy grain, still-frame photography"
)

STYLE_VARIANTS = [
    "gritty 90s thriller grade",
    "modern digital cinema look",
    "low-contrast nocturnal palette"
]


def generate_canon(run_folder: Path) -> Dict[str, str]:
    rng = random.Random(stable_seed(run_folder))

    character = (
        f"White adult male, {rng.choice(CHARACTER_POOL['age'])}, "
        f"{rng.choice(CHARACTER_POOL['build'])}, "
        f"{rng.choice(CHARACTER_POOL['skin'])}, "
        f"{rng.choice(CHARACTER_POOL['hair'])}, "
        f"{rng.choice(CHARACTER_POOL['facial_hair'])}, "
        f"{rng.choice(CHARACTER_POOL['eyes'])}, "
        f"{rng.choice(CHARACTER_POOL['expression'])}, "
        f"wearing a {rng.choice(CHARACTER_POOL['clothing'])}, "
        f"{rng.choice(CHARACTER_POOL['detail'])}."
    )

    style = f"{STYLE_BASE}, {rng.choice(STYLE_VARIANTS)}"

    return {
        "character_description": character,
        "style": style
    }


# -------------------------------------------------
# Storyboard Prompt (Minimal, Creative)
# -------------------------------------------------

def build_storyboard_prompt(
    sentences: List[str],
    canon: Dict[str, str],
    winning_idea: str
) -> str:
    return f"""
You are a top-tier youtube shorts visual director specializing in viral, high-retention, confessional horror stories.

You are creating a storyboard where EACH IMAGE must help prevent the viewer from scrolling away.

STRICT RULES (follow exactly):
- Create ONE still image per narrated sentence.
- Every scene must introduce NEW visual information.
- At least every 2–3 scenes, the visual situation MUST visibly escalate or change.
- The final scene MUST feel worse, more threatening, or more inescapable than the first.
- You have complete freedom to show whatever you want as long as it fits in the narrative of the story. 

IMAGE CONSTRAINTS:
- Describe ONLY what is physically visible.
- Use concrete, physical details (objects, posture, light, motion, damage).
- NO abstract concepts (e.g. “visible rhythm”, “felt presence”, “sense of dread”).
- NO metaphors.
- NO symbolism.
- NO camera directions.
- NO movement

CHARACTER CONSISTENCY:
When the character appears, use this description consistently:
{canon["character_description"]}

GLOBAL VISUAL STYLE (applies to all scenes):
{canon["style"]}

STORY CONTEXT (do not restate, only inform escalation):
{winning_idea}

SCRIPT SENTENCES (one image per sentence, in order):
{json.dumps(sentences, indent=2)}

ESCALATION GUIDANCE:
- Early scenes: tension, anticipation, subtle unease.
- Middle scenes: abnormal behavior, rule changes, physical reaction.
- Late scenes: loss of control, intensification, or inevitability.
- Each escalation must introduce a new physical behavior from the threat or a new failed coping attempt.
- The FINAL image must visually place the anomaly closer to the character’s body than ever before (bed surface, chest level, hand level, under covers, inches from face).

Return ONLY valid JSON in this format:

{{
  "scenes": [
    {{
      "sentence_index": 0,
      "visual_description": "A grounded, physical description of what the viewer sees."
    }}
  ]
}}
""".strip()


# -------------------------------------------------
# Main
# -------------------------------------------------

def main():
    run_folder = find_latest_run_folder()
    print(f"[*] Processing Storyboard for: {run_folder.name}")

    script_path = run_folder / "script.json"
    if not script_path.exists():
        raise FileNotFoundError("Missing script.json")

    script_json = json.loads(script_path.read_text(encoding="utf-8"))

    script_text = script_json.get("script", "")
    if not script_text:
        raise RuntimeError("Script is empty")

    sentences = extract_sentences(script_text)
    winning_idea = script_json.get("winning_idea", "")

    canon = generate_canon(run_folder)
    (run_folder / "visual_canon.json").write_text(
        json.dumps(canon, indent=2),
        encoding="utf-8"
    )

    prompt = build_storyboard_prompt(sentences, canon, winning_idea)

    print("[*] Calling LLM for Storyboard creation...")
    response = call_llm(prompt)
    payload = extract_json(response)

    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != len(sentences):
        raise RuntimeError("Storyboard scene count does not match script")
    
    # Basic escalation sanity check: final scene should not be calmer than first
    first_desc = scenes[0]["visual_description"].lower()
    last_desc = scenes[-1]["visual_description"].lower()
    body_markers = ["bed", "chest", "hands", "face", "under the covers", "pillow"]
    if not any(b in last_desc for b in body_markers):
        raise RuntimeError(
            "Final storyboard frame lacks body-proximity escalation."
        )

    weak_end_markers = ["quiet", "still", "calm", "motionless", "unchanged"]

    if any(w in last_desc for w in weak_end_markers) and not any(w in first_desc for w in weak_end_markers):
        print("[WARN] Final storyboard scene may lack escalation. Consider regenerating.")

    storyboard = {
        "schema": {"name": "storyboard", "version": PROJECT_VERSION},
        "run_id": script_json.get("run_id"),
        "created_at": utc_now_iso(),
        "canon": canon,
        "scenes": []
    }

    for i, scene in enumerate(scenes):
        storyboard["scenes"].append({
            "sentence_index": i,
            "script_text": sentences[i],
            "visual_description": scene["visual_description"]
        })

    out_path = run_folder / "storyboard.json"
    out_path.write_text(json.dumps(storyboard, indent=2), encoding="utf-8")

    print(f"[SUCCESS] Storyboard saved with {len(sentences)} scenes.")


if __name__ == "__main__":
    main()
