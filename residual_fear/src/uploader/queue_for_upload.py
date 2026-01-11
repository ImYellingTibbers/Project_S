import argparse
from pathlib import Path
import re
import random
import subprocess
import shutil
import json

INDEX_RE = re.compile(r"(\d{3})_final_vid\.mp4")

def get_next_index(awaiting_dir: Path) -> int:
    max_idx = 0
    for f in awaiting_dir.glob("*_final_vid.mp4"):
        m = INDEX_RE.match(f.name)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", "--run-id", dest="run_id", required=True)
    args = parser.parse_args()

    ROOT = Path(__file__).resolve().parents[2]
    RUNS_DIR = ROOT / "runs"
    AWAITING_DIR = ROOT / "awaiting_upload"
    TEMP_DIR = ROOT / "_tmp_queue"

    AWAITING_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)

    run_dir = RUNS_DIR / args.run_id
    story_vid = run_dir / "render" / "final_with_cta.mp4"

    if not story_vid.exists():
        raise FileNotFoundError(f"Missing story_only.mp4 in {run_dir}")

    idx = get_next_index(AWAITING_DIR)
    idx_str = f"{idx:03d}"

    temp_out = TEMP_DIR / f"{idx_str}_concat.mp4"
    final_out = AWAITING_DIR / f"{idx_str}_final_vid.mp4"
    meta_out = AWAITING_DIR / f"{idx_str}_meta.json"
    shutil.copy(story_vid, final_out)

    meta_src = run_dir / "metadata.json"
    if not meta_src.exists():
        raise FileNotFoundError("metadata.json missing in run dir")

    metadata = json.loads(meta_src.read_text(encoding="utf-8"))

    upload_payload = {
        "run_id": args.run_id,
        "video_file": final_out.name,
        "created_at": metadata.get("created_at"),
        "metadata": metadata.get("data"),
    }

    meta_out.write_text(
        json.dumps(upload_payload, indent=2),
        encoding="utf-8"
    )


    print(f"[queue] Queued run {args.run_id} as {idx_str}")

if __name__ == "__main__":
    main()
