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
ROOT = Path("/home/jcpix/projects/Project_S/TEST")
RUNS_DIR = ROOT / "runs"
load_dotenv(dotenv_path=ROOT / ".env")

# --- CONFIGURATION ---
VO_SAMPLE_RATE_HZ = 44100 # ElevenLabs supports higher quality
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

def find_latest_run_folder() -> Path:
    if not RUNS_DIR.exists():
        raise RuntimeError(f"Directory NOT FOUND: {RUNS_DIR}")
    
    runs = sorted(
        [p for p in RUNS_DIR.iterdir() if p.is_dir() and p.name.startswith("run_")],
        key=os.path.getmtime
    )
    
    if not runs: 
        raise RuntimeError(f"No 'run_' folders found in {RUNS_DIR}")
    
    for run in reversed(runs):
        script_path = run / "script.json"
        if script_path.exists() and script_path.stat().st_size > 0:
            return run
            
    raise RuntimeError(f"No folder in {RUNS_DIR} contains a valid script.json")

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
        "Accept": "audio/mpeg", # We get MPEG and convert if needed, or use pcm_44100
    }
    
    # Using pcm_44100 for raw processing compatibility
    params = {"output_format": "pcm_44100"}
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
    model = whisper.load_model("base")
    result = model.transcribe(str(audio_path), word_timestamps=True)
    words, sentences = [], []
    for seg in result["segments"]:
        sentences.append({"text": seg["text"].strip(), "start": round(seg["start"], 3), "end": round(seg["end"], 3)})
        for w in seg.get("words", []):
            words.append({"word": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)})
    return words, sentences

def main():
    try:
        run = find_latest_run_folder()
        script_path = run / "script.json"
        
        with open(script_path, "r") as f:
            data = json.load(f)

        segments = data.get("segments", [])
        if not segments:
            raise RuntimeError(f"No segments found in {script_path}")

        vo_dir = run / "vo"
        vo_dir.mkdir(exist_ok=True)
        
        full_pcm = b""
        segment_timings = []
        current_offset = 0.0

        print(f"🎙️ [ELEVENLABS] Generating VO for: {data.get('title', 'Untitled')}")

        for i, seg in enumerate(segments):
            text = seg.get('text', '').strip()
            if not text: continue

            print(f"  ➜ Processing Segment {i+1}/{len(segments)}: \"{text[:30]}...\"")
            
            # Generate audio for the segment
            pcm = elevenlabs_tts_pcm(text)
            
            # Calculate duration (PCM 16-bit Mono = 2 bytes per sample)
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