import subprocess
import sys
import os
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


ROOT = Path(__file__).resolve().parents[1]


def _assert_exists(label: str, path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label}: missing {path.relative_to(ROOT)} ({path})")


def _latest_run_dir(runs_dir: Path) -> Path:
    _assert_exists("runs dir", runs_dir)
    run_dirs = sorted([p for p in runs_dir.iterdir() if p.is_dir()])
    if not run_dirs:
        raise RuntimeError("No run folders found in runs/")
    return run_dirs[-1]


def run_step(label: str, script_rel_path: str, extra_args: List[str] | None = None) -> None:
    script_path = (ROOT / script_rel_path).resolve()
    _assert_exists(label, script_path)

    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd += extra_args

    print(f"\n=== {label} ===")
    print("$ " + " ".join(cmd))

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"\nFAILED: {label} (exit {proc.returncode})")


def main() -> int:
    runs_dir = ROOT / "runs"
    runs_dir.mkdir(exist_ok=True)

    # Snapshot latest run BEFORE starting (helps detect whether a step created a new run folder)
    before = None
    try:
        before = _latest_run_dir(runs_dir)
    except Exception:
        before = None

    steps: List[Tuple[str, str]] = [
        ("Step 1 - Idea generator", "src/run_steps/idea_generator.py"),
        ("Step 2 - Idea selector", "src/run_steps/idea_selector.py"),
        ("Step 3 - Scriptwriter", "src/run_steps/scriptwriter.py"),
        ("Step 4 - Image prompt planner", "src/run_steps/image_prompt_planner.py"),
        ("Step 5 - VO generator", "src/run_steps/vo_generator.py"),
        ("Step 6 - Timing planner", "src/run_steps/timing_planner.py"),
        ("Step 7 - Image generator (ComfyUI)", "src/run_steps/image_generator.py"),
        ("Step 8 - I2V generator (ComfyUI)", "src/run_steps/i2v_generator.py"),
        ("Step 9 - Video Assembly", "src/run_steps/video_assembler.py"),
    ]

    for label, rel in steps:
        run_step(label, rel)
        
    # Resolve latest run AFTER pipeline completes
    after = _latest_run_dir(runs_dir)
    
    # Step 10 - Ingest Run (DB write, final)
    run_step(
        "Step 10 - Ingest Run",
        "src/run_steps/ingest_run.py",
        extra_args=[
            "--run-id", after.name,
        ],
    )


    # Step 11 - Queue for Upload (requires --run)
    run_step(
        "Step 10 - Queue for Upload",
        "src/uploader/queue_for_upload.py",
        extra_args=[
            "--run-id", after.name,
            "--channel-root", ".",
        ],
    )


    # Resolve latest run AFTER all steps
    after = _latest_run_dir(runs_dir)

    # If nothing changed, still print it, but call it out
    if before and after == before:
        print(f"\nDONE: Run complete. Latest run folder (unchanged): {after}")
    else:
        print(f"\nDONE: Run complete. Latest run folder: {after}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
