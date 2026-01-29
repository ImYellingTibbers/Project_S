import json
import math
import os
import shutil
import subprocess
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# -------------------------
# Config
# -------------------------
ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"
PROJECT_ROOT = ROOT

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

# Effects (simplified)
ENABLE_VIGNETTE = True
ENABLE_TRANSITIONS = True
ENABLE_FIRST_FRAME_INTERRUPT = True
FIRST_FRAME_GLITCH_DUR = 0.30  # seconds (max 0.35)
FIRST_FRAME_BASS_DB = -6.0     # subtle, not loud

# Global "dust specks" vibe (subtle)
DUST_SPECKS_STRENGTH = float(os.getenv("RENDER_DUST_SPECKS_STRENGTH", "0.12"))
DUST_SPECKS_ALPHA    = float(os.getenv("RENDER_DUST_SPECKS_ALPHA", "0.22"))
DUST_SPECKS_THRESH   = int(os.getenv("RENDER_DUST_SPECKS_THRESH", "180"))

# Per-segment motion intensity
KB_MAX_ZOOM_IN = float(os.getenv("RENDER_KB_MAX_ZOOM_IN", "1.06"))   # zoom-in peak
KB_START_ZOOM_OUT = float(os.getenv("RENDER_KB_START_ZOOM_OUT", "1.06"))  # zoom-out start
PAN_PCT = float(os.getenv("RENDER_PAN_PCT", "0.06"))  # how far to pan as % of frame

# xfade transition pools (safe, FFmpeg xfade transitions)
SEGMENT_XFADE_TRANSITIONS = [
    "fade", "dissolve"
]
STITCH_XFADE_TRANSITIONS = [
    "fade", "dissolve",
    "circleopen", "circleclose",
    "horzopen", "horzclose", "vertopen", "vertclose",
    "pixelize",
]

# Ken Burns for stills
KB_ZOOM_PER_SEC = float(os.getenv("RENDER_KB_ZOOM_PER_SEC", "0.010"))
KB_MAX_ZOOM = float(os.getenv("RENDER_KB_MAX_ZOOM", "1.06"))

# Audio (NEW: prefer vo.json)
VO_JSON = "vo.json"  # new artifact
AUDIO_FALLBACK_REL = os.getenv("RENDER_AUDIO", "vo/full.wav")  # old fallback

# Music bed pool (global, not per-run)
MUSIC_ENABLED = os.getenv("RENDER_MUSIC_ENABLED", "1").strip() == "1"
MUSIC_DIR = (PROJECT_ROOT / "src" / os.getenv("RENDER_MUSIC_DIR", "assets/music/horror_shorts")).resolve()
MUSIC_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
MUSIC_GAIN_DB = float(os.getenv("RENDER_MUSIC_GAIN_DB", "-10.0"))  # bed level under VO
MUSIC_HP_HZ = int(os.getenv("RENDER_MUSIC_HP_HZ", "100"))
MUSIC_LP_HZ = int(os.getenv("RENDER_MUSIC_LP_HZ", "7000"))
MUSIC_SEED = os.getenv("RENDER_MUSIC_SEED", "").strip()  # optional deterministic selection

# Images + timing
IMAGES_DIRNAME = "img"
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


def find_latest_run_folder():
    if not RUNS_DIR.exists():
        raise RuntimeError(f"Directory NOT FOUND: {RUNS_DIR}")

    valid_runs = []

    for f in RUNS_DIR.iterdir():
        if not f.is_dir():
            continue

        vo_path = f / "vo.json"
        script_path = f / "script_with_prompts.json"

        if not vo_path.exists() or not script_path.exists():
            continue

        try:
            vo_data = json.loads(vo_path.read_text(encoding="utf-8"))
            sentences = vo_data.get("alignment", {}).get("sentences", [])
            if sentences:
                valid_runs.append(f)
        except Exception:
            continue

    if not valid_runs:
        raise RuntimeError("No runs found containing valid vo.json + script_with_prompts.json")

    return max(valid_runs, key=os.path.getmtime)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _ffmpeg_path(p: Path) -> str:
    # concat demuxer is happiest with absolute, forward-slash paths on Windows
    return p.resolve().as_posix()


