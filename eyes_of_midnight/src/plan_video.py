"""
Step 0 of the batch pipeline. Selects one unused title from title_bank.json,
generates 3 unique story seeds for that title, and writes video_plan.json.

Usage:
    python eyes_of_midnight/src/plan_video.py
"""

from __future__ import annotations

import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found in environment")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-70b-instruct"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

CHANNEL_ROOT = Path(__file__).resolve().parent.parent
TITLE_BANK_PATH = Path(__file__).resolve().parent / "assets" / "title_bank.json"
VIDEO_PLAN_PATH = CHANNEL_ROOT / "video_plan.json"


def call_llm(messages, temperature=0.85, max_tokens=2000) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=120)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"].get("content", "").strip()
    if not content:
        raise RuntimeError("LLM returned empty content")
    return content


def pick_title() -> Dict:
    """Select a random unused title from the bank and mark it used."""
    if not TITLE_BANK_PATH.exists():
        raise RuntimeError(
            f"Title bank not found at {TITLE_BANK_PATH}.\n"
            "Run generate_title_bank.py first."
        )

    bank = json.loads(TITLE_BANK_PATH.read_text(encoding="utf-8"))
    available = [t for t in bank["titles"] if not t["used"]]

    if not available:
        raise RuntimeError(
            "Title bank is exhausted. All titles have been used.\n"
            "Re-run generate_title_bank.py to generate more."
        )

    chosen = random.choice(available)

    # Mark as used
    for t in bank["titles"]:
        if t["id"] == chosen["id"]:
            t["used"] = True
            break

    bank["available"] = sum(1 for t in bank["titles"] if not t["used"])
    TITLE_BANK_PATH.write_text(json.dumps(bank, indent=2), encoding="utf-8")

    print(f"[PLAN] Selected title: {chosen['title']}")
    print(f"[PLAN] Titles remaining: {bank['available']}")
    return chosen


def generate_story_seeds(main_title: str) -> List[Dict]:
    """
    Generate 3 distinct story seeds that each fit under the main title theme.
    Each seed gets: a 2-sentence idea, a mini title, and a one-line summary.
    """

    system = """\
You are planning three distinct horror stories for a confessional YouTube horror channel.
All three stories will appear in one video under a shared theme title.

Your job is to generate three story seeds that:
- All fit under the shared theme title
- Are meaningfully different from each other in setting, victim, and threat dynamic
- Feel like real first-person confessional accounts
- Are non-supernatural — fear comes entirely from human behavior and intent
- Are specific and personal, not generic

For each story you will output:
- MINI_TITLE: A short, punchy 3-7 word title for the story (e.g. "He Knew My Schedule", "The Storage Room", "She Wouldn't Leave")
- SEED: Exactly two sentences in first-person that describe the specific situation and what made it terrifying. This will be used as the story's core idea prompt.
- SUMMARY: One sentence describing what the story is about (for internal tracking).

OUTPUT FORMAT (repeat exactly 3 times):
STORY 1:
MINI_TITLE: [title]
SEED: [two sentences]
SUMMARY: [one sentence]

STORY 2:
MINI_TITLE: [title]
SEED: [two sentences]
SUMMARY: [one sentence]

STORY 3:
MINI_TITLE: [title]
SEED: [two sentences]
SUMMARY: [one sentence]

No other text. No commentary. No extra formatting."""

    user = (
        f"Main video title: \"{main_title}\"\n\n"
        "Generate three distinct story seeds that all fit this theme.\n"
        "Make each story feel like it happened to a different person, in a different situation.\n"
        "Vary the settings — workplaces, homes, outdoors, vehicles, public spaces.\n"
        "Vary the threat — a stranger, a coworker, an ex, a service person, a neighbor.\n"
        "Each seed must be specific enough that a full 10-minute horror story could be written from it.\n"
        "The two SEED sentences must be in first-person (I) and feel like a real confession."
    )

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.88,
    )

    return parse_story_seeds(raw)


def parse_story_seeds(raw: str) -> List[Dict]:
    stories = []

    story_blocks = re.split(r"STORY\s+\d+\s*:", raw, flags=re.IGNORECASE)
    story_blocks = [b.strip() for b in story_blocks if b.strip()]

    for i, block in enumerate(story_blocks[:3]):
        mini_title = ""
        seed = ""
        summary = ""

        for line in block.splitlines():
            line = line.strip()
            upper = line.upper()
            # Accept MINI_TITLE: and LLM hallucinations like "MINI GETTITLE:", "MINI:", etc.
            if upper.startswith("MINI_TITLE:") or upper.startswith("MINI ") or (upper.startswith("MINI:") and not mini_title):
                mini_title = line.split(":", 1)[1].strip()
            elif upper.startswith("SEED:"):
                seed = line.split(":", 1)[1].strip()
            elif upper.startswith("SUMMARY:"):
                summary = line.split(":", 1)[1].strip()

        if not mini_title or not seed:
            raise RuntimeError(
                f"Failed to parse story seed {i + 1} from LLM output.\n"
                f"Block:\n{block}\n\nFull raw output:\n{raw}"
            )

        stories.append({
            "index": i,
            "mini_title": mini_title,
            "seed": seed,
            "summary": summary,
        })

    if len(stories) < 3:
        raise RuntimeError(
            f"Expected 3 story seeds, only parsed {len(stories)}.\n"
            f"Raw output:\n{raw}"
        )

    return stories


def sanitize_folder_name(title: str) -> str:
    """Convert a title to a safe folder name."""
    safe = re.sub(r"[^\w\s-]", "", title)
    safe = re.sub(r"\s+", "_", safe.strip())
    return safe[:120]  # Cap length


def main():
    title_entry = pick_title()
    main_title = title_entry["title"]

    print("[PLAN] Generating story seeds...")
    stories = generate_story_seeds(main_title)

    for s in stories:
        print(f"  Story {s['index'] + 1}: {s['mini_title']}")
        print(f"    Seed: {s['seed'][:80]}...")

    plan = {
        "main_title": main_title,
        "sanitized_title": sanitize_folder_name(main_title),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "stories": stories,
        "run_folders": [],
    }

    VIDEO_PLAN_PATH.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"\n[PLAN] video_plan.json written to {VIDEO_PLAN_PATH}")


if __name__ == "__main__":
    main()
