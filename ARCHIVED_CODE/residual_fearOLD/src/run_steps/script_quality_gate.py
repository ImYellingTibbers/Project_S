import json
import sys
from pathlib import Path
from datetime import datetime, timezone

from src.llm.qwen_instruct_llm import call_llm
from src.config import RUNS_DIR

QUALITY_PROMPT = """You are a PASS/FAIL quality gate for VIRAL YouTube Shorts horror confessionals.

Your job is NOT to rewrite, improve, or suggest.
Your job is to decide if this script is strong enough to ship as a retention-first horror short.

Default stance: FAIL unless it clearly meets viral mechanics.

You must answer ONLY with a JSON object.

CRITERIA (all must be true to PASS):

1) SHORTS STRUCTURE
- 6 to 8 paragraphs separated by blank lines.
- Most paragraphs are 1 sentence (2 max only if necessary).
- Word count is roughly 110–170. If far outside, FAIL.

2) HOOK (FIRST 2 SECONDS)
- The first sentence starts INSIDE CONSEQUENCE (loss/restriction/invasion).
- Structural losses (job, home, city, routine, relationship) count as valid consequences IF they are irreversible and tied to the anomaly.
- State-based loss statements (e.g., "I no longer sleep", "I stopped using my bed") ARE valid.
- Discovery framing only applies to observation-based openings ("I noticed", "It started", "One day", "I found").
- If the first sentence describes observation instead of loss, FAIL.

3) ONE DOMINANT ANOMALY
- The story revolves around one primary anomaly (one sensory/physical channel).
- No additional unrelated horror vectors. If multiple vectors drive the fear, FAIL.

4) ESCALATION DENSITY (RETENTION)
- Every paragraph introduces a NEW escalation: a new failure, restriction, invasion, or loss.
- No paragraph exists only to restate dread/fear. If any paragraph is filler, FAIL.

5) NO “TRY EVERYTHING” MONTAGE
- The script does NOT list multiple coping attempts in a row ("I tried X, I tried Y, I tried Z").
- If it does, FAIL (it kills pacing).

6) SNAP MOMENT (CRITICAL)
- There is at least one moment where the anomaly reacts as if it noticed a coping attempt (it counters it, anticipates it, escalates immediately after it).
- This must use the same anomaly (no new mechanics). If missing, FAIL.

7) REALISM / VOICE
- Sounds like a real person confessing under pressure: plain, direct, specific.
- Not poetic, not theatrical, not generic (“gnaws at my sanity” style lines). If it reads like fiction prose, FAIL.

8) ENDING (TRAP)
- Final line is a single unresolved sentence that implies it is worse tonight / closer / unavoidable.
- No wrap-up, no explanation, no comfort. If it resolves or softens, FAIL.

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


DISALLOWED_COMBINATIONS = [
    # True multi-vector conflicts (separate mechanisms)
    ("knife", "voice"),
    ("weapon", "voice"),
    ("song", "voice"),
    ("lullaby", "voice"),
    ("chain", "knife"),
]

ESCALATION_COMPATIBLE_TERMS = [
    # Allowed escalation expressions of the SAME anomaly
    ("click", "static"),
    ("hum", "static"),
    ("knock", "thud"),
    ("breath", "breathing"),
    ("footstep", "movement"),
]


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

    # HARD FAIL: anomaly density heuristic
    lower = script_text.lower()
    for a, b in DISALLOWED_COMBINATIONS:
        if a in lower and b in lower:
            # Allow escalation-compatible terms
            if any(
                ea in lower and eb in lower
                for ea, eb in ESCALATION_COMPATIBLE_TERMS
            ):
                continue

            out = {
                "schema": {"name": "script_quality_gate", "version": "1.0"},
                "run_id": run_id,
                "created_at": utc_now_iso(),
                "verdict": {
                    "pass": False,
                    "reason": "Multiple unrelated horror vectors detected",
                },
            }
    # Hard fail if first sentence lacks anomaly mention
    first_sentence = script_text.splitlines()[0].lower()
    if not any(
        k in first_sentence
        for k in ["knock", "click", "hum", "breath", "footstep", "static", "sound"]
    ):
        out = {
            "schema": {"name": "script_quality_gate", "version": "1.0"},
            "run_id": run_id,
            "created_at": utc_now_iso(),
            "verdict": {
                "pass": False,
                "reason": "First sentence lacks concrete anomaly reference",
            },
        }
        out_path = run_dir / "quality_gate.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print("[quality_gate] pass=False reason='First sentence lacks concrete anomaly reference'")
        return 1

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