def _motion_filter(duration_s: float, seg_idx: int) -> str:
    frames = max(1, int(duration_s * TARGET_FPS))
    denom = max(1, frames - 1)

    # 0..1 escalation curve across early segments (keeps energy rising)
    intensity = min(1.0, seg_idx / 12.0)

    # Deterministic variety per segment (repeatable render)
    rng = random.Random(f"motion|{seg_idx}")

    # Motion "modes" – this is what stops slideshow vibes.
    # push_in: slow creep toward subject
    # pull_out: reverse creep (uneasy reveal)
    # pan_lr / pan_ud: lateral movement (more cinematic)
    # punch: quick micro-zoom + settle (attention grab)
    mode_pool = ["push_in", "push_in", "pan_lr", "pan_ud", "pull_out", "punch"]
    mode = rng.choice(mode_pool)

    # Overscale so we can move/rotate without black edges
    overscale = 1.14 + 0.03 * intensity
    scale_w = int(TARGET_W * overscale)
    scale_h = int(TARGET_H * overscale)

    # Base zoom endpoints (kept subtle, but not boring)
    z_min = 1.015 + 0.015 * intensity
    z_max = 1.060 + 0.030 * intensity

    if mode == "push_in":
        z0, z1 = z_min, z_max
    elif mode == "pull_out":
        z0, z1 = z_max, z_min
    elif mode in ("pan_lr", "pan_ud"):
        # Keep zoom flatter when panning
        z0 = 1.030 + 0.015 * intensity
        z1 = 1.040 + 0.020 * intensity
    else:  # "punch"
        # punch-in then settle (handled via expression)
        z0 = 1.020 + 0.010 * intensity
        z1 = 1.070 + 0.030 * intensity

    # Smoothstep interpolation factor p in [0..1] based on frame index
    # p = on/denom; smoothstep = p*p*(3-2*p)
    p = f"(on/{denom})"
    smooth = f"({p}*{p}*(3-2*{p}))"

    # Micro-handheld drift (varies per segment)
    amp = 6 + int(10 * intensity) + rng.randint(0, 6)         # pixels
    fx1 = 0.010 + rng.random() * 0.020
    fx2 = 0.017 + rng.random() * 0.025
    fy1 = 0.012 + rng.random() * 0.020
    fy2 = 0.019 + rng.random() * 0.025

    # Pan targets (in pixels within the overscaled frame)
    pan_span_x = int(TARGET_W * (0.05 + 0.05 * intensity))
    pan_span_y = int(TARGET_H * (0.04 + 0.04 * intensity))
    pan_dir_x = rng.choice([-1, 1])
    pan_dir_y = rng.choice([-1, 1])

    # Zoom expression
    if mode == "punch":
        # Fast punch (first ~25%), then ease back to a steadier zoom
        punch_cut = 0.25
        # piecewise on p:
        # if p<punch_cut: ramp to z1 quickly
        # else: drift toward mid zoom
        mid = 1.045 + 0.020 * intensity
        z = (
            f"if(lte({p},{punch_cut}),"
            f"{z0:.4f}+({z1 - z0:.4f})*(({p}/{punch_cut})*({p}/{punch_cut})*(3-2*({p}/{punch_cut}))),"
            f"{z1:.4f}+({mid - z1:.4f})*(({p}-{punch_cut})/(1-{punch_cut}))"
            f")"
        )
    else:
        z = f"{z0:.4f}+({z1 - z0:.4f})*{smooth}"

    # Position expressions:
    # Start centered, add drift always, add intentional pan depending on mode.
    drift_x = f"sin(on*{fx1:.5f})*{amp} + sin(on*{fx2:.5f})*{int(amp*0.6)}"
    drift_y = f"cos(on*{fy1:.5f})*{amp} + cos(on*{fy2:.5f})*{int(amp*0.6)}"

    # Base center framing
    base_x = "iw/2-(iw/zoom/2)"
    base_y = "ih/2-(ih/zoom/2)"

    # Add a slow pan that *changes per segment*
    if mode == "pan_lr":
        pan_x = f"({pan_dir_x}*{pan_span_x})*{smooth}"
        pan_y = f"0"
    elif mode == "pan_ud":
        pan_x = f"0"
        pan_y = f"({pan_dir_y}*{pan_span_y})*{smooth}"
    else:
        pan_x = "0"
        pan_y = "0"

    x = f"{base_x} + ({drift_x}) + ({pan_x})"
    y = f"{base_y} + ({drift_y}) + ({pan_y})"

    # Subtle gate-weave rotate AFTER zoompan (rotate uses t, which exists here)
    rot_amp = 0.0020 + 0.0015 * intensity + rng.random() * 0.0010  # radians
    rot_freq = 0.45 + rng.random() * 0.35

    return (
        f"scale={scale_w}:{scale_h},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={TARGET_W}x{TARGET_H}:fps={TARGET_FPS},"
        f"rotate={rot_amp:.6f}*sin(2*PI*t*{rot_freq:.3f}):c=black,"
        f"crop={TARGET_W}:{TARGET_H}:x=(iw-ow)/2:y=(ih-oh)/2,"
        f"format=yuv420p"
    )


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
    return sorted(files)


