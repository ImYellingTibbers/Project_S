import os
import json
from sys import path
from pathlib import Path
from datetime import datetime, timezone
import wave
import requests
import math
import struct

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import (
    SCHEMA_VERSION,
    RUNS_DIR,
    ELEVENLABS_MODEL_ID,
    VO_SAMPLE_RATE_HZ,
)

from dotenv import load_dotenv
load_dotenv()

SCHEMA_NAME = "vo_generator"

# We will request raw PCM and wrap it into WAV ourselves.
# This avoids "wrong file type" issues and keeps timing deterministic.
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_run_folder() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError("runs/ folder not found")
    run_folders = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()])
    if not run_folders:
        raise RuntimeError("No run folders found in runs/")
    return run_folders[-1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _silence_bytes(sample_rate: int, seconds: float, sample_width: int = 2, channels: int = 1) -> bytes:
    frames = int(round(sample_rate * max(0.0, seconds)))
    # 16-bit little-endian PCM silence is just zero bytes.
    return b"\x00" * frames * sample_width * channels


def _pcm_to_wav_bytes(pcm: bytes, sample_rate: int, sample_width: int = 2, channels: int = 1) -> bytes:
    # Write to an in-memory wav (bytes) by using wave over a BytesIO buffer.
    # We avoid BytesIO import by writing to file directly in _write_wav_file().
    raise NotImplementedError("Use _write_wav_file() to write directly to disk.")


def _write_wav_file(path: Path, pcm_frames: bytes, sample_rate: int, sample_width: int = 2, channels: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_frames)


def _wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def elevenlabs_tts_pcm(
    api_key: str,
    voice_id: str,
    text: str,
    model_id: str,
    sample_rate: int = VO_SAMPLE_RATE_HZ,
) -> bytes:
    """
    Returns raw 16-bit little-endian PCM audio at sample_rate.
    """
    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    params = {"output_format": f"pcm_{sample_rate}"}
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/octet-stream",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        # Keep it simple. You can add voice_settings later if needed.
    }

    resp = requests.post(url, params=params, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"ElevenLabs TTS failed ({resp.status_code}): {resp.text[:500]}")
    return resp.content


def normalize_pcm_rms(
    pcm: bytes,
    target_rms_db: float = -18.0,
    sample_width: int = 2
) -> bytes:
    """
    Normalize 16-bit PCM audio to a target RMS level.
    Returns new PCM bytes.
    """
    if sample_width != 2:
        raise RuntimeError("Only 16-bit PCM supported for normalization")

    # Unpack PCM into signed int16 samples
    sample_count = len(pcm) // 2
    if sample_count == 0:
        return pcm

    samples = struct.unpack("<" + "h" * sample_count, pcm)

    # Compute RMS
    square_sum = sum(s * s for s in samples)
    rms = math.sqrt(square_sum / sample_count)
    if rms == 0:
        return pcm

    # Convert target dBFS to linear RMS
    target_rms = (10 ** (target_rms_db / 20.0)) * 32768.0

    gain = target_rms / rms

    # Apply gain with clipping protection
    normalized = []
    for s in samples:
        v = int(round(s * gain))
        if v > 32767:
            v = 32767
        elif v < -32768:
            v = -32768
        normalized.append(v)

    return struct.pack("<" + "h" * sample_count, *normalized)


def _read_wav_frames(path: Path) -> tuple[bytes, int, int, int]:
    """
    Returns (pcm_frames, sample_rate, sample_width, channels)
    """
    with wave.open(str(path), "rb") as wf:
        return (
            wf.readframes(wf.getnframes()),
            wf.getframerate(),
            wf.getsampwidth(),
            wf.getnchannels(),
        )


