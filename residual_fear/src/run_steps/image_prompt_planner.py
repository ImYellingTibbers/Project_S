import json
import time
from sys import path
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, PROJECT_VERSION
from src.llm.qwen_instruct_llm import call_llm


# ---------------------------
# Utilities
# ---------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_run_folder() -> Path:
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    if not runs:
        raise RuntimeError("No run folders found")
    return runs[-1]


def extract_json(text: str) -> dict:
    if not text or not text.strip():
        raise RuntimeError("LLM returned empty response")

    text = text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # HARD PREFIX ENFORCEMENT
    first_brace = text.find("{")
    if first_brace == -1:
        raise RuntimeError(
            f"LLM returned no JSON object:\n{text[:300]}"
        )

    text = text[first_brace:]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt to auto-fix common truncation: missing closing braces
        open_braces = text.count("{")
        close_braces = text.count("}")

        if close_braces < open_braces:
            text = text + ("}" * (open_braces - close_braces))

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Invalid JSON from LLM:\n{text[:500]}"
            ) from e

        
        
PROMPTGEN_PROMPT = """
TASK LOCK (MANDATORY)

You are NOT allowed to:
- summarize
- explain
- restate
- describe the storyboard
- list scenes in prose
- add headings or sections

You MUST:
- read the input silently
- output ONLY the JSON defined below

You are an IMAGE PROMPT GENERATOR.

You do NOT decide story, motion, pacing, or meaning.
You translate storyboard intent into simple, literal, diffusion-ready image prompts.

--------------------------------
CORE PRINCIPLE (CRITICAL)
--------------------------------
Less is more.

Use minimal, literal, physically clear language, but make sure to not omit any crucial details (setting, colors, objects, etc.)
Do NOT be poetic, narrative, or descriptive beyond what is visually necessary.

--------------------------------
GLOBAL VISUAL STYLE CANON (MANDATORY)
--------------------------------
All images MUST follow this exact visual style:

- cinematic horror still
- realistic, grounded environments
- low-key lighting, high contrast
- deep shadows, limited color palette
- muted colors (dark blues, sickly greens, dirty browns)
- subtle film grain
- soft volumetric fog or haze where applicable
- shallow to moderate depth of field
- no stylization, no illustration, no surreal art styles
- photorealistic but unsettling

This style is NON-NEGOTIABLE and must be implicitly applied to every image_prompt_body.
Do NOT restate this style verbatim in the prompt.

--------------------------------
GLOBAL RULES
--------------------------------
- The image generator has NO memory
- Every image prompt must be fully self-contained
- Humans MAY appear when explicitly required by the storyboard unit.
- If a human is present, they will be referred to as "the narrator" ONLY.
- Do NOT invent appearance details for the narrator.
- Do NOT describe faces unless explicitly required by the framing.
- No animals or wildlife of any kind.
- Supernatural or impossible creatures are allowed.
- Creatures must not resemble real animals
- If an object appears, it should be static and partially framed
- If "includes_narrator": true, the prompt MUST explicitly reference "the narrator" as a visible human.
- If false, do NOT reference the narrator.

For the first scene ONLY (scene_index == 0):
- Add a visually arresting element that creates immediate curiosity or tension.
- Use descriptors like “striking contrast,” “partial silhouette,” “unexpected detail,” “unsettling composition.”
  
--------------------------------
LANGUAGE RULES (VERY IMPORTANT)
--------------------------------
- Prefer static physical states over actions
- Prefer neutral verbs:
  - touching
  - resting
  - standing
  - positioned
  - partially visible
  - etc.
- Prefer simple adjectives
- Avoid adjectives that could be interpreted as other items, or use words with double meanings
- Avoid verbs that can imply tools or objects:
- DO NOT use: brushing, scrubbing, sweeping, painting, wiping
- Do NOT invent props, tools, or symbolic details
- Do NOT add sensory details unless they are required for setting continuity
- Do NOT describe emotions, thoughts, or intent
- Keep prompts simple, make it dead easy for the AI image generator to create the desired scene
- When the narrator appears, ALWAYS refer to them using the exact phrase: "the narrator"
- Do NOT use synonyms (man, person, figure, male, etc.)

--------------------------------
SETTING CONSISTENCY
--------------------------------
- Maintain consistent location identity across scenes
- Re-describe the setting simply from different angles or distances
- Do NOT add new environmental elements unless implied by the storyboard

--------------------------------
PER-UNIT TASK
--------------------------------
For EACH input unit:
- Generate image_prompt_body (txt2img) using ALL provided fields
- scene_index is a zero-based index indicating scene order.

--------------------------------
IMAGE PROMPT GUIDELINES
--------------------------------
Each image_prompt_body should:
- Describe a single realistic frame
- Use simple, literal language
- Clearly state:
  - subject (if any)
  - setting
  - framing or viewpoint if relevant
- Avoid unnecessary adjectives
- Avoid narrative sequencing

--------------------------------
OUTPUT FORMAT (STRICT)
--------------------------------
{
  "scenes": [
    {
      "scene_index": number,
      "image_prompt_body": string
    }
  ]
}

- No explanations
- No commentary
- Output JSON only

IMPORTANT:
- Your entire response MUST be valid JSON
- Do not include any text before or after the JSON
- Do not wrap the JSON in markdown
- Begin your response with '{' and end with '}'
""".strip()


