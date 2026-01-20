import json
import shutil
import subprocess
import sys
import re
from pathlib import Path

INDEX_RE = re.compile(r"(\d{3})_final_vid\.mp4")

ROOT = Path(__file__).resolve().parents[2]
AWAITING = ROOT / "awaiting_upload"
UPLOADER = ROOT / "src" / "uploader" / "youtube_uploader.py"

print("[uploader] queued_youtube_uploader.py STARTED")

def find_next_item():
    vids = sorted(AWAITING.glob("*_final_vid.mp4"))
    if not vids:
        return None, None

    vid = vids[0]
    meta = vid.with_name(vid.name.replace("_final_vid.mp4", "_meta.json"))

    if not meta.exists():
        raise RuntimeError(f"Missing metadata for {vid.name}")

    return vid, meta

def main():
    video_path, meta_path = find_next_item()

    if not video_path:
        print("[uploader] Queue empty")
        return

    print("[uploader] video:", video_path)
    print("[uploader] meta :", meta_path)

    cmd = [
        "python3",
        str(UPLOADER),
        "--video", str(video_path),
        "--meta", str(meta_path),
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    print("[uploader] stdout:")
    print(proc.stdout)

    print("[uploader] stderr:")
    print(proc.stderr)

    if proc.returncode != 0:
        raise RuntimeError("Upload failed; queued files preserved")

    video_path.unlink()
    meta_path.unlink()

    print("[uploader] Upload successful; item removed from queue")


if __name__ == "__main__":
    main()
