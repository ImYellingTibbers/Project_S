from __future__ import annotations

import os
import re
import json
import math
import random
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from openai import OpenAI

# ============================================================
# Bootstrap
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

WORDS_PER_SECOND = 2.4
MIN_WORDS = 18
MAX_WORDS = 40

SENTENCE_END_RE = re.compile(r"[.!?\u2026]")

# ============================================================
# Utilities
# ============================================================

LOCATION_TOKEN = "{{LOCATION}}"
MAIN_CHARACTER_TOKEN = "{{MAIN_CHARACTER}}"
ENTITY_TOKEN = "{{ENTITY}}"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def find_latest_run_folder() -> Path:
    runs = [
        p for p in RUNS_DIR.iterdir()
        if p.is_dir() and (p / "script.json").exists()
    ]
    if not runs:
        raise RuntimeError("No valid run folders found.")
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0]

def load_script_from_run(run_folder: Path) -> str:
    data = read_json(run_folder / "script.json")
    script = data.get("script")
    if not isinstance(script, str) or not script.strip():
        raise RuntimeError("script.json missing valid 'script'")
    return script.strip()

# ============================================================
# Canon
# ============================================================

def _clean_short(s: str, max_len: int = 220) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0].strip()
    return s

def extract_canons_from_script(script: str) -> Tuple[str, str, str, Dict[str, Any]]:
    """
    Returns:
      place: short location anchor
      entity_behavior: short behavior label/summary (safe + flexible for prompting)
      entity_canon: visual description (comic-friendly, consistent, not too specific)
      protagonist_profile: dict with identity traits inferred from script
    """
    system = """
You extract legend anchors and canon descriptions from a third-person urban legend script.

Rules:
- Return ONLY valid JSON (no markdown, no extra text).
- Do NOT add new story facts.
- Keep descriptions concrete, visual, and generator-friendly.
- Entity canon should be detailed enough for consistency, but not so specific that it becomes unrenderable.
- Protagonist_profile should reflect what the script implies (age/gender), but avoid invented biography.

Schema:
{
  "place": "short grounded place",
  "entity_behavior": "short behavior summary (8-20 words)",
  "entity_canon": "visual description of entity (20-45 words), avoid exact numbers/brands",
  "protagonist_profile": {
    "gender": "male|female|unknown",
    "age_range": "teen|20s|30s|40s|50s|60+|unknown",
    "ethnicity": "short descriptor or unknown",
    "build": "short descriptor or unknown",
    "hair": "short descriptor or unknown"
  }
}
""".strip()

    user = f"SCRIPT:\n{script}\n\nExtract canons."
    raw = ollama_chat(OLLAMA_MODEL, system, user)

    # Extract the FIRST valid JSON object only
    matches = re.finditer(r"\{.*?\}", raw, re.DOTALL)
    for m in matches:
        try:
            data = json.loads(m.group())
            break
        except json.JSONDecodeError:
            continue
    else:
        raise RuntimeError(f"Failed to extract valid JSON from model output:\n{raw}")

    place = _clean_short(data.get("place", ""), 80)
    entity_behavior = _clean_short(data.get("entity_behavior", ""), 140)
    entity_canon = _clean_short(data.get("entity_canon", ""), 240)

    prof = data.get("protagonist_profile") or {}
    if not isinstance(prof, dict):
        prof = {}

    # normalize expected keys
    protagonist_profile = {
        "gender": _clean_short(str(prof.get("gender", "unknown")), 24).lower(),
        "age_range": _clean_short(str(prof.get("age_range", "unknown")), 24).lower(),
        "ethnicity": _clean_short(str(prof.get("ethnicity", "unknown")), 48),
        "build": _clean_short(str(prof.get("build", "unknown")), 48),
        "hair": _clean_short(str(prof.get("hair", "unknown")), 64),
    }

    # sane fallbacks
    if not place:
        place = "a rural area"
    if not entity_behavior:
        entity_behavior = "a presence that appears when conditions are met"
    if not entity_canon:
        entity_canon = "a shadowy, humanoid figure with unsettling, wrong proportions"

    return place, entity_behavior, entity_canon, protagonist_profile


