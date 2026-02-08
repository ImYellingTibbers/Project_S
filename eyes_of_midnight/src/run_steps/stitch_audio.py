from __future__ import annotations

from pathlib import Path
import soundfile as sf
import numpy as np

# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = ROOT / "runs"

OUTPUT_NAME = "full_narration.wav"

# ============================================================
# Helpers
# ============================================================

def find_latest_audio_run() -> Path:
    run_dirs = sorted(
        [
            d for d in RUNS_ROOT.iterdir()
            if d.is_dir() and (d / "audio" / "paragraphs").exists()
        ],
        reverse=True,
    )

    if not run_dirs:
        raise RuntimeError("No runs with audio paragraphs found")

    return run_dirs[0]


def stitch_wavs(wav_files: list[Path], output_path: Path):
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
    run_dir = find_latest_audio_run()

    audio_dir = run_dir / "audio" / "paragraphs"
    wav_files = sorted(audio_dir.glob("p*.wav"))

    if not wav_files:
        raise RuntimeError("No paragraph WAV files found")

    output_path = run_dir / "audio" / OUTPUT_NAME

    print(f"[STITCH] Run: {run_dir.name}", flush=True)
    print(f"[STITCH] Paragraph WAVs: {len(wav_files)}", flush=True)
    print(f"[STITCH] Output: {output_path}", flush=True)

    stitch_wavs(wav_files, output_path)

    print("[STITCH] Full narration written successfully.", flush=True)


if __name__ == "__main__":
    main()
