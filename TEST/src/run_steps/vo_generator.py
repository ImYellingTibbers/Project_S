import os
import json
import math
import wave
import struct
import requests
import whisper
from sys import path
from pathlib import Path
from datetime import datetime, timezone

# ---- project root bootstrap ----
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import SCHEMA_VERSION, VO_SAMPLE_RATE_HZ, ELEVENLABS_MODEL_ID

RUNS_DIR = ROOT / "runs"

from dotenv import load_dotenv
load_dotenv()

SCHEMA_NAME = "vo_generator_simple"
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


# -----------------------------
# helpers
# -----------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, obj: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def find_latest_run_folder() -> Path:
    runs = sorted([p for p in RUNS_DIR.iterdir() if p.is_dir()])
    if not runs:
        raise RuntimeError("No runs found")
    return runs[-1]


def write_wav(path_out: Path, pcm: bytes, sample_rate: int) -> None:
    path_out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path_out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


def elevenlabs_tts_pcm(api_key: str, voice_id: str, text: str, model_id: str, sample_rate: int) -> bytes:
    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/octet-stream",
    }
    params = {"output_format": f"pcm_{sample_rate}"}
    payload = {"text": text, "model_id": model_id}

    r = requests.post(url, headers=headers, params=params, json=payload, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs failed: {r.text[:300]}")
    return r.content


def normalize_pcm_rms(pcm: bytes, target_rms_db: float) -> bytes:
    samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
    if not samples:
        return pcm

    sq = sum(s * s for s in samples)
    rms = math.sqrt(sq / len(samples))
    if rms <= 0:
        return pcm

    target = (10 ** (target_rms_db / 20.0)) * 32768.0
    gain = target / rms

    out = []
    for s in samples:
        v = int(s * gain)
        out.append(max(-32768, min(32767, v)))

    return struct.pack("<" + "h" * len(out), *out)


def pcm_to_samples(pcm: bytes) -> list[int]:
    return list(struct.unpack("<" + "h" * (len(pcm) // 2), pcm))


def find_silence_runs(samples, sample_rate, silence_dbfs, min_silence_ms=100):
    frame_len = int(sample_rate * 0.01)
    thresh = (10 ** (silence_dbfs / 20.0)) * 32768
    min_frames = max(1, int(min_silence_ms / 10))

    silent = []
    for i in range(0, len(samples), frame_len):
        frame = samples[i:i + frame_len]
        rms = math.sqrt(sum(s * s for s in frame) / max(1, len(frame)))
        silent.append(rms < thresh)

    runs = []
    start = None
    for i, is_silent in enumerate(silent):
        if is_silent and start is None:
            start = i
        elif not is_silent and start is not None:
            if i - start >= min_frames:
                runs.append((start * frame_len, i * frame_len))
            start = None

    if start is not None and len(silent) - start >= min_frames:
        runs.append((start * frame_len, len(samples)))

    return runs


def trim_silence_with_buffers(
    pcm: bytes,
    sample_rate: int,
    silence_dbfs: float,
    max_pause_sec: float,
):
    samples = pcm_to_samples(pcm)
    runs = find_silence_runs(samples, sample_rate, silence_dbfs)

    max_pause = int(max_pause_sec * sample_rate)

    out = []
    cursor = 0

    for start, end in runs:
        # voiced before silence
        if start > cursor:
            out.extend(samples[cursor:start])

        silence_len = end - start
        keep = min(silence_len, max_pause)

        out.extend(samples[start : start + keep])
        cursor = end

    if cursor < len(samples):
        out.extend(samples[cursor:])

    return struct.pack("<" + "h" * len(out), *out)


def whisper_align(audio_path: Path):
    model = whisper.load_model("base")
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        condition_on_previous_text=False,
        fp16=False,
    )

    words = []
    sentences = []

    for seg in result["segments"]:
        sentences.append({
            "text": seg["text"].strip(),
            "start_time": round(seg["start"], 6),
            "end_time": round(seg["end"], 6),
            "duration": round(seg["end"] - seg["start"], 6),
        })

        for w in seg.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start_time": round(w["start"], 6),
                "end_time": round(w["end"], 6),
                "duration": round(w["end"] - w["start"], 6),
            })

    return words, sentences


# -----------------------------
# main
# -----------------------------
def main() -> int:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")

    silence_dbfs = float(os.getenv("VO_SILENCE_THRESHOLD_DBFS", "-40"))
    max_pause_sec = float(os.getenv("VO_MAX_PAUSE_SECONDS", "0.1"))
    target_rms_db = float(os.getenv("VO_TARGET_RMS_DB", "-16"))
    force_regen = False

    if not api_key or not voice_id:
        raise RuntimeError("Missing ELEVENLABS env vars")

    run = find_latest_run_folder()
    script_json = _read_json(run / "script.json")
    script_text = script_json.get("script", "").strip()
    if not script_text:
        raise RuntimeError("Empty script")

    vo_dir = run / "vo"
    vo_dir.mkdir(parents=True, exist_ok=True)

    raw_path = vo_dir / "full_raw.wav"
    clean_path = vo_dir / "vo_clean.wav"

    if not raw_path.exists() or force_regen:
        pcm = elevenlabs_tts_pcm(
            api_key,
            voice_id,
            script_text,
            ELEVENLABS_MODEL_ID,
            VO_SAMPLE_RATE_HZ,
        )
        pcm = normalize_pcm_rms(pcm, target_rms_db)
        write_wav(raw_path, pcm, VO_SAMPLE_RATE_HZ)
    else:
        with wave.open(str(raw_path), "rb") as wf:
            pcm = wf.readframes(wf.getnframes())

    cleaned_pcm = trim_silence_with_buffers(
        pcm,
        VO_SAMPLE_RATE_HZ,
        silence_dbfs,
        max_pause_sec,
    )

    write_wav(clean_path, cleaned_pcm, VO_SAMPLE_RATE_HZ)

    words, sentences = whisper_align(clean_path)

    out = {
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        "run_id": script_json.get("run_id"),
        "created_at": utc_now_iso(),
        "artifacts": {
            "full_raw_wav": "vo/full_raw.wav",
            "cleaned_wav": "vo/vo_clean.wav",
        },
        "timing": {
            "sentences": sentences,
            "words": words,
            "total_duration_seconds": round(len(cleaned_pcm) / (VO_SAMPLE_RATE_HZ * 2), 6),
        },
    }

    _write_json(run / "vo.json", out)
    print("VO generation + timing complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
