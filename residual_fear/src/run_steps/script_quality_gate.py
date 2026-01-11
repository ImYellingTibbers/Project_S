import json
import sys
from pathlib import Path
from datetime import datetime, timezone

from src.llm.qwen_instruct_llm import call_llm
from src.config import RUNS_DIR


QUALITY_PROMPT = """You are a quality control evaluator for short-form horror scripts.

Your job is NOT to rewrite, improve, or suggest changes.
Your job is to decide whether this script is GOOD ENOUGH to ship.

Evaluate the script strictly as a YouTube Shorts horror confessional.

You must answer ONLY with a JSON object.

CRITERIA (all must be true to PASS):

1) HOOK
- The first sentence implies danger, loss, or restriction.
- It is NOT merely an observation or description.

2) CORE ANOMALY
- The story revolves around ONE physical anomaly.
- No unrelated threats or lateral horror elements appear.

3) ESCALATION
- The situation clearly worsens as the script progresses.
- The narrator attempts to cope, adapt, or endure, and it fails.

4) REALISM
- The narrator sounds like a real person under pressure.
- No poetic language, no theatrical panic, no obvious fiction tropes.

5) SHORTS FIT
- The story becomes threatening immediately.
- A viewer would not scroll away in the first 2 seconds.

6) IRREVERSIBILITY
- At least one permanent loss or point-of-no-return occurs.
- If the situation could still be escaped, undone, or waited out, FAIL.

7) DENSITY
- No paragraph exists solely to restate fear
- Each paragraph introduces a NEW restriction, failure, or loss

OUTPUT FORMAT (STRICT):
{
  "pass": true | false,
  "reason": "<short reason if false, or 'ok'>"
}

Do NOT include any suggestions.
Do NOT include any rewritten text.
Do NOT include analysis outside the JSON.

SCRIPT:
<<<SCRIPT>>>
"""


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: script_quality_gate.py <run_id>")

    run_id = sys.argv[1]
    run_dir = RUNS_DIR / run_id

    script_path = run_dir / "script.json"
    idea_path = run_dir / "idea.json"

    if not script_path.exists():
        raise RuntimeError("script.json not found")
    if not idea_path.exists():
        raise RuntimeError("idea.json not found")

    script_json = json.loads(script_path.read_text(encoding="utf-8"))
    script_text = script_json["script"].strip()

    prompt = QUALITY_PROMPT.replace("<<<SCRIPT>>>", script_text)

    raw = call_llm(prompt)

    try:
        verdict = json.loads(raw)
        passed = bool(verdict.get("pass"))
        reason = verdict.get("reason", "unknown")
    except Exception:
        verdict = {
            "pass": False,
            "reason": "Invalid JSON from quality gate model",
        }
        passed = False
        reason = verdict["reason"]

    out = {
        "schema": {"name": "script_quality_gate", "version": "1.0"},
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "verdict": {
            "pass": passed,
            "reason": reason,
        },
    }

    out_path = run_dir / "quality_gate.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"[quality_gate] pass={passed} reason='{reason}'")
    return 0 if passed else 1



if __name__ == "__main__":
    raise SystemExit(main())
