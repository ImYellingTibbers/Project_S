import json
from pathlib import Path
from datetime import datetime, timezone
from sys import path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, PROJECT_VERSION
from src.llm.qwen_instruct_llm import call_llm


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_run_folder() -> Path:
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    if not runs:
        raise RuntimeError("No run folders found")
    return runs[-1]


def extract_json(text: str) -> dict:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"No JSON object found:\n{text[:500]}")
    return json.loads(text[start:end + 1])


METADATA_PROMPT = """
You generate metadata for YouTube Shorts horror channels.

You are NOT summarizing the plot.
You are NOT extracting story details.
You are positioning the video inside the HORROR SHORTS ecosystem.

--------------------------------
CORE MINDSET
--------------------------------
Think in BROAD TERMS ONLY.

- What kind of horror is this?
- What expectation does it set?
- Why would someone who likes horror Shorts stop scrolling?

The script informs tone and category, not specifics.

--------------------------------
TITLE RULES (SCROLL-STOPPING)
--------------------------------
- 30–50 characters (optimize for Shorts truncation)
- First-person confessional
- Explicit fear state OR threat (being watched, followed, trapped, hunted)
- ONE dominant fear keyword that maps to known horror clusters
- Prefer phrases commonly used in viral horror titles.
- Avoid poetic abstraction when a concrete fear phrase exists.
- Genre words allowed if natural
- When the threat is unclear, prefer “someone” over “something.”

GOOD EXAMPLES:
- I Think Something Evil Is Watching Me
- I Shouldn’t Have Ignored the Knocking
- I Don’t Feel Safe in My Own House
- Something Is Wrong When I’m Alone

BAD EXAMPLES:
- An Entity Appeared at 3:14 AM
- The Door Was Possessed
- Paranormal Bedroom Incident

--------------------------------
DESCRIPTION RULES (DISCOVERY-OPTIMIZED)
--------------------------------
4–6 short lines.

Rules:
- Plain language
- No poetry
- No emojis
- No hashtags
- No CTAs

Structure:
- Line 1: Confessional setup
- Line 2: What changed or escalated
- Line 3: Loss of control or safety
- Line 4–6: Reinforce dread, uncertainty, isolation

Descriptions should read like a quiet admission.
The core fear concept from the title should appear at least once in the description using different wording.
At least two different lines must independently imply the same fear topic using different wording.
At most one additional line may restate the fear using different wording.

--------------------------------
TAGS RULES (TIERED REACH)
--------------------------------
20–30 tags total.

Tier 0 (Search-aligned queries):
- someone watching me
- not alone
- creepy true stories
- scary true stories
- real horror stories

Tier 1 (High volume):
- horror
- scary
- creepy
- scary story
- horror short
- horror shorts
- creepy story
- fear

Tier 2 (Medium intent):
- first person horror
- confessional horror
- short horror story
- scary confession
- true horror style
- unsettling stories
- paranoia
- dread
- anxiety
- isolation
- unease
- panic

Tier 3 (Format signals):
- youtube shorts
- shorts horror
- horror narration
- dark stories

--------------------------------
INPUTS
--------------------------------
You are given:
- A horror narration
- A storyboard summary

Use them ONLY to understand tone and category.

--------------------------------
OUTPUT (STRICT JSON)
--------------------------------
{
  "title": "...",
  "description_lines": ["...", "...", "..."],
  "tags": [...],
  "language": "en",
  "made_for_kids": false
}

Output JSON only.
""".strip()


def main():
    run_folder = find_latest_run_folder()

    script_path = run_folder / "script.json"
    storyboard_path = run_folder / "storyboard.json"

    if not script_path.exists():
        raise RuntimeError("script.json not found")
    if not storyboard_path.exists():
        raise RuntimeError("storyboard.json not found")

    script = json.loads(script_path.read_text(encoding="utf-8"))
    storyboard = json.loads(storyboard_path.read_text(encoding="utf-8"))

    script_text = script.get("script", "").strip()
    if not script_text:
        raise RuntimeError("script.json missing script text")

    # Build a compact storyboard summary (no fluff)
    storyboard_summary = []
    for beat in storyboard.get("beats", []):
        summary = {
            "location": beat.get("location"),
            "visual_intent": beat.get("visual_intent"),
            "objects": beat.get("framing"),
            "pacing": beat.get("pacing"),
        }
        storyboard_summary.append(summary)

    prompt = (
        METADATA_PROMPT
        + "\n\nSCRIPT:\n"
        + script_text
        + "\n\nSTORYBOARD SUMMARY:\n"
        + json.dumps(storyboard_summary, indent=2)
    )

    raw = call_llm(prompt)
    metadata = extract_json(raw)
    # --- HARD VALIDATION ---
    title = metadata.get("title", "")
    SEO_FEAR_TERMS = [
        "watch", "follow", "alone", "trapped", "knocking",
        "someone", "inside", "behind", "staring", "coming"
    ]

    if not any(term in title.lower() for term in SEO_FEAR_TERMS):
        raise RuntimeError("Title lacks strong SEO fear term")

    if not (22 <= len(title) <= 50):
        raise RuntimeError(f"Title length out of bounds: {len(title)}")

    tags = metadata.get("tags", [])
    if not (20 <= len(tags) <= 30):
        raise RuntimeError(f"Invalid tag count: {len(tags)}")

    description_lines = metadata.get("description_lines", [])

    if len(description_lines) < 4:
        # Pad description by repeating core fear in different wording
        title = metadata.get("title", "")
        fear_hint = title.lower().replace("i ", "").strip()

        while len(description_lines) < 4:
            description_lines.append(
                f"I can’t shake the feeling that {fear_hint}."
            )

        metadata["description_lines"] = description_lines

    metadata["description_lines"] = [
        line[:1].upper() + line[1:] if line else line
        for line in metadata.get("description_lines", [])
    ]
    
    out = {
        "schema": {
            "name": "metadata_generator",
            "version": PROJECT_VERSION,
        },
        "run_id": script.get("run_id"),
        "created_at": utc_now_iso(),
        "data": metadata,
    }

    out_path = run_folder / "metadata.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
