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

def get_story_phase(chunk: str, *, witness_locked: bool, is_opening: bool) -> str:
    if is_opening:
        return "HOOK"
    if witness_locked:
        return "WITNESS"
    return "LEGEND"

# ============================================================
# Canon
# ============================================================


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

def extract_entity_canon(script: str, entity_name: str) -> str:
    system = """
You extract a SINGLE, reusable visual description of a folklore entity.

Rules:
- Base the description ONLY on the script.
- Do NOT invent new traits.
- Keep it purely visual.
- One sentence.
- No metaphors, no poetry.

Return ONLY plain text.
""".strip()

    user = f"""
ENTITY NAME:
{entity_name}

SCRIPT:
{script}

TASK:
Describe what the entity visibly looks like.
""".strip()

    return ollama_chat(OLLAMA_MODEL, system, user).strip()

def extract_witness_canon(script_chunk: str) -> str:
    system = """
You extract a reusable visual description of a human witness.

Rules:
- Adult only.
- Prefer male if unspecified.
- Specific but neutral, everyday clothing (no logos, no uniforms, no bright colors).
- Two sentences. First sentence describes the person (age range, gender, general build), second sentence describes their clothing (i.e. red hoodie, black pants, baseball cap/beanie). Clothing must make sense in the setting of the script.
- No personality traits.
- No story events.

Return ONLY plain text.
""".strip()

    user = f"""
SCRIPT SEGMENT:
{script_chunk}

TASK:
Describe what the witness looks like visually.
""".strip()

    return ollama_chat(OLLAMA_MODEL, system, user).strip()

def extract_place_entity(script: str) -> Tuple[str, str]:
    system = """
You extract grounded story anchors from an urban legend or folklore horror script.

Rules:
- Return ONLY valid JSON.
- Keep outputs short, concrete, non-poetic.
- Do NOT add new story facts.
- Entity may be named, described, or physically characterized if present in the legend.
- Entity description must be stable and reusable across images.
- Monetization-safe.

Schema:
{
  "place": "...",
  "entity": "..."
}
""".strip()

    user = f"SCRIPT:\n{script}\n\nExtract anchors."
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
    
    return data["place"], data["entity"]

