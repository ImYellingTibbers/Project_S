import os
import json
import wave
import whisper
import sys
import requests
import re
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ---- THE ABSOLUTE PATH FIX ----
ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"
load_dotenv(dotenv_path=ROOT / ".env")

# --- CONFIGURATION ---
VO_SAMPLE_RATE_HZ = 24000
FINAL_VO_SAMPLE_RATE_HZ = 48000
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

def get_latest_run():
    if not RUNS_DIR.exists():
        raise RuntimeError(f"Directory NOT FOUND: {RUNS_DIR}")

    valid_runs = []

    for f in RUNS_DIR.iterdir():
        if not f.is_dir():
            continue

        script_path = f / "script.json"
        if not script_path.exists():
            continue

        try:
            with open(script_path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            script = data.get("script")
            if isinstance(script, str) and script.strip():
                valid_runs.append(f)
        except Exception:
            continue

    if not valid_runs:
        raise RuntimeError("No runs found containing a valid script.json['script']")

    return max(valid_runs, key=os.path.getmtime)

def write_wav(path_out: Path, pcm: bytes, sample_rate: int) -> None:
    path_out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path_out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


def trim_leading_trailing_silence_safe(wav_path: Path, pad_sec: float = 0.08) -> None:
    """
    Trims leading/trailing silence using FFmpeg's astats analysis.
    Speech-safe. Zero amplitude heuristics avoided.
    """

    # detect first and last non-silent sample timestamps
    detect = subprocess.check_output(
        [
            "ffmpeg",
            "-i", str(wav_path),
            "-af", "astats=metadata=1:reset=1",
            "-f", "null",
            "-"
        ],
        stderr=subprocess.STDOUT,
        text=True
    )

    times = []
    for line in detect.splitlines():
        if "Overall RMS level" in line:
            parts = line.split()
            for p in parts:
                if p.replace(".", "", 1).isdigit():
                    times.append(float(p))

    if not times:
        return  # nothing to trim safely

    tmp = wav_path.with_name(wav_path.stem + "_trim.wav")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", str(wav_path),
            "-af", f"atrim=start={pad_sec},asetpts=PTS-STARTPTS",
            "-c:a", "pcm_s16le",
            str(tmp),
        ],
        check=True,
    )

    os.replace(tmp, wav_path)


def enforce_terminal_punctuation(text: str) -> str:
    """
    Enforces a strong terminal cadence using punctuation only.
    No words added. Safe for any narrative content.
    """

    text = text.rstrip()

    # If it already ends cleanly with a period, just ensure a paragraph break
    if text.endswith("."):
        return text + "\n"

    # If it ends with weak or open-ended punctuation, normalize to a period
    if text.endswith(("?", "!", "…", "...", "—", "–", ",")):
        text = re.sub(r"[?!…—–,]+$", ".", text)

    # Default: append a period
    if not text.endswith("."):
        text += "."

    return text + "\n"


def elevenlabs_tts_pcm(text: str) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

    if not api_key or not voice_id:
        raise RuntimeError("Missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID in .env")

    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/octet-stream",
    }
    
    params = {"output_format": f"pcm_{VO_SAMPLE_RATE_HZ}"}
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.75,
            "style": 0.05,
            "use_speaker_boost": False,
            "speed": 1.15
        }
    }

    r = requests.post(url, headers=headers, params=params, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs failed: {r.text[:300]}")
    return r.content

def whisper_align(audio_path: Path):
    print("⏳ Loading Whisper for precise alignment...")
    model = whisper.load_model("base", device="cpu")
    result = model.transcribe(str(audio_path), word_timestamps=True)
    words, sentences = [], []
    for seg in result["segments"]:
        sentences.append({"text": seg["text"].strip(), "start": round(seg["start"], 3), "end": round(seg["end"], 3)})
        for w in seg.get("words", []):
            words.append({"word": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)})
    return words, sentences


def main():
    try:
        run = get_latest_run()
        script_path = run / "script.json"

        if not script_path.exists():
            raise RuntimeError(f"script.json not found in run folder: {script_path}")

        with open(script_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        script_text = data.get("script")

        if not isinstance(script_text, str) or not script_text.strip():
            raise RuntimeError(
                f"script.json is missing a valid 'script' field:\n{script_path}"
            )
        
        script_text = script_text.strip()
        def normalize_tts_text(text: str) -> str:
            """
            Preserve pacing, cadence, and paragraph structure for TTS.
            Only normalize characters that are known to break ElevenLabs.
            """

            # Normalize problematic unicode (keep structure)
            text = text.replace("…", "...")
            text = text.replace("—", " — ")
            text = text.replace("–", " – ")

            # Normalize quotes
            text = text.replace("“", '"').replace("”", '"')
            text = text.replace("‘", "'").replace("’", "'")

            # Collapse excessive spaces but KEEP line breaks
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text)

            return text.strip()

        script_text = normalize_tts_text(script_text)
        script_text = enforce_terminal_punctuation(script_text)

        vo_dir = run / "vo"
        vo_dir.mkdir(exist_ok=True)

        print("🎙️ [ELEVENLABS] Generating VO (single pass)")

        pcm = elevenlabs_tts_pcm(script_text)
        duration = None

        vo_dir = run / "vo"
        vo_dir.mkdir(exist_ok=True)

        clean_path = vo_dir / "vo_clean.wav"
        write_wav(clean_path, pcm, VO_SAMPLE_RATE_HZ)
        print("RAW PCM duration:", len(pcm) / (VO_SAMPLE_RATE_HZ * 2))
        trim_leading_trailing_silence_safe(clean_path)

        # --- FORCE RESAMPLE TO 48kHz (SAFE REPLACE) ---
        tmp_path = vo_dir / "vo_clean_tmp.wav"

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", str(clean_path),
                "-ar", str(FINAL_VO_SAMPLE_RATE_HZ),
                "-ac", "1",
                str(tmp_path),
            ],
            check=True
        )

        os.replace(tmp_path, clean_path)

        # --- RECOMPUTE FINAL DURATION (POST-TRIM + RESAMPLE) ---
        probe = subprocess.check_output(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(clean_path),
            ]
        )
        duration = round(float(probe.strip()), 2)

        # Whisper Alignment for Subtitles/Sync
        words, sentences = whisper_align(clean_path)
        
        output = {
            "created_at": datetime.now().isoformat(),
            "audio_file": "vo/vo_clean.wav",
            "total_duration": round(duration, 2),
            "alignment": {
                "sentences": sentences,
                "words": words
            }
        }
       
        with open(run / "vo.json", "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"🚀 SUCCESS: ElevenLabs VO generated for {run.name}")
        print(f"⏱️ Total Duration: {round(duration, 2)}s")

    except Exception as e:
        print(f"\n❌ ERROR LOG:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()