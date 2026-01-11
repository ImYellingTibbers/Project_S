import json
import os
from sys import path
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, IMAGE_PLANNER_LLM_MODEL, PROJECT_VERSION


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
    return json.loads(text)
  

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
- One sentence of narration should usually produce 2–4 distinct frames
- Even static environments should be broken into multiple beats
- Do NOT collapse multiple visual moments into one beat just because the story did not advance

--------------------------------
CORE GOAL
--------------------------------
Create a 16–24 beat (2-4 per sentence of the script) visual storyboard that:
- Is engaging to WATCH
- Builds tension visually
- Uses absence, implication, framing, and motion deliberately
- Expresses the story visually across beats, like a cinematographer would create for a short movie
- Prefer to include 1-2 beats that show the protagonist (marked with protagonist_visible = true)

IMPORTANT:
No more than 3 beats are to include the protagonist ever. If this rule is violated, the output will be rejected. 
If there are less than 12 beats, the output will be rejected. 

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
- CRUCIAL: protagonist_visible (true/false), true if the protagonist is visible in the image
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

--------------------------------
IMAGE-TO-VIDEO MOTION DESCRIPTION (REQUIRED)
--------------------------------
For each beat, generate an i2v_prompt_body that follows ALL rules below:
- Describe motion ONLY
  - Do NOT describe people, objects, locations, or appearance
  - Assume the image already contains everything
- Keep it physically subtle
  - Prefer: flicker, drift, sway, breathe, shift
  - Avoid: walk, turn, move across, approach, emerge
- Limit scope
  - One motion idea per beat
  - No compound actions
- Avoid camera choreography
  - No fast pans, spins, or dramatic moves
  - Only subtle drift or stillness
- Avoid emotional abstraction
  - Do NOT say: terrifying, ominous, threatening
  - Motion should imply emotion, not name it
- Keep it short
  - 5–20 words
  - One sentence fragment, not prose
- Assume 2 seconds of animation
  - Motion should make sense in a very short loop

Good examples (these are gold):
- “Subtle candle flame flicker with soft light variation”
- “Very slow shadow movement along the wall”
- “Barely perceptible breathing motion and stillness”
- “Gentle ambient light shift, otherwise motionless”
- “Soft camera drift with minimal environmental movement”

Bad examples (these will break the generator):
- “A man nervously looks around the dark cabin”
- “The camera slowly pans across the room”
- “Shadows crawl ominously toward him”
- “The environment feels tense and unsettling”
- “A disturbing transformation begins”
- (These describe events or emotions, not motion.)

--------------------------------
PROTAGONIST RULES
--------------------------------
- Protagonist is always MALE, and always CAUCASION
- Appears early OR late (or both)
- Most beats should NOT show the protagonist

These rules are STRICT.
- Prefer to include one protagonist_visible beat in beat 1 or 2
- Prefer to include one protagonist_visible beat between the middle and the end

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
- Output VALID JSON ONLY
""".strip()


PROMPTGEN_PROMPT = """
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
GLOBAL RULES
--------------------------------
- The image generator has NO memory
- Every image prompt must be fully self-contained
- Protagonist is ALWAYS male
- If protagonist_visible = true:
  - NO other characters may appear
  - The protagonist MUST be described consistently across all beats
    (same clothing, general body type, age range, and appearance)
- If protagonist_visible = false:
  - Do NOT describe the protagonist at all
  
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
CANON IMAGE (MANDATORY)
--------------------------------
Generate EXACTLY ONE canon protagonist image prompt. 

IMPORTANT
The protagonist is ALWAYS a caucasion adult male between 30 and 45 years old 

Purpose:
- Establish visual identity ONLY
- No story context
- Studio-style portrait
- Neutral or plain background
- Realistic, imperfect appearance
- Non-model, non-glamorous
- EXACTLY one subtle unique facial feature
- This description defines the protagonist for all later beats

--------------------------------
PER-BEAT TASK
--------------------------------
For EACH storyboard beat:
- Generate image_prompt_body (txt2img)
- Generate i2v_prompt_body (mandatory)
- Use the i2v_prompt_body exactly as provided
- Do NOT add new motion ideas
- Do NOT describe appearance, story, or emotion in i2v_prompt_body
- If the beat is protagonist_visible = true, redescribe the character as the canon image is described in consistent clothing before giving the rest of the description of the character/scene, include the race (always caucasion) and build of the protagonist every time you describe them for a beat

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
  "canon": {
    "image_prompt_body": string
  },
  "beats": [
    {
      "beat_id": number,
      "image_prompt_body": string,
      "i2v_prompt_body": string,
    }
  ]
}

