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
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError("Judge LLM did not return JSON")
    return json.loads(text[start:end + 1])


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
        JUDGE_PROMPT
        + "\n\nINPUT:\n"
        + json.dumps(judge_input, indent=2)
        + "\n\nOUTPUT:\n"
    )

    raw = call_llm(prompt)
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