def main() -> int:
    load_dotenv() 
    
    # ---- env ----
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY not found in environment (.env)")

    voice_id = os.getenv("SHORTS_HORROR_ELEVENLABS_VOICE_ID", "").strip()
    if not voice_id:
        raise RuntimeError("SHORTS_HORROR_ELEVENLABS_VOICE_ID not found in environment (.env)")

    model_id = os.getenv("SHORTS_HORROR_ELEVENLABS_MODEL_ID", ELEVENLABS_MODEL_ID).strip()

    buffer_pre = float(os.getenv("VO_BUFFER_PRE_SECONDS", "0.25"))
    buffer_post = float(os.getenv("VO_BUFFER_POST_SECONDS", "0.25"))
    force_regen = os.getenv("VO_FORCE_REGEN", "0").strip() == "1"
    generate_full_wav = os.getenv("VO_GENERATE_FULL_WAV", "1").strip() == "1"

    # ---- find run + load script ----
    run_folder = find_latest_run_folder()
    script_path = run_folder / "script.json"
    if not script_path.exists():
        raise RuntimeError(f"script.json not found in {run_folder}")

    script_json = _read_json(script_path)
    script_text = (script_json.get("script") or "").strip()
    if not script_text:
        raise RuntimeError("script.json missing 'script' text")

    lines = [ln.strip() for ln in script_text.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("No non-empty lines found in script")

    # ---- output dirs ----
    vo_dir = run_folder / "vo"
    vo_dir.mkdir(parents=True, exist_ok=True)

    # ---- audio format ----
    sample_rate = VO_SAMPLE_RATE_HZ
    sample_width = 2  # 16-bit
    channels = 1


    pre_silence = _silence_bytes(sample_rate, buffer_pre, sample_width, channels)
    post_silence = _silence_bytes(sample_rate, buffer_post, sample_width, channels)

    timing_lines = []
    combined_frames_parts: list[bytes] = []

    current_t = 0.0

    for i, text in enumerate(lines):
        out_name = f"line_{i:03d}.wav"
        out_path = vo_dir / out_name

        if out_path.exists() and not force_regen:
            # Reuse existing audio for deterministic runs.
            seg_duration = _wav_duration_seconds(out_path)
            # We don't know speech-only duration if reused; approximate by subtracting buffers (clamped).
            speech_duration = max(0.0, seg_duration - (buffer_pre + buffer_post))
            with wave.open(str(out_path), "rb") as wf:
                combined_frames_parts.append(wf.readframes(wf.getnframes()))
        else:
            pcm = elevenlabs_tts_pcm(
                api_key=api_key,
                voice_id=voice_id,
                text=text,
                model_id=model_id,
                sample_rate=sample_rate,
            )
            pcm = normalize_pcm_rms(
                pcm,
                target_rms_db=float(os.getenv("VO_TARGET_RMS_DB", "-18.0")),
            )

            # Wrap: [pre silence] + [speech pcm] + [post silence]
            frames = pre_silence + pcm + post_silence
            _write_wav_file(out_path, frames, sample_rate, sample_width, channels)

            speech_duration = len(pcm) / float(sample_rate * sample_width * channels)
            seg_duration = len(frames) / float(sample_rate * sample_width * channels)
            combined_frames_parts.append(frames)

        start_time = current_t
        end_time = current_t + seg_duration
        timing_lines.append(
            {
                "line_index": i,
                "text": text,
                "file": f"vo/{out_name}",
                "speech_duration_seconds": round(speech_duration, 6),
                "segment_duration_seconds": round(seg_duration, 6),
                "start_time_seconds": round(start_time, 6),
                "end_time_seconds": round(end_time, 6),
                "buffer_pre_seconds": buffer_pre,
                "buffer_post_seconds": buffer_post,
            }
        )
        current_t = end_time

        print(f"[{i+1}/{len(lines)}] Wrote: {out_path}")

    # ---- combined wav ----
    combined_path = vo_dir / "combined.wav"
    combined_frames = b"".join(combined_frames_parts)
    _write_wav_file(combined_path, combined_frames, sample_rate, sample_width, channels)
    total_duration = len(combined_frames) / float(sample_rate * sample_width * channels)
    
   # ---- optional: full-pass narration wav (story only, no CTA) ----
    full_duration = None
    full_rel_path = None

    if generate_full_wav:
        full_path = vo_dir / "full.wav"
        full_text = " ".join(lines).strip()

        if full_text:
            pcm_full = elevenlabs_tts_pcm(
                api_key=api_key,
                voice_id=voice_id,
                text=full_text,
                model_id=model_id,
                sample_rate=sample_rate,
            )

            pcm_full = normalize_pcm_rms(
                pcm_full,
                target_rms_db=float(os.getenv("VO_TARGET_RMS_DB", "-18.0")),
            )

            full_frames = pcm_full

            _write_wav_file(full_path, full_frames, sample_rate, sample_width, channels)

            full_duration = _wav_duration_seconds(full_path)
            full_rel_path = "vo/full.wav"
            print(f"Wrote: {full_path}")



    out = {
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        "run_id": script_json.get("run_id"),
        "created_at": utc_now_iso(),
        "source_script": "script.json",
        "tts": {
            "provider": "elevenlabs",
            "voice_id_env": "SHORTS_HORROR_ELEVENLABS_VOICE_ID",
            "model_id": model_id,
            "sample_rate_hz": sample_rate,
            "channels": channels,
            "sample_width_bytes": sample_width,
            "buffer_pre_seconds": buffer_pre,
            "buffer_post_seconds": buffer_post,
        },
        "artifacts": {
            "combined_wav": "vo/combined.wav",
            "segments_dir": "vo/",
            **({"full_wav": full_rel_path} if full_rel_path else {}),
        },
        "timing": {
            "total_duration_seconds": round(total_duration, 6),
            **({"full_duration_seconds": round(full_duration, 6)} if full_duration is not None else {}),
            **({"full_vs_segment_scale": round((full_duration / total_duration), 6)} if (full_duration is not None and total_duration > 0) else {}),
            "line_count": len(lines),
            "lines": timing_lines,
        },
    }

    vo_json_path = run_folder / "vo.json"
    _write_json(vo_json_path, out)
    print(f"Wrote: {vo_json_path}")
    print(f"Wrote: {combined_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
