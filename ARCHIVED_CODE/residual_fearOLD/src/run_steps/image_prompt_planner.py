import json
import time
import re
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

    # Find first JSON object and parse ONLY that object (brace-balanced)
    start = text.find("{")
    if start == -1:
        raise RuntimeError(f"LLM returned no JSON object:\n{text[:300]}")

    depth = 0
    end = None
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end is None:
        raise RuntimeError(f"LLM returned unterminated JSON:\n{text[start:start+500]}")

    candidate = text[start:end]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from LLM:\n{candidate[:500]}") from e
            
            
AUDIO_REGEX = re.compile(
    r"""
    \b(
        hear|heard|hearing|
        sound|sounds|sounded|
        noise|noises|
        echo|echoes|echoing|
        ring|rings|ringing|
        knock|knocks|knocking|
        whisper|whispers|whispering|
        scream|screams|screaming|
        shout|shouts|shouting|
        murmur|murmurs|murmuring|
        hum|hums|humming|
        buzz|buzzes|buzzing|
        click|clicks|clicking|
        creak|creaks|creaking|
        scrape|scrapes|scraping|
        tap|taps|tapping
    )\b
    """,
    re.IGNORECASE | re.VERBOSE
)


def strip_audio_language(text: str) -> str:
    # Remove clauses containing audio references
    text = re.sub(
        r"[^.]*\b(" + AUDIO_REGEX.pattern + r")\b[^.]*\.?",
        "",
        text,
        flags=re.IGNORECASE | re.VERBOSE
    )

    # Clean up spacing and punctuation
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r"\s+\.", ".", text)

    return text.strip()

        
PROMPTGEN_PROMPT = """
You are a STRICT IMAGE PROMPT TRANSLATOR.

Your job is to COPY the visual_description into an image prompt.
You MUST NOT invent new objects, locations, lighting, environments, or actions.
You MAY vary the STATE or CONDITION of an existing object if it is explicitly mentioned.
If an object appears multiple times across scenes, allow its behavior or condition to escalate.

ALLOWED CHANGES:
- Minor grammar cleanup
- Remove audio-only words if present

FORBIDDEN:
- Adding new locations
- Adding new props
- Changing time of day
- Changing lighting
- Adding symbolism
- Adding narrative detail
- Adding emotions or emotional interpretation
- Adding camera language
- Adding ANY detail not explicitly present

If the visual_description is vague, KEEP IT VAGUE.
If the visual_description describes a state, preserve it exactly.
DO NOT improve it.

OUTPUT FORMAT (STRICT JSON ONLY):
{
  "scene_index": number,
  "image_prompt_body": string
}
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
    canon = storyboard.get("canon", {})
    canon_character = canon.get("character_description", "").strip()
    canon_style = canon.get("style", "").strip()

    # -------- Prompt generation pass --------
    pg_input = {
        "units": storyboard["scenes"],
    }
    
    promptgen_scenes = []

    for unit in pg_input["units"]:
        unit = dict(unit)
        unit["includes_narrator"] = unit.get("includes_narrator", True)

        original_visual_description = unit.get("visual_description", "").strip()
        clean_visual_description = strip_audio_language(original_visual_description)

        # If audio stripping nukes the entire description, fall back to original
        if not clean_visual_description:
            clean_visual_description = original_visual_description

        single_pg_input = {
            "scene": {
                "scene_index": unit["scene_index"],
                "visual_description": clean_visual_description,
                "includes_narrator": unit.get("includes_narrator", True)
            }
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

        # Normalize possible shapes
        if isinstance(parsed, dict) and (
            "image_prompt_body" in parsed or "image_prompt" in parsed
        ):
            image_prompt_body = parsed.get("image_prompt_body") or parsed.get("image_prompt")

        elif isinstance(parsed, dict) and "scene" in parsed and isinstance(parsed["scene"], dict):
            image_prompt_body = (
                parsed["scene"].get("image_prompt_body")
                or parsed["scene"].get("image_prompt")
            )

        elif (
            isinstance(parsed, dict)
            and "scenes" in parsed
            and isinstance(parsed["scenes"], list)
            and parsed["scenes"]
        ):
            first = parsed["scenes"][0]
            image_prompt_body = first.get("image_prompt_body") or first.get("image_prompt")

        else:
            raise RuntimeError(
                f"Promptgen returned unusable JSON for scene_index={unit['scene_index']}"
            )


        if not isinstance(image_prompt_body, str) or not image_prompt_body.strip():
            # Deterministic fallback: use cleaned visual_description verbatim
            image_prompt_body = clean_visual_description

            if not image_prompt_body or not image_prompt_body.strip():
                raise RuntimeError(
                    f"Promptgen failed and visual_description is empty for scene_index={unit['scene_index']}\nParsed JSON:\n{json.dumps(parsed, indent=2)}"
                )

        promptgen_scenes.append({
            "scene_index": unit["scene_index"],
            "image_prompt_body": image_prompt_body.strip(),
        })

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

        # Prepend canonical style verbatim to every prompt
        if canon_style:
            image_prompt_body = f"{canon_style}. {image_prompt_body}"

        # Preserve narrator detection logic
        if "narrator" in pg["image_prompt_body"].lower():
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