def create_main_character_canon(rng: random.Random, prof: Dict[str, Any]) -> str:
    """
    Uses script-derived identity traits (age/gender/etc),
    but randomizes clothing + surface look locally for consistency across images.
    """
    # Identity traits from script (keep short)
    gender = (prof.get("gender") or "unknown").lower()
    age_range = (prof.get("age_range") or "unknown").lower()
    ethnicity = (prof.get("ethnicity") or "unknown").strip()
    build = (prof.get("build") or "unknown").strip()
    hair = (prof.get("hair") or "unknown").strip()

    # Clothing pools (adult-leaning, non-gimmicky, generator-friendly)
    tops = [
        "dark crewneck sweatshirt", "faded black t-shirt", "heather grey hoodie",
        "dark flannel shirt", "plain long-sleeve thermal", "navy work shirt"
    ]
    outerwear = [
        "worn denim jacket", "dark bomber jacket", "black canvas jacket",
        "olive field jacket", "charcoal zip hoodie"
    ]
    bottoms = [
        "dark jeans", "black work pants", "grey jeans", "dark cargo pants"
    ]
    footwear = [
        "scuffed sneakers", "work boots", "dark running shoes"
    ]
    accessories = [
        "a simple wristwatch", "a plain ring", "a small backpack", "a phone in hand", "none"
    ]

    # Build a compact identity phrase
    parts = []

    # Gender/age baseline
    if gender in ("male", "female"):
        gword = "man" if gender == "male" else "woman"
        if age_range != "unknown":
            parts.append(f"an adult {gword} in their {age_range}")
        else:
            parts.append(f"an adult {gword}")
    else:
        parts.append("an adult person")

    # Optional traits (only if not unknown)
    if ethnicity.lower() != "unknown":
        parts.append(ethnicity)
    if build.lower() != "unknown":
        parts.append(build)
    if hair.lower() != "unknown":
        parts.append(hair)

    identity = ", ".join(parts)

    # Randomized outfit (deterministic via rng seed)
    top = rng.choice(tops)
    out = rng.choice(outerwear)
    bot = rng.choice(bottoms)
    shoe = rng.choice(footwear)
    acc = rng.choice(accessories)

    outfit = f"wearing a {top}, a {out}, {bot}, and {shoe}"
    if acc != "none":
        outfit += f", with {acc}"

    return f"{identity}, {outfit}."

# ============================================================
# Local LLM (Ollama)
# ============================================================

def ollama_chat(model: str, system: str, user: str) -> str:
    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]

def extract_place_entity(script: str) -> Tuple[str, str]:
    # Backwards-compatible helper: returns place + entity_behavior
    place, entity_behavior, _entity_canon, _protagonist_profile = extract_canons_from_script(script)
    return place, entity_behavior

# ============================================================
# Chunking
# ============================================================

def chunk_script(script: str) -> List[str]:
    words = script.split()
    chunks = []
    buf = []

    for w in words:
        buf.append(w)
        wc = len(buf)

        if wc >= MIN_WORDS:
            if SENTENCE_END_RE.search(w) or wc >= MAX_WORDS:
                chunks.append(" ".join(buf))
                buf = []

    if buf:
        chunks.append(" ".join(buf))
        
    # Merge last chunk if too short
    if len(chunks) >= 2 and len(chunks[-1].split()) < MIN_WORDS:
        chunks[-2] = chunks[-2] + " " + chunks[-1]
        chunks.pop()

    return chunks

def images_for_chunk(word_count: int) -> int:
    seconds = word_count / WORDS_PER_SECOND
    if word_count < 18:
        return 1
    if word_count <= 40:
        return 2
    return 3

# ============================================================
# GPT-4o Image Prompting
# ============================================================

