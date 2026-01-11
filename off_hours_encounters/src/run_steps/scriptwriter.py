import json
import os
from sys import path
from pathlib import Path 
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, SCRIPTWRITER_LLM_MODEL

MAX_ATTEMPTS = 3

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _count_words(text: str) -> int:
    return len([w for w in text.split() if w])


PROMPT_TEMPLATE = """
You are recounting a disturbing personal experience that still feels unresolved and plagues your mind, keeping you awake at night.

This must sound like a real human person speaking, not a written story.
Write as a spoken recollection, told calmly and plainly, as if explaining to one listener some time after it happened, while it still feels unresolved.

Instead of focusing on being explicitly scary, let the unease come only from what occurred. The story is scary and interesting, almost like you have been thinking about what happened for a very long time, and you are now confessing what has been plaguing you all this time.

CRITICAL HOOK REQUIREMENT:
- The first sentence must describe something already wrong or unsettling
- No setup, no reflection, no internal thought
- The listener must immediately understand why this moment is disturbing
- If the first sentence could be removed without losing tension, the output is invalid
- The first sentence should still sound like something a real person would naturally say out loud.

INPUT CONTEXT (BACKGROUND — DO NOT REPEAT VERBATIM):
- Story idea and premise are provided below
- Prep story provides context, setup, or framing
Use both to guide the narration, but do not restate them directly.

LENGTH TARGET (CRITICAL):
- Target 120–170 words
- Hard maximum: 190 words
- Anything above 190 words will be rejected.

STORY SHAPE (FOR INTERNAL GUIDANCE ONLY — DO NOT OUTPUT):
- The first sentence must combine immediate context with something already wrong
- Begin inside a specific moment or observation
- Introduce one small detail that felt off
- Accept or rationalize it at the time to justify you not immediately running away or calling the police
- Let the same detail or a related detail return
- Make one deliberate choice to stay, watch, or continue
- End with how this still affects you now

Do not rigidly map sentences to these points.
They are guidance only.

NARRATOR VOICE:
- Adult male, roughly 30-45 years old
- First person
- Past tense
- Calm, restrained, observant
- Slight uncertainty, but not rambling
- You do not understand what happened
- You are not trying to interpret or explain it, only confess it to the listener

STYLE RULES:
- Plain, conversational language
- Natural contractions allowed
- No poetic phrasing
- No dramatic or emotional language
- Let sentence length vary naturally
- Minor hesitation is fine, but do not force filler phrases
- Do not begin with stillness, waiting, or silence unless something is already wrong

REALISM RULES:
- Only describe what you directly saw, heard, noticed, or chose to do
- Do not describe motives or intent of unknown people or things
- Do not introduce new locations late in the narration
- Do not suddenly reframe or explain the meaning of events

ESCALATION:
- Escalate through repetition or persistence, not emotion
- At least one detail must repeat with variation
- No more than two consecutive sentences without new information or change

ENDING:
- The final sentence must describe a real-world habit, avoidance, or behavior that changed
- It must apply to everyday life, not just the memory
- Do not explain why
- Do not provide closure or reassurance, leave the listener with the same sense of unknown/unease that you still feel

OUTPUT FORMAT (CRITICAL):
- One sentence per line
- End every sentence with a newline character: \n
- Output narration text only
- No headings
- No explanations
- No extra formatting
- The first sentence must be visually understandable without audio
- Avoid pronouns in the first sentence unless the referent is explicit


{winning_idea}
{prep_story}
""".strip()


def _validate(script: str):
    lines = [l for l in script.splitlines() if l.strip()]
    wc = len(script.split())

    if wc > 190:
        return False, f"Too many words ({wc}). Reduce length."
    if wc < 100:
        return False, f"Too few words ({wc}). Expand slightly."
    if not (8 <= len(lines) <= 12):
        return False, f"Invalid sentence count ({len(lines)})."
    return True, "ok"



def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing")

    client = OpenAI(api_key=api_key)

    run_folder = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())[-1]
    idea_json = json.loads((run_folder / "idea.json").read_text(encoding="utf-8"))

    prep_story = idea_json["data"]["prep_story"]["text"]
    winning_idea = idea_json["data"]["winner"]["idea"]

    prompt = PROMPT_TEMPLATE.format(
        winning_idea=winning_idea,
        prep_story=prep_story
    )

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        messages = [
            {
                "role": "system",
                "content": "You write restrained, realistic horror narration."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        if last_error:
            messages.append({
                "role": "user",
                "content": f"Fix the previous output. Issue: {last_error}"
            })

        resp = client.chat.completions.create(
            model=SCRIPTWRITER_LLM_MODEL,
            messages=messages,
        )

        script = resp.choices[0].message.content.strip()
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
        "schema": {"name": "scriptwriter", "version": "0.6.0"},
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

    out_path = run_folder / "script.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
