from __future__ import annotations

import subprocess
from pathlib import Path
import sys
import random

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
    runs = [
        d for d in RUNS_DIR.iterdir()
        if d.is_dir()
        and (d / "img" / "background_img.png").exists()
        and (d / "audio" / "full_narration.wav").exists()
    ]
    if not runs:
        raise RuntimeError("No run with background image and p000.wav found")
    return max(runs, key=lambda p: p.stat().st_mtime)

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

# ============================================================
# Main
# ============================================================

def main():
    run_dir = get_latest_run()

    img_path = run_dir / "img" / "background_img.png"
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
    out_path = run_dir / "video_test_background.mp4"

    duration = get_audio_duration(audio_path)

    print(f"[VIDEO] Run: {run_dir.name}")
    print(f"[VIDEO] Duration: {duration:.2f}s")

    # --------------------------------------------------------
    # Visual design parameters (tuned for confessional horror)
    # --------------------------------------------------------

    zoom_start = 1.00
    zoom_end = 1.06
    fps = 30

    zoom_expr = (
        f"{zoom_start}"
        f"+({zoom_end}-{zoom_start})"
        f"*(t/{duration})"
    )

    x_expr = "iw/2-(iw/zoom/2)+sin(t*0.003)+sin(t*0.0007)*2"
    y_expr = "ih/2-(ih/zoom/2)+cos(t*0.002)+cos(t*0.0009)*2"

    total_frames = int(duration * fps)

    vf = (
        f"zoompan="
        f"z='1+0.045*on/{total_frames}':"
        f"x='iw/2-(iw/zoom/2)+sin(on*0.003)*2':"
        f"y='ih/2-(ih/zoom/2)+cos(on*0.002)*2':"
        f"d=1:s=1920x1080,"
        f"fps={fps},"
        f"vignette=PI/3,"
        f"fade=t=in:st=0:d=0.75,"
        f"noise=alls=4:allf=t"
    )

    cmd = [
        "ffmpeg",
        "-y",

        # ---------------------------
        # Inputs
        # ---------------------------

        # Background image (looped)
        "-stream_loop", "-1",
        "-i", str(img_path),
        
        # Bass sting (one-shot)
        "-i", str(bass_sting_path),

        # Narration (main audio)
        "-i", str(audio_path),

        # Ambient bed (looped)
        "-stream_loop", "-1",
        "-i", str(bg_audio_path),

        # ---------------------------
        # Filters
        # ---------------------------

        "-filter_complex",
        (
            # Narration: untouched, dominant
            "[2:a]volume=1.0[vo];"

            # Ambient bed: very subtle
            "[3:a]volume=0.06,lowpass=f=4200[amb];"

            # Bass sting: restrained
            "[1:a]volume=0.1,lowpass=f=3000[bass];"

            # Mix VO + ambient + bass (VO first, no normalization)
            "[vo][amb][bass]amix="
            "inputs=3:"
            "weights=1 1 1:"
            "dropout_transition=0:"
            "normalize=0[a]"
        ),

        # ---------------------------
        # Video
        # ---------------------------

        "-t", f"{duration}",
        "-vf", vf,
        "-map", "0:v",
        "-map", "[a]",

        "-c:v", "h264_nvenc",
        "-preset", "p7",
        "-tune", "hq",
        "-rc", "vbr",
        "-cq", "19",
        "-profile:v", "high",
        "-pix_fmt", "yuv420p",

        # ---------------------------
        # Audio
        # ---------------------------

        "-c:a", "aac",
        "-b:a", "192k",

        "-movflags", "+faststart",
        str(out_path),
    ]

    subprocess.run(cmd, check=True)

    print(f"[VIDEO] Test render complete:")
    print(f"        {out_path}")

if __name__ == "__main__":
    main()
