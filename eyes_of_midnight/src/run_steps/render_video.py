from __future__ import annotations

import subprocess
from pathlib import Path
import sys
import random

from timing_plan import build_image_timing_plan

# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"
MUSIC_DIR = ROOT / "src" / "assets" / "music"
SFX_DIR = ROOT / "src" / "assets" / "sfx"

# ============================================================
# Helpers
# ============================================================

def get_latest_run() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError(f"Runs directory does not exist: {RUNS_DIR}")

    run_dirs = sorted(
        [d for d in RUNS_DIR.iterdir() if d.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not run_dirs:
        raise RuntimeError(f"No run directories found in {RUNS_DIR}")

    for run_dir in run_dirs:
        audio_ok = (run_dir / "audio" / "full_narration.wav").exists()
        script_ok = (run_dir / "script" / "paragraph_index.json").exists()
        visuals_ok = (run_dir / "script" / "visual_chunks.json").exists()
        img_dir_ok = (run_dir / "img").exists()

        if audio_ok and script_ok and visuals_ok and img_dir_ok:
            return run_dir

    raise RuntimeError(
        "No run directory contains required files:\n"
        "Required:\n"
        "  audio/full_narration.wav\n"
        "  script/paragraph_index.json\n"
        "  script/visual_chunks.json\n"
        "  img/ (directory)"
    )

def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    out = subprocess.check_output(cmd).decode().strip()
    return float(out)

def build_video_segments(run_dir: Path, image_timing: list[dict], fps: int) -> list[str]:
    segments = []

    for idx, item in enumerate(image_timing):
        img_path = run_dir / "img" / item["image"]
        duration = item["duration"]

        if not img_path.exists():
            raise RuntimeError(f"Missing image: {img_path}")

        segment_path = run_dir / "video" / f"seg_{idx:02d}.mp4"
        segment_path.parent.mkdir(parents=True, exist_ok=True)

        total_frames = int(duration * fps)

        vf = (
            f"zoompan="
            f"z='1+0.045*on/{total_frames}':"
            f"x='iw/2-(iw/zoom/2)+sin(on*0.003)*2':"
            f"y='ih/2-(ih/zoom/2)+cos(on*0.002)*2':"
            f"d=1:s=3840x2160,"
            f"fps={fps},"
            f"vignette=PI/3,"
            f"fade=t=in:st=0:d=0.5,"
            f"noise=alls=4:allf=t"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-t", f"{duration}",
            "-vf", vf,
            "-c:v", "h264_nvenc",
            "-preset", "p7",
            "-pix_fmt", "yuv420p",
            str(segment_path),
        ]

        subprocess.run(cmd, check=True)
        segments.append(str(segment_path))

    return segments

def concat_video_segments(segments: list[str], out_path: Path):
    list_file = out_path.parent / "segments.txt"
    list_file.write_text(
        "\n".join(f"file '{s}'" for s in segments),
        encoding="utf-8",
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_path),
    ]

    subprocess.run(cmd, check=True)

# ============================================================
# Main
# ============================================================

def main():
    run_dir = get_latest_run()
    
    image_timing = build_image_timing_plan(run_dir)

    if not image_timing:
        raise RuntimeError("Image timing plan is empty")

    audio_path = run_dir / "audio" / "full_narration.wav"
    bass_sting_path = SFX_DIR / "spooky_bass_start.mp3"
    if not bass_sting_path.exists():
        raise RuntimeError(f"Missing bass sting file: {bass_sting_path}")
    # --------------------------------------------------------
    # Select random ambient background audio
    # --------------------------------------------------------
    ambient_tracks = sorted(
        p for p in MUSIC_DIR.iterdir()
        if p.suffix.lower() in {".wav", ".mp3"}
    )
    if not ambient_tracks:
        raise RuntimeError(f"No ambient audio files found in {MUSIC_DIR}")
    bg_audio_path = random.choice(ambient_tracks)
    print(f"[AUDIO] Using ambient bed: {bg_audio_path.name}")
    
    fps = 30

    print("[VIDEO] Building image segments...")
    segments = build_video_segments(run_dir, image_timing, fps)

    video_only_path = run_dir / "video" / "video_only.mp4"
    concat_video_segments(segments, video_only_path)

    out_path = run_dir / "video_final.mp4"

    duration = get_audio_duration(audio_path)

    print(f"[VIDEO] Run: {run_dir.name}")
    print(f"[VIDEO] Duration: {duration:.2f}s")

    cmd = [
        "ffmpeg",
        "-y",

        "-i", str(video_only_path),
        "-i", str(bass_sting_path),
        "-i", str(audio_path),
        "-stream_loop", "-1",
        "-i", str(bg_audio_path),

        "-filter_complex",
        (
            "[2:a]volume=1.0[vo];"
            "[3:a]volume=0.06,lowpass=f=4200[amb];"
            "[1:a]volume=0.1,lowpass=f=3000[bass];"
            "[vo][amb][bass]amix=inputs=3:normalize=0[a]"
        ),

        "-map", "0:v",
        "-map", "[a]",

        "-c:v", "h264_nvenc",
        "-preset", "p7",
        "-cq", "19",
        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "192k",

        "-t", f"{duration}",

        "-movflags", "+faststart",
        str(out_path),
    ]

    subprocess.run(cmd, check=True)

    print(f"[VIDEO] Test render complete:")
    print(f"        {out_path}")

if __name__ == "__main__":
    main()
