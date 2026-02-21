#!/usr/bin/env python3
"""
Project S — Master Night Runner
Run from: ~/projects/Project_S
Usage:    python run_all.py

To skip a channel tonight, set its flag to False below.
To add a new channel, add an entry to the RUNS list.
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ============================================================
# Configuration — edit here each night as needed
# ============================================================

ROOT = Path(__file__).resolve().parent

RUNS = [
    {
        "label": "The Rulebook",
        "script": ROOT / "the_rulebook" / "src" / "run.py",
        "enabled": True,
        "repeat": 2,
    },
    {
        "label": "Eyes of Midnight",
        "script": ROOT / "eyes_of_midnight" / "src" / "run.py",
        "enabled": True,
        "repeat": 3,
    },
]

# ============================================================
# Runner
# ============================================================

def run_script(label: str, script: Path, run_number: int = 1) -> bool:
    """Run a single script. Returns True on success, False on failure."""

    display = f"{label}" if run_number == 1 else f"{label} (run {run_number})"

    print(f"\n{'=' * 60}", flush=True)
    print(f"  STARTING: {display}", flush=True)
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'=' * 60}", flush=True)

    if not script.exists():
        print(f"  ERROR: Script not found: {script}", flush=True)
        return False

    start = time.time()

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=script.parent.parent,  # run from the channel root (e.g. the_rulebook/)
    )

    elapsed = time.time() - start
    mins, secs = divmod(int(elapsed), 60)

    if result.returncode == 0:
        print(f"\n  FINISHED: {display} — {mins}m {secs}s", flush=True)
        print(f"{'=' * 60}", flush=True)
        return True
    else:
        print(f"\n  FAILED:   {display} — exit code {result.returncode}", flush=True)
        print(f"{'=' * 60}", flush=True)
        return False


def main() -> None:
    overall_start = time.time()
    print(f"Project S — Night Run starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    for channel in RUNS:
        if not channel["enabled"]:
            print(f"\n  SKIPPED: {channel['label']}", flush=True)
            continue

        for i in range(1, channel["repeat"] + 1):
            success = run_script(channel["label"], channel["script"], run_number=i)
            results.append((channel["label"], i, success))

            if not success:
                print(f"\n🛑 Stopping — {channel['label']} failed.", flush=True)
                sys.exit(1)

    # ---- Summary ----
    elapsed = time.time() - overall_start
    hours, remainder = divmod(int(elapsed), 3600)
    mins, secs = divmod(remainder, 60)

    print(f"\n{'=' * 60}", flush=True)
    print(f"  ALL RUNS COMPLETE — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"  Total time: {hours}h {mins}m {secs}s", flush=True)
    print(f"{'=' * 60}", flush=True)

    for label, run_num, success in results:
        status = "✓" if success else "✗"
        run_str = f" (run {run_num})" if run_num > 1 else ""
        print(f"  {status} {label}{run_str}", flush=True)

    print()


if __name__ == "__main__":
    main()