def _pick_music_file(run_id: str) -> Path:
    files = _list_music_files()
    if not files:
        raise RuntimeError(f"No music files found in {MUSIC_DIR}")

    # If MUSIC_SEED is set, user wants deterministic selection.
    if MUSIC_SEED:
        rng = random.Random(MUSIC_SEED)
        return rng.choice(files)

    # Otherwise: truly random every render (even in same run folder)
    return random.SystemRandom().choice(files)
    

def _build_bed_audio(tmp_dir: Path, bed_path: Path, target_duration: float) -> Path:
    """
    Create a processed bed track matching target_duration:
      1) loop/trim to duration
      2) normalize AFTER trim
      3) apply HP/LP + gain
    Output: AAC in .m4a
    """
    out_bed = tmp_dir / "music_bed.m4a"

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
# New-artifact loaders
# -------------------------
def _load_vo_audio_path(run_dir: Path) -> Path:
    """
    Prefer new vo.json (audio_file field). Fallback to env RENDER_AUDIO.
    """
    vo_json_path = run_dir / VO_JSON
    if vo_json_path.exists():
        vo = _read_json(vo_json_path)
        rel = vo.get("audio_file")
        if rel:
            p = run_dir / str(rel)
            if p.exists():
                return p

    # fallback
    p2 = run_dir / AUDIO_FALLBACK_REL
    if p2.exists():
        return p2

    raise RuntimeError(f"Missing VO audio. Tried {vo_json_path.name} and fallback {AUDIO_FALLBACK_REL}")


def _load_segment_timing(run_dir: Path) -> List[Dict[str, Any]]:
    """
    Load timing_plan.json (v4+):
    Each beat is a renderable segment and MUST contain:
      - segment_index
      - start_time
      - end_time
      - image_file
    """
    timing_path = run_dir / TIMING_PLAN
    if not timing_path.exists():
        raise RuntimeError(f"Missing {TIMING_PLAN} in {run_dir}")

    timing = _read_json(timing_path)
    beats = timing.get("beats")
    if not isinstance(beats, list) or not beats:
        raise RuntimeError(f"{TIMING_PLAN} missing beats list")

    segments: List[Dict[str, Any]] = []

    for b in beats:
        seg_idx = int(b["segment_index"])
        start = _safe_float(b["start_time"])
        end = _safe_float(b["end_time"])

        if end <= start:
            raise RuntimeError(
                f"Invalid timing for segment {seg_idx}: start={start}, end={end}"
            )

        image_file = b.get("image_file")
        if not image_file:
            raise RuntimeError(f"Missing image_file for segment {seg_idx}")

        segments.append({
            "segment_index": seg_idx,
            "start_time": start,
            "end_time": end,
            "duration": end - start,
            "image_file": image_file,
            "chunk_index": b.get("chunk_index"),
        })

    # Deterministic order
    segments.sort(key=lambda s: s["segment_index"])
    return segments


