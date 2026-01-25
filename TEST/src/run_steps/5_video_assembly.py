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
ROOT = Path("/home/jcpix/projects/Project_S/TEST")
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

# Global "dust specks" vibe (subtle)
DUST_SPECKS_STRENGTH = float(os.getenv("RENDER_DUST_SPECKS_STRENGTH", "0.03"))  # 0 disables

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


def _latest_run_dir() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError("runs/ folder not found")
    runs = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir() and p.name.startswith("run_")])
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


def _ffmpeg_path(p: Path) -> str:
    # concat demuxer is happiest with absolute, forward-slash paths on Windows
    return p.resolve().as_posix()


def _motion_filter(duration_s: float, seed: str) -> str:
    """
    Randomly choose ONE camera move per segment:
      1) zoom in
      2) zoom out (starts zoomed in)
      3) pan left/right
      4) pan up/down
      5) pan diagonal
      6) combo zoom + pan (Ken Burns)
    Output: a vf string for ffmpeg -vf
    """
    frames = max(1, int(math.ceil(duration_s * TARGET_FPS)))
    rng = random.Random(seed)

    # Choose move type
    move = rng.choice(["zoom_in", "zoom_out", "pan_lr", "pan_ud", "pan_diag", "combo"])

    # Scale up first so pans have room
    # (Keep it simple: just ensure extra pixels exist)
    pre = [
        f"scale={int(TARGET_W*1.12)}:{int(TARGET_H*1.12)}:force_original_aspect_ratio=increase"
    ]

    # Helper terms
    t = f"(on/{max(1, frames-1)})"  # 0..1 across segment
    pan_max_x = f"(iw - iw/zoom)*{PAN_PCT:.6f}"
    pan_max_y = f"(ih - ih/zoom)*{PAN_PCT:.6f}"

    # Defaults: centered
    x_expr = "iw/2-(iw/zoom/2)"
    y_expr = "ih/2-(ih/zoom/2)"

    # Zoom expressions
    # Use clamps so it doesn't go nuts
    if move == "zoom_in":
        inc = (KB_MAX_ZOOM_IN - 1.0) / max(1, frames-1)
        z_expr = f"min(zoom+{inc:.8f},{KB_MAX_ZOOM_IN:.6f})"

    elif move == "zoom_out":
        dec = (KB_START_ZOOM_OUT - 1.0) / max(1, frames-1)
        z_expr = f"max(zoom-{dec:.8f},1.000000)"
        # start zoomed in
        z_expr = f"if(eq(on,0),{KB_START_ZOOM_OUT:.6f},{z_expr})"

    elif move == "pan_lr":
        # Keep slight zoom so pan has room
        z_expr = "1.030000"
        direction = rng.choice(["left_to_right", "right_to_left"])
        if direction == "left_to_right":
            x_expr = f"0 + {pan_max_x}*{t}"
        else:
            x_expr = f"{pan_max_x}*(1-{t})"
        y_expr = "ih/2-(ih/zoom/2)"

    elif move == "pan_ud":
        z_expr = "1.030000"
        direction = rng.choice(["top_to_bottom", "bottom_to_top"])
        if direction == "top_to_bottom":
            y_expr = f"0 + {pan_max_y}*{t}"
        else:
            y_expr = f"{pan_max_y}*(1-{t})"
        x_expr = "iw/2-(iw/zoom/2)"

    elif move == "pan_diag":
        z_expr = "1.040000"
        direction = rng.choice(["tl_br", "br_tl", "tr_bl", "bl_tr"])
        if direction == "tl_br":
            x_expr = f"0 + {pan_max_x}*{t}"
            y_expr = f"0 + {pan_max_y}*{t}"
        elif direction == "br_tl":
            x_expr = f"{pan_max_x}*(1-{t})"
            y_expr = f"{pan_max_y}*(1-{t})"
        elif direction == "tr_bl":
            x_expr = f"{pan_max_x}*(1-{t})"
            y_expr = f"0 + {pan_max_y}*{t}"
        else:  # bl_tr
            x_expr = f"0 + {pan_max_x}*{t}"
            y_expr = f"{pan_max_y}*(1-{t})"

    else:  # combo (Ken Burns)
        # Zoom gently + pan gently
        z0 = rng.choice([1.01, 1.02, 1.03])
        z1 = rng.choice([1.04, 1.05, 1.06])
        z_expr = f"({z0:.6f} + ({z1:.6f}-{z0:.6f})*{t})"

        # small pan directions
        x_dir = rng.choice([-1, 1])
        y_dir = rng.choice([-1, 1])
        x_expr = f"iw/2-(iw/zoom/2) + ({x_dir})*{pan_max_x}*{t}"
        y_expr = f"ih/2-(ih/zoom/2) + ({y_dir})*{pan_max_y}*{t}"

    # Final zoompan into target size
    zp = (
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={TARGET_W}x{TARGET_H}:fps={TARGET_FPS}"
    )

    return ",".join(pre + [zp, "format=yuv420p"])


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

    rng = random.Random(MUSIC_SEED if MUSIC_SEED else run_id)
    return rng.choice(files)


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
    Load timing_plan.json v3_consistent style:
    beats[] items contain segment_index, start_time, end_time.
    """
    timing_path = run_dir / TIMING_PLAN
    if not timing_path.exists():
        raise RuntimeError(f"Missing {TIMING_PLAN} in {run_dir}")

    timing = _read_json(timing_path)
    beats = timing.get("beats")
    if not isinstance(beats, list) or not beats:
        raise RuntimeError(f"{TIMING_PLAN} missing beats list")

    # Sort by segment_index if present
    def _key(b: Dict[str, Any]) -> int:
        if "segment_index" in b:
            return int(b["segment_index"])
        if "beat_id" in b:
            return int(b["beat_id"])
        return 0

    beats = sorted(beats, key=_key)

    # Normalize duration per segment
    segments: List[Dict[str, Any]] = []
    for b in beats:
        seg_idx = int(b.get("segment_index", b.get("beat_id", 0)))
        start = _safe_float(b.get("start_time"), 0.0)
        end = _safe_float(b.get("end_time"), 0.0)

        # Fallback support for older timing schemas
        if end <= start:
            dur = _safe_float(b.get("duration_seconds"), 0.0)
            end = start + dur

        dur = max(0.0, end - start)
        if dur <= 0.02:
            raise RuntimeError(f"Invalid segment duration for segment {seg_idx}: start={start} end={end}")

        segments.append({
            "segment_index": seg_idx,
            "start_time": start,
            "end_time": end,
            "duration": dur,
            "text": b.get("text", ""),
            "image_prompt": b.get("image_prompt", ""),
        })

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

    patterns = [
        f"segment_{padded}*.png",
        f"segment_{seg_idx}*.png",
        f"seg_{padded}*.png",
        f"seg_{seg_idx}*.png",
        f"{padded}.png",
        f"*_{padded}.png",
        f"beat_{padded}*.png",
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


def _render_segment_clip(tmp_dir: Path, image_path: Path, seg_idx: int, duration: float, seed: str) -> Path:
    out_path = tmp_dir / f"segment_{seg_idx:03d}.mp4"

    vf = _motion_filter(duration, seed)

    _run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf",
        f"{vf},trim=duration={duration:.6f},setpts=PTS-STARTPTS",
        "-an",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_path),
    ])

    return out_path


# -------------------------
# Main
# -------------------------
def main() -> int:
    run_dir = _latest_run_dir()

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

        img = _resolve_image_for_segment(images_dir, seg_idx, all_pngs)
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

    pad = max(0.0, audio_dur - stitched_dur)
    vf = []
    if pad > 0.02:
        vf.append(f"tpad=stop_mode=clone:stop_duration={pad:.6f}")

    # Global post look (applied ONCE)
    post = []
    if ENABLE_VIGNETTE:
        post.append("vignette=PI/4")

    # "Floating specks" approximation:
    # Low-intensity temporal noise + soft blend -> dusty/VCR vibe without heavy grain.
    if DUST_SPECKS_STRENGTH > 0.0:
        alls = max(1, min(12, int(DUST_SPECKS_STRENGTH * 120)))
        post.append(f"noise=alls={alls}:allf=t")

    vf.append(",".join(post) if post else "")
    vf.append(f"trim=duration={audio_dur:.6f},setpts=PTS-STARTPTS")

    # clean join
    vf = [x for x in vf if x.strip()]
    vf_str = ",".join(vf)


    if bed_path and bed_path.exists():
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
