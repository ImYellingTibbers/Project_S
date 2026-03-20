"""
Step 4: Stitch three story videos into one compiled video.

Structure of the output:
  [Opening title card]  - main title + "Story #1: <mini_title>"
  [Story 1 video]
  [Transition card]     - "Story #2: <mini_title>"
  [Story 2 video]
  [Transition card]     - "Story #3: <mini_title>"
  [Story 3 video]

Title cards are rendered as 4K PNG via Pillow, converted to video segments
via FFmpeg (matching story video specs), then everything is concatenated.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ============================================================
# Paths
# ============================================================

CHANNEL_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = CHANNEL_ROOT / "runs"
SFX_DIR = CHANNEL_ROOT / "src" / "assets" / "sfx"
VIDEO_PLAN_PATH = CHANNEL_ROOT / "video_plan.json"

# Card specs — must match story video output
CARD_W, CARD_H = 3840, 2160
FPS = 30
OPENING_DURATION = 8    # seconds
TRANSITION_DURATION = 5  # seconds

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


# ============================================================
# Font helpers
# ============================================================

def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""

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


# ============================================================
# Title card rendering
# ============================================================

def render_card(lines_top: list[str], lines_bottom: list[str], out_path: Path):
    """
    Render a title card PNG.
    lines_top: large text (e.g., main video title)
    lines_bottom: smaller text (e.g., "Story #1: He Knew My Schedule")
    """
    img = Image.new("RGB", (CARD_W, CARD_H), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)

    padding = 160  # px from edges
    max_text_w = CARD_W - padding * 2

    # ---- Top block (main title or story label) ----
    font_top = load_font(130)
    wrapped_top = []
    for line in lines_top:
        wrapped_top.extend(wrap_text(line, font_top, max_text_w, draw))

    # ---- Bottom block (sub-label) ----
    font_bottom = load_font(80)
    wrapped_bottom = []
    for line in lines_bottom:
        wrapped_bottom.extend(wrap_text(line, font_bottom, max_text_w, draw))

    # Measure total block height
    def block_height(wrapped, font, line_gap=20):
        if not wrapped:
            return 0
        sample_bbox = draw.textbbox((0, 0), "Ag", font=font)
        line_h = sample_bbox[3] - sample_bbox[1]
        return len(wrapped) * (line_h + line_gap) - line_gap

    top_h = block_height(wrapped_top, font_top, line_gap=24)
    bot_h = block_height(wrapped_bottom, font_bottom, line_gap=16)
    separator_h = 60 if (wrapped_top and wrapped_bottom) else 0

    total_h = top_h + separator_h + bot_h
    y_start = (CARD_H - total_h) // 2

    # Draw top block
    y = y_start
    for line in wrapped_top:
        bbox = draw.textbbox((0, 0), line, font=font_top)
        x = (CARD_W - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font_top, fill=(255, 255, 255))
        y += (bbox[3] - bbox[1]) + 24

    y += separator_h

    # Draw bottom block in a dimmer white
    for line in wrapped_bottom:
        bbox = draw.textbbox((0, 0), line, font=font_bottom)
        x = (CARD_W - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font_bottom, fill=(200, 200, 200))
        y += (bbox[3] - bbox[1]) + 16

    img.save(str(out_path), format="PNG")


# ============================================================
# FFmpeg helpers
# ============================================================

def png_to_video(png_path: Path, out_path: Path, duration: float, sfx_path: Path | None):
    """Convert a PNG card image into a video segment with optional SFX audio."""
    # Build silent video first
    silent_path = out_path.with_suffix(".silent.mp4")

    vf = (
        f"fade=t=in:st=0:d=0.5,"
        f"fade=t=out:st={duration - 0.5}:d=0.5"
    )

    cmd_video = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(png_path),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "h264_nvenc",
        "-preset", "p7",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(silent_path),
    ]
    subprocess.run(cmd_video, check=True)

    if sfx_path and sfx_path.exists():
        cmd_audio = [
            "ffmpeg", "-y",
            "-i", str(silent_path),
            "-i", str(sfx_path),
            "-filter_complex",
            f"[1:a]volume=0.4,atrim=duration={duration}[sfx];[sfx]apad=pad_dur={duration}[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", str(duration),
            str(out_path),
        ]
        subprocess.run(cmd_audio, check=True)
        silent_path.unlink(missing_ok=True)
    else:
        # No SFX — add silent audio track so concat works cleanly
        cmd_mux = [
            "ffmpeg", "-y",
            "-i", str(silent_path),
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_path),
        ]
        subprocess.run(cmd_mux, check=True)
        silent_path.unlink(missing_ok=True)


def fix_story_audio(video_path: Path, temp_dir: Path) -> Path:
    """
    Re-encode the audio track of a story video to clean 48 kHz stereo AAC.
    The story pipeline produces malformed AAC (FFmpeg built-in encoder 'too many
    bits' issue) that crashes the concat step. We fix it here by processing each
    file individually — individual files sync much better than the concat demuxer.
    """
    fixed_path = temp_dir / f"{video_path.parent.name}_fixed.mp4"

    # Step 1: extract audio to WAV with full error tolerance.
    # Processing individually (not through concat) gives the decoder a clean start.
    wav_path = temp_dir / f"{video_path.parent.name}_audio.wav"
    cmd_extract = [
        "ffmpeg", "-y",
        "-fflags", "+discardcorrupt+genpts",
        "-err_detect", "ignore_err",
        "-i", str(video_path),
        "-vn",
        "-ar", "48000",
        "-ac", "2",
        "-c:a", "pcm_s16le",
        str(wav_path),
    ]
    subprocess.run(cmd_extract, check=False)  # best-effort; silence for bad frames

    # Step 2: remux: copy video + encode clean WAV → AAC.
    cmd_remux = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(wav_path),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        str(fixed_path),
    ]
    subprocess.run(cmd_remux, check=True)

    wav_path.unlink(missing_ok=True)
    return fixed_path


def concat_segments(segment_paths: list[Path], story_indices: set[int], out_path: Path):
    """Concatenate video segments using the FFmpeg concat demuxer.

    Story segments (identified by story_indices) are pre-processed to fix their
    malformed AAC before being included. Title card segments are already clean.
    All audio is normalised to 48 kHz stereo so stream-copy works cleanly.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        fixed_paths: list[Path] = []
        for i, seg in enumerate(segment_paths):
            if i in story_indices:
                print(f"[STITCH] Fixing story audio for segment {i}...")
                fixed_paths.append(fix_story_audio(seg, tmp_dir))
            else:
                fixed_paths.append(seg)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, dir=tmp) as f:
            for seg in fixed_paths:
                f.write(f"file '{seg.resolve()}'\n")
            list_file = Path(f.name)

        # All segments now have matching codec/params — use stream copy.
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-movflags", "+faststart",
            str(out_path),
        ]
        subprocess.run(cmd, check=True)


