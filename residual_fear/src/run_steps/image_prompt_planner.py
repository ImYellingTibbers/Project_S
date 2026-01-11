import json
import time
import os
import random
from sys import path
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, STORYBOARD_LLM_MODEL, PROJECT_VERSION, USE_MICROBEATS
from src.run_steps.microbeat_generator import main as generate_microbeats
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
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Invalid JSON from LLM:\n{text[:500]}"
        ) from e
        
        
STYLE_ANCHOR = (
    "cinematic horror still, "
    "photorealistic, grounded environment, "
    "low-key lighting, high contrast, "
    "muted color palette, deep shadows, "
    "subtle film grain, shallow depth of field"
)

LOCATION_ANCHORS = [
    "single overhead light source",
    "uneven wall texture",
    "narrow architectural proportions",
    "darkened corners and edges",
    "visible surface wear and decay",
]
  

STORYBOARD_PROMPT = """
You are a VISUAL STORYBOARD PLANNER for short-form horror videos.

Your job is to design a visually compelling horror short that SHOWS the story, providing a beat by beat story that follows the script's story and creates visuals that tell the narrative story through images. You will be given the initial idea, a brief prep story that helped create the script, and the final script. The script should be your source of truth, use the idea and prep story only for additional context.

Think like a cinematographer and editor.

--------------------------------
INPUT
--------------------------------
IDEA (HIGH-LEVEL CONTEXT)
{idea}

PREP STORY (TONE / MOOD REFERENCE)
{prep_story}

SCRIPT (PRIMARY SOURCE)
SCRIPT (indexed lines):
{script}

IMPORTANT BEAT DENSITY RULE (CRITICAL):

A "beat" is a SINGLE VISUAL MOMENT, not a story beat.

You MUST:
- Create multiple beats within the same narrative moment
- Use camera distance, framing, angle, foreground/background, or lighting changes
  to justify additional beats even when story context is unchanged
- Prefer SMALL visual changes over fewer large beats

Think like this:
- One NARRATIVE MOMENT may produce multiple visual frames when visually justified
- Even static environments should be broken into multiple beats
- Do NOT collapse multiple visual moments into one beat just because the story did not advance

--------------------------------
CORE GOAL
--------------------------------
Create a {min_beats}–{max_beats} beat visual storyboard that:
- Covers the ENTIRE script:
  - Every script line index MUST appear in exactly one beat’s script_lines array
- Beat count MUST remain within {min_beats}–{max_beats}
- Do NOT create one beat per line unless absolutely necessary
- Prefer grouping multiple short script lines into a single beat when they belong to the same visual moment
  - If line_count <= {max_beats}, you may add extra beats on some lines (multiple beats can share the same line_index).
- Is engaging to WATCH
- Builds tension visually
- Uses absence, implication, framing, and visual change deliberately
- Expresses the story visually across beats, like a cinematographer would create for a short movie

When generating the first beat for a short, specify a **hook intention** that includes:
- pattern interrupt: unexpected visual element
- implied tension or partial threat (no full creature reveal yet)
- high contrast visual cues
This should be designed to grab attention in the first 1–3 seconds.

IMPORTANT:
Script alignment is IMPORTANT for beat density, but beats should not be literal reenactments.

--------------------------------
OUTPUT
--------------------------------
Return a JSON object with:
- schema
- run_id
- created_at
- beats (ordered)

--------------------------------
EACH BEAT MUST INCLUDE
--------------------------------
- beat_id (1-based, sequential)
- script_lines (array of script line indexes that match the beat)
- framing ("wide" | "medium" | "close")

- location:
  - canonical (single stable location name)
  - context (how this space appears in THIS beat)

- visual_intent:
  - what tension, information, or unease this beat provides
  - overall vibe of the beat

- storyboard_description:
  - cinematic description of what is visible
  - written like a shot list, not a prompt
  
- DO NOT overexplain the beat

SCRIPT LINE ALIGNMENT (CRITICAL FOR TIMING)

- Each beat MUST reference one or more CONTIGUOUS script line indexes
- "script_lines" must be an array of integers in ascending order
- Each script line index MUST appear in exactly one beat
- Before finalizing, mentally verify that EVERY script line index from 0 to {line_count_minus_1} appears in the beats
- Missing even ONE line index is a fatal error
- Beats should represent VISUAL MOMENTS, not sentence boundaries
- Multiple short script lines that express the same idea SHOULD be grouped into a single beat
- Beat boundaries should align with:
  - idea shifts
  - location changes
  - emotional escalation
- NOT punctuation or line breaks

--------------------------------
RULES - CRUCIAL
--------------------------------
- Avoid boring shots
- Avoid literal sentence reenactments
- Environment-only shots must imply tension or change
- No explanations
- Give simple descriptions of each beat, do not over explain
- DO NOT create abstract beats
- DO NOT create beats with hands
- Humans must NEVER appear in any beat
- No living real-world beings of any kind
- No humans, animals, pets, insects, birds, or wildlife
- Supernatural, demonic, monstrous, or impossible creatures ARE allowed
- If a creature is shown, it must clearly be non-real and non-natural
- No faces, bodies, silhouettes, reflections, or shadows of people
- No hands, limbs, or implied human presence
- Environments, objects, spaces, and absence must carry the story
- Visuals should follow the emotional and narrative FLOW of the story,
  not literal sentence reenactments
- Output VALID JSON ONLY
""".strip()


