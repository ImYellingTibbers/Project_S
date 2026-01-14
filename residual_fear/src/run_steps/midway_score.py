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


def extract_json(text: str) -> dict:
    if not text or not text.strip():
        raise RuntimeError("Judge LLM returned empty response")

    text = text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Find first JSON object
    first_brace = text.find("{")
    if first_brace == -1:
        raise RuntimeError(f"Judge LLM did not return JSON:\n{text[:300]}")

    text = text[first_brace:]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt to auto-fix missing closing braces
        open_braces = text.count("{")
        close_braces = text.count("}")

        if close_braces < open_braces:
            text = text + ("}" * (open_braces - close_braces))

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Invalid JSON from Judge LLM:\n{text[:500]}"
            ) from e


# ---------------------------
# Judge Prompt
# ---------------------------

JUDGE_PROMPT = """
You are a STRICT EVALUATION SYSTEM for YouTube Shorts confessional horror, you specialize in creating and judging youtube shorts that get millions of views with high retention, specifically in the confessional horror stories genre. 

You are NOT allowed to:
- explain
- suggest improvements
- rewrite content
- summarize creatively
- add commentary

You MUST:
- evaluate ONLY structure and virality-relevant signals
- output ONLY valid JSON in the exact format below

--------------------------------
EVALUATION GOAL
--------------------------------
Assess how likely this content is to achieve:
- high retention
- strong algorithmic distribution
- large view counts (hundreds of thousands to millions)

You are NOT predicting exact views.
You are classifying QUALITY and VIRAL POTENTIAL.

--------------------------------
WHAT YOU ARE GIVEN
--------------------------------
1. A spoken horror script
2. A visual storyboard that follows the script
3. AI image generation prompts that follow the storyboard

They represent a single YouTube Shorts video concept.

--------------------------------
SCORING RULES
--------------------------------
Score each category from 0.0 to 10.0

Use the FULL range.
Do NOT cluster everything around 7–8.
Weak content must score low.

Definitions:

- hook_strength:
  Does the first line force a scroll-stop via immediacy or violation?

- anchor_clarity:
  Is there a single repeating concrete element the viewer can track?

- escalation_quality:
  Does the threat clearly intensify in proximity, frequency, or consequence?

- boundary_violation:
  Does the threat cross into personal, private, or safe spaces?

- public_relatability:
  Does the story move beyond private isolation into shared or public contexts?

- ending_inevitability:
  Does the ending imply unavoidable danger without explanation?

--------------------------------
OVERALL SCORE
--------------------------------
overall_score is the weighted average:
- hook_strength (20%)
- anchor_clarity (15%)
- escalation_quality (20%)
- boundary_violation (15%)
- public_relatability (15%)
- ending_inevitability (15%)

--------------------------------
VIEW TIER CLASSIFICATION
--------------------------------
Assign ONE tier:

- "under_100k"
- "100k_500k"
- "500k_1M"
- "1M_2M"
- "2M_plus"

This is a qualitative tier, not a prediction.

--------------------------------
OUTPUT FORMAT (STRICT)
--------------------------------
{
  "overall_score": number,
  "scores": {
    "hook_strength": number,
    "anchor_clarity": number,
    "escalation_quality": number,
    "boundary_violation": number,
    "public_relatability": number,
    "ending_inevitability": number
  },
  "likely_view_tier": string,
  "confidence": "low" | "medium" | "high"
}

--------------------------------
BEGIN EVALUATION
--------------------------------
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
      "SYSTEM:\n"
      "You are a JSON-only evaluation engine.\n"
      "You MUST output ONLY valid JSON.\n"
      "DO NOT include explanations, analysis, summaries, or text.\n"
      "If you include anything outside JSON, the output is invalid.\n\n"
      + JUDGE_PROMPT
      + "\n\nINPUT:\n"
      + json.dumps(judge_input, indent=2)
      + "\n\nOUTPUT (JSON ONLY):\n"
  )

    raw = call_llm(prompt)

    try:
        judged = extract_json(raw)
    except RuntimeError:
        # One forced retry with hard JSON constraint
        retry_prompt = (
            "SYSTEM:\n"
            "OUTPUT ONLY JSON.\n"
            "NO TEXT.\n"
            "NO EXPLANATIONS.\n"
            "NO ANALYSIS.\n"
            "JSON ONLY.\n\n"
            + prompt
        )
        raw = call_llm(retry_prompt)
        judged = extract_json(raw)

    output = {
        "schema": {"name": "midway_score", "version": "1.0"},
        "run_id": script_json.get("run_id"),
        "created_at": utc_now_iso(),
        "input": judge_input,
        "judgement": judged,
    }

    out_path = run_folder / "midway_score.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
