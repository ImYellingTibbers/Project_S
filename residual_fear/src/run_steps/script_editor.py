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
You are a professional horror script editor.

Your job is to preserve the story while sharpening consequence and inevitability.
Your job is to make a good script stronger without breaking it.

You are editing a first-person confessional horror script intended for YouTube Shorts.

IMPORTANT CONTEXT:
- The story is built around ONE physical anomaly.
- You may NOT introduce new plot elements, threats, locations, characters, or mechanisms.
- You may NOT change what the anomaly is.
- All fear must come from the SAME anomaly becoming more intrusive or unavoidable.
- The script has already passed strict validation for hook strength and loss of agency. Do not weaken these.

GOALS (in order of priority):

0) DO NOT REDUCE THREAT
- If a line softens consequence, inevitability, or danger, rewrite it.
- Prefer specific harm or loss over vague dread.

1) Improve the HOOK if needed
- The hook must already imply loss or consequence.
- If the hook already does this, do NOT rewrite it.
- Do NOT replace a strong hook with louder language.

2) Ensure the script feels SCARY THROUGH ESCALATION
- Fear should increase because the situation worsens, not because of language tricks.
- Remove vague or abstract fear if it replaces concrete action or consequence.
- Preserve cause-and-effect wherever it exists.

2.5) PRESERVE NARRATIVE CONTINUITY
- Each paragraph must clearly follow from the previous one.
- If a line feels interchangeable or episodic, rewrite locally to restore cause-and-effect.
- Do NOT reorder events, but clarify consequence if needed.

3) Make sure it sounds like a REAL HUMAN SPEAKING
- Natural spoken cadence.
- Imperfect but coherent.
- Emotional stress is shown through urgency, resistance, or hesitation — not poetry.
- Do NOT turn the narrator into constant panic or rambling.

4) Ensure the script MAKES SENSE
- Events should follow a clear progression.
- Do not jumble the order of events.
- Do not collapse multiple moments into one confusing paragraph.
- Do NOT smooth or clarify the ending if it is already unsettling.
- Only rewrite the ending if it is genuinely confusing, not just abrupt.

COMPRESSION RULE (CRITICAL):
- If two adjacent paragraphs express the same type of consequence, merge them
- Prefer one strong escalation over two mild ones
- Remove repetition even if it is emotionally valid
- Do NOT remove the first moment where the narrator realizes a coping strategy has failed

WHEN TO REWRITE:
- Rewrite ONLY if a line weakens tension, clarity, or realism.
- If the script already works, return it unchanged.
- Prefer small, local edits over full rewrites.

EDITING RULES:
- Do NOT add lore, explanations, causes, rules, or symbolism.
- Do NOT aestheticize or philosophize the horror.
- Do NOT add metaphors.
- Do NOT add filler panic phrases.
- Do NOT add sentence fragments unless they sound like real speech.

STYLE GUIDELINES:
- Short paragraphs (1–2 sentences).
- Clear, spoken language.
- Concrete details over abstract dread.
- Monetization safe.
- Keep the final script under 200 words.

OUTPUT FORMAT (STRICT):
- Output MUST be ONLY the spoken script text.
- Do NOT output ANY of the following: analysis, explanation, summary, rationale, notes, bullets, headings, quotes, JSON, code fences, or meta commentary.
- Do NOT include any sentence that refers to "this script", "this version", "the story", "the fear", "the horror", or any evaluation of quality.
- Start immediately with the first sentence of the script.
- End immediately with the last sentence of the script.
- No extra lines before or after.

If you violate the output format, the output is unusable.

The draft script begins below.
"""

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
            "model": "mixtral-8x7b",
        },
    }

    out_path = run_folder / "script.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
