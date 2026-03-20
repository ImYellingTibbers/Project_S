"""
Run this script ONCE to generate the title bank.
It calls the LLM in batches and writes title_bank.json to src/assets/.

Usage:
    python eyes_of_midnight/src/generate_title_bank.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List

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

OUTPUT_PATH = Path(__file__).resolve().parent / "assets" / "title_bank.json"
TARGET_COUNT = 510  # Generate a little extra so dedup still gives us 500+
BATCH_SIZE = 50


def call_llm(messages, temperature=0.9, max_tokens=3000) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


SYSTEM_PROMPT = """\
You are writing YouTube video titles for a first-person confessional horror channel.
The channel features real-sounding stories of stalkers, home invasions, being watched, \
followed, deceived, or trapped. Stories are grounded, modern, and deeply personal.

TITLE FORMAT RULES:
- Always structured as: "3 [Adjective] [Noun] of [Specific Situation or Threat]"
- Adjectives vary: True, Terrifying, Disturbing, Chilling, Horrifying, Unsettling, Real, Harrowing
- Nouns vary: Stories, Accounts, Encounters, Experiences, Incidents, Confessions
- The [Specific Situation] must be CONCRETE and SPECIFIC — not vague
- AVOID: anything supernatural, monsters, paranormal, ghosts, demons
- AVOID: generic titles like "Scary Stories" or "Horror Stories"
- Titles must feel like real confessional horror content

GREAT EXAMPLES:
- 3 True Stories of Stalkers Who Knew Their Victims' Daily Routines
- 3 Disturbing Encounters With Men Who Wouldn't Accept No
- 3 Chilling Accounts of People Who Found Evidence Someone Had Been in Their Home
- 3 Horrifying Stories of Night Shift Workers Who Were Not Alone
- 3 True Confessions From People Who Were Followed Home
- 3 Harrowing Experiences of Women Alone in Parking Garages at Night
- 3 Terrifying Stories of Airbnb Guests Who Discovered Hidden Cameras
- 3 Disturbing Accounts of People Who Realized They Were Being Watched for Months
- 3 Unsettling Stories of Hitchhikers Who Should Never Have Gotten in That Car
- 3 True Stories of Employees Who Discovered Their Coworker Was Living in the Building

OUTPUT: Output ONLY a numbered list. No commentary, no intro, no outro.
"""


def generate_batch(batch_num: int, existing_titles: List[str]) -> List[str]:
    already = "\n".join(f"- {t}" for t in existing_titles[-100:]) if existing_titles else "None yet."

    user = (
        f"Generate exactly {BATCH_SIZE} unique, compelling horror compilation titles.\n\n"
        f"DO NOT repeat or closely mirror any of these already-generated titles:\n{already}\n\n"
        f"Output exactly {BATCH_SIZE} titles, one per line, numbered 1 through {BATCH_SIZE}.\n"
        "Each title must be for a DIFFERENT specific threat or situation.\n"
        "Vary the settings: workplaces, homes, parking lots, campgrounds, rideshares, hotels, \n"
        "gyms, hospitals, running trails, rest stops, grocery stores, college campuses, \n"
        "moving to new places, online meetups, and more.\n"
        "Vary the victim perspectives: women alone, men at night, couples, college students, \n"
        "retail workers, delivery drivers, night shift workers, hikers, travelers.\n"
        "Vary the threat type: stalkers, intruders, fake identities, obsessive ex-partners, \n"
        "predatory employers, strangers who won't leave, people hiding in spaces, \n"
        "people following from a distance, service workers with access, online manipulators."
    )

    raw = call_llm(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]
    )

    titles = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading number + period/dot
        if line[0].isdigit():
            dot = line.find(".")
            if dot != -1:
                line = line[dot + 1:].strip()
        if len(line) > 10:
            titles.append(line)

    print(f"  Batch {batch_num}: got {len(titles)} titles")
    return titles


def main():
    all_titles: List[str] = []
    seen: set = set()

    # Load existing bank if present (append / top-up mode)
    if OUTPUT_PATH.exists():
        existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        for entry in existing["titles"]:
            t = entry["title"]
            all_titles.append(t)
            seen.add(t.lower().strip())
        print(f"Loaded {len(all_titles)} existing titles. Topping up to 500...")

    still_needed = max(0, 500 - len(all_titles))
    if still_needed == 0:
        print("Already at 500+. Nothing to do.")
        return

    num_batches = (still_needed + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(1, num_batches + 1):
        print(f"Generating batch {i}/{num_batches}...")
        batch = generate_batch(i, all_titles)

        for title in batch:
            normalized = title.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                all_titles.append(title)

        print(f"  Total unique so far: {len(all_titles)}")

        if len(all_titles) >= TARGET_COUNT:
            break

        if i < num_batches:
            time.sleep(1)

    # Trim to exactly 500 if we have more
    all_titles = all_titles[:500]

    bank = {
        "total": len(all_titles),
        "available": len(all_titles),
        "titles": [
            {"id": i + 1, "title": t, "used": False}
            for i, t in enumerate(all_titles)
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(bank, indent=2), encoding="utf-8")

    print(f"\nDone. {len(all_titles)} titles written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
