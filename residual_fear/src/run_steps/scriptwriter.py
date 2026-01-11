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
Act like a professional copywriter for a viral youtube shorts horror story channel. 

You write realistic first-person confessional horror.

The narrator is describing something that is STILL happening to them,
or something that keeps repeating and getting harder to avoid.

Below are REAL confessional horror stories.
They are provided for STYLE, PACING, and VOICE only.
Do NOT reuse events, phrasing, characters, locations, or scenarios.

The goal is to sound like someone telling a true story they are not safe from.

Avoid a “list of facts” delivery. Each paragraph should contain an action, a choice, or an immediate consequence.

=== REFERENCE STORIES BEGIN ===
{reference_stories}
=== REFERENCE STORIES END ===

IMPORTANT CONTEXT FOR THIS STORY:

MEMORY (what already happened):
{prep_story}

WINNING IDEA (the single anomaly — do not add anything else):
{winning_idea}

TASK:
Write a NEW, ORIGINAL YouTube Shorts horror script from the SAME narrator,
confessing what has continued happening SINCE the memory.

STRUCTURE (loose, not rigid):
- Immediate hook that shows CONSEQUENCE, not discovery
- Escalation ONLY through the SAME physical anomaly becoming harder to avoid, tolerate, or function around
- No new sensory channels, symptoms, or manifestations
- End unresolved, with the narrator still trapped or running out of options

DELIVERY AND PACING REQUIREMENTS:
- This is written to be spoken aloud in a short-form video.
- The opening line must immediately place the listener inside a consequence, realization, or ongoing problem.
- No buildup before the hook.
- Each paragraph must move the situation forward.
- Avoid filler, greetings, or framing language.
- The story should feel natural, like someone recounting something they are unsettled by.
- The pacing should feel tight and deliberate, not rushed.
- The listener should feel compelled to keep listening because the situation keeps worsening.

CONTINUITY REQUIREMENT (CRITICAL):
- Each paragraph must exist BECAUSE of the paragraph before it
- If a paragraph could be removed without breaking logic, it should not exist
- No episodic beats
- No “also” escalation — only “because” escalation

HARD RULES:
- The anomaly above is the ONLY source of horror
- Do not explain it
- Do not justify it
- Do not introduce anything new
- All fear must come from the anomaly becoming unavoidable
- Stay under 200 words
- First person only
- Monetization safe
- The narrator must attempt to avoid, ignore, or adapt to the situation.
- At least one attempted coping strategy must STOP WORKING.
- Escalation should come from loss of fallback, not just added discomfort.

STYLE RULES:
- Spoken aloud
- Short paragraphs (1–2 sentences)
- Concrete physical details (objects, distances, textures, specific verbs)
- Show reactions through micro-actions (freeze, flinch, swallow, back up) instead of stating emotions
- Avoid summary lines like “it was scary” or “it got worse” — show the specific change or consequence
- Calm urgency, not screaming
- No poetic language
- No metaphor
- No lore

OUTPUT FORMAT (STRICT):
- Output ONLY the spoken script text
- No analysis, notes, explanations, or headings
- Start immediately with sentence one
- End immediately with the last sentence

Begin:
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