def gpt_image_prompts(
    script: str,
    chunk: str,
    place: str,
    entity_behavior: str,
    entity_canon: str,
    main_character_canon: str,
    prior_prompts: List[str],
    count: int,
    is_opening: bool,
) -> List[Dict[str, str]]:

    system = """
You generate STRICTLY literal, physically depictable image prompts
for a third-person urban legend horror short.

ABSOLUTE RULES (NON-NEGOTIABLE):

1. Every image MUST depict something that can be physically seen.
   - No mood, no tone, no atmosphere, no symbolism.
   - No emotions, no vibes, no implication language.

2. Every image MUST clearly show:
   - WHO is present (people, entity, or both)
   - WHAT is happening (a visible action or state)
   - WHERE it is happening (basic physical setting)

3. If people are present, they MUST be described as visible figures,
   not vague silhouettes, unless the script explicitly implies distance or obstruction.

4. If the entity is present or being demonstrated:
   - Show the entity DOING something physically observable
   If the entity is visible:
    - Use the placeholder {{ENTITY}}
    - Do NOT describe the entity in detail

5. DO NOT describe:
   - fear, dread, tension, unease
   - cinematic framing
   - lighting mood
   - symbolism
   - anything abstract or interpretive

6. DO NOT add story information not explicitly present in the script.

7. Each image prompt describes EXACTLY ONE moment in time.

FORMAT RULES:
- Plain, literal language
- One paragraph per image
- No adjectives that imply mood or emotion
- Describe only what is visible in the frame

PLACEHOLDER RULES (MANDATORY):

- If a physical location is visible, use {{LOCATION}}.
- If the main encounter character is visible, use {{MAIN_CHARACTER}}.
- If the entity is visible, use {{ENTITY}}.

DO NOT describe these directly.
DO NOT paraphrase them.
DO NOT partially describe them.

Only use placeholders.

Return ONLY valid JSON:

{
  "images": [
    { "prompt": "...", "source_detail": "..." }
  ]
}
""".strip()

    context = "\n".join(prior_prompts[-6:])

    opening_directive = ""
    if is_opening:
        opening_directive = (
            "OPENING IMAGE DIRECTIVE:\n"
            "- This is the FIRST image of the video.\n"
            "- Show the THREAT described by the warning in the script.\n"
            "- Do NOT explain it.\n"
            "- Do NOT show consequences yet.\n"
            "- The image must make the rule feel necessary by showing the condition itself.\n"
            "- The location MUST be represented using {{LOCATION}}.\n\n"
        )

    user = f"""
{opening_directive}
SCRIPT CONTEXT:
{script}

ANCHORS:
Place: {place}
Entity behavior: {entity_behavior}
Entity canon: {entity_canon}
Main encounter character canon: {main_character_canon}

RECENT IMAGES:
{context}

CURRENT SCRIPT CHUNK:
{chunk}

STORY PHASE GUIDANCE:

- If the script describes a WARNING or RULE:
  Show the THREAT itself (fog, sound, signal, object, condition).
  Do NOT show victims yet.

- If the script explains the LEGEND or ENTITY:
  Show the entity or phenomenon exactly as it is being described.

- If the script tells the story of a PERSON encountering the entity:
  Show the main encounter character and the entity in the same scene,
  using the established character and entity descriptions.

TASK:
Generate {count} distinct image prompts.

Each prompt MUST explicitly describe:
- WHO is visible in the image
- WHAT is physically happening
- WHAT the threat or entity is doing, if present

Do NOT describe anything that cannot be directly seen.
Do NOT imply outcomes.

Each image must focus on ONE observable detail only.
Do NOT combine multiple story beats into a single image.
""".strip()

    for attempt in range(2):
        try:
            resp = openai_client.responses.create(
                model="gpt-4o",
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.7,
            )

            text = getattr(resp, "output_text", None)
            if not text:
                text = ""
                for item in getattr(resp, "output", []) or []:
                    # Some SDK versions surface raw output text directly
                    if getattr(item, "type", None) == "output_text":
                        text += getattr(item, "text", "") or ""
                    # Others wrap it in message -> content -> output_text
                    if getattr(item, "type", None) == "message":
                        for c in getattr(item, "content", []) or []:
                            if getattr(c, "type", None) == "output_text":
                                text += getattr(c, "text", "") or ""


            # Extract the first JSON object from the model output (handles accidental preface/codefence text)
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError(f"No JSON object found in model output: {text[:200]}")

            payload = json.loads(text[start:end + 1])
            images = payload.get("images")

            if not isinstance(images, list) or not images:
                raise ValueError(f"JSON parsed but 'images' missing/invalid: keys={list(payload.keys())}")

            return images

        except Exception:
            pass  # silent retry

    # only reached if BOTH attempts fail
    return [{
        "prompt": f"POV environmental shot implied by the following moment: {chunk[:120]}",
        "source_detail": "fallback_from_chunk"
    }]
    

# ============================================================
# Local LLM – Anomaly Detection
# ============================================================

def detect_visual_anomaly(
    base_prompt: str,
    script_context: str,
    place: str,
    *,
    is_opening: bool,
    escalation_level: int,
) -> str:
    system = """
You generate a SINGLE visual anomaly that is STRICTLY ANCHORED to the current image prompt.

CRITICAL RULE (NON-NEGOTIABLE):
- You may ONLY alter or modify objects that already appear in the IMAGE PROMPT or SCRIPT CONTEXT.
- You may NOT introduce new objects, furniture, or scene elements.

PRIMARY GOAL:
Create a subtle visual inconsistency that feels wrong immediately,
but still belongs naturally to the scene described.

WHAT AN ANOMALY IS:
A small, visible mutation of an existing object’s:
- position
- orientation
- state
- symmetry
- completeness

VISIBILITY RULE:
- The anomaly must be noticeable only on second glance.
- If it would immediately explain the threat, it is TOO STRONG.
- Prefer “off-normal” over “clearly/obviously wrong”.

GOOD EXAMPLES (FORMAT ONLY):
- “The vent cover is slightly ajar”
- “The door is not fully closed”
- “The phone screen is on but unreadable”
- “The reflection does not match the angle”
- “The stain extends farther than before”

BAD EXAMPLES (NEVER DO THIS):
- Adding new objects not mentioned
- Abstract phrases like “evidence” or “presence”
- Emotional or interpretive language
- Horror tropes or supernatural elements
- Generic props like chairs unless already present

OPENING IMAGE RULE:
If this is the opening image, prefer anomalies that:
- Interrupt a normal expectation
- Suggest something mid-change
- Look accidental rather than staged

OUTPUT RULES:
- ONE short sentence.
- Max 12 words.
- Describe only what is visibly wrong.
- Or return exactly: NONE
"""

    user = f"""
PLACE:
{place}

SCRIPT CONTEXT:
{script_context}

IMAGE PROMPT:
{base_prompt}

ESCALATION LEVEL:
{escalation_level}

IS OPENING IMAGE:
{is_opening}

TASK:
Determine the most effective subtle visual anomaly for this image.
""".strip()

    raw = ollama_chat(OLLAMA_MODEL, system, user).strip()

    # Hard guardrails
    if not raw or raw.upper() == "NONE":
        return "NONE"

    # Safety clamp: keep it short and concrete
    return raw.split(".")[0][:120]


