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

# ============================================================
# Canon
# ============================================================

def create_narrator_canon(rng: random.Random) -> str:
    hair_styles = ["short buzz-cut", "messy bedhead", "slicked-back", "wavy"]
    hair_colors = ["ash brown", "jet black", "salt-and-pepper", "dark blonde"]
    tops = ["charcoal grey hoodie", "black thermal shirt", "faded navy t-shirt", "brown canvas jacket"]
    bottoms = ["dark denim jeans", "black cargo pants", "grey sweatpants"]
    ages = ["mid-20s", "mid-30s", "early-40s"]

    return (
        f"Caucasian male in his {rng.choice(ages)}, "
        f"{rng.choice(hair_styles)} {rng.choice(hair_colors)} hair, "
        f"wearing a {rng.choice(tops)} and {rng.choice(bottoms)}."
    )

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
    system = """
You extract grounded story anchors from a confessional horror script.

Rules:
- Return ONLY valid JSON.
- Keep outputs short, concrete, non-poetic.
- Do NOT add new story facts.
- Entity must be unseen, described ONLY by behavior or evidence.
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
    narrator_canon: str,
    prior_prompts: List[str],
    count: int,
    is_opening: bool,
) -> List[Dict[str, str]]:

    system = """
You generate concise, cinematic image prompts for a confessional horror short.

CRITICAL STORY RULE:
- Images must ONLY depict information that the narrator would plausibly know at THIS exact moment in the story.
- Do NOT show future discoveries, future evidence, or implied outcomes early.
- If something is not yet discovered in the narration, it must NOT appear.

VISUAL RULES:
- Simple, grounded shots.
- Prefer POV or environmental storytelling.
- One primary subject per image.
- Background must remain minimal and non-distracting.
- The UPCOMING section is for mood and anticipation ONLY.
- Do NOT depict objects, text, or evidence that appear only in UPCOMING.

CHARACTER RULES:
- Do NOT show full faces of any person.
- If a human is present, show only hands, silhouette, partial body, or hair.
- If narrator or entity is visible beyond silhouette, insert placeholder tokens:
  {{NARRATOR_CANON}}, {{ENTITY_BEHAVIOR}}

Return ONLY a single JSON object (no markdown, no code fences, no extra text):
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
            "- Show the MOST unsettling PHYSICAL EVIDENCE that appears later in the story, presented without context, explanation, or visible cause.\n"
            "  but without context or explanation.\n"
            "- No faces. No answers. No explanations.\n"
            "- Make the viewer need to know how this happened.\n\n"
        )

    user = f"""
{opening_directive}
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

def inject_canon(prompt: str, narrator: str, entity: str) -> Tuple[str, bool, bool]:
    uses_narrator = "{{NARRATOR_CANON}}" in prompt
    uses_entity = "{{ENTITY_BEHAVIOR}}" in prompt

    if uses_narrator:
        prompt = prompt.replace("{{NARRATOR_CANON}}", narrator)
    if uses_entity:
        prompt = prompt.replace("{{ENTITY_BEHAVIOR}}", entity)

    return prompt, uses_narrator, uses_entity

# ============================================================
# Main
# ============================================================

def main():
    rng = random.Random(42)

    run = find_latest_run_folder()
    script = load_script_from_run(run)

    place, entity = extract_place_entity(script)
    narrator_canon = create_narrator_canon(rng)

    chunks = chunk_script(script)

    prior_prompts: List[str] = []
    out_chunks = []

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
            entity,
            narrator_canon,
            prior_prompts,
            img_count,
            is_opening=(idx == 0),
        )

        processed = []
        for img in images:
            p, u_n, u_e = inject_canon(
                img["prompt"],
                narrator_canon,
                entity,
            )

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
                "uses_narrator": u_n,
                "uses_entity": u_e,
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
        "entity": entity,
        "narrator_canon": narrator_canon,
        "chunks": out_chunks,
    }

    write_json(run / "script_with_prompts.json", output)
    print(f"[ok] Wrote script_with_prompts.json → {run}")

if __name__ == "__main__":
    main()
