import os
import subprocess
import wave
import math
import struct
from pathlib import Path
from dotenv import load_dotenv
import requests
from sys import path

load_dotenv()

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]

# ---------------- CONFIG ----------------

INPUT_ENDCARD_MP4 = REPO_ROOT / "src/assets/cta_mp4/endcard_mp4/input_endcard.mp4"
OUTPUT_DIR = Path("cta_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import (
    ELEVENLABS_MODEL_ID,
    VO_SAMPLE_RATE_HZ,
)

SAMPLE_WIDTH = 2
CHANNELS = 1

CTAS = [
    "Subscribe for more spooky horror stories.",
    "Comment what chilling story you want to hear next.",
    "Follow for daily horror stories.",
    "If this tickled your nose, subscribe now.",
    "Comment if you have massive cojones and made it to the end.",
    "Comment below the scariest thing that's ever happened to you."
]

ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

# ---------------- ELEVENLABS ----------------

def tts_pcm(text: str) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("SHORTS_HORROR_ELEVENLABS_VOICE_ID")
    model_id = os.getenv(
        "SHORTS_HORROR_ELEVENLABS_MODEL_ID",
        ELEVENLABS_MODEL_ID
    )

    if not api_key or not voice_id:
        raise RuntimeError("Missing ElevenLabs env vars")

    resp = requests.post(
        ELEVENLABS_URL.format(voice_id=voice_id),
        headers={
            "xi-api-key": api_key,
            "Accept": "application/octet-stream",
            "Content-Type": "application/json",
        },
        params={"output_format": f"pcm_{VO_SAMPLE_RATE_HZ}"},
        json={"text": text, "model_id": model_id},
        timeout=60,
    )

    if resp.status_code != 200:
        raise RuntimeError(resp.text)

    return resp.content

def normalize_pcm(pcm: bytes, target_db=-18.0) -> bytes:
    samples = struct.unpack("<" + "h" * (len(pcm) // 2), pcm)
    rms = math.sqrt(sum(s*s for s in samples) / len(samples))
    if rms == 0:
        return pcm

    target = (10 ** (target_db / 20.0)) * 32768
    gain = target / rms

    out = []
    for s in samples:
        v = int(s * gain)
        v = max(min(v, 32767), -32768)
        out.append(v)

    return struct.pack("<" + "h" * len(out), *out)

def write_wav(path: Path, pcm: bytes):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(VO_SAMPLE_RATE_HZ)
        wf.writeframes(pcm)

# ---------------- MAIN ----------------

def main():
    if not INPUT_ENDCARD_MP4.exists():
        raise RuntimeError("Input endcard MP4 not found")

    for i, text in enumerate(CTAS):
        print(f"Generating CTA {i+1}/{len(CTAS)}")

        pcm = tts_pcm(text)
        pcm = normalize_pcm(pcm)

        wav_path = OUTPUT_DIR / f"cta_{i:02d}.wav"
        write_wav(wav_path, pcm)

        out_mp4 = OUTPUT_DIR / f"cta_{i:02d}.mp4"

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(INPUT_ENDCARD_MP4),
            "-i", str(wav_path),
            "-filter_complex",
            "[0:v]split=2[vf][vr];"
            "[vr]reverse[vr];"
            "[vf][vr]concat=n=2:v=1:a=0,"
            "loop=loop=-1:size=96:start=0[v]",
            "-map", "[v]",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(out_mp4)
        ]

        subprocess.run(cmd, check=True)

        print(f"-> {out_mp4.name}")

    print("All CTA endcards generated.")

if __name__ == "__main__":
    main()
