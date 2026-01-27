import os
import json
import wave
import whisper
import sys
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ---- THE ABSOLUTE PATH FIX ----
ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "runs"
load_dotenv(dotenv_path=ROOT / ".env")

# --- CONFIGURATION ---
VO_SAMPLE_RATE_HZ = 24000
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
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.06,
            "use_speaker_boost": True
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


def split_script_for_vo(text: str, max_chars: int = 260):
    """
    Splits narration into natural VO-sized chunks.
    Prefers paragraph breaks, falls back to sentence splits.
    """
    parts = []
    buffer = ""

    for para in text.split("\n\n"):
        para = para.strip()
        buffer = ""
        if not para:
            continue

        if len(para) <= max_chars:
            parts.append(para)
            continue

        # sentence fallback
        for sentence in para.replace("—", ".").split("."):
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(buffer) + len(sentence) < max_chars:
                buffer += sentence + ". "
            else:
                parts.append(buffer.strip())
                buffer = sentence + ". "

        if buffer:
            parts.append(buffer.strip())
            buffer = ""

    return parts


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

        segments = split_script_for_vo(script_text)

        vo_dir = run / "vo"
        vo_dir.mkdir(exist_ok=True)

        full_pcm = b""
        segment_timings = []
        current_offset = 0.0

        print(f"🎙️ [ELEVENLABS] Generating VO ({len(segments)} segments)")

        for i, text in enumerate(segments):
            text = text.strip()
            if not text:
                continue

            print(f"  ➜ VO Segment {i+1}/{len(segments)}: \"{text[:40]}...\"")

            pcm = elevenlabs_tts_pcm(text)

            duration = len(pcm) / (VO_SAMPLE_RATE_HZ * 2)

            segment_timings.append({
                "segment_index": i,
                "start": round(current_offset, 3),
                "end": round(current_offset + duration, 3),
                "text": text
            })

            full_pcm += pcm
            current_offset += duration

        # Finalize Audio File
        clean_path = vo_dir / "vo_clean.wav"
        write_wav(clean_path, full_pcm, VO_SAMPLE_RATE_HZ)
        
        # Whisper Alignment for Subtitles/Sync
        words, sentences = whisper_align(clean_path)
        
        output = {
            "created_at": datetime.now().isoformat(),
            "audio_file": "vo/vo_clean.wav",
            "total_duration": round(current_offset, 2),
            "segments_timing": segment_timings,
            "alignment": {"sentences": sentences, "words": words}
        }
        
        with open(run / "vo.json", "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"🚀 SUCCESS: ElevenLabs VO generated for {run.name}")
        print(f"⏱️ Total Duration: {round(current_offset, 2)}s")

    except Exception as e:
        print(f"\n❌ ERROR LOG:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()