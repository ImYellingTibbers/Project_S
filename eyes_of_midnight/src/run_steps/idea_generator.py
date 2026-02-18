from __future__ import annotations

import os
import json
from typing import List, Dict
from dotenv import load_dotenv
import requests

# ============================================================
# Environment
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found in environment")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model optimized for creative ideation
MODEL = "meta-llama/llama-3.3-70b-instruct"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

# ============================================================
# Core LLM Call
# ============================================================

def call_llm(messages: List[Dict], temperature: float, max_tokens: int) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"].get("content")

    if not content or not content.strip():
        raise RuntimeError("LLM returned empty content")

    return content.strip()

def judge_horror_idea(idea: str) -> bool:
    system = (
        "You are a strict binary judge for horror story ideas.\n\n"
        "Your job is to decide whether the idea PASSES or FAILS.\n"
        "Do NOT suggest improvements. Do NOT explain reasoning.\n\n"
        "PASS ONLY IF ALL CONDITIONS ARE MET:\n"
        "- First-person POV (uses 'I').\n"
        "- Exactly two sentences.\n"
        "- Modern, realistic, plausible situation.\n"
        "- No supernatural, paranormal, or unexplained forces.\n"
        "- Fear comes from human behavior, access, intent, surveillance, or coincidence.\n"
        "- Sounds like a true story that could have happened recently.\n\n"
        "FAIL if any condition is violated.\n\n"
        "OUTPUT RULES:\n"
        "- Output ONLY one word: PASS or FAIL."
    )

    user = f"Idea:\n{idea}"

    verdict = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,   # deterministic judge
        max_tokens=5,
    )

    return verdict.strip() == "PASS"


# ============================================================
# Idea Generation + Selection
# ============================================================

def generate_best_horror_idea_raw() -> str:
    system = (
"""You are generating realistic first-person horror story ideas for a modern confessional horror channel.
These stories must feel like true experiences that could have happened recently to an ordinary person.
The tone is: “this really happened to me, and I still think about it.”
STRICT CONSTRAINTS:
- First person POV ONLY (“I”).
- Modern, relatable settings only (work, driving, dating, hotels, gyms, stores, apartments, travel).
- The situation must be plausible and grounded in human behavior.
- NO supernatural elements of any kind (no ghosts, entities, curses, unexplained forces).
- The fear must come from people, intent, access, coincidence, surveillance, manipulation, or being targeted.
- Avoid gore, monsters, demons, urban legends, or folklore.
- Avoid technology gimmicks as the main hook; technology may exist but must not be the point.
TASK:
1. Generate THREE distinct horror story ideas.
2. Each idea MUST be exactly two sentences.
3. Each idea must describe a specific unsettling situation that escalates or recontextualizes itself.
4. Each idea must include a subtle human mistake or social pressure (politeness, obligation, fatigue, money, fear of overreacting).
OUTPUT RULES:
- Output ONLY the selected idea.
- Exactly two sentences.
- No titles, labels, explanations, formatting, or commentary."""
    )

    user = (
        "Generate and select the strongest horror idea.\n"
        "Final output MUST be exactly two grammatically complete sentences.\n"
        "Do not use clichés, monsters, demons, or jump-scare tropes.\n"
        "Favor slow-burn dread, personal stakes, and implications that worsen over time."
    )

    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.9,
        max_tokens=300,
    )

# ============================================================
# Manual Test
# ============================================================

def generate_best_horror_idea(max_retries: int = 3) -> str:
    last_idea = None

    for attempt in range(1, max_retries + 1):
        idea = generate_best_horror_idea_raw()
        last_idea = idea

        try:
            if judge_horror_idea(idea):
                return idea
        except Exception:
            # If judge fails unexpectedly, treat as FAIL and retry
            pass

    # Fallback: return last generated idea even if it failed
    # This prevents total pipeline failure
    return last_idea

if __name__ == "__main__":
    idea = generate_best_horror_idea()
    print(idea)
