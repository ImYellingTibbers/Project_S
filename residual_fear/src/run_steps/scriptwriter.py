import json
import os
from sys import path
from pathlib import Path 
from datetime import datetime, timezone

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, SCRIPTWRITER_LLM_MODEL
from src.llm.openai_llm import call_llm
# from src.llm.qwen_instruct_llm import call_llm

MAX_ATTEMPTS = 2

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _count_words(text: str) -> int:
    return len([w for w in text.split() if w])


def _has_strong_hook(script: str) -> bool:
    first_line = script.strip().splitlines()[0].lower()

    if len(first_line.split()) > 15:
        return False

    anomaly_triggers = [
        "doesn't",
        "didn't",
        "wasn't",
        "weren't",
        "never",
        "kept",
        "started",
        "moved",
        "appeared",
        "followed",
        "asked me",
        "knew my",
        "said my name",
        "no one else",
        "only i could",
        "every night",
    ]

    return any(trigger in first_line for trigger in anomaly_triggers)


REFERENCE_PATH = (
    Path(__file__).resolve()
    .parents[2]
    / "assets"
    / "reference_files"
    / "viral_horror_scripts.txt"
)


def load_reference_scripts() -> str:
    if not REFERENCE_PATH.exists():
        return ""

    text = REFERENCE_PATH.read_text(encoding="utf-8").strip()
    if not text:
        return ""

    return text


PROMPT_TEMPLATE = """
Act like a YouTube Shorts horror specialist whose sole job is to maximize:
- Scroll-stopping hooks (first 1–2 seconds)
- Retention through escalation
- Unresolved dread that forces rewatches and comments

Below are REAL viral horror confessional scripts.
They are provided ONLY to demonstrate:
- Hook cadence
- Sentence length patterns
- Escalation structure
- Symbol repetition
- Ending restraint

DO NOT copy plots, characters, names, locations, or specific objects.
DO NOT reference these scripts directly.
Use them ONLY as stylistic and structural guidance.

=== VIRAL REFERENCE SCRIPTS ===
{reference_scripts}
=== END REFERENCE SCRIPTS ===

NOW WRITE A NEW SCRIPT WITH THESE STRICT RULES:

NARRATOR:
- White adult male
- First-person confessional
- Speaking as if this is real and unresolved

STORY:
- Do not make any scripts around the idea of mirrors or reflections.
- Prefer the threat to be an unknown or unseen physical force rather than an emotional one.
- Do not center the horror around identity confusion, self-doubt, or internal psychological transformation.
- The threat must be external, observable, and capable of acting independently of the narrator’s emotions.

HOOK (CRITICAL):
- The FIRST LINE must immediately imply something impossible, wrong, or unseen by others
- No backstory before the hook
- No throat-clearing
- No “I don’t believe in ghosts” style openings unless paired with an immediate contradiction

CADENCE RULES:
- Prefer short sentences early (5–10 words)
- Allow longer sentences ONLY after tension is established
- Use paragraph breaks to simulate breath and panic
- Avoid flowery language

ESCALATION RULES:
- Choose ONE escalation mode and stick to it:
  (A) Time-based escalation (night → days → years later)
  OR
  (B) Location-based escalation (private → outside → public)
- Introduce ONE repeating symbol, sound, phrase, or behavior
- Repeat it at least 3 times with increasing threat or proximity
- Each repetition must make avoidance harder
- Avoid framing the climax around “who I am” or “what I’m becoming.”

ENDING RULES:
- Do NOT explain the phenomenon
- Do NOT resolve the threat
- The final line must imply one of the following:
  • The threat has moved closer
  • The narrator has been found
  • The narrator has been identified or remembered
- End on an external implication, not internal reflection
- Prefer endings where the danger is situational rather than existential.

MONETIZATION:
- No gore
- No explicit violence
- Fear should come from implication, surveillance, pursuit, or inevitability

FORMAT:
- ~60 seconds spoken (80–220 words)
- Output ONLY the spoken script
- No title
- No preface
- Start immediately with the first line
- End immediately with the last line
""".strip()


def _validate(script: str):
    wc = len(script.split())
    if wc < 80 or wc > 220:
        return False, f"Word count out of bounds ({wc})"

    if not _has_strong_hook(script):
        return False, "First line too long or not hook-like"

    return True, "ok"



def main():
    run_id = build_run_id()
    run_folder = RUNS_DIR / run_id
    run_folder.mkdir(parents=True, exist_ok=True)

    reference_scripts = load_reference_scripts()

    prompt = PROMPT_TEMPLATE.format(
        reference_scripts=reference_scripts
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
        "schema": {"name": "scriptwriter"},
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "script": script,
        "word_count": _count_words(script),
        "validation": {
            "passed": ok,
            "attempts": attempt,
            "last_error": None if ok else last_error,
        },
    }

    out_path = run_folder / "script.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
