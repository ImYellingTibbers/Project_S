import json
import os
from sys import path
from pathlib import Path 
from datetime import datetime, timezone

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

REFERENCE_PATH = ROOT / "src" / "assets" / "reference_files" / "confessional_reference_stories.txt"

if not REFERENCE_PATH.exists():
    raise FileNotFoundError(f"Missing reference file: {REFERENCE_PATH}")

REFERENCE_STORIES = REFERENCE_PATH.read_text(encoding="utf-8")

from src.config import RUNS_DIR, SCRIPTWRITER_LLM_MODEL
# from src.llm.mixtral_llm import call_llm
from src.llm.qwen_instruct_llm import call_llm

MAX_ATTEMPTS = 3

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _count_words(text: str) -> int:
    return len([w for w in text.split() if w])


PROMPT_TEMPLATE = """
You are writing a VIRAL YouTube Shorts horror confessional.
Your only goal is to maximize retention and replay by making the viewer feel personally unsafe in the first 2 seconds.

Write realistic first-person confessional horror.
The narrator is a man.
The threat is STILL happening.
It has already forced real sacrifices, and it is getting worse right now.

Use the reference stories ONLY for voice, pacing, and realism.
Do NOT reuse their events, phrasing, characters, locations, or scenarios.

=== REFERENCE STORIES BEGIN ===
{reference_stories}
=== REFERENCE STORIES END ===

CONTEXT YOU MUST USE:

TONE ANCHOR (NOT CANON — do not treat as facts):
{prep_story}

Important: Use the tone and urgency only.
Ignore any detail in the tone anchor that is not explicitly present in the WINNING IDEA.
Do not reuse exact phrasing from the tone anchor.

WINNING IDEA (the single anomaly — keep it the same core anomaly):
{winning_idea}

WRITE THE SCRIPT (performance-first):
- 6 to 8 paragraphs.
- Paragraph 4 must be a 'Pattern Interrupt': a sentence under 5 words that resets the tension (e.g., 'Then it stopped.' or 'I was wrong.')
- Each paragraph is 1 sentence (2 max if absolutely necessary).
- Total length: 110–170 words.
- Spoken aloud: plain, direct, confessional. No poetry.
- The FIRST sentence must contain BOTH:
  (a) the irreversible loss AND
  (b) the anomaly itself.
  If either is missing, the script is invalid.
- By paragraph 2, the narrator has already permanently changed a normal behavior (sleep, routine, home layout, job, relationships).
- Every paragraph must introduce NEW escalation: a new failure, a new restriction, a new invasion, a new loss.
- Include ONE “snap” moment where the anomaly reacts as if it noticed the narrator’s coping attempt (no lore, no explanation, no named entity).
- End on a single devastating unresolved line that implies it is closer / stronger / unavoidable tonight.
- Exactly 6 to 8 paragraphs separated by a single blank line (no more, no less).
- The first paragraph must be consequence-first and must include the irreversible change already made.
- Use specific, low-budget, high-impact visuals.

DO NOT:
- Do not explain what it is or why it happens.
- Do not add lore, rules, demon names, symbolism, or metaphors.
- Do not add extra anomalies or unrelated horror elements.
- Do not use discovery framing (avoid: “I noticed”, “I found”, “it started”, “one day”).
- Do not waste lines on “I tried X, I tried Y” montages. Pick ONE coping attempt and make it fail hard.
- Do not mention filming, cameras, posts, or social media.

OUTPUT:
Only the spoken script text.
No title.
No preface.
Start immediately with sentence one.
End immediately with the last sentence.
""".strip()


def _validate(script: str):
    lines = [l for l in script.splitlines() if l.strip()]
    wc = len(script.split())

    if wc > 190:
        return False, f"Too many words ({wc}). Compress escalation."
    if wc < 100:
        return False, f"Too few words ({wc}). Expand slightly."
    if len(lines) < 6:
        return False, f"Too few paragraphs ({len(lines)})."

    first = lines[0].lower()
    bad_openers = [
        "something felt",
        "something was wrong",
        "i noticed",
        "it started",
        "there was something",
        "i didn't think much",
    ]

    if any(b in first for b in bad_openers):
        return False, "Weak hook: first sentence describes observation, not consequence."

    loss_markers = [
        "i couldn't",
        "i can't",
        "i stopped",
        "i don't sleep",
        "i no longer",
        "i don't leave",
        "i avoid",
    ]

    if not any(m in script.lower() for m in loss_markers):
        return False, "No clear loss of agency detected."

    return True, "ok"



def main():
    run_folder = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())[-1]
    idea_json = json.loads((run_folder / "idea.json").read_text(encoding="utf-8"))

    prep_story = idea_json["data"]["winner"]["prep_story"]["text"]
    winning_idea = idea_json["data"]["winner"]["idea"]

    prompt = PROMPT_TEMPLATE.format(
        reference_stories=REFERENCE_STORIES,
        winning_idea=winning_idea,
        prep_story=prep_story
    )

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        retry_prompt = prompt
        if last_error:
            retry_prompt = (
                prompt
                + "\n\nVALIDATION FEEDBACK FROM PREVIOUS ATTEMPT:\n"
                + last_error
                + "\nFix this while keeping all rules above.\n"
            )

        script = call_llm(retry_prompt)
        ok, feedback = _validate(script)

        if ok:
            break

        last_error = feedback
    else:
        print(
            f"[WARN] Script failed validation after {MAX_ATTEMPTS} attempts. "
            f"Continuing with last output. Issue: {last_error}"
        )



    out = {
        "schema": {"name": "scriptwriter_draft", "version": "0.6.0"},
        "run_id": idea_json["run_id"],
        "created_at": utc_now_iso(),
        "winning_idea": winning_idea,
        "prep_story": prep_story,
        "script": script,
        "word_count": _count_words(script),
        "validation": {
            "passed": ok,
            "attempts": attempt,
            "last_error": None if ok else last_error,
        },
    }

    out_path = run_folder / "draft.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
