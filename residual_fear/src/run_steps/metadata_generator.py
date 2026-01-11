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
TITLE RULES (HOOK-BASED)
--------------------------------
- 28–45 characters
- Statement, not a question
- Broad hook based on the core situation
- First-person phrasing preferred
- NO specific objects, locations, or events
- NO metaphors
- NO emojis
- NO genre words (horror, scary, spooky, paranormal)

GOOD:
- I Think Something Is Trapping Me
- I Shouldn’t Have Stayed Inside
- I Don’t Feel Alone Anymore

BAD:
- My Bedroom Door Sealed Itself Shut
- The Wardrobe Started Whispering
- The Floor Isn’t Solid Anymore

--------------------------------
DESCRIPTION RULES (LIGHT SPECIFICITY)
--------------------------------
Exactly 3 short lines.

This is the ONLY place specificity is allowed.

Structure:
- Line 1: “This is a story about …”
- Line 2: escalation or worsening
- Line 3: confessional unease

Keep it simple.
No poetry.
No emojis.
No hashtags.
No CTAs.

--------------------------------
TAGS RULES (EXTREMELY BROAD)
--------------------------------
- 15–20 tags
- Tags MUST be generic, high-volume horror terms
- Tags MUST apply to thousands of videos
- ZERO story details
- ZERO clever phrasing

Use only concepts like:
- horror
- scary
- creepy
- spooky
- horror short
- horror shorts
- scary story
- scary stories
- creepypasta
- horror storytime
- disturbing
- dark
- nightmare
- suspense
- fear

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
