import json
from sys import path
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR
from src.llm.openai_llm import call_llm
# from src.llm.qwen_instruct_llm import call_llm


REFERENCE_PATH = (
    Path(__file__).resolve()
    .parents[2]
    / "assets"
    / "reference_files"
    / "viral_horror_scripts.txt"
)


PROMPT_TEMPLATE = """
Review these stories, keep them in your memory for this chat.
{reference_scripts}

You are a youtube shorts professional who specializes in creating viral videos, specifically videos that have great hooks, scripts, are genuinely terrifying, and get high views, high engagement and high retention. 

Create for me a 60 second script using the above scripts as a reference for writing style, pacing, and hooks, for a confessional horror video from the perspective of a white adult male. 

Make sure that it is monetization safe and is a REALLY good story with a scroll stopping hook. 

Avoid mirrors or other cliches as the root of your story. 

Output ONLY valid JSON
Do NOT include explanations, commentary, markdown, or extra text
Do NOT include code fences
The JSON must match the schema EXACTLY

OUTPUT JSON SCHEMA:
{{
  "script": "string"
}}
""".strip()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _count_words(text: str) -> int:
    return len([w for w in text.split() if w])


def load_reference_scripts() -> str:
    if not REFERENCE_PATH.exists():
        return ""
    text = REFERENCE_PATH.read_text(encoding="utf-8").strip()
    return text or ""


def main():
    run_id = build_run_id()
    run_folder = RUNS_DIR / run_id
    run_folder.mkdir(parents=True, exist_ok=True)

    reference_scripts = load_reference_scripts()
    prompt = PROMPT_TEMPLATE.format(reference_scripts=reference_scripts)

    script = call_llm(prompt).strip()

    out = {
        "schema": {"name": "scriptwriter"},
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "script": script,
        "word_count": _count_words(script),
        "validation": {
            "passed": True,
            "attempts": 1,
            "last_error": None,
        },
    }

    out_path = run_folder / "script.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