# -------------------------
# Image resolving (flexible)
# -------------------------
def _list_pngs(images_dir: Path) -> List[Path]:
    if not images_dir.exists():
        return []
    return sorted([p for p in images_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png"])


def _resolve_image_for_segment(images_dir: Path, seg_idx: int, fallback_sorted: List[Path]) -> Path:
    """
    Supports multiple naming styles:
      segment_000.png / segment_0.png
      seg_000.png
      000.png
      *_000.png
      beat_000.png  (just in case)
    If nothing matches, fallback to sorted list by index.
    """
    padded = f"{seg_idx:03d}"
    candidates: List[Path] = []

    # Hard exact match for your actual naming convention: image_001.png, image_002.png, etc.
    exact = images_dir / f"image_{seg_idx+1:03d}.png"
    if exact.exists():
        return exact

    patterns = [
        # Prefer image_001 style (1-based)
        f"image_{seg_idx+1:03d}*.png",
        f"image_{seg_idx+1}*.png",

        # Then explicit segment naming
        f"segment_{padded}*.png",
        f"segment_{seg_idx}*.png",
        f"seg_{padded}*.png",
        f"seg_{seg_idx}*.png",
        f"beat_{padded}*.png",

        # Then generic fallbacks
        f"{padded}.png",
        f"*_{padded}.png",
    ]

    for pat in patterns:
        candidates.extend(images_dir.glob(pat))

    candidates = [p for p in candidates if p.is_file()]
    if candidates:
        # deterministic: shortest name first, then alpha
        candidates = sorted(candidates, key=lambda p: (len(p.name), p.name))
        return candidates[0]

    # Fallback: map by index position if counts match-ish
    if fallback_sorted and 0 <= seg_idx < len(fallback_sorted):
        return fallback_sorted[seg_idx]

    raise RuntimeError(
        f"Could not find image for segment {seg_idx} in {images_dir}. "
        f"Expected patterns like segment_{padded}.png (or sequential fallback)."
    )


# -------------------------
# FFmpeg stitching
# -------------------------
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
        fc_parts.append(
            f"[{i}:v]"
            f"fps={TARGET_FPS},"
            f"settb=1/{TARGET_FPS},"
            f"setpts=PTS-STARTPTS"
            f"[v{i}]"
        )

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


def _build_video_filter_complex(audio_dur: float, stitched_dur: float) -> str:
    """
    Builds a filter_complex video graph that:
      - pads video to VO length if needed
      - overlays floating dust specks
      - applies a strong vignette at the end
    Output label: [vout]
    """
    pad = max(0.0, audio_dur - stitched_dur)

    # Base video: pad -> trim -> format
    v_parts = []
    v_parts.append("[0:v]setpts=PTS-STARTPTS")

    if pad > 0.02:
        v_parts.append(f"tpad=stop_mode=clone:stop_duration={pad:.6f}")

    v_parts.append(f"trim=duration={audio_dur:.6f}")
    v_parts.append("format=rgba[vbase]")
    
    # Controls
    DUST_AMOUNT = float(os.getenv("RENDER_DUST_AMOUNT", "0.35"))   # 0–1
    DUST_SIZE   = float(os.getenv("RENDER_DUST_SIZE", "0.6"))      # particle size
    DUST_ALPHA  = float(os.getenv("RENDER_DUST_ALPHA", "0.18"))    # visibility
    DUST_BLUR   = float(os.getenv("RENDER_DUST_BLUR", "3.0"))      # softness

    specks = (
        f"color=c=black:s={TARGET_W}x{TARGET_H}:d={audio_dur:.6f},"
        f"noise=alls=60:allf=t+u,"
        f"lut=y='if(gt(val,{DUST_SPECKS_THRESH}),255,0)',"
        f"gblur=sigma=1.2,"
        f"format=rgba,"
        f"colorchannelmixer=aa={DUST_SPECKS_ALPHA}"
        f"[specks]"
    )

    # 1) Horror grade first (affects the image, NOT the dust)
    horror_grade = (
        "[vbase]"
        "hue=s=0.80,"
        "eq=contrast=1.25:brightness=-0.05:gamma=0.92"
        "[vgraded]"
    )
    
    found_footage = (
        "[vgraded]"
        "noise=alls=8:allf=t+u,"
        "eq=contrast=1.08:brightness=-0.02,"
        "tblend=all_mode=average:all_opacity=0.15"
        "[vff]"
    )

    # 2) True BLACK vignette overlay (color-stable)
    vign_alpha = (
        "0.75*min(max(("
        "sqrt("
        "((X-W/2)/(W/2))*((X-W/2)/(W/2)) + "
        "((Y-H/2)/(H/2))*((Y-H/2)/(H/2))"
        ") - 0.25"
        ")/0.55,0),1)"
    )

    vignette_layer = (
        f"color=c=black:s={TARGET_W}x{TARGET_H}:d={audio_dur:.6f},"
        f"format=rgba,"
        f"geq=r='0':g='0':b='0':a='{vign_alpha}'"
        f"[vign]"
    )

    overlay_vignette = "[vff][vign]overlay=shortest=1:format=auto[vfx]"

    # 3) Specks LAST (film dirt sits on top)
    enable_expr = (
        f"between(t,0,{audio_dur*0.5:.3f})"
        f"+between(t,{audio_dur*0.8:.3f},{audio_dur:.3f})"
    )

    overlay_specks = (
        "[vfx][specks]"
        f"overlay=shortest=1:format=auto:enable='{enable_expr}'"
        "[vout]"
    )

    # NOTE: `specks` is a standalone generator chain appended into the main graph
    # so we append it directly into the filter graph string.
    return ";".join([
        ",".join(v_parts),
        specks,
        horror_grade,
        found_footage,
        vignette_layer,
        overlay_vignette,
        overlay_specks,
    ])



def _render_segment_clip(tmp_dir: Path, image_path: Path, seg_idx: int, duration: float, seed: str) -> Path:
    out_path = tmp_dir / f"segment_{seg_idx:03d}.mp4"
    is_first = seg_idx == 0

    vf = _motion_filter(duration, seg_idx)
    vf_chain = vf

    if is_first and ENABLE_FIRST_FRAME_INTERRUPT:
        glitch = (
            f"[0:v]"
            f"scale={TARGET_W}:{TARGET_H},"
            f"eq=contrast=1.8:brightness=-0.15,"
            f"gblur=sigma=8:steps=1,"
            f"fps={TARGET_FPS},settb=1/{TARGET_FPS},"
            f"trim=duration={FIRST_FRAME_GLITCH_DUR},setpts=PTS-STARTPTS"
            f"[g];"
            f"[0:v]{vf},"
            f"fps={TARGET_FPS},settb=1/{TARGET_FPS},"
            f"trim=start={FIRST_FRAME_GLITCH_DUR},setpts=PTS-STARTPTS"
            f"[n];"
            f"[g][n]concat=n=2:v=1:a=0[v0]"
        )
        vf_chain = glitch

    if is_first and ENABLE_FIRST_FRAME_INTERRUPT:
        filter_complex = (
            f"{vf_chain};"
            f"[v0]trim=duration={duration:.6f},setpts=PTS-STARTPTS[v]"
        )
    else:
        filter_complex = (
            f"{vf_chain},trim=duration={duration:.6f},setpts=PTS-STARTPTS[v]"
        )

    _run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-an",
        "-c:v", "libx264",
        "-r", str(TARGET_FPS),
        "-video_track_timescale", "24000",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path),
    ])

    return out_path