# ============================================================
# Main
# ============================================================

def main():
    if not VIDEO_PLAN_PATH.exists():
        raise RuntimeError(f"video_plan.json not found at {VIDEO_PLAN_PATH}")

    plan = json.loads(VIDEO_PLAN_PATH.read_text(encoding="utf-8"))
    main_title = plan["main_title"]
    sanitized = plan["sanitized_title"]
    stories = plan["stories"]
    run_folders = plan.get("run_folders", [])

    if len(run_folders) < 3:
        raise RuntimeError(
            f"Expected 3 run folders in video_plan.json, found {len(run_folders)}.\n"
            "Make sure all 3 story pipeline runs completed successfully."
        )

    # Verify each run folder has video_final.mp4
    story_videos: list[Path] = []
    for folder_name in run_folders[:3]:
        video_path = RUNS_DIR / folder_name / "video_final.mp4"
        if not video_path.exists():
            raise RuntimeError(f"Missing video: {video_path}")
        story_videos.append(video_path)

    # Output folder
    out_dir = RUNS_DIR / sanitized
    out_dir.mkdir(parents=True, exist_ok=True)

    sfx_path = SFX_DIR / "spooky_bass_start.mp3"
    cards_dir = out_dir / "_cards"
    cards_dir.mkdir(exist_ok=True)

    segments: list[Path] = []
    story_segment_indices: set[int] = set()  # tracks which segment indices are story videos

    # ------------------------------------------------------------------
    # Opening title card
    # ------------------------------------------------------------------
    print("[STITCH] Rendering opening title card...")
    opening_png = cards_dir / "opening.png"
    render_card(
        lines_top=[main_title],
        lines_bottom=[f"Story #1: {stories[0]['mini_title']}"],
        out_path=opening_png,
    )
    opening_vid = cards_dir / "opening.mp4"
    png_to_video(opening_png, opening_vid, OPENING_DURATION, sfx_path)
    segments.append(opening_vid)

    # ------------------------------------------------------------------
    # Stories + transition cards
    # ------------------------------------------------------------------
    for i, video_path in enumerate(story_videos):
        story_segment_indices.add(len(segments))
        segments.append(video_path)

        if i < 2:
            next_story = stories[i + 1]
            print(f"[STITCH] Rendering transition card {i + 1}→{i + 2}...")
            trans_png = cards_dir / f"transition_{i + 1}_{i + 2}.png"
            render_card(
                lines_top=[f"Story #{i + 2}"],
                lines_bottom=[next_story["mini_title"]],
                out_path=trans_png,
            )
            trans_vid = cards_dir / f"transition_{i + 1}_{i + 2}.mp4"
            png_to_video(trans_png, trans_vid, TRANSITION_DURATION, sfx_path)
            segments.append(trans_vid)

    # ------------------------------------------------------------------
    # Concatenate
    # ------------------------------------------------------------------
    out_video = out_dir / "compiled_final.mp4"
    print(f"[STITCH] Concatenating {len(segments)} segments...")
    concat_segments(segments, story_segment_indices, out_video)

    print(f"\n[STITCH] Done.")
    print(f"         {out_video}")


if __name__ == "__main__":
    main()
