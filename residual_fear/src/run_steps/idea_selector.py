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
You are a ruthless YouTube Shorts producer. Your goal is to choose the ONE idea with the highest probability of going viral as a first-person horror confessional.

Pick the idea that:
- Stops the scroll instantly (threat is obvious in 1 sentence)
- Feels real (a normal life is being violated, not “spooky vibes”)
- Escalates fast (worsens through repeat violation)
- Has a clear irreversible cost already paid (sleep/safety/privacy/sanity/routine)
- Stays SIMPLE (one anomaly, one narrator, minimal setup)
- Has strong “I need to comment/share this” energy (creepy, unfair, personal)

SCORING (1–10):
Score each idea on viral potential using these signals:
1) Immediate hook potential (could be the first line of the script)
2) Personal violation + consequence (already losing something)
3) Escalation speed + inevitability (can’t ignore, can’t outwait)
4) Simplicity/clarity (one anomaly, instantly visualizable)
5) Freshness (doesn’t feel generic)

WINNER REQUIREMENTS:
- Do NOT rewrite ideas. Select as-is.
- If an idea is unclear, slow, harmless, or “discovery framed,” score it low.
- Prefer the idea that can end with a single devastating unresolved line.

PREP STORY (winner only):
Write EXACTLY 2 sentences, first-person, past tense, spoken/confessional.

Hard constraint: The prep_story must mention ONLY the single anomaly from the winner idea.
- You must reuse the same anomaly noun from the winner idea (e.g., "knocking", "hum", "clicking").
- Do NOT introduce any new objects or effects (no closets, lights, shadows, footprints, whispers, etc.) unless that exact element is already the anomaly in the winner idea.
- Do NOT add a second anomaly.

Sentence rules:
- Sentence 1 starts inside consequence (loss/restriction) and anchors the setting in one place (bedroom/hallway/apartment/etc).
- Sentence 1 includes the irreversible change already made.
- Sentence 2 ends with escalation (closer/louder/more frequent/less avoidable).
- No explanations, no lore.
- NEVER use "..." or the ellipsis character "…".

OUTPUT:
Return ONLY valid minified JSON with exactly these keys:
- scored: list of objects {idea, score, reason}
- top_three: list of 3 objects {idea, reason}
- winner: object {idea, reason, prep_story}
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
    winner_raw = str(selection["winner"].get("idea", "")).strip()

    if re.fullmatch(r"\d+", winner_raw):
        idx = int(winner_raw) - 1
        if 0 <= idx < len(shuffled):
            selection["winner"]["idea"] = shuffled[idx]["idea"]

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
