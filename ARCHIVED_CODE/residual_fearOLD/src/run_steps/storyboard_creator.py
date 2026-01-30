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
    "expression": ["neutral expression"],
    "clothing": ["dark canvas work jacket", "faded black t-shirt"],
    "detail": ["slight nervous sweat at the hairline"]
}

STYLE_BASE = (
    "cinematic horror still, "
    "dark atmospheric realism, "
    "stylized realism, not a photograph, "
    "intentional cinematic composition, "
    "clear foreground, midground, and background separation, "
    "shadow-driven lighting, minimal fill light, "
    "desaturated, cold moody color palette, "
    "soft volumetric fog and atmospheric depth, "
    "environmental storytelling emphasis, "
    "grim folklore horror tone"
)

STYLE_VARIANTS = [
    "grim folklore horror cinematic still"
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
    script_text: str,
    canon: Dict[str, str],
    min_scenes: int
) -> str:
    return f"""
You are a YouTube Shorts professional who specializes in creating visually interesting scenes that keep viewer retention high.

Your task is to create approximately {min_scenes} short visual scenes that follow the narrative flow of the provided script.

The first scene must:
- Be visually scroll-stopping on its own at phone size
- Show a single, unmistakable anomaly happening right now
- Show a completed or irreversible physical change (a lock already open, an object already displaced, a barrier already breached)
- NOT rely on flickering alone as the anomaly

Each scene should:
- Show something visually interesting or changed in the story
- Feel like a frozen moment from a video (a clear visual state)
In the first 3 scenes, at least ONE anomaly must already be completed or irreversible rather than merely in progress

Visual impact requirements:
- Each scene should feel unsettling or tense on sight
- Prefer moments that imply danger, intrusion, or loss of control
- Favor images that raise a question (“what’s about to happen?”) rather than explain it

Guidelines:
- You will need MANY scenes to maintain retention
- Scenes should escalate visually over time
- Focus on environments, objects, reflections, and physical outcomes
- The narrator may appear, but should not dominate every scene
- Describe each scene purely visually (assume audio may be muted)
- Avoid slapstick, sudden forceful motion, or physically implausible interactions
- When people appear, show only physical posture, position, or interaction with objects; avoid naming emotions.

For each scene:
- Write a concise visual description
- Indicate whether the narrator is visible in the scene

In the final third of scenes, favor interior or close-proximity anomalies over distant exterior sources.

FULL SCRIPT (for reference only):
\"\"\"{script_text}\"\"\"

Output JSON only:
{{
  "scenes": [
    {{
      "visual_description": "A concise physical description of what is visible.",
      "includes_narrator": true
    }}
  ]
}}

Do NOT include explanations or commentary.
""".strip()


# -------------------------------------------------
# Main
# -------------------------------------------------

def main():
    run_folder = find_latest_run_folder()

    script_path = run_folder / "script.json"
    if not script_path.exists():
        raise FileNotFoundError("Missing script.json")

    script_json = json.loads(script_path.read_text(encoding="utf-8"))

    script_text = script_json.get("script", "")
    word_count = len(script_text.split())
    estimated_duration_sec = word_count / 2.5

    MIN_SCENES = int(estimated_duration_sec // 3)
    if not script_text:
        raise RuntimeError("Script is empty")

    canon = generate_canon(run_folder)
    (run_folder / "visual_canon.json").write_text(
        json.dumps(canon, indent=2),
        encoding="utf-8"
    )

    prompt = build_storyboard_prompt(script_text, canon, MIN_SCENES)

    response = call_llm(prompt)
    payload = extract_json(response)

    scenes = payload.get("scenes")
    if not isinstance(scenes, list):
        raise RuntimeError("Storyboard response missing scenes list")

    scene_count = len(scenes)

    ALLOWED_UNDER = 2  # wiggle room

    if scene_count < (MIN_SCENES - ALLOWED_UNDER):
        raise RuntimeError(
            f"Storyboard scene count too low: {scene_count} "
            f"(minimum required: {MIN_SCENES}, allowed underflow: {ALLOWED_UNDER})"
        )

    storyboard = {
        "schema": {"name": "storyboard", "version": PROJECT_VERSION},
        "run_id": script_json.get("run_id"),
        "created_at": utc_now_iso(),
        "canon": canon,
        "scenes": []
    }

    for i, scene in enumerate(scenes):
        storyboard["scenes"].append({
            "scene_index": i,
            "visual_description": scene["visual_description"],
            "includes_narrator": bool(scene.get("includes_narrator", True)),
            "visual_intent": (
                "human_focus"
                if bool(scene.get("includes_narrator", True)) and random.random() < 0.35
                else "environment_focus"
            )
        })

    out_path = run_folder / "storyboard.json"
    out_path.write_text(json.dumps(storyboard, indent=2), encoding="utf-8")

    print(f"[SUCCESS] Storyboard saved with {scene_count} scenes.")


if __name__ == "__main__":
    main()
