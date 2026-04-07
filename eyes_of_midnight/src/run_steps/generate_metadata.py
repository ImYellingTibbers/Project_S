"""
Step 5: Generate YouTube metadata for the compiled video.

Reads video_plan.json + all 3 scripts, calls the LLM to write:
  - SEO-optimized YouTube title
  - Description
  - Tags (base tags + LLM-generated niche tags)

Writes metadata.json to runs/{sanitized_title}/metadata.json
Writes thumbnail.jpg to runs/{sanitized_title}/thumbnail.jpg
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

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

    # Merge base tags + niche tags, deduplicated, output as comma-separated string
    all_tags = list(dict.fromkeys(
        BASE_TAGS + [t.lower().strip() for t in data.get("niche_tags", [])]
    ))

    return {
        "main_title": main_title,
        "seo_title": data.get("seo_title", main_title),
        "description": data.get("description", ""),
        "tags": ", ".join(all_tags),
        "story_titles": story_titles,
    }


FONT_CANDIDATES = [
    str(Path(__file__).resolve().parents[3] / "assets/fonts/Anton-Regular.ttf"),
    "/usr/share/fonts/opentype/bebas-neue/BebasNeue-Bold.otf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

THUMB_W, THUMB_H = 1920, 1080


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font,
    fill: tuple,
    outline: tuple,
    outline_width: int = 6,
) -> None:
    x, y = xy
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def _apply_vignette(img: Image.Image) -> Image.Image:
    """Darken edges so text area is readable while center stays visible."""
    overlay = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    top_depth = int(THUMB_H * 0.50)
    bot_depth = int(THUMB_H * 0.20)
    side_depth = int(THUMB_W * 0.06)
    for i in range(top_depth):
        a = int(170 * (1 - i / top_depth) ** 1.6)
        d.line([(0, i), (THUMB_W, i)], fill=(0, 0, 0, a))
    for i in range(bot_depth):
        a = int(100 * (1 - i / bot_depth) ** 1.6)
        d.line([(0, THUMB_H - 1 - i), (THUMB_W, THUMB_H - 1 - i)], fill=(0, 0, 0, a))
    for i in range(side_depth):
        a = int(60 * (1 - i / side_depth) ** 1.6)
        d.line([(i, 0), (i, THUMB_H)], fill=(0, 0, 0, a))
        d.line([(THUMB_W - 1 - i, 0), (THUMB_W - 1 - i, THUMB_H)], fill=(0, 0, 0, a))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _fit_and_crop(img: Image.Image) -> Image.Image:
    img_ratio = img.width / img.height
    target_ratio = THUMB_W / THUMB_H
    if img_ratio > target_ratio:
        new_h = THUMB_H
        new_w = int(new_h * img_ratio)
    else:
        new_w = THUMB_W
        new_h = int(new_w / img_ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - THUMB_W) // 2
    top = (new_h - THUMB_H) // 2
    return img.crop((left, top, left + THUMB_W, top + THUMB_H))


def _render_text_block(img: Image.Image, seo_title: str) -> Image.Image:
    """
    Split title at ':' for two-tier layout.
    Top line: smaller white text. Bottom: large yellow with black outline + drop shadow.
    Separated by a thin red accent bar.
    """
    draw = ImageDraw.Draw(img)
    padding = 90
    max_text_w = THUMB_W - padding * 2

    YELLOW = (255, 218, 0)
    WHITE = (230, 230, 230)
    ACCENT_RED = (190, 15, 15)
    BLACK = (0, 0, 0)

    if ":" in seo_title:
        tag_raw, main_raw = seo_title.split(":", 1)
        tag_text = tag_raw.strip().upper()
        main_text = main_raw.strip().upper()
    else:
        tag_text = None
        main_text = seo_title.upper()

    tag_font = _load_font(62) if tag_text else None

    font_size = 120
    main_font = _load_font(font_size)
    main_lines = _wrap_text(main_text, main_font, max_text_w, draw)
    while len(main_lines) > 3 and font_size > 72:
        font_size -= 6
        main_font = _load_font(font_size)
        main_lines = _wrap_text(main_text, main_font, max_text_w, draw)

    def lh(font):
        bb = draw.textbbox((0, 0), "Ag", font=font)
        return bb[3] - bb[1]

    tag_lh = lh(tag_font) + 10 if tag_font else 0
    accent_h = 5
    accent_pad = 18
    main_lh = lh(main_font)
    main_gap = 12

    total_h = tag_lh
    if tag_text:
        total_h += accent_h + accent_pad * 2
    total_h += len(main_lines) * main_lh + max(0, len(main_lines) - 1) * main_gap

    y_center = int(THUMB_H * 0.36)
    y = y_center - total_h // 2

    if tag_text and tag_font:
        bb = draw.textbbox((0, 0), tag_text, font=tag_font)
        x = (THUMB_W - (bb[2] - bb[0])) // 2
        _draw_outlined_text(draw, (x, y), tag_text, tag_font,
                            fill=WHITE, outline=BLACK, outline_width=4)
        y += tag_lh
        y += accent_pad
        bar_w = int(THUMB_W * 0.38)
        bar_x = (THUMB_W - bar_w) // 2
        draw.rectangle([(bar_x, y), (bar_x + bar_w, y + accent_h)], fill=ACCENT_RED)
        y += accent_h + accent_pad

    for line in main_lines:
        bb = draw.textbbox((0, 0), line, font=main_font)
        x = (THUMB_W - (bb[2] - bb[0])) // 2
        # Drop shadow — offset copy in black before the main text
        draw.text((x + 5, y + 5), line, font=main_font, fill=BLACK)
        # Yellow with clean black outline
        _draw_outlined_text(draw, (x, y), line, main_font,
                            fill=YELLOW, outline=BLACK, outline_width=8)
        y += main_lh + main_gap

    return img


def compose_thumbnail(
    seo_title: str,
    run_folders: List[str],
    out_dir: Path,
) -> Optional[Path]:
    """Compose a YouTube thumbnail from story 1's thumbnail_a.png."""
    source_img = None
    for folder_name in run_folders[:3]:
        candidate = RUNS_DIR / folder_name / "img" / "thumbnail_a.png"
        if candidate.exists():
            source_img = candidate
            break

    if source_img is None:
        print("[META] No thumbnail_a.png found — skipping thumbnail composition")
        return None

    img = _fit_and_crop(Image.open(source_img).convert("RGB"))
    img = _apply_vignette(img)
    img = _render_text_block(img, seo_title)

    out_path = out_dir / "thumbnail.jpg"
    img.save(out_path, "JPEG", quality=88, optimize=True)
    size_kb = out_path.stat().st_size // 1024
    print(f"[META] Thumbnail written to {out_path} ({size_kb} KB)")
    return out_path


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
    print(f"[META] Tags: {metadata['tags'][:120]}...")

    compose_thumbnail(metadata["seo_title"], run_folders, out_dir)


if __name__ == "__main__":
    main()
