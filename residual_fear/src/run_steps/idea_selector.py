import json
import random
import os
import re
import time
from sys import path
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, IDEA_SELECTOR_LLM_MODEL
from src.llm.qwen_instruct_llm import call_llm

def extract_json(text: str, max_repairs: int = 2) -> dict:
    text = text.strip()

    def strip_to_json(t: str) -> str:
        start = t.find("{")
        end = t.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found")
        return t[start:end + 1]

    def repair(t: str) -> str:
        t = t.replace("\u201c", '"').replace("\u201d", '"')
        t = t.replace("\u2019", "'")
        t = re.sub(r'//.*', '', t)
        t = re.sub(r'"\s*\n\s*', '" ', t)
        t = re.sub(r'"\s*score"\s*:\s*\d+\s*-\s*\d+', '"score": null', t)
        t = re.sub(r',\s*([}\]])', r'\1', t)
        return t

    last_error = None

    for _ in range(max_repairs + 1):
        try:
            block = strip_to_json(text)
            block = repair(block)
            return json.loads(block)
        except Exception as e:
            last_error = e
            time.sleep(0.1)

    raise ValueError(f"Invalid JSON returned by LLM:\n{text}") from last_error


def call_llm_with_retry(prompt: str, retries: int = 3) -> str:
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return call_llm(prompt)
        except Exception as e:
            last_error = e
            print(f"[idea_selector] LLM failure {attempt}/{retries}: {e}")
            time.sleep(0.5 * attempt)
    raise last_error


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_run_folder() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError("runs/ folder not found")
    run_folders = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()])
    if not run_folders:
        raise RuntimeError("No run folders found in runs/")
    return run_folders[-1]


def _contains_ellipsis(obj) -> bool:
    if isinstance(obj, str):
        return ("..." in obj) or ("…" in obj)
    if isinstance(obj, list):
        return any(_contains_ellipsis(x) for x in obj)
    if isinstance(obj, dict):
        return any(_contains_ellipsis(v) for v in obj.values())
    return False


SELECTION_PROMPT = """
You are selecting the strongest idea for a short-form horror video AND imagining the memory it would naturally come from.

Think like someone deciding what they are finally willing to confess.
Choose the idea that feels most dangerous to ignore or leave unresolved when told in first person.

PRIMARY SELECTION CRITERIA (MOST IMPORTANT):
- The idea must already include a clear loss that has occurred before narration
- The idea must imply that the narrator is ALREADY losing something (sleep, safety, access, control, ability to function)
- The anomaly must actively interfere with normal life, not just be observed
- The idea must make it clear that the narrator cannot simply ignore, delay, or leave the situation
- The situation must be getting worse THROUGH REPEAT VIOLATION, not discovery
- If the idea does not imply restriction, harm, or forced adaptation, it is invalid

CRITICAL FRAMING RULE (NON-NEGOTIABLE):
- The winning idea must be written as if the anomaly has already been happening before the narration begins
- Do NOT select or rewrite ideas framed as first discovery (e.g. "discovers", "finds", "investigates", "comes across")
- The idea must imply the narrator is already living inside the problem, not encountering it for the first time
- If the idea sounds like an inciting incident instead of an ongoing violation, it is invalid
- If the idea could be summarized as “this is where it started,” it is invalid

SECONDARY CRITERIA:
- Believability when told as a calm recollection
- Escalation through persistence, proximity, or consequence
- Supernatural elements are allowed but must remain implied or observed only

AVOID SELECTING IDEAS THAT:
- Require cameras, recordings, screens, or footage to perceive the anomaly
- Are strange but ultimately harmless
- Can be solved by simply leaving, waiting, or ignoring the situation
- Rely only on mood, atmosphere, or curiosity
- Feel like anecdotes instead of confessions
- Bundle multiple strange events instead of one escalating violation
- Rely on thematic horror (identity, replacement) without a clear physical anchor

RULES:
- Evaluate ideas independently (ignore order)
- Must work as a 45–55 second first-person narration
- Implied horror only (no gore, no lore, no explanations)
- Avoid gimmicks or twists that require explanation

For the winning idea:
- Select the idea ONLY IF it is already framed as an ONGOING situation
- Do NOT fix, rescue, or rewrite weak ideas
- If an idea requires reframing to work, it is invalid
- Avoid verbs like "discovers", "finds", "investigates", or "comes across"
- Briefly explain WHY it works as a short horror story
- Focus on stakes, escalation, and consequence
- Provide a short prep story that feels like a memory the narrator is recalling
- Avoid verbs like "finds", "discovers", "investigates"
- The idea must feel like something that has been happening for a while

CRITICAL CONSTRAINT:
- Prefer ideas with ONE dominant physical anomaly.
- If an idea introduces multiple unrelated anomalies (keys + doors + objects + identity), it is weaker.
- The best idea can be summarized as: "One thing keeps happening, and it’s getting worse."

PREP STORY RULES:
- Exactly 2 sentences
- First person, past tense
- Conversational + confessional (sounds spoken), with understated dread (not purple prose)
- Mention the location once
- Name the ONE physical anomaly explicitly using a concrete noun
- Include one quick human reaction (e.g., "I froze", "I laughed", "I told myself it was nothing")
- Establish that the anomaly was already happening before the narration
- End sentence 2 with an unresolved escalation (it persists / gets closer / happens again)
- No resolution, no explanation
- Do NOT introduce any other anomalies
- NEVER use "..." or the ellipsis character "…" anywhere

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
    "prep_story": "2 sentence first-person memory seed"
  }
}
""".strip()


def main():
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

    prompt = (
        "You evaluate horror story ideas.\n"
        "Return ONLY valid minified JSON.\n"
        "No comments, no explanations, no schema examples.\n"
        "All strings must be single-line.\n\n"
        + selection_prompt
    )


    for attempt in range(1, 4):
        raw = call_llm_with_retry(prompt)
        selection = extract_json(raw)

        if _contains_ellipsis(selection):
            print(
                f"[idea_selector] Rejecting output with ellipses/truncation "
                f"(attempt {attempt}/3). Retrying..."
            )
            time.sleep(0.5 * attempt)
            continue

        break
    else:
        raise RuntimeError(
            "idea_selector failed: ellipses/truncation persisted after retries."
        )

    prep_story = selection["winner"].get("prep_story", "")

    out = {
        "schema": {"name": "idea_selector", "version": "0.6.1"},
        "run_id": None,
        "created_at": utc_now_iso(),
        "source": "idea_generator.json",
        "ideas_considered": len(ideas),
        "data": {
            "scored": selection.get("scored", []),
            "top_three": selection.get("top_three", []),
            "winner": {
                "idea": selection["winner"]["idea"],
                "reason": selection["winner"]["reason"],
                "prep_story": {
                    "text": prep_story,
                    "purpose": "bridge_to_scriptwriter"
                }
            }
        }
    }

    out_path = run_folder / "idea.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