def is_witness_chunk_llm(script_so_far: str, chunk: str) -> bool:
    system = """
You determine whether a story has transitioned into following
a specific human witness’s experience.

Rules:
- Return ONLY one of: YES or NO
- YES only if a specific person is now being followed
- General legend exposition = NO
- Vague or anonymous warnings = NO
- Once YES, future chunks will remain YES
- Do NOT guess or assume
""".strip()

    user = f"""
STORY SO FAR:
{script_so_far}

CURRENT CHUNK:
{chunk}

QUESTION:
Does this chunk introduce a specific human witness whose experience is now being narrated?
""".strip()

    raw = ollama_chat(OLLAMA_MODEL, system, user).strip().upper()
    return raw == "YES"

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
    entity: str,
    prior_prompts: List[str],
    count: int,
    *,
    phase: str,
) -> List[Dict[str, str]]:

    system = """
You generate concise image prompts for an urban legend / folklore horror short.

CRITICAL STORY RULE:
- Images must ONLY depict information that is already known or being described at THIS moment in the narration.
- Do NOT show future events, future victims, or outcomes that have not been revealed yet.

VISUAL TONE:
- Illustrated folklore style, not photorealistic.
- Dark, graphic-novel or storybook horror feel.
- Simple compositions with strong shapes and shadows.
- Grounded, literal visuals — no abstract or symbolic imagery.

STORY FLOW GUIDANCE:
- Early images establish the warning or threat.
- Middle images show how the legend appears or behaves.
- Later images may show a person encountering the legend, if the script does.

CHARACTER GUIDANCE:
- Adults preferred.
- If a recurring entity or witness appears, keep their look consistent.
- Use placeholders when appropriate:
  {{ENTITY_CANON}}, {{WITNESS_CANON}}

COMPOSITION RULES:
- One clear subject per image.
- Prefer people or places over empty atmosphere.
- Everything shown should plausibly exist in the scene.

Return ONLY a single JSON object (no markdown, no code fences, no extra text):
{
  "images": [
    { "prompt": "...", "source_detail": "..." }
  ]
}
""".strip()

    context = "\n".join(prior_prompts[-6:])

    user = f"""
STORY PHASE:
{phase}

SCRIPT CONTEXT:
{script}

ANCHORS:
Place: {place}
Entity: {entity}

RECENT IMAGES:
{context}

CURRENT SCRIPT CHUNK:
{chunk}

TASK:
Generate {count} distinct image prompts that visually advance this moment.

Each image must focus on ONE observable, physical detail.

MANDATORY:
- Every image must include at least one of:
  - the place
  - the entity
  - a human figure
- No symbolic, abstract, or metaphorical imagery
- No “visions”, “dreamlike”, or internal imagery
- Everything shown must plausibly exist in the scene
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

def inject_canon(prompt: str, *, entity: str | None, witness: str | None) -> str:
    if entity and "{{ENTITY_CANON}}" in prompt:
        prompt = prompt.replace("{{ENTITY_CANON}}", entity)
    if witness and "{{WITNESS_CANON}}" in prompt:
        prompt = prompt.replace("{{WITNESS_CANON}}", witness)
    return prompt

# ============================================================
# Main
# ============================================================

def main():
    rng = random.Random(42)

    run = find_latest_run_folder()
    script = load_script_from_run(run)

    place, entity = extract_place_entity(script)
    entity_canon = extract_entity_canon(script, entity)

    chunks = chunk_script(script)

    prior_prompts: List[str] = []
    out_chunks = []
    
    witness_canon: str | None = None
    witness_locked = False

    script_so_far = ""

    for idx, chunk in enumerate(chunks):
        script_so_far = f"{script_so_far} {chunk}".strip()

        if not witness_locked and is_witness_chunk_llm(script_so_far, chunk):
            witness_canon = extract_witness_canon(chunk)
            witness_locked = True

        next_chunk = ""
        if idx + 1 < len(chunks):
            next_chunk = chunks[idx + 1]

        script_context = script

        wc = len(chunk.split())
        img_count = images_for_chunk(wc)

        phase = get_story_phase(
            chunk,
            witness_locked=witness_locked,
            is_opening=(idx == 0),
        )

        images = gpt_image_prompts(
            script_context,
            chunk,
            place,
            entity,
            prior_prompts,
            img_count,
            phase=phase,
        )

        processed = []
        for img in images:
            p = inject_canon(
                img["prompt"],
                entity=entity_canon,
                witness=witness_canon,
            )

            anomaly = "NONE"

            if phase in ("HOOK", "LEGEND") and not witness_locked:
                anomaly = detect_visual_anomaly(
                    base_prompt=p,
                    script_context=chunk,
                    place=place,
                    is_opening=(phase == "HOOK"),
                    escalation_level=0
                )

            if anomaly != "NONE":
                p = f"{p}, subtle irregularity: {anomaly}"

            processed.append({
                "prompt": p,
                "uses_anomaly": anomaly != "NONE",
                "anomaly": None if anomaly == "NONE" else anomaly,
            })

            prior_prompts.append(
                p.split(",")[0][:120].lower()
            )

        out_chunks.append({
            "chunk_index": idx,
            "story_phase": phase,
            "script_text": chunk,
            "word_count": wc,
            "image_prompts": processed,
        })

    output = {
        "place": place,
        "entity": entity,
        "entity_canon": entity_canon,
        "witness_canon": witness_canon,
        "chunks": out_chunks,
    }

    write_json(run / "script_with_prompts.json", output)
    print(f"[ok] Wrote script_with_prompts.json → {run}")

if __name__ == "__main__":
    main()
