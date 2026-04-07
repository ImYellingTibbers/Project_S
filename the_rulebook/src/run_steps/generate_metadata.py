"""
Step 5: Generate YouTube metadata for the Rulebook video.

Reads full_script.txt from the latest run, calls the LLM to write:
  - SEO-optimized YouTube title
  - Description
  - Tags (base tags + LLM-generated niche tags)

Writes metadata.json + thumbnail.jpg to the run folder.
"""

from __future__ import annotations

import json
import os
import time
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

BASE_TAGS = [
    "scary stories",
    "horror stories",
    "workplace horror",
    "true scary stories",
    "night shift horror",
    "horror narration",
    "creepypasta rules",
    "don't break the rules",
    "horror compilation",
    "the rulebook",
    "rule based horror",
    "job horror stories",
]


def call_llm(messages, temperature=0.4, max_tokens=2000) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    for attempt in range(8):
        try:
            r = requests.post(OPENROUTER_URL, headers=HEADERS, json=payload, timeout=120)
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            wait = 30 * (attempt + 1)
            print(f"[META] Network error ({type(e).__name__}) — waiting {wait}s before retry {attempt + 1}/8")
            time.sleep(wait)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            wait = 30 * (attempt + 1)
            print(f"[META] HTTP {r.status_code} — waiting {wait}s before retry {attempt + 1}/8")
            time.sleep(wait)
            continue
        r.raise_for_status()
        content = r.json()["choices"][0]["message"].get("content", "").strip()
        if not content:
            raise RuntimeError("LLM returned empty content")
        return content
    raise RuntimeError("call_llm failed after 8 retries")


def get_latest_run() -> Path:
    candidates = [
        d for d in RUNS_DIR.iterdir()
        if d.is_dir() and (d / "script" / "full_script.txt").exists()
    ]
    if not candidates:
        raise RuntimeError("No run folder with full_script.txt found")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def generate_metadata(script_text: str) -> dict:
    # Trim to first 600 words so the prompt stays manageable
    trimmed = " ".join(script_text.split()[:600])

    system = (
        "You are a YouTube SEO specialist for a horror narration channel called The Rulebook.\n"
        "The channel features workplace horror stories where employees discover a set of strange rules "
        "on the job and must navigate what happens when those rules are broken.\n"
        "Stories are first-person, grounded, realistic — no supernatural, just deeply unsettling human behavior "
        "and consequences.\n\n"
        "You must output STRICT JSON ONLY. No markdown. No commentary.\n"
        "Output exactly this schema:\n"
        "{\n"
        '  "seo_title": "...",\n'
        '  "description": "...",\n'
        '  "niche_tags": ["tag1", "tag2", ...]\n'
        "}\n\n"
        "RULES:\n"
        "- seo_title: 60-70 characters. Include a power word (True, Real, Disturbing, Chilling, Terrifying). "
        "Reference the rules or workplace setting. Keep it compelling.\n"
        "- description: 150-200 words. Start with a 2-3 sentence hook about discovering strange rules at a job. "
        "Tease the story's setting and what goes wrong. End with a call to watch/subscribe. "
        "Do NOT include links or hashtags.\n"
        "- niche_tags: 15-20 specific tags. Focus on the workplace type, the kind of rules, "
        "what goes wrong (e.g. 'overnight security horror', 'warehouse job horror', 'strange rules at work'). "
        "Mix 2-word and 3-word phrases. No single generic words. All lowercase. Each tag under 30 characters."
    )

    user = (
        "Here is the beginning of the story script:\n\n"
        f"{trimmed}\n\n"
        "Generate the YouTube metadata JSON."
    )

    raw = call_llm([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])

    data = json.loads(raw)

    all_tags = list(dict.fromkeys(
        BASE_TAGS + [t.lower().strip() for t in data.get("niche_tags", [])]
    ))

    return {
        "seo_title": data.get("seo_title", "The Rulebook — True Workplace Horror"),
        "description": data.get("description", ""),
        "tags": ", ".join(all_tags),
    }


# ============================================================
# Thumbnail composition
# ============================================================

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
        # Drop shadow
        draw.text((x + 5, y + 5), line, font=main_font, fill=BLACK)
        # Yellow with clean black outline
        _draw_outlined_text(draw, (x, y), line, main_font,
                            fill=YELLOW, outline=BLACK, outline_width=8)
        y += main_lh + main_gap

    return img


def compose_thumbnail(seo_title: str, run_dir: Path) -> Optional[Path]:
    """
    Compose a YouTube thumbnail from a mid-story chunk image.
    Uses chunk_03 as first preference (deeper into the story, more atmospheric).
    Saves to run_dir/thumbnail.jpg. Returns path or None if source image missing.
    """
    # Prefer a mid-story chunk — more atmospheric than the establishing shot
    source_img = None
    for i in [3, 4, 2, 5, 1, 0]:
        candidate = run_dir / "img" / f"chunk_{i:02d}.png"
        if candidate.exists():
            source_img = candidate
            break

    if source_img is None:
        print("[META] No chunk image found — skipping thumbnail composition")
        return None

    img = _fit_and_crop(Image.open(source_img).convert("RGB"))
    img = _apply_vignette(img)
    img = _render_text_block(img, seo_title)

    out_path = run_dir / "thumbnail.jpg"
    img.save(out_path, "JPEG", quality=88, optimize=True)
    size_kb = out_path.stat().st_size // 1024
    print(f"[META] Thumbnail written to {out_path} ({size_kb} KB)")
    return out_path


def main():
    run_dir = get_latest_run()
    print(f"[META] Generating metadata for run: {run_dir.name}")

    script_text = (run_dir / "script" / "full_script.txt").read_text(encoding="utf-8").strip()
    metadata = generate_metadata(script_text)

    out_path = run_dir / "metadata.json"
    out_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"[META] Written to {out_path}")
    print(f"[META] SEO title: {metadata['seo_title']}")
    print(f"[META] Tags: {metadata['tags'][:120]}...")

    compose_thumbnail(metadata["seo_title"], run_dir)


if __name__ == "__main__":
    main()
