import json
import math
import os
import sys
import shutil
import subprocess
import random
from pathlib import Path
from typing import Dict, Any, List

# -------------------------
# Config
# -------------------------
RUNS_DIR = Path("runs")
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Output
OUT_DIRNAME = "render"
TMP_DIRNAME = "tmp"
FINAL_NAME = "story_only.mp4"

# Target format
TARGET_W = int(os.getenv("RENDER_W", "1080"))
TARGET_H = int(os.getenv("RENDER_H", "1920"))
TARGET_FPS = int(os.getenv("RENDER_FPS", "24"))

# Crossfade: default ~2 frames at 24fps = 0.083333s
XFADE_FRAMES = int(os.getenv("RENDER_XFADE_FRAMES", "2"))
XFADE_DUR = float(os.getenv("RENDER_XFADE_DUR", str(XFADE_FRAMES / TARGET_FPS)))

# Effects intensity
GRAIN_STRENGTH = 0.08          # 0.0 disables
ENABLE_VIGNETTE = True
ENABLE_HANDHELD = True
ENABLE_COLOR_GRADE = True      # mild contrast/saturation shift
ENABLE_TRANSITIONS = True      # varied xfade transitions (micro + beat stitching)

# xfade transition pools (safe, FFmpeg xfade transitions)
MICRO_XFADE_TRANSITIONS = [
    "fade", "dissolve",
    "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
]
BEAT_XFADE_TRANSITIONS = [
    "fade", "dissolve",
    "circleopen", "circleclose",
    "horzopen", "horzclose", "vertopen", "vertclose",
    "pixelize",
]

# Ken Burns for stills
KB_ZOOM_PER_SEC = float(os.getenv("RENDER_KB_ZOOM_PER_SEC", "0.010"))
KB_MAX_ZOOM = float(os.getenv("RENDER_KB_MAX_ZOOM", "1.06"))

# Audio
AUDIO_REL = os.getenv("RENDER_AUDIO", "vo/full.wav")  # relative to run dir

# Music bed pool (global, not per-run)
MUSIC_ENABLED = os.getenv("RENDER_MUSIC_ENABLED", "1").strip() == "1"
MUSIC_DIR = (PROJECT_ROOT / "src" / os.getenv("RENDER_MUSIC_DIR", "assets/music/horror_shorts")).resolve()
MUSIC_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
MUSIC_GAIN_DB = float(os.getenv("RENDER_MUSIC_GAIN_DB", "-10.0"))  # bed level under VO
MUSIC_HP_HZ = int(os.getenv("RENDER_MUSIC_HP_HZ", "100"))
MUSIC_LP_HZ = int(os.getenv("RENDER_MUSIC_LP_HZ", "7000"))
MUSIC_SEED = os.getenv("RENDER_MUSIC_SEED", "").strip()  # optional deterministic selection

# Images only (i2v disabled)
IMAGES_DIRNAME = "images"
TIMING_PLAN = "timing_plan.json"

# -------------------------
# Helpers
# -------------------------
def _run(cmd: List[str], cwd: Path | None = None) -> None:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if p.returncode != 0:
        raise RuntimeError(f"Command failed ({p.returncode}):\n{cmd}\n\nOUTPUT:\n{p.stdout}")


def _ffprobe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}:\n{p.stderr}")
    s = p.stdout.strip()
    return float(s) if s else 0.0

def _latest_run_dir() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError("runs/ folder not found")
    runs = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()])
    if not runs:
        raise RuntimeError("No run folders found")
    return runs[-1]

def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _beat_id_to_name(beat_id: int) -> str:
    return f"beat_{beat_id:03d}"


def _list_micro_images(images_dir: Path, beat_id: int) -> List[Path]:
    prefix = f"beat_{beat_id:03d}_micro_"
    files = [
        p for p in images_dir.iterdir()
        if p.is_file() and p.name.startswith(prefix) and p.suffix.lower() == ".png"
    ]

    if not files:
        raise RuntimeError(f"No micro images found for beat {beat_id:03d}")

    # Sort by micro index
    def _micro_index(p: Path) -> int:
        # beat_001_micro_003.png -> 3
        return int(p.stem.split("_")[-1])

    return sorted(files, key=_micro_index)


