import json
import shutil
import subprocess
import sys
import re
from pathlib import Path

INDEX_RE = re.compile(r"(\d{3})_final_vid\.mp4")

ROOT = Path(__file__).resolve().parents[2]
AWAITING = ROOT / "awaiting_upload"
TEMP_RUN = ROOT / "_upload_tmp_run"

def find_next_item():
    if not AWAITING.exists():
        return None, None

    items = []
    for f in AWAITING.glob("*_final_vid.mp4"):
        m = INDEX_RE.match(f.name)
        if m:
            items.append((int(m.group(1)), f))

    if not items:
        return None, None

    items.sort()
    idx, video_path = items[0]
    meta_path = AWAITING / f"{idx:03d}_final_metadata.json"

    if not meta_path.exists():
        raise RuntimeError(f"Metadata missing for {video_path.name}")

    return video_path, meta_path

def main():
    video_path, meta_path = find_next_item()
    if not video_path:
        print("[queue] No videos awaiting upload")
        return

    print(f"[queue] Uploading {video_path.name}")

    # Prepare temp run folder
    if TEMP_RUN.exists():
        shutil.rmtree(TEMP_RUN)
    (TEMP_RUN / "render").mkdir(parents=True)

    shutil.copy2(video_path, TEMP_RUN / "render" / "final_short.mp4")
    shutil.copy2(meta_path, TEMP_RUN / "idea.json")

    cmd = [
        sys.executable,
        str(ROOT / "src" / "youtube_uploader.py"),
        "--run", str(TEMP_RUN),
        "--privacy", "public",
    ]

    print("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))

    if proc.returncode != 0:
        raise RuntimeError("Upload failed; queued files preserved")

    # Cleanup queue + temp
    video_path.unlink()
    meta_path.unlink()
    shutil.rmtree(TEMP_RUN)

    print("[queue] Upload successful; item removed from queue")

if __name__ == "__main__":
    main()