PROMPTGEN_PROMPT = """
TASK LOCK (MANDATORY)

You are NOT allowed to:
- summarize
- explain
- restate
- describe the storyboard
- list beats in prose
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
- Humans must NEVER appear in images
- No real-world living beings of any kind
- Do NOT include animals, pets, insects, birds, or wildlife
- Supernatural or impossible creatures are allowed
- Creatures must not resemble real animals
- Do NOT describe people, faces, bodies, silhouettes, shadows, reflections, or hands
- Do NOT imply human presence through clothing, mirrors, or movement
- Focus on environments, objects, lighting, weather, decay, stillness, and space
- Prefer empty environments over object-focused shots
- If an object appears, it should be static and partially framed
- Avoid first-person or implied observer viewpoints

For the very first visual units (single beat or several microbeats):
- Add a **hook modifier**: describe a visually arresting element that creates immediate curiosity or tension.
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
- Keep prompts simple, make it dead easy for the AI image generator to create the desired beat

--------------------------------
SETTING CONSISTENCY
--------------------------------
- Maintain consistent location identity across beats
- Re-describe the setting simply from different angles or distances
- Do NOT add new environmental elements unless implied by the storyboard

--------------------------------
PER-UNIT TASK
--------------------------------
For EACH input unit:
- Generate image_prompt_body (txt2img) using ALL provided fields
- If unit_type is "microbeat", generate ONE image for that microbeat

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

If camera_distance is provided:
- Explicitly describe framing distance

If camera_angle is provided:
- Explicitly describe camera angle

If distortion_level is provided:
- Level 0–1: normal perspective
- Level 2–3: subtle perspective warping
- Level 4+: obvious spatial distortion

--------------------------------
OUTPUT FORMAT (STRICT)
--------------------------------
{
  "beats": [
    {
      "beat_id": number,
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
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")

    client = OpenAI(api_key=api_key)
    run_folder = find_latest_run_folder()
    
    idea_path = run_folder / "idea.json"
    if not idea_path.exists():
        idea_path = run_folder / "idea_generator.json"

    idea_json = json.loads(idea_path.read_text(encoding="utf-8"))
    
    vo_json = json.loads((run_folder / "vo.json").read_text(encoding="utf-8"))

    vo_by_line = {
        l["line_index"]: l
        for l in vo_json["timing"]["lines"]
    }

    winning_idea = idea_json["data"]["winner"]["idea"]
    prep_story = idea_json["data"]["winner"].get("prep_story", {}).get("text", "")

    script_json = json.loads((run_folder / "script.json").read_text(encoding="utf-8"))
    script_lines = [l.strip() for l in script_json["script"].splitlines() if l.strip()]
    indexed_script = "\n".join(f"{i}: {l}" for i, l in enumerate(script_lines))
    
    # -------- Storyboard pass --------
    line_count = len(script_lines)

    # -------- Beat budgeting (VO-duration driven) --------
    total_seconds = vo_json["timing"]["total_duration_seconds"]

    # Target ~1 beat every 2.5 seconds
    target_beats = max(8, int(total_seconds / 2.5))

    min_beats = target_beats
    max_beats = int(target_beats * 1.4)


    sb_prompt = STORYBOARD_PROMPT.format(
        idea=winning_idea,
        prep_story=prep_story,
        script=indexed_script,
        min_beats=min_beats,
        max_beats=max_beats,
        line_count=line_count,
        line_count_minus_1=line_count - 1,
    )


    sb_resp = client.chat.completions.create(
        model=STORYBOARD_LLM_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You design cinematic horror storyboards."},
            {"role": "user", "content": sb_prompt},
        ],
    )

    storyboard = extract_json(sb_resp.choices[0].message.content)

    # ---- Coverage retry (single retry only) ----
    covered = sorted({
        i
        for b in storyboard.get("beats", [])
        for i in b.get("script_lines", [])
        if isinstance(i, int)
    })

    missing = [i for i in range(line_count) if i not in covered]

    if missing:
        print(
            "[image_prompt_planner] Storyboard missing lines "
            f"{missing}. Retrying storyboard once."
        )

        sb_resp = client.chat.completions.create(
            model=STORYBOARD_LLM_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You design cinematic horror storyboards."},
                {"role": "user", "content": sb_prompt + "\n\nIMPORTANT: The previous attempt FAILED because some script line indexes were missing. Ensure FULL coverage this time."},
            ],
        )

        storyboard = extract_json(sb_resp.choices[0].message.content)

    
    for beat in storyboard.get("beats", []):
        if not beat.get("script_lines"):
            continue

        lines = beat["script_lines"]

        if not all(isinstance(i, int) for i in lines):
            raise RuntimeError(f"Beat {beat.get('beat_id')} has invalid script_lines")

        start_line = lines[0]
        end_line = lines[-1]


        if start_line not in vo_by_line or end_line not in vo_by_line:
            raise RuntimeError(
                f"Storyboard references missing VO lines: start={start_line}, end={end_line}"
            )


        start_vo = vo_by_line[start_line]
        end_vo = vo_by_line[end_line]

        beat["timing_scope"] = {
            "start_line": start_line,
            "end_line": end_line,
            "line_start": start_vo["start_time_seconds"],
            "line_end": end_vo["end_time_seconds"],
            "line_duration": end_vo["end_time_seconds"] - start_vo["start_time_seconds"],
        }
        
        # -------- Pacing metadata (deterministic, no LLM) --------
        total_duration = vo_json["timing"]["total_duration_seconds"]

        progress_ratio = beat["timing_scope"]["line_start"] / total_duration

        if progress_ratio < 0.25:
            pacing_zone = "early"
        elif progress_ratio < 0.70:
            pacing_zone = "middle"
        else:
            pacing_zone = "late"

        beat["pacing"] = {
            "zone": pacing_zone,
            "story_progress_ratio": round(progress_ratio, 3),
        }
        
        if pacing_zone == "early":
            beat["camera_bias"] = "wide"
        elif pacing_zone == "middle":
            beat["camera_bias"] = "medium"
        else:
            beat["camera_bias"] = "close"

        
    # -------- Coverage validation (CRITICAL) --------
    covered = sorted({
        i
        for b in storyboard.get("beats", [])
        for i in b.get("script_lines", [])
        if isinstance(i, int)
    })

    missing = [i for i in range(len(script_lines)) if i not in covered]
    if missing:
        raise RuntimeError(
            "Storyboard did not cover the full script. "
            f"Missing script line indexes: {missing}. "
            "Fix the storyboard prompt/beat budget so every line_index has at least one beat."
        )
        
    # -------- Assign persistent location anchors --------
    location_anchor_map = {}

    for beat in storyboard.get("beats", []):
        loc_key = beat["location"]["canonical"]
        if loc_key not in location_anchor_map:
            location_anchor_map[loc_key] = random.choice(LOCATION_ANCHORS)
        beat["location_anchor"] = location_anchor_map[loc_key]

    storyboard_out = {
        "schema": {"name": "storyboard", "version": PROJECT_VERSION},
        "run_id": script_json["run_id"],
        "created_at": utc_now_iso(),
        "beats": storyboard["beats"],
    }

    (run_folder / "storyboard.json").write_text(
        json.dumps(storyboard_out, indent=2),
        encoding="utf-8",
    )
    # -------- Microbeat generation (AFTER storyboard artifact exists) --------
    microbeat_plan = None
    if USE_MICROBEATS:
        microbeat_path = run_folder / "microbeat_plan.json"
        generate_microbeats()

        microbeat_plan = json.loads(
            microbeat_path.read_text(encoding="utf-8")
        )
        
        # -------- Microbeat density sanity check (CRITICAL) --------
        total_seconds = vo_json["timing"]["total_duration_seconds"]

        microbeat_count = sum(
            len(b["microbeats"]) for b in microbeat_plan.get("beats", [])
        )

        # Target ~1 microbeat per second (allow variance)
        min_microbeats = int(total_seconds * 0.75)
        max_microbeats = int(total_seconds * 1.5)

        if microbeat_count < min_microbeats:
            print(
                "[image_prompt_planner][warn] "
                "Low microbeat density detected. "
                f"microbeats={microbeat_count}, "
                f"expected~{min_microbeats}, "
                f"vo_seconds={total_seconds:.1f}. "
                "Proceeding with scaled image durations."
            )

        if microbeat_count > max_microbeats:
            raise RuntimeError(
                f"Too many microbeats for VO duration. "
                f"microbeats={microbeat_count}, "
                f"max_allowed={max_microbeats}, "
                f"vo_seconds={total_seconds:.1f}"
            )



    # -------- Prompt generation pass --------
    if USE_MICROBEATS:
        pg_units = []
        for beat in microbeat_plan["beats"]:
            parent = next(
                b for b in storyboard_out["beats"]
                if b["beat_id"] == beat["beat_id"]
            )

            for m in beat["microbeats"]:
                pg_units.append({
                    "unit_type": "microbeat",
                    "beat_id": beat["beat_id"],
                    "microbeat_id": m["microbeat_id"],
                    "timing_scope": parent["timing_scope"],
                    "framing": parent["framing"],
                    "camera_bias": parent.get("camera_bias"),
                    "location": parent["location"],
                    "visual_intent": parent["visual_intent"],
                    "storyboard_description": parent["storyboard_description"],
                    "visual_adjustment": m["visual_adjustment"],
                    "pacing": parent["pacing"],
                    "camera_distance": m.get("camera_distance"),
                    "camera_angle": m.get("camera_angle"),
                    "distortion_level": m.get("distortion_level"),
                })


        pg_input = {
            "mode": "microbeats",
            "units": pg_units,
        }
    else:
        pg_input = {
            "mode": "beats",
            "units": storyboard_out["beats"],
        }

    pg_prompt = (
        PROMPTGEN_PROMPT
        + "\n\nINPUT:\n"
        + json.dumps(pg_input, indent=2)
        + "\n\nOUTPUT:\n{"
    )

    prompt = (
        "SYSTEM:\n"
        "You are a deterministic image-prompt compiler.\n"
        "You do not explain, summarize, analyze, or comment.\n"
        "You ONLY transform structured input into structured JSON output.\n"
        "If you cannot comply exactly, output nothing.\n\n"
        + pg_prompt
    )


    promptgen_beats = []

    for unit in pg_input["units"]:
        single_pg_input = {
            "mode": pg_input["mode"],
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
            + "\n\nOUTPUT:\n{"
        )

        raw = call_llm(single_prompt)

        if not raw or not raw.strip():
            raw = call_llm(single_prompt)  # single retry only

        parsed = extract_json(raw)

        if "beats" not in parsed or not parsed["beats"]:
            raise RuntimeError(
                f"Promptgen returned no beats for beat_id={unit.get('beat_id')}"
            )

        # Take the first beat only (promptgen is single-unit scoped)
        promptgen_beats.append(parsed["beats"][0])


        # CRITICAL: throttle GPU + Ollama
        time.sleep(0.05)

    promptgen = {"beats": promptgen_beats}



    # -------- Validation --------
    if not isinstance(promptgen, dict):
        raise RuntimeError(f"Prompt generator returned non-dict JSON: {type(promptgen)}")

    if "beats" not in promptgen or not isinstance(promptgen["beats"], list):
        raise RuntimeError(
            "Prompt generator returned invalid beats array. "
            f"Top-level keys returned: {list(promptgen.keys())}"
        )


    # -------- Assemble final plan (MERGE storyboard + promptgen) --------
    sb_beats = storyboard_out["beats"]
    pg_beats = promptgen["beats"]

    # In microbeat mode, promptgen returns MANY rows per beat_id.
    # Beat-level 1:1 validation is invalid here.
    if not USE_MICROBEATS:
        sb_by_id = {b["beat_id"]: b for b in sb_beats}
        pg_by_id = {b["beat_id"]: b for b in pg_beats}

        missing_in_pg = [bid for bid in sb_by_id.keys() if bid not in pg_by_id]
        missing_in_sb = [bid for bid in pg_by_id.keys() if bid not in sb_by_id]
        if missing_in_pg or missing_in_sb:
            raise RuntimeError(
                f"Beat id mismatch. missing_in_pg={missing_in_pg} missing_in_sb={missing_in_sb}"
            )


    merged_beats = []

    for unit, pg in zip(pg_input["units"], promptgen["beats"]):
        anchor = unit.get("location_anchor")
        merged = {
            "image_prompt_body": f"{STYLE_ANCHOR}, {anchor}. {pg['image_prompt_body']}"
        }

        if USE_MICROBEATS:
            merged.update({
                "unit_type": "microbeat",
                "beat_id": unit["beat_id"],
                "camera_bias": unit.get("camera_bias"),
                "microbeat_id": unit["microbeat_id"],
                "timing_scope": unit["timing_scope"],
                "framing": unit["framing"],
                "location": unit["location"],
                "visual_intent": unit["visual_intent"],
                "storyboard_description": unit["storyboard_description"],
                "visual_adjustment": unit["visual_adjustment"],
                "pacing": unit["pacing"],
            })

            if unit.get("pacing", {}).get("zone") == "late":
                merged["image_prompt_body"] += ", partial obstruction in foreground"
        else:
            merged.update({
                "unit_type": "beat",
                "beat_id": unit["beat_id"],
                "script_lines": unit["script_lines"],
                "framing": unit["framing"],
                "location": unit["location"],
                "visual_intent": unit["visual_intent"],
                "storyboard_description": unit["storyboard_description"],
                "timing_scope": unit.get("timing_scope"),
            })

        merged_beats.append(merged)

    image_plan = {
        "schema": {
            "name": "image_prompt_planner",
            "version": PROJECT_VERSION,
        },
        "run_id": script_json["run_id"],
        "created_at": utc_now_iso(),
        # canon intentionally omitted (no humans allowed)
        "beats": merged_beats,
    }

    (run_folder / "image_plan.json").write_text(
        json.dumps(image_plan, indent=2),
        encoding="utf-8",
    )

    print("Wrote storyboard.json and image_plan.json")


if __name__ == "__main__":
    main()
