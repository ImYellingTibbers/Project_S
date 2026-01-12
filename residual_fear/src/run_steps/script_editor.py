import json
from sys import path
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR
# from src.llm.mixtral_llm import call_llm
from src.llm.qwen_instruct_llm import call_llm

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


REWRITE_PROMPT = """
You are a ruthless VIRAL YouTube Shorts horror editor.

Your only goal: maximize retention + replay by sharpening threat, consequence, and inevitability.
Rewrite aggressively. Do NOT “lightly polish.” Make it hit harder while still sounding like a real person.

NON-NEGOTIABLE CONSTRAINTS:
- Keep the narrator as the same person (first-person, man).
- Keep ONE dominant anomaly. Do not change what the anomaly is.
- Do NOT introduce new characters, new locations, new mechanisms, new objects that change the plot, or new “lore.”
- You may delete weak elements. You may NOT add new plot elements.
- Do NOT explain what it is or why it happens. No named entities, no rules, no symbolism.

STRUCTURE (must hold after editing):
- 6 to 8 paragraphs.
- Each paragraph is 1 sentence (2 max only if absolutely necessary).
- 110–170 words total.
- Spoken, direct, confessional. No poetry.

VIRAL RULES (priority order):
1) HOOK MUST BE CONSEQUENCE
- First sentence must show an active restriction/loss (sleep/safety/privacy/sanity/routine), not observation.
- If the first sentence is not consequence-first, rewrite it.
- The first sentence MUST contain BOTH:
  (a) the irreversible change already made, AND
  (b) the anomaly named with a concrete noun (knocking, clicking, footprints, hum, etc.).
- The first sentence MUST also imply escalation (worse tonight / louder / closer / more frequent) in the same line.
- Do not allow a generic hook (e.g., “I don’t sleep anymore.”) unless it also names the anomaly and the sacrifice.

2) EVERY PARAGRAPH MUST ESCALATE
- Each paragraph must introduce a NEW escalation: a new failure, new restriction, new invasion, or new loss.
- Delete “I tried X, I tried Y” montages. Keep ONE coping attempt and make it fail HARD.

3) INSERT ONE “SNAP” MOMENT IF MISSING
- Add exactly one line where the anomaly reacts as if it noticed the coping attempt.
- This must be done using the SAME anomaly (no new mechanics).

4) MAKE IT FEEL REAL
- Concrete, normal-life details (door wedge, hallway light, bedding, work schedule, neighbors hearing things, etc.).
- Keep it plausible in voice even if the anomaly is not.
- No melodrama. No filler panic. No generic lines like “it gnawed at my sanity.”

5) END LIKE A TRAP
- Final line must be ONE single unresolved “trap statement.”
- It MUST be specific and concrete (not generic like “It’s getting closer” or “I can’t do this”).
- It MUST imply a new, worse placement/behavior of the SAME anomaly tonight (e.g., “It’s knocking again—but it’s not on the door this time.”).
- No wrap-up. No explanation. No comfort. No reflection.

IF THE DRAFT CONTAINS MULTIPLE HORROR ELEMENTS:
- Remove the weaker ones so only ONE dominant anomaly remains.
- Do not “give up” or return unchanged.

OUTPUT FORMAT (STRICT):
- Output MUST be ONLY the spoken script text.
- Do NOT output analysis, notes, bullets, headings, quotes, JSON, code fences, or meta commentary.
- Do NOT mention "this script" or evaluate quality.
- Start immediately with the first sentence of the script.
- End immediately with the last sentence of the script.
- No extra lines before or after.
- Do NOT use "..." or the ellipsis character "…".

The draft script begins below.
""".strip()

def main():
    run_folder = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())[-1]
    draft_path = run_folder / "draft.json"

    if not draft_path.exists():
        raise RuntimeError("draft.json not found")

    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    original_script = draft["script"]

    prompt = (
        REWRITE_PROMPT
        + "\n\n<BEGIN DRAFT SCRIPT>\n"
        + original_script.strip()
        + "\n<END DRAFT SCRIPT>\n"
    )

    rewritten_script = call_llm(prompt)

    out = {
        "schema": {"name": "scriptwriter_final", "version": "0.6.0"},
        "run_id": draft["run_id"],
        "created_at": utc_now_iso(),
        "winning_idea": draft["winning_idea"],
        "prep_story": draft["prep_story"],
        "script": rewritten_script,
        "word_count": len(rewritten_script.split()),
        "source": {
            "rewritten_from": "draft.json",
            "model": "qwen 7b instruct",
        },
    }

    out_path = run_folder / "script.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