# ---------------------------
# Main
# ---------------------------

def main():
    load_dotenv()


    run_folder = find_latest_run_folder()

    script_json = json.loads((run_folder / "script.json").read_text(encoding="utf-8"))
    run_id = script_json.get("run_id")
    storyboard = json.loads((run_folder / "storyboard.json").read_text(encoding="utf-8"))

    # -------- Prompt generation pass --------
    pg_input = {
        "units": storyboard["scenes"],
    }
    
    promptgen_scenes = []

    for unit in pg_input["units"]:
        unit = dict(unit)
        unit["includes_narrator"] = unit.get("includes_narrator", True)

        single_pg_input = {
            "units": [unit],
        }

        single_prompt = (
            "SYSTEM:\n"
            "You are a deterministic image-prompt compiler.\n"
            "You do not explain, summarize, analyze, or comment.\n"
            "You ONLY transform structured input into structured JSON output.\n"
            "If you cannot comply exactly, output nothing.\n\n"
            + PROMPTGEN_PROMPT
            + "\n\nINPUT:\n"
            + json.dumps(single_pg_input, indent=2)
            + "\n\nOUTPUT:\n"
        )

        raw = call_llm(single_prompt)

        if not raw or not raw.strip():
            raw = call_llm(single_prompt)  # single retry only

        parsed = extract_json(raw)

        if "scenes" not in parsed or not parsed["scenes"]:
            raise RuntimeError(
                f"Promptgen returned no scenes for scene_index={unit.get('scene_index')}"
            )

        # Take the first scene only (promptgen is single-unit scoped)
        promptgen_scenes.append(parsed["scenes"][0])


        # CRITICAL: throttle GPU + Ollama
        time.sleep(0.05)

    promptgen = {"scenes": promptgen_scenes}



    # -------- Validation --------
    if not isinstance(promptgen, dict):
        raise RuntimeError(f"Prompt generator returned non-dict JSON: {type(promptgen)}")

    if "scenes" not in promptgen or not isinstance(promptgen["scenes"], list):
        raise RuntimeError(
            "Prompt generator returned invalid scenes array. "
            f"Top-level keys returned: {list(promptgen.keys())}"
        )
    
    merged_scenes = []

    pg_by_id = {b["scene_index"]: b for b in promptgen["scenes"]}

    for unit in pg_input["units"]:
        pg = pg_by_id.get(unit["scene_index"])
        if not pg:
            raise RuntimeError(f"Missing promptgen scene_index={unit['scene_index']}")
        
        image_prompt_body = pg["image_prompt_body"]

        if "narrator" in image_prompt_body.lower():
            unit["includes_narrator"] = True

        merged = {
            "unit_type": "scene",
            "scene_index": unit["scene_index"],
            "script_lines": unit.get("script_lines"),
            "framing": unit.get("framing"),
            "location": unit.get("location"),
            "visual_intent": unit.get("visual_intent"),
            "storyboard_description": unit.get("storyboard_description"),
            "includes_narrator": unit.get("includes_narrator", True),
            "image_prompt_body": image_prompt_body,
        }

        merged_scenes.append(merged)

    image_plan = {
        "schema": {
            "name": "image_prompt_planner",
            "version": PROJECT_VERSION,
        },
        "run_id": run_id,
        "created_at": utc_now_iso(),
        # canon will be injected downstream by replacing "the narrator"
        "scenes": merged_scenes,
    }

    (run_folder / "image_plan.json").write_text(
        json.dumps(image_plan, indent=2),
        encoding="utf-8",
    )

    print("Wrote image_plan.json")


if __name__ == "__main__":
    main()
