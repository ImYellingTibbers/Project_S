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
    script_text: str,
    canon: Dict[str, str],
    winning_idea: str
) -> str:
    return f"""
You are a top-tier YouTube Shorts visual director specializing in viral, high-retention, confessional horror.

You are creating a COHESIVE VISUAL STORY centered on a human experiencing the narrated horror.

IMPORTANT:
- Do NOT illustrate every sentence.
- Create visual SCENES that follow the narrative beats and escalation of the story.
- Each scene may represent multiple spoken lines.
- Focus on cohesion, continuity, and escalation — not timing precision.

SCENE COUNT RULES (follow exactly):
- Create BETWEEN 8 AND 16 scenes total.
- Fewer scenes if the story is simple.
- More scenes only if escalation demands it.

STRICT RULES:
- Every scene must introduce NEW visual information.
- The visual situation MUST escalate over time.

HUMAN PRESENCE RULES (IMPORTANT):
- Unless impossible, EACH scene should visibly include the narrator or another humanoid figure.
- When the narrator is visible in a scene, explicitly include the phrase “the narrator” in the visual_description.
- If the narrator is not visible in a scene, do not mention them at all.
- The human may be shown as:
  • full body
  • partial body (torso, legs, back)
  • silhouette
  • figure in darkness
  • figure at a distance
- Faces are allowed but not required.
- The human must be visible in the frame, not implied only by objects or environment.
- Avoid excessive close-ups; vary distance and framing across scenes.

IMAGE CONSTRAINTS:
- Describe ONLY what is physically visible.
- Use concrete, physical details only.
- NO abstract concepts.
- NO metaphors.
- NO symbolism.
- NO camera directions.
- NO camera movement.
- NO abstract motion.
- Physical change is allowed (objects moved, doors ajar, lights failing).

CHARACTER CONSISTENCY:
The narrator is a single consistent human across scenes.
Do NOT invent or vary appearance details.

GLOBAL VISUAL STYLE (applies to all scenes):
{canon["style"]}

STORY CONTEXT (do not restate verbatim, only guide escalation):
{winning_idea}

FULL SCRIPT (for narrative understanding only):
\"\"\"
{script_text}
\"\"\"

Return ONLY valid JSON in this format:

{{
  "scenes": [
    {{
      "visual_description": "A grounded, physical description of what the viewer sees.",
      "includes_narrator": true
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

    winning_idea = script_json.get("winning_idea", "")

    canon = generate_canon(run_folder)
    (run_folder / "visual_canon.json").write_text(
        json.dumps(canon, indent=2),
        encoding="utf-8"
    )

    prompt = build_storyboard_prompt(script_text, canon, winning_idea)

    print("[*] Calling LLM for Storyboard creation...")
    response = call_llm(prompt)
    payload = extract_json(response)

    scenes = payload.get("scenes")
    if not isinstance(scenes, list):
        raise RuntimeError("Storyboard response missing scenes list")

    scene_count = len(scenes)
    if scene_count < 8 or scene_count > 16:
        raise RuntimeError(
            f"Storyboard scene count out of bounds: {scene_count} (expected 8–16)"
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
            "includes_narrator": bool(scene.get("includes_narrator", True))
        })

    out_path = run_folder / "storyboard.json"
    out_path.write_text(json.dumps(storyboard, indent=2), encoding="utf-8")

    print(f"[SUCCESS] Storyboard saved with {scene_count} scenes.")


if __name__ == "__main__":
    main()