def _ken_burns_filter(duration_s: float) -> str:
    frames = max(1, int(math.ceil(duration_s * TARGET_FPS)))
    inc = KB_ZOOM_PER_SEC / TARGET_FPS
    z = f"min(zoom+{inc:.8f},{KB_MAX_ZOOM})"
    if ENABLE_HANDHELD:
        x = "iw/2-(iw/zoom/2)+12*sin(2*PI*on/120)"
        y = "ih/2-(ih/zoom/2)+12*cos(2*PI*on/180)"
    else:
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"

    filt = []
    filt.append(f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase")
    filt.append(f"crop={TARGET_W}:{TARGET_H}")
    filt.append(f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={TARGET_W}x{TARGET_H}:fps={TARGET_FPS}")
    filt.append("format=yuv420p")

    post = []
    if ENABLE_COLOR_GRADE:
        post.append("eq=contrast=1.08:saturation=1.12:brightness=-0.02")
    if GRAIN_STRENGTH > 0:
        alls = max(1, min(30, int(GRAIN_STRENGTH * 120)))
        post.append(f"noise=alls={alls}:allf=t+u")
    if ENABLE_VIGNETTE:
        post.append("vignette=PI/4")
    if post:
        filt.append(",".join(post))

    return ",".join(filt)

def _ffmpeg_path(p: Path) -> str:
    # concat demuxer is happiest with absolute, forward-slash paths on Windows
    return p.resolve().as_posix()

# -------------------------
# Music helpers
# -------------------------
def _list_music_files() -> List[Path]:
    if not MUSIC_DIR.exists():
        print(f"[audio][debug] MUSIC_DIR does not exist: {MUSIC_DIR}")
        return []

    files: List[Path] = []

    for ext in MUSIC_EXTS:
        files.extend(MUSIC_DIR.glob(f"*{ext}"))

    files = [p for p in files if p.is_file()]

    print(f"[audio][debug] scanned {MUSIC_DIR}, found {len(files)} files")
    for p in files[:5]:
        print(f"[audio][debug] music candidate: {p.name}")

    return sorted(files)


def _pick_music_file(run_id: str) -> Path:
    files = _list_music_files()
    if not files:
        raise RuntimeError(f"No music files found in {MUSIC_DIR}")

    if MUSIC_SEED:
        rnd = random.Random(MUSIC_SEED)
    else:
        # deterministic per run_id by default, unless user sets MUSIC_SEED differently
        rnd = random.Random(run_id)

    return rnd.choice(files)

def _build_bed_audio(tmp_dir: Path, bed_path: Path, target_duration: float) -> Path:
    """
    Create a processed bed track matching target_duration:
      1) loop/trim to duration
      2) normalize AFTER trim
      3) apply HP/LP + gain
    Output: AAC in .m4a (keeps things small; will be mixed into final anyway)
    """
    out_bed = tmp_dir / "music_bed.m4a"

    # We use:
    # -stream_loop -1 to loop indefinitely, then -t to trim.
    #
    # Then filter:
    #   loudnorm AFTER trim (so hot endings don't ruin the whole normalization)
    #   highpass/lowpass to keep out of VO band extremes
    #   volume to set bed level
    #
    # Note: loudnorm is EBU R128; we keep it conservative. You can tune later.
    af = (
        f"loudnorm=I=-24:TP=-2:LRA=11,"
        f"highpass=f={MUSIC_HP_HZ},"
        f"lowpass=f={MUSIC_LP_HZ},"
        f"volume={MUSIC_GAIN_DB}dB"
    )

    _run([
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(bed_path),
        "-t", f"{target_duration:.6f}",
        "-vn",
        "-af", af,
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_bed),
    ])

    return out_bed

# -------------------------
# Video assembly core
# -------------------------
def _render_beat_clip(run_dir: Path, tmp_dir: Path, beat_id: int, beat_duration: float) -> Path:
    images_dir = run_dir / IMAGES_DIRNAME
    out_path = tmp_dir / f"beat_{beat_id:03d}_final.mp4"

    micro_images = _list_micro_images(images_dir, beat_id)

    micro_dur = beat_duration / len(micro_images)
    if micro_dur <= 0:
        raise RuntimeError(f"Invalid micro duration for beat {beat_id}")

    micro_clips: List[Path] = []

    for i, img_path in enumerate(micro_images, start=1):
        micro_out = tmp_dir / f"beat_{beat_id:03d}_micro_{i:03d}_{img_path.stem}.mp4"

        _run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-vf",
            f"{_ken_burns_filter(micro_dur)},"
            f"trim=duration={micro_dur:.6f},setpts=PTS-STARTPTS",
            "-an",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(micro_out),
        ])

        micro_clips.append(micro_out)

    # Crossfade micros into one beat clip
    _xfade_chain(micro_clips, XFADE_DUR, out_path, MICRO_XFADE_TRANSITIONS, f"{run_dir.name}|beat{beat_id}|micro")

    return out_path