# ============================================================
# Post-processing
# ============================================================

def inject_location(prompt: str, location: str) -> Tuple[str, bool]:
    uses_location = LOCATION_TOKEN in prompt
    if uses_location:
        prompt = prompt.replace(LOCATION_TOKEN, location)
    return prompt, uses_location


def inject_main_character(prompt: str, character_canon: str) -> Tuple[str, bool]:
    uses_character = MAIN_CHARACTER_TOKEN in prompt
    if uses_character:
        prompt = prompt.replace(MAIN_CHARACTER_TOKEN, character_canon)
    return prompt, uses_character


def inject_entity(prompt: str, entity_canon: str) -> Tuple[str, bool]:
    uses_entity = ENTITY_TOKEN in prompt
    if uses_entity:
        prompt = prompt.replace(ENTITY_TOKEN, entity_canon)
    return prompt, uses_entity

# ============================================================
# Main
# ============================================================

def main():
    rng = random.Random(42)

    run = find_latest_run_folder()
    script = load_script_from_run(run)

    place, entity_behavior, entity_canon, protagonist_profile = extract_canons_from_script(script)
    main_character_canon = create_main_character_canon(rng, protagonist_profile)

    chunks = chunk_script(script)

    prior_prompts: List[str] = []
    out_chunks = []
    current_location = place

    for idx, chunk in enumerate(chunks):
        past_script = " ".join(chunks[: idx + 1])

        next_chunk = ""
        if idx + 1 < len(chunks):
            next_chunk = chunks[idx + 1]

        script_context = past_script
        if next_chunk:
            script_context += "\n\nUPCOMING (FORESHADOW ONLY):\n" + next_chunk
        wc = len(chunk.split())
        img_count = images_for_chunk(wc)

        images = gpt_image_prompts(
            script_context,
            chunk,
            place,
            entity_behavior,
            entity_canon,
            main_character_canon,
            prior_prompts,
            img_count,
            is_opening=(idx == 0),
        )

        processed = []
        for img in images:
            p = img["prompt"]

            # Location: only inject if placeholder is present
            p, used_loc = inject_location(p, current_location)

            # Main character
            p, used_char = inject_main_character(p, main_character_canon)

            # Entity
            p, used_ent = inject_entity(p, entity_canon)
            
            if used_loc:
                current_location = location

            anomaly = detect_visual_anomaly(
                base_prompt=p,
                script_context=chunk,
                place=place,
                is_opening=(idx == 0),
                escalation_level=3 if idx == 0 else min(3, idx + 1),
            )

            if anomaly != "NONE":
                p = f"{p}, subtle irregularity: {anomaly}"

            processed.append({
                "prompt": p,
                "uses_location": used_loc,
                "uses_main_character": used_char,
                "uses_entity": used_ent,
                "uses_anomaly": anomaly != "NONE",
                "anomaly": None if anomaly == "NONE" else anomaly,
            })

            prior_prompts.append(
                p.split(",")[0][:120].lower()
            )

        out_chunks.append({
            "chunk_index": idx,
            "script_text": chunk,
            "word_count": wc,
            "image_prompts": processed,
        })

    output = {
        "place": place,
        "entity_behavior": entity_behavior,
        "entity_canon": entity_canon,
        "main_character_profile": protagonist_profile,
        "main_character_canon": main_character_canon,
        "chunks": out_chunks,
    }

    write_json(run / "script_with_prompts.json", output)
    print(f"[ok] Wrote script_with_prompts.json → {run}")

if __name__ == "__main__":
    main()
