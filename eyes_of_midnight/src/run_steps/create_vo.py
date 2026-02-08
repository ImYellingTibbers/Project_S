from __future__ import annotations

import sys
import time
from pathlib import Path

import torch
import soundfile as sf
import numpy as np
from qwen_tts import Qwen3TTSModel

# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = ROOT / "runs"

REFERENCE_WAV = (
    ROOT
    / "src"
    / "assets"
    / "voice_ref"
    / "jacob_whisper_ref.wav"
)

# ============================================================
# TTS Model (singleton)
# ============================================================

_MODEL = None

def get_model() -> Qwen3TTSModel:
    global _MODEL
    if _MODEL is None:
        print("[TTS] Loading Qwen3-TTS-12Hz-1.7B-Base...", flush=True)
        _MODEL = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            device_map="cuda",
            dtype=torch.bfloat16,
            attn_implementation="sdpa",
        )
    return _MODEL

# ============================================================
# Voice parameters (Mr Nightmare–style restraint)
# ============================================================
# temperature:
#   Lower = flatter, more monotone delivery
#   Raise slightly for more emotional variation
TEMPERATURE = 0.45

# top_p:
#   Controls randomness ceiling
#   Lower = tighter, more predictable phrasing
TOP_P = 0.85

# repetition_penalty:
#   Prevents subtle looping / phrase echo
REPETITION_PENALTY = 1.1

MAX_NEW_TOKENS = 8192

# ============================================================
# Paragraph synthesis
# ============================================================

def synthesize_paragraph(
    model: Qwen3TTSModel,
    text: str,
    output_wav: Path,
    attempt: int,
):
    wavs, sr = model.generate_voice_clone(
        text=text,
        language="English",
        ref_audio=str(REFERENCE_WAV),
        x_vector_only_mode=True,
        max_new_tokens=MAX_NEW_TOKENS,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        repetition_penalty=REPETITION_PENALTY,
    )

    audio = wavs[0]
    sf.write(str(output_wav), audio, sr)
    

# ============================================================
# Audio stitching
# ============================================================

def stitch_audio_paragraphs(audio_dir: Path, output_path: Path):
    wav_files = sorted(audio_dir.glob("p*.wav"))

    if not wav_files:
        raise RuntimeError("No paragraph WAV files found for stitching")

    audio_blocks = []
    sample_rate = None

    for wav in wav_files:
        data, sr = sf.read(wav, dtype="float32")

        if sample_rate is None:
            sample_rate = sr
        elif sr != sample_rate:
            raise RuntimeError(
                f"Sample rate mismatch in {wav.name}: "
                f"{sr} != {sample_rate}"
            )

        audio_blocks.append(data)

    full_audio = np.concatenate(audio_blocks, axis=0)
    sf.write(output_path, full_audio, sample_rate)


# ============================================================
# Main
# ============================================================

def main():
    run_dirs = sorted(
        [
            d for d in RUNS_ROOT.iterdir()
            if d.is_dir() and (d / "script" / "paragraphs").exists()
        ],
        reverse=True,
    )

    if not run_dirs:
        raise RuntimeError(f"No run folders found in {RUNS_ROOT}")

    run_dir = run_dirs[0]
    run_id = run_dir.name


    paragraph_dir = run_dir / "script" / "paragraphs"
    audio_dir = run_dir / "audio" / "paragraphs"

    if not paragraph_dir.exists():
        raise RuntimeError(f"Paragraph directory not found: {paragraph_dir}")

    audio_dir.mkdir(parents=True, exist_ok=True)

    paragraph_files = sorted(paragraph_dir.glob("p*.txt"))

    if not paragraph_files:
        raise RuntimeError("No paragraph files found")

    model = get_model()

    print(f"[TTS] Run: {run_id}")
    print(f"[TTS] Paragraphs: {len(paragraph_files)}")

    for idx, p_file in enumerate(paragraph_files):
        text = p_file.read_text(encoding="utf-8").strip()
        out_wav = audio_dir / f"{p_file.stem}.wav"

        print(f"[TTS] ({idx+1}/{len(paragraph_files)}) {p_file.name}")

        success = False
        for attempt in range(1, 6):
            try:
                synthesize_paragraph(
                    model=model,
                    text=text,
                    output_wav=out_wav,
                    attempt=attempt,
                )
                success = True
                break
            except Exception as e:
                print(
                    f"[TTS] retry {attempt}/5 failed for {p_file.name}: {e}",
                    flush=True,
                )
                time.sleep(1)

        if not success:
            raise RuntimeError(
                f"TTS failed after 5 attempts for {p_file.name}"
            )

    full_audio_path = run_dir / "audio" / "full_narration.wav"

    print("[TTS] Stitching full narration...", flush=True)
    stitch_audio_paragraphs(audio_dir, full_audio_path)

    print("[TTS] Full narration written:", full_audio_path, flush=True)
    print("[TTS] All paragraphs synthesized successfully.", flush=True)


if __name__ == "__main__":
    main()
