from __future__ import annotations

import json
from pathlib import Path
import soundfile as sf

# ============================================================
# Configuration
# ============================================================

SILENCE_SECONDS = 0.75

# ============================================================
# Core timing logic
# ============================================================

def get_wav_duration(path: Path) -> float:
    with sf.SoundFile(path) as f:
        return len(f) / f.samplerate


def build_image_timing_plan(
    run_dir: Path,
) -> list[dict]:
    """
    Returns ordered image timing plan.

    Output format:
    [
      { "image": "chunk_00.png", "duration": 57.86 },
      { "image": "chunk_01.png", "duration": 65.23 }
    ]
    """

    paragraph_audio_dir = run_dir / "audio" / "paragraphs"
    paragraph_index_path = run_dir / "script" / "paragraph_index.json"
    visual_chunks_path = run_dir / "script" / "visual_chunks.json"

    if not paragraph_audio_dir.exists():
        raise RuntimeError(f"Missing paragraph audio dir: {paragraph_audio_dir}")

    paragraph_index = json.loads(
        paragraph_index_path.read_text(encoding="utf-8")
    )["paragraphs"]

    visual_chunks = json.loads(
        visual_chunks_path.read_text(encoding="utf-8")
    )["chunks"]

    # Cache paragraph durations
    paragraph_durations = {}

    for p in paragraph_index:
        pid = p["paragraph_id"]
        wav_path = paragraph_audio_dir / p["filename"].replace(".txt", ".wav")

        if not wav_path.exists():
            raise RuntimeError(f"Missing audio file: {wav_path}")

        paragraph_durations[pid] = get_wav_duration(wav_path)

    timing_plan = []

    for chunk in visual_chunks:
        chunk_id = chunk["chunk_id"]
        paragraph_ids = chunk["paragraph_ids"]

        duration = 0.0

        for i, pid in enumerate(paragraph_ids):
            duration += paragraph_durations[pid]

            # Add silence unless this is the FINAL paragraph of the ENTIRE script
            is_last_global_paragraph = (
                pid == max(paragraph_durations.keys())
            )

            if not is_last_global_paragraph:
                duration += SILENCE_SECONDS

        timing_plan.append({
            "image": f"chunk_{chunk_id:02d}.png",
            "duration": round(duration, 2),
        })

    return timing_plan


# ============================================================
# CLI entry
# ============================================================

def main():
    RUNS_ROOT = Path(__file__).resolve().parents[2] / "runs"

    run_dirs = sorted(
        [d for d in RUNS_ROOT.iterdir() if d.is_dir()],
        reverse=True,
    )

    if not run_dirs:
        raise RuntimeError("No run directories found")

    run_dir = run_dirs[0]

    timing = build_image_timing_plan(run_dir)

    out_path = run_dir / "video" / "image_timing.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_text(
        json.dumps(timing, indent=2),
        encoding="utf-8",
    )

    print("[TIMING] Image timing plan written:", out_path, flush=True)


if __name__ == "__main__":
    main()
