import json
import shutil
import argparse
from pathlib import Path
import re

INDEX_RE = re.compile(r"(\d{3})_final_vid\.mp4")

def get_next_index(awaiting_dir: Path) -> int:
    max_idx = 0
    for f in awaiting_dir.glob("*_final_vid.mp4"):
        m = INDEX_RE.match(f.name)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1

def main(run_id: str, channel_root: Path):
    # Resolve paths relative to channel root
    run_dir = channel_root / "runs" / run_id
    final_video = run_dir / "render" / "final_short.mp4"
    idea_json = run_dir / "idea.json"

    if not final_video.exists():
        raise FileNotFoundError(f"Final video not found: {final_video}")
    if not idea_json.exists():
        raise FileNotFoundError(f"idea.json not found: {idea_json}")

    awaiting_dir = channel_root / "awaiting_upload"
    awaiting_dir.mkdir(parents=True, exist_ok=True)

    next_idx = get_next_index(awaiting_dir)
    idx_str = f"{next_idx:03d}"

    vid_out = awaiting_dir / f"{idx_str}_final_vid.mp4"
    meta_out = awaiting_dir / f"{idx_str}_final_metadata.json"

    # Copy video
    shutil.copy2(final_video, vid_out)

    # Load idea.json
    with idea_json.open("r", encoding="utf-8") as f:
        idea = json.load(f)

    yt = idea["data"]["youtube"]

    upload_metadata = {
        "run_id": idea.get("run_id"),
        "title": yt["title"],
        "description": "\n".join(yt.get("description_lines", [])),
        "tags": yt.get("tags", []),
        "language": yt.get("language", "en"),
        "made_for_kids": yt.get("made_for_kids", False),
        "content_flags": yt.get("content_flags", {})
    }

    with meta_out.open("w", encoding="utf-8") as f:
        json.dump(upload_metadata, f, indent=2)

    print(f"[queue] Queued run {run_id} as {idx_str}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--channel-root",
        required=True,
        type=Path,
        help="Path to channel root (e.g. residual_fear/)"
    )
    args = parser.parse_args()

    main(args.run_id, args.channel_root)
