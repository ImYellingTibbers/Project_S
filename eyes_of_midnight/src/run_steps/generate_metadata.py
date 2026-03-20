"""
Step 5: Generate YouTube metadata for the compiled video.

Reads video_plan.json + all 3 scripts, calls the LLM to write:
  - SEO-optimized YouTube title
  - Description
  - Tags (base tags + LLM-generated niche tags)

Writes metadata.json to runs/{sanitized_title}/metadata.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found in environment")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemma-3-27b-it"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

CHANNEL_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = CHANNEL_ROOT / "runs"
VIDEO_PLAN_PATH = CHANNEL_ROOT / "video_plan.json"

# Base tags always included
BASE_TAGS = [
    "scary stories",
    "horror stories",
    "true horror stories",
    "real horror stories",
    "confessional horror",
    "true scary stories",
    "reddit horror stories",
    "horror narration",
    "scary true stories",
    "horror compilation",
    "mr nightmare style",
    "eyes of midnight",
]


def call_llm(messages, temperature=0.4, max_tokens=2000) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=120)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"].get("content", "").strip()
    if not content:
        raise RuntimeError("LLM returned empty content")
    return content


def load_scripts(run_folders: List[str]) -> List[str]:
    scripts = []
    for folder_name in run_folders[:3]:
        script_path = RUNS_DIR / folder_name / "script" / "full_script.txt"
        if script_path.exists():
            scripts.append(script_path.read_text(encoding="utf-8").strip())
        else:
            scripts.append("")
    return scripts


def generate_metadata(main_title: str, story_titles: List[str], scripts: List[str]) -> dict:
    # Trim scripts so the prompt doesn't get too large (first 400 words each)
    def trim(text: str, words: int = 400) -> str:
        return " ".join(text.split()[:words])

    script_summaries = "\n\n".join(
        f"Story {i + 1} - \"{story_titles[i]}\":\n{trim(scripts[i])}"
        for i in range(len(story_titles))
        if scripts[i]
    )

    system = (
        "You are a YouTube SEO specialist for a horror narration channel.\n"
        "You write metadata that helps horror fans discover the videos they want to watch.\n"
        "The channel is confessional, grounded, realistic horror — true-sounding stories.\n"
        "No supernatural, no jump scares — just deeply unsettling human behavior.\n\n"
        "You must output STRICT JSON ONLY. No markdown. No commentary.\n"
        "Output exactly this schema:\n"
        '{\n'
        '  "seo_title": "...",\n'
        '  "description": "...",\n'
        '  "niche_tags": ["tag1", "tag2", ...]\n'
        '}\n\n'
        "RULES:\n"
        "- seo_title: 60-70 characters. Can differ slightly from main_title for better SEO. "
        "Include a power word (True, Real, Disturbing, Chilling, Terrifying). "
        "Keep it compelling and specific.\n"
        "- description: 150-200 words. Start with a 2-3 sentence hook about the video's theme. "
        "Then briefly tease each of the 3 stories (1 sentence each, no spoilers). "
        "End with a call to watch/subscribe. Do NOT include links or hashtags in the description text.\n"
        "- niche_tags: 15-20 specific tags beyond the base tags. "
        "Focus on the specific situations in the stories (e.g., 'night shift horror', "
        "'parking garage encounter', 'stalker at work stories'). "
        "Mix 2-word and 3-word phrases. No single generic words. "
        "All lowercase. Each tag under 30 characters."
    )

    user = (
        f"Main video title: \"{main_title}\"\n\n"
        f"Story titles:\n"
        + "\n".join(f"  {i + 1}. {t}" for i, t in enumerate(story_titles))
        + f"\n\nScript excerpts:\n{script_summaries}\n\n"
        "Generate the YouTube metadata JSON."
    )

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )

    data = json.loads(raw)

    # Merge base tags + niche tags, deduplicated
    all_tags = list(dict.fromkeys(
        BASE_TAGS + [t.lower().strip() for t in data.get("niche_tags", [])]
    ))

    return {
        "main_title": main_title,
        "seo_title": data.get("seo_title", main_title),
        "description": data.get("description", ""),
        "tags": all_tags,
        "story_titles": story_titles,
    }


def main():
    if not VIDEO_PLAN_PATH.exists():
        raise RuntimeError(f"video_plan.json not found at {VIDEO_PLAN_PATH}")

    plan = json.loads(VIDEO_PLAN_PATH.read_text(encoding="utf-8"))
    main_title = plan["main_title"]
    sanitized = plan["sanitized_title"]
    stories = plan["stories"]
    run_folders = plan.get("run_folders", [])

    story_titles = [s["mini_title"] for s in stories]

    print(f"[META] Generating metadata for: {main_title}")

    scripts = load_scripts(run_folders)
    metadata = generate_metadata(main_title, story_titles, scripts)

    out_dir = RUNS_DIR / sanitized
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "metadata.json"
    out_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"[META] Written to {out_path}")
    print(f"[META] SEO title: {metadata['seo_title']}")
    print(f"[META] Tags ({len(metadata['tags'])}): {', '.join(metadata['tags'][:8])}...")


if __name__ == "__main__":
    main()