def _xfade_chain(clips: List[Path], xfade_dur: float, out_path: Path, transition_pool: List[str], seed: str) -> float:
    if len(clips) == 1:
        _run(["ffmpeg", "-y", "-i", str(clips[0]), "-c", "copy", str(out_path)])
        return _ffprobe_duration(out_path)

    durs = []
    for p in clips:
        d = _ffprobe_duration(p)
        if d <= 0:
            raise RuntimeError(f"Invalid clip duration: {p}")
        durs.append(d)
        
    pool = transition_pool if ENABLE_TRANSITIONS else ["fade"]
    rng = random.Random(seed)

    inputs = []
    for p in clips:
        inputs += ["-i", str(p)]

    fc_parts = []
    for i in range(len(clips)):
        fc_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")

    current = "v0"
    timeline = durs[0]

    for i in range(1, len(clips)):
        offset = max(0.0, timeline - xfade_dur)
        out_label = f"vx{i}"
        
        transition = rng.choice(pool)

        fc_parts.append(
            f"[{current}][v{i}]"
            f"xfade=transition={transition}:"
            f"duration={xfade_dur:.6f}:"
            f"offset={offset:.6f}"
            f"[{out_label}]"
        )

        timeline += durs[i] - xfade_dur
        current = out_label


    filter_complex = ";".join(fc_parts)

    _run([
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{current}]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path),
    ])

    return _ffprobe_duration(out_path)


def main() -> int:
    run_dir = _latest_run_dir()
    timing_path = run_dir / TIMING_PLAN
    if not timing_path.exists():
        raise RuntimeError(f"Missing {TIMING_PLAN} in {run_dir}")

    timing = _read_json(timing_path)
    beats = timing.get("beats")
    if not isinstance(beats, list) or not beats:
        raise RuntimeError("timing_plan.json missing beats list")

    audio_path = run_dir / AUDIO_REL
    if not audio_path.exists():
        raise RuntimeError(f"Missing VO audio: {audio_path}")

    audio_dur = _ffprobe_duration(audio_path)

    out_dir = run_dir / OUT_DIRNAME
    tmp_dir = out_dir / TMP_DIRNAME
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    _ensure_dir(tmp_dir)

    # 1) Render each beat final clip
    beat_clips: List[Path] = []
    for b in sorted(beats, key=lambda x: int(x["beat_id"])):
        beat_id = int(b["beat_id"])
        dur = _safe_float(b.get("duration_seconds"), 0.0)
        if dur <= 0:
            raise RuntimeError(f"Invalid duration for beat {beat_id}: {dur}")
        clip = _render_beat_clip(run_dir, tmp_dir, beat_id, dur)
        beat_clips.append(clip)
        print(f"[render] beat {beat_id:03d} -> {clip.name}")

    # 2) Crossfade stitch all beats
    stitched_path = out_dir / "stitched_video.mp4"
    stitched_dur = _xfade_chain(beat_clips, XFADE_DUR, stitched_path, BEAT_XFADE_TRANSITIONS, f"{run_dir.name}|stitch")
    print(f"[render] stitched -> {stitched_path.name} ({stitched_dur:.3f}s)")

    # 3) Optional music bed (loop/trim -> normalize -> filter -> gain)
    bed_path = None
    if MUSIC_ENABLED:
        try:
            bed_src = _pick_music_file(run_dir.name)
            bed_path = _build_bed_audio(tmp_dir, bed_src, audio_dur)
            print(f"[audio] music bed -> {bed_src.name}")
        except Exception as e:
            print(f"[audio] music disabled (reason: {e})")
            bed_path = None

    # 4) Lay in VO (+ music if present); pad/trim video to audio duration
    final_path = out_dir / FINAL_NAME

    pad = max(0.0, audio_dur - stitched_dur)
    vf = []
    if pad > 0.02:
        vf.append(f"tpad=stop_mode=clone:stop_duration={pad:.6f}")
    vf.append(f"trim=duration={audio_dur:.6f},setpts=PTS-STARTPTS")

    vf_str = ",".join(vf)

    if bed_path and bed_path.exists():
        # Mix VO and bed into one track. VO stays clean; bed is already filtered/leveled.
        # Slight safety limiter at the end.
        af = (
            "[1:a]aresample=48000,volume=1.0[vo];"
            "[2:a]aresample=48000,volume=1.0[bed];"
            "[vo][bed]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.98[aout]"
        )

        _run([
            "ffmpeg", "-y",
            "-i", _ffmpeg_path(stitched_path),
            "-i", _ffmpeg_path(audio_path),
            "-i", _ffmpeg_path(bed_path),
            "-vf", vf_str,
            "-filter_complex", af,
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            FINAL_NAME,
        ], cwd=out_dir)
        mixed_final_path = out_dir / FINAL_NAME
    else:
        _run([
            "ffmpeg", "-y",
            "-i", _ffmpeg_path(stitched_path),
            "-i", _ffmpeg_path(audio_path),
            "-vf", vf_str,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            FINAL_NAME,
        ], cwd=out_dir)
        mixed_final_path = out_dir / FINAL_NAME
        
        return 0
        
if __name__ == "__main__":
    raise SystemExit(main())
