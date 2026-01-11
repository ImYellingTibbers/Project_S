import json
import math
import os
import re
import whisper
import shutil
import subprocess
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple

# -------------------------
# Config
# -------------------------
RUNS_DIR = Path("runs")
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Output
OUT_DIRNAME = "render"
TMP_DIRNAME = "tmp"
FINAL_NAME = "final_short.mp4"

# Target format
TARGET_W = int(os.getenv("RENDER_W", "1080"))
TARGET_H = int(os.getenv("RENDER_H", "1920"))
TARGET_FPS = int(os.getenv("RENDER_FPS", "24"))

# Crossfade: default ~2 frames at 24fps = 0.083333s
XFADE_FRAMES = int(os.getenv("RENDER_XFADE_FRAMES", "2"))
XFADE_DUR = float(os.getenv("RENDER_XFADE_DUR", str(XFADE_FRAMES / TARGET_FPS)))

# Effects intensity
GRAIN_STRENGTH = float(os.getenv("RENDER_GRAIN", "0.08"))
VIGNETTE = os.getenv("RENDER_VIGNETTE", "1").strip() == "1"
HANDHELD = os.getenv("RENDER_HANDHELD", "1").strip() == "1"

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

# -------------------------
# Captions
# -------------------------
CAPTIONS_ENABLED = os.getenv("RENDER_CAPTIONS_ENABLED", "1").strip() == "1"
CAPTIONS_MODEL = os.getenv("RENDER_CAPTIONS_MODEL", "base").strip()  # tiny/base/small
CAPTIONS_WORDS_PER_CAPTION = int(os.getenv("RENDER_CAPTIONS_WORDS_PER_CAPTION", "4"))
# Caption styling
CAPTIONS_FONT = os.getenv("RENDER_CAPTIONS_FONT", "Bebas Neue").strip()
CAPTIONS_FONT_SIZE = int(os.getenv("RENDER_CAPTIONS_FONT_SIZE", "200"))
CAPTIONS_ALIGN = int(os.getenv("RENDER_CAPTIONS_ALIGN", "5"))  # 5 = center screen
CAPTIONS_MARGIN_V = int(os.getenv("RENDER_CAPTIONS_MARGIN_V", "0"))
CAPTIONS_OUTLINE = int(os.getenv("RENDER_CAPTIONS_OUTLINE", "6"))
CAPTIONS_SHADOW = int(os.getenv("RENDER_CAPTIONS_SHADOW", "6"))

# Prefer i2v if present
I2V_DIRNAME = "i2v"
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


def _transcribe_with_whisper(audio_path: Path) -> List[Dict[str, Any]]:
    """
    Returns word-level timestamps:
    [
      {"word": "hello", "start": 0.12, "end": 0.45},
      ...
    ]
    """
    model = whisper.load_model(CAPTIONS_MODEL)
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        verbose=False,
    )

    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": float(w["start"]),
                "end": float(w["end"]),
            })

    return words


