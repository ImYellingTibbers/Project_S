import json
from pathlib import Path
from datetime import datetime, timezone

from src.config import RUNS_DIR
from src.llm.qwen_instruct_llm import call_llm


# ---------------------------
# Utilities
# ---------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_run_folder() -> Path:
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    if not runs:
        raise RuntimeError("No run folders found")
    return runs[-1]


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def extract_json_strict(text: str) -> dict:
    """
    Extract JSON or raise immediately.
    """
    if not text:
        raise RuntimeError("Empty LLM response")

    text = text.strip()

    # Strip markdown
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("No JSON object found")

    candidate = text[start:end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON:\n{candidate[:500]}") from e


# ---------------------------
# Scoring
# ---------------------------

SCORE_KEYS = {
    "hook_strength",
    "anchor_clarity",
    "escalation_quality",
    "boundary_violation",
    "public_relatability",
    "ending_inevitability",
}


def normalize_judge_output(judged: dict) -> dict:
    if "scores" in judged and isinstance(judged["scores"], dict):
        return judged

    if SCORE_KEYS.issubset(judged.keys()):
        return {
            "scores": {k: judged[k] for k in SCORE_KEYS},
            "likely_view_tier": judged.get("likely_view_tier"),
            "confidence": judged.get("confidence"),
        }

    for key in ("evaluation", "result", "output"):
        if key in judged and isinstance(judged[key], dict):
            return normalize_judge_output(judged[key])

    raise RuntimeError("No recoverable score structure")


def coerce_scores(scores: dict) -> dict:
    cleaned = {}
    for k in SCORE_KEYS:
        try:
            cleaned[k] = float(scores.get(k, 0.0))
        except (TypeError, ValueError):
            cleaned[k] = 0.0

        cleaned[k] = max(0.0, min(10.0, cleaned[k]))

    if all(v == 0.0 for v in cleaned.values()):
        raise RuntimeError("All scores zero after coercion")

    return cleaned


def compute_overall_score(scores: dict) -> float:
    weights = {
        "hook_strength": 0.20,
        "anchor_clarity": 0.15,
        "escalation_quality": 0.20,
        "boundary_violation": 0.15,
        "public_relatability": 0.15,
        "ending_inevitability": 0.15,
    }

    total = sum(scores[k] * weights[k] for k in weights)
    return round(total, 2)


# ---------------------------
# Prompts
# ---------------------------

JUDGE_PROMPT = """
You are a STRICT EVALUATION SYSTEM for YouTube Shorts confessional horror.

You MUST output ONLY valid JSON in the exact structure provided.
Do NOT explain. Do NOT comment.

OUTPUT JSON:
{
  "scores": {
    "hook_strength": 0.0,
    "anchor_clarity": 0.0,
    "escalation_quality": 0.0,
    "boundary_violation": 0.0,
    "public_relatability": 0.0,
    "ending_inevitability": 0.0
  },
  "likely_view_tier": "under_100k",
  "confidence": "low"
}
""".strip()


REPAIR_PROMPT = """
You previously failed to output valid JSON.

TASK:
Convert the following evaluation into VALID JSON ONLY.

RULES:
- Output ONLY JSON
- Match this EXACT schema
- Use numeric scores 0.0–10.0

SCHEMA:
{
  "scores": {
    "hook_strength": 0.0,
    "anchor_clarity": 0.0,
    "escalation_quality": 0.0,
    "boundary_violation": 0.0,
    "public_relatability": 0.0,
    "ending_inevitability": 0.0
  },
  "likely_view_tier": "under_100k",
  "confidence": "low"
}

FAILED RESPONSE:
""".strip()


# ---------------------------
# Main
# ---------------------------

def main():
    run_folder = find_latest_run_folder()

    script_json = load_json(run_folder / "script.json")
    storyboard_json = load_json(run_folder / "storyboard.json")
    image_plan_json = load_json(run_folder / "image_plan.json")

    judge_input = {
        "script": script_json,
        "storyboard": storyboard_json,
        "image_plan": image_plan_json,
    }

    prompt = (
        "SYSTEM:\nJSON ONLY.\n\n"
        + JUDGE_PROMPT
        + "\n\nINPUT:\n"
        + json.dumps(judge_input, indent=2)
    )

    raw = call_llm(prompt)

    try:
        judged_raw = extract_json_strict(raw)
    except RuntimeError:
        repair_raw = call_llm(
            REPAIR_PROMPT + "\n\n" + raw.strip()
        )
        judged_raw = extract_json_strict(repair_raw)

    judged_norm = normalize_judge_output(judged_raw)
    scores = coerce_scores(judged_norm["scores"])

    judgement = {
        "scores": scores,
        "likely_view_tier": judged_norm.get("likely_view_tier", "under_100k"),
        "confidence": judged_norm.get("confidence", "low"),
        "overall_score": compute_overall_score(scores),
    }

    output = {
        "schema": {"name": "midway_score", "version": "1.0"},
        "run_id": script_json.get("run_id"),
        "created_at": utc_now_iso(),
        "input": judge_input,
        "judgement": judgement,
    }

    out_path = run_folder / "midway_score.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
