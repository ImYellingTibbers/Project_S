"""
Full batch pipeline for Eyes of Midnight.

Flow:
  Step 0  - plan_video.py        → picks a title, writes video_plan.json
  Step 1  - run.py (story 0)     → full pipeline for story 1
  Step 2  - run.py (story 1)     → full pipeline for story 2
  Step 3  - run.py (story 2)     → full pipeline for story 3
  Step 4  - stitch_videos.py     → assembles compiled_final.mp4
  Step 5  - generate_metadata.py → writes metadata.json

Usage:
    python eyes_of_midnight/src/batch_run.py
"""

import subprocess
import sys
import os
import time
from pathlib import Path

CHANNEL_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = Path(__file__).resolve().parent

env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"


def run_script(label: str, script_path: Path, extra_env: dict | None = None) -> bool:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")

    merged_env = env.copy()
    if extra_env:
        merged_env.update(extra_env)

    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=merged_env,
        cwd=str(CHANNEL_ROOT),
    )

    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="", flush=True)

    code = proc.wait()
    if code != 0:
        print(f"\n[BATCH] FAILED at: {label} (exit code {code})")
    return code == 0


def main():
    total_start = time.time()

    # ------------------------------------------------------------------
    # Step 0: Plan
    # ------------------------------------------------------------------
    ok = run_script(
        "Step 0 - Plan Video",
        SRC_ROOT / "plan_video.py",
    )
    if not ok:
        print("\n[BATCH] Stopped: planning step failed.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Steps 1-3: Three story pipeline runs
    # ------------------------------------------------------------------
    run_script_path = SRC_ROOT / "run.py"

    for story_index in range(3):
        label = f"Step {story_index + 1} - Story {story_index + 1} Pipeline"
        ok = run_script(
            label,
            run_script_path,
            extra_env={"STORY_INDEX": str(story_index)},
        )
        if not ok:
            print(f"\n[BATCH] Stopped: story {story_index + 1} pipeline failed.")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Step 4: Stitch
    # ------------------------------------------------------------------
    ok = run_script(
        "Step 4 - Stitch Videos",
        SRC_ROOT / "run_steps" / "stitch_videos.py",
    )
    if not ok:
        print("\n[BATCH] Stopped: stitching step failed.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 5: Metadata
    # ------------------------------------------------------------------
    ok = run_script(
        "Step 5 - Generate Metadata",
        SRC_ROOT / "run_steps" / "generate_metadata.py",
    )
    if not ok:
        print("\n[BATCH] Stopped: metadata step failed.")
        sys.exit(1)

    elapsed = time.time() - total_start
    print(f"\n[BATCH] Full batch complete in {elapsed:.2f}s.")


if __name__ == "__main__":
    main()