def _build_caption_events(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups words into 2–4 word captions with accurate timing.
    """
    captions = []
    buf = []

    for w in words:
        buf.append(w)

        if len(buf) >= CAPTIONS_WORDS_PER_CAPTION:
            captions.append({
                "text": " ".join(x["word"] for x in buf),
                "start": buf[0]["start"],
                "end": buf[-1]["end"],
            })
            buf = []

    if buf:
        captions.append({
            "text": " ".join(x["word"] for x in buf),
            "start": buf[0]["start"],
            "end": buf[-1]["end"],
        })

    return captions


def _write_ass_captions(captions: List[Dict[str, Any]], ass_path: Path) -> None:
    """
    Writes stylized ASS subtitles for Shorts-style captions.
    """
    def ts(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    header = f"""[Script Info]
    ScriptType: v4.00+
    PlayResX: 1080
    PlayResY: 1920

    [V4+ Styles]
    Style: Default,{CAPTIONS_FONT},{CAPTIONS_FONT_SIZE},&H00FFFFFF,&H00000000,&H80000000,&H80000000,1,0,0,0,100,100,0,0,1,{CAPTIONS_OUTLINE},{CAPTIONS_SHADOW},{CAPTIONS_ALIGN},10,10,{CAPTIONS_MARGIN_V},1

    [Events]
    """


    lines = []
    for c in captions:
        lines.append(
            f"Dialogue: 0,{ts(c['start'])},{ts(c['end'])},Default,,0,0,0,,{c['text'].upper()}"
        )

    ass_path.write_text(header + "\n".join(lines), encoding="utf-8")


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

def _find_i2v_segments(i2v_dir: Path, beat_id: int) -> List[Path]:
    base = _beat_id_to_name(beat_id)

    exact = i2v_dir / f"{base}.mp4"
    if exact.exists():
        return [exact]

    rx = re.compile(rf"^{re.escape(base)}_seg(\d+)\.mp4$", re.IGNORECASE)
    segs: List[Tuple[int, Path]] = []
    if i2v_dir.exists():
        for p in i2v_dir.iterdir():
            m = rx.match(p.name)
            if m:
                segs.append((int(m.group(1)), p))
    segs.sort(key=lambda t: t[0])
    return [p for _, p in segs]

def _video_effects_filter() -> str:
    filters = []
    filters.append(f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase")
    filters.append(f"crop={TARGET_W}:{TARGET_H}")

    if HANDHELD:
        filters.append("rotate=0.0015*sin(2*PI*t/4):c=black@0:ow=iw:oh=ih")
        filters.append(
            "crop=iw-8:ih-8:"
            "x=4+2*sin(2*PI*t/5):"
            "y=4+2*cos(2*PI*t/6)"
        )


    if GRAIN_STRENGTH > 0:
        alls = max(1, min(30, int(GRAIN_STRENGTH * 120)))
        filters.append(f"noise=alls={alls}:allf=t+u")

    if VIGNETTE:
        filters.append("vignette=PI/4")

    filters.append(f"fps={TARGET_FPS}")
    filters.append(f"scale={TARGET_W}:{TARGET_H}")
    filters.append("format=yuv420p")
    return ",".join(filters)

def _ken_burns_filter(duration_s: float) -> str:
    frames = max(1, int(math.ceil(duration_s * TARGET_FPS)))
    inc = KB_ZOOM_PER_SEC / TARGET_FPS
    z = f"min(zoom+{inc:.8f},{KB_MAX_ZOOM})"
    x = "iw/2-(iw/zoom/2)+10*sin(2*PI*on/240)"
    y = "ih/2-(ih/zoom/2)+10*cos(2*PI*on/300)"

    filt = []
    filt.append(f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase")
    filt.append(f"crop={TARGET_W}:{TARGET_H}")
    filt.append(f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={TARGET_W}x{TARGET_H}:fps={TARGET_FPS}")
    filt.append("format=yuv420p")

    post = []
    if GRAIN_STRENGTH > 0:
        alls = max(1, min(30, int(GRAIN_STRENGTH * 120)))
        post.append(f"noise=alls={alls}:allf=t+u")
    if VIGNETTE:
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
    i2v_dir = run_dir / I2V_DIRNAME

    base = _beat_id_to_name(beat_id)
    out_path = tmp_dir / f"{base}_final.mp4"

    img_path = images_dir / f"{base}.png"
    if not img_path.exists():
        raise RuntimeError(f"Missing still image for beat {beat_id}: {img_path}")

    segs = _find_i2v_segments(i2v_dir, beat_id)
    if segs:
        src = segs[0]

        normalized = tmp_dir / f"{base}_i2v_normalized.mp4"
        src_dur = _ffprobe_duration(src)

        vf = [
            f"fps={TARGET_FPS}",
            "setpts=PTS-STARTPTS",
        ]

        if src_dur < beat_duration:
            pad = beat_duration - src_dur
            vf.append(f"tpad=stop_mode=clone:stop_duration={pad:.6f}")

        vf.append(f"trim=duration={beat_duration:.6f}")

        _run([
            "ffmpeg", "-y",
            "-i", str(src),
            "-vf", ",".join(vf),
            "-an",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(normalized),
        ])


        fx = tmp_dir / f"{base}_fx.mp4"
        _run([
            "ffmpeg", "-y",
            "-i", str(normalized),
            "-vf", _video_effects_filter(),
            "-an",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(fx),
        ])

        return fx

    _run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-t", f"{beat_duration:.6f}",
        "-i", str(img_path),
        "-vf", _ken_burns_filter(beat_duration),
        "-an",
        "-movflags", "+faststart",
        str(out_path),
    ])
    return out_path

def _xfade_chain(clips: List[Path], xfade_dur: float, out_path: Path) -> float:
    if len(clips) == 1:
        _run(["ffmpeg", "-y", "-i", str(clips[0]), "-c", "copy", str(out_path)])
        return _ffprobe_duration(out_path)

    durs = []
    for p in clips:
        d = _ffprobe_duration(p)
        if d <= 0:
            raise RuntimeError(f"Invalid clip duration: {p}")
        durs.append(d)

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

        fc_parts.append(
            f"[{current}][v{i}]"
            f"xfade=transition=fade:"
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

    
    # --- Auto captions ---
    ass_path = tmp_dir / "captions.ass"

    captions_ok = False

    if CAPTIONS_ENABLED:
        try:
            print("[caption] transcribing VO...")
            words = _transcribe_with_whisper(audio_path)
            captions = _build_caption_events(words)
            _write_ass_captions(captions, ass_path)
            shutil.copyfile(ass_path, out_dir / "captions.ass")
            captions_ok = True
            print(f"[caption] captions -> {ass_path.name}")
        except Exception as e:
            print(f"[caption] disabled (reason: {e})")


    # 1) Render each beat final clip
    beat_clips: List[Path] = []
    for b in beats:
        beat_id = int(b["beat_id"])
        dur = _safe_float(b.get("duration_seconds"), 0.0)
        if dur <= 0:
            raise RuntimeError(f"Invalid duration for beat {beat_id}: {dur}")
        clip = _render_beat_clip(run_dir, tmp_dir, beat_id, dur)
        beat_clips.append(clip)
        print(f"[render] beat {beat_id:03d} -> {clip.name}")

    # 2) Crossfade stitch all beats
    stitched_path = out_dir / "stitched_video.mp4"
    stitched_dur = _xfade_chain(beat_clips, XFADE_DUR, stitched_path)
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
    if captions_ok and (out_dir / "captions.ass").exists():
        vf.append(
            f"subtitles=captions.ass:original_size={TARGET_W}x{TARGET_H}"
        )

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
    else:
        _run([
            "ffmpeg", "-y",
            "-i", "stitched_video.mp4",
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


    print(f"[render] FINAL -> {final_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
