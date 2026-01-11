import json
import random
import os
from sys import path
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, IDEA_SELECTOR_LLM_MODEL

def extract_json(text: str) -> dict:
    text = text.strip()

    # Fast path: already valid JSON
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)

    # Fallback: extract first JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in response:\n{text}")

    return json.loads(text[start:end + 1])


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_run_folder() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError("runs/ folder not found")
    run_folders = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()])
    if not run_folders:
        raise RuntimeError("No run folders found in runs/")
    return run_folders[-1]


SELECTION_PROMPT = """
You are selecting the strongest idea for a short-form horror video AND imagining the memory it would naturally come from.

Think like a storyteller, not a list scorer.
Choose the idea that would feel most believable and unsettling when told as a first-person recollection.

RULES:
- Evaluate ideas independently (ignore order)
- Favor interesting stories, realism, plausibility, and quiet escalation
- Must work as a 45–55 second first-person narration
- Implied horror only (no gore, no lore), may include real-world threats (people, animals, accidents), but avoid explaining any supernatural lore
- Avoid gimmicks, twists that require explanation, or supernatural exposition

For the winning idea:
- Briefly explain WHY it works as a short horror story
- Provide a short prep story that feels like a memory the narrator is recalling

PREP STORY RULES:
- 2–4 sentences
- First person, past tense
- Calm, matter-of-fact tone
- Mention the location once, naturally
- Establish normal setting context and one subtle wrong detail
- No resolution, no explanation
- Do not interpret motives or emotions of unknown figures
- This is NOT the final script — it is a memory seed intended to help a scriptwriter create a rich script
- Prep story must include at least one concrete sensory detail (sound/lighting/temperature/smell) not already stated in the idea.

YOUTUBE METADATA RULES:
- Create 1 title (28–45 chars)
- Title must be hook-first and interruptive
- Title must imply personal danger, loss of control, or a wrong reaction
- Avoid describing the phenomenon directly
- First-person implied or explicit
- Do not resolve or explain anything
- No quotes, no ALL CAPS, no emojis
- Create a description of exactly 3 short lines:
  - Line 1: first-person tension hook
  - Line 2: escalation or reaction hint
  - Line 3: subtle CTA framed as confession (e.g., “I still think about it. Subscribe.”)
- No questions
- No emojis
- No explanation
- Provide 12–15 tags
- At least 5 tags must describe physical actions, sounds, or sensory details
- Avoid vague genre tags (eerie, spooky, paranormal, ghostly)
- Favor situational and sensory phrases
- Provide content flags:
  - made_for_kids: false
  - contains_gore: false
  - contains_explicit_sex: false
  - contains_hate: false

OUTPUT JSON ONLY:
{
  "scored": [
    { "idea": "...", "score": 1-10, "reason": "one sentence" }
  ],
  "top_three": [
    { "idea": "...", "reason": "one sentence" }
  ],
  "winner": {
    "idea": "...",
    "reason": "why this idea works as a story",
    "prep_story": "2–4 sentence first-person memory seed"
  },
  "youtube": {
    "title": "...",
    "description_lines": ["...", "...", "..."],
    "tags": [...],
    "language": "en",
    "made_for_kids": false,
    "content_flags": {
        "contains_gore": false,
        "contains_explicit_sex": false,
        "contains_hate": false
    },
    "shorts_intent": {
        "primary_emotion": "unease",
        "hook_type": "pattern_violation",
        "pov": "first_person",
        "sensory_focus": ["sound", "movement"]
    }
  }
}
""".strip()


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found")

    client = OpenAI(api_key=api_key)

    run_folder = find_latest_run_folder()
    raw_path = run_folder / "idea_generator.json"
    if not raw_path.exists():
        raise RuntimeError("idea_generator.json not found")

    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    ideas = raw.get("data", {}).get("ideas", [])

    if not ideas:
        raise RuntimeError("No ideas found")

    shuffled = ideas[:]
    random.shuffle(shuffled)

    ideas_block = "\n".join(
        f"{idx + 1}. {idea['idea']}"
        for idx, idea in enumerate(shuffled)
    )

    selection_prompt = f"{SELECTION_PROMPT}\n\nIDEAS:\n{ideas_block}"

    selection_resp = client.chat.completions.create(
        model=IDEA_SELECTOR_LLM_MODEL,
        messages=[
            {"role": "system", "content": "You evaluate horror story ideas."},
            {"role": "user", "content": selection_prompt},
        ],
    )

    selection = extract_json(selection_resp.choices[0].message.content)
    prep_story = selection["winner"].get("prep_story")

    out = {
        "schema": {"name": "idea_selector", "version": "0.6.0"},
        "run_id": None,
        "created_at": utc_now_iso(),
        "source": "idea_generator.json",
        "ideas_considered": len(ideas),
        "data": {
            **selection,
            "prep_story": {
                "text": prep_story,
                "purpose": "bridge_to_scriptwriter"
            }
        }
    }

    out_path = run_folder / "idea.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