- Beats count MUST match storyboard
- beat_id MUST match exactly
- No explanations
- No commentary
- Output JSON only
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
    
    idea_json = json.loads((run_folder / "idea.json").read_text(encoding="utf-8"))   
    winning_idea = idea_json["data"]["winner"]["idea"]
    prep_story = idea_json["data"]["prep_story"]["text"]

    script_json = json.loads((run_folder / "script.json").read_text(encoding="utf-8"))
    script_lines = [l.strip() for l in script_json["script"].splitlines() if l.strip()]
    indexed_script = "\n".join(f"{i}: {l}" for i, l in enumerate(script_lines))
    
    # -------- Storyboard pass --------
    sb_prompt = STORYBOARD_PROMPT.format(
      idea=winning_idea,
      prep_story=prep_story,
      script=indexed_script
    )

    sb_resp = client.chat.completions.create(
        model=IMAGE_PLANNER_LLM_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You design cinematic horror storyboards."},
            {"role": "user", "content": sb_prompt},
        ],
    )

    storyboard = extract_json(sb_resp.choices[0].message.content)

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

    # -------- Prompt generation pass --------
    pg_prompt = PROMPTGEN_PROMPT + "\n\nSTORYBOARD:\n" + json.dumps(storyboard_out, indent=2)

    pg_resp = client.chat.completions.create(
        model=IMAGE_PLANNER_LLM_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You generate precise diffusion prompts."},
            {"role": "user", "content": pg_prompt},
        ],
    )

    promptgen = extract_json(pg_resp.choices[0].message.content)

    # -------- Validation --------
    if not isinstance(promptgen, dict):
        raise RuntimeError(f"Prompt generator returned non-dict JSON: {type(promptgen)}")

    if "beats" not in promptgen or not isinstance(promptgen["beats"], list):
        raise RuntimeError(
            "Prompt generator returned invalid beats array. "
            f"Top-level keys returned: {list(promptgen.keys())}"
        )

    if len(promptgen["beats"]) != len(storyboard_out["beats"]):
        raise RuntimeError(
            f"Beat count mismatch between storyboard ({len(storyboard_out['beats'])}) "
            f"and promptgen ({len(promptgen['beats'])})"
        )

    # -------- Assemble final plan (MERGE storyboard + promptgen) --------
    sb_beats = storyboard_out["beats"]
    pg_beats = promptgen["beats"]

    sb_by_id = {b["beat_id"]: b for b in sb_beats}
    pg_by_id = {b["beat_id"]: b for b in pg_beats}

    missing_in_pg = [bid for bid in sb_by_id.keys() if bid not in pg_by_id]
    missing_in_sb = [bid for bid in pg_by_id.keys() if bid not in sb_by_id]
    if missing_in_pg or missing_in_sb:
        raise RuntimeError(
            f"Beat id mismatch. missing_in_pg={missing_in_pg} missing_in_sb={missing_in_sb}"
        )

    merged_beats = []
    for bid in sorted(sb_by_id.keys()):
        sb = sb_by_id[bid]
        pg = pg_by_id[bid]

        i2v = pg.get("i2v_prompt_body")
        if i2v is None or str(i2v).strip() == "":
            raise RuntimeError(f"Beat {bid} missing i2v_prompt_body")

        merged_beats.append({
          "beat_id": sb["beat_id"],
          "script_lines": sb["script_lines"],
          "protagonist_visible": sb["protagonist_visible"],
          "framing": sb["framing"],
          "location": sb["location"],
          "visual_intent": sb["visual_intent"],
          "storyboard_description": sb["storyboard_description"],
          "image_prompt_body": pg["image_prompt_body"],
          "i2v_prompt_body": pg["i2v_prompt_body"],
        })


    image_plan = {
        "schema": {
            "name": "image_prompt_planner",
            "version": PROJECT_VERSION,
        },
        "run_id": script_json["run_id"],
        "created_at": utc_now_iso(),
        "canon": promptgen.get("canon"),
        "beats": merged_beats,
    }

    (run_folder / "image_plan.json").write_text(
        json.dumps(image_plan, indent=2),
        encoding="utf-8",
    )

    print("Wrote storyboard.json and image_plan.json")


if __name__ == "__main__":
    main()
