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
Based on this video transcript (to understand the style, pacing, and tone), create a new YouTube Shorts video idea designed to immediately stop viewers from scrolling and hold their attention through the final line.

00:00:00.080 in 1918 a boy from Japan bought a doll
00:00:02.560 for his little sister Okiku she named
00:00:04.720 the doll after herself and took it
00:00:06.560 everywhere to bed to meals even to the
00:00:09.120 market but one winter Okiku got sick and
00:00:12.000 never recovered she died at just 3 years
00:00:14.559 old heartbroken the family placed her
00:00:16.720 beloved doll on a home shelf to remember
00:00:18.720 her but soon something strange happened
00:00:20.960 the doll's hair originally cut short
00:00:23.119 began to grow at first it reached the
00:00:24.960 shoulders then the waist they trimmed it
00:00:26.800 but it kept growing one night the mother
00:00:28.800 claimed she heard soft footsteps near
00:00:30.560 that shelf another time the lights
00:00:32.320 flickered when someone tried to move the
00:00:33.920 doll the family became convinced their
00:00:36.000 daughter's spirit was inside it
00:00:37.520 eventually they entrusted it to Manenji
00:00:39.680 Temple where monks agreed to take care
00:00:41.600 for it visitors began reporting odd
00:00:44.000 chills or hearing someone whisper their
00:00:46.079 name when alone and the hair still grows
00:00:48.719 even now over a hundred years later the
00:00:50.719 monks say they still trim it and last
00:00:52.719 year one of them swore it smiled with
00:00:54.800 its eyes still wide


Then, write a full script for this new YouTube Shorts idea in the same viral style as the transcript provided — fast hook, engaging storytelling/facts, clear pacing, and designed to keep viewers watching until the end. 

Important: 
- Everything must be original (no copying). 
- Keep the script short, punchy, and optimized for ~60 seconds. 
- The hook must grab attention in the first 3 seconds. 
- Write it in a natural spoken style, not like a blog post. 
- Make sure the flow feels viral and shareable, just like the example shared.
- The opening should make it immediately clear that something has already gone wrong.
- The ending should leave the viewer with a new, unsettling realization rather than just stopping the story.
- Output script only, no timestamps

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