# -------------------------
# Main
# -------------------------
def main() -> int:
    run_dir = find_latest_run_folder()

    # Load segment timing (new timing_plan.json format)
    segments = _load_segment_timing(run_dir)

    # Load VO audio (prefer vo.json)
    audio_path = _load_vo_audio_path(run_dir)
    audio_dur = _ffprobe_duration(audio_path)
    if audio_dur <= 0.02:
        raise RuntimeError(f"Invalid VO duration: {audio_path}")

    images_dir = run_dir / IMAGES_DIRNAME
    all_pngs = _list_pngs(images_dir)
    if not all_pngs:
        raise RuntimeError(f"No .png images found in: {images_dir}")

    out_dir = run_dir / OUT_DIRNAME
    tmp_dir = out_dir / TMP_DIRNAME
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    _ensure_dir(tmp_dir)

    # 1) Render each segment clip
    segment_clips: List[Path] = []
    for s in segments:
        seg_idx = int(s["segment_index"])
        dur = float(s["duration"])

        image_file = s.get("image_file")
        if not image_file:
            raise RuntimeError(f"Missing image_file for segment {seg_idx}")

        img = images_dir / image_file
        if not img.exists():
            raise RuntimeError(f"Image not found: {img}")

        clip = _render_segment_clip(tmp_dir, img, seg_idx, dur, seed=f"{run_dir.name}|seg{seg_idx}")
        segment_clips.append(clip)
        print(f"[render] segment {seg_idx:03d} ({dur:.3f}s) -> {clip.name} (img={img.name})")

    # 2) Crossfade stitch all segments
    stitched_path = tmp_dir / "stitched_tmp.mp4"
    stitched_dur = _xfade_chain(
        segment_clips,
        XFADE_DUR,
        stitched_path,
        SEGMENT_XFADE_TRANSITIONS,
        f"{run_dir.name}|segments"
    )
    print(f"[render] stitched -> {stitched_path.name} ({stitched_dur:.3f}s)")

    # 3) Optional music bed
    bed_path: Optional[Path] = None
    if MUSIC_ENABLED:
        try:
            bed_src = _pick_music_file(run_dir.name)
            bed_path = _build_bed_audio(tmp_dir, bed_src, audio_dur)
            print(f"[audio] music bed -> {bed_src.name}")
        except Exception as e:
            print(f"[audio] music disabled (reason: {e})")
            bed_path = None

    # 4) Lay VO (+ music if present); pad/trim video to audio duration
    final_path = out_dir / FINAL_NAME

    video_fc = _build_video_filter_complex(audio_dur, stitched_dur)

    if bed_path and bed_path.exists():
        audio_fc = (
        "[1:a]aresample=48000,volume=1.0,"
        f"afade=t=out:st={max(audio_dur-0.4, 0):.2f}:d=0.35[vo];"
        "[2:a]aresample=48000,volume=1.0[bed];"
        "[vo][bed]amix=inputs=2:duration=first:dropout_transition=0,"
        "alimiter=limit=0.98[aout]"
    )

        fc = video_fc + ";" + audio_fc

        _run([
            "ffmpeg", "-y",
            "-i", _ffmpeg_path(stitched_path),   # 0:v
            "-i", _ffmpeg_path(audio_path),      # 1:a
            "-i", _ffmpeg_path(bed_path),        # 2:a
            "-filter_complex", fc,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            FINAL_NAME,
        ], cwd=out_dir)
    else:
        audio_fc = (
            "[1:a]aresample=48000,volume=1.0,"
            f"afade=t=out:st={max(audio_dur-0.4, 0):.2f}:d=0.35,"
            "alimiter=limit=0.98[aout]"
        )

        fc = video_fc + ";" + audio_fc

        _run([
            "ffmpeg", "-y",
            "-i", _ffmpeg_path(stitched_path),  # 0:v
            "-i", _ffmpeg_path(audio_path),     # 1:a
            "-filter_complex", fc,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            FINAL_NAME,
        ], cwd=out_dir)

    # Cleanup (only keep story_only.mp4)
    try:
        if stitched_path.exists():
            stitched_path.unlink()
    except Exception:
        pass

    print(f"[done] final -> {final_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
