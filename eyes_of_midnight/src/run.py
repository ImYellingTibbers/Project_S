import json
import subprocess
import sys
import time
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CHANNEL_ROOT = PROJECT_ROOT.parent
RUNS_DIR = CHANNEL_ROOT / "runs"
VIDEO_PLAN_PATH = CHANNEL_ROOT / "video_plan.json"

STEP_1 = {"label": "Step 1 - Generate Script", "script": "run_steps/generate_script.py"}
STEP_2 = {"label": "Step 2 - Create VO", "script": "run_steps/create_vo.py"}
STEP_3 = {"label": "Step 3 - Generate Images", "script": "run_steps/generate_images.py"}
STEP_4 = {"label": "Step 4 - Render Video", "script": "run_steps/render_video.py"}

STEPS = [STEP_1, STEP_2, STEP_3, STEP_4]


def run_step(label, script_rel_path, extra_env: dict | None = None):
    script_path = (PROJECT_ROOT / script_rel_path).resolve()
    if not script_path.exists():
        print(f"Error: {label} missing at {script_path}")
        return False

    print(f"\n=== {label} ===")
    cmd = [sys.executable, str(script_path)]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["PYTHONUNBUFFERED"] = "1"
    if extra_env:
        env.update(extra_env)

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return result.returncode == 0


def get_newest_run_folder() -> str | None:
    """Return the name of the most recently modified run folder with video_final.mp4."""
    if not RUNS_DIR.exists():
        return None
    candidates = sorted(
        [d for d in RUNS_DIR.iterdir() if d.is_dir() and (d / "video_final.mp4").exists()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0].name if candidates else None


def record_run_folder(run_folder_name: str):
    """Append the completed run folder name to video_plan.json."""
    if not VIDEO_PLAN_PATH.exists():
        return
    plan = json.loads(VIDEO_PLAN_PATH.read_text(encoding="utf-8"))
    if run_folder_name not in plan.get("run_folders", []):
        plan.setdefault("run_folders", []).append(run_folder_name)
    VIDEO_PLAN_PATH.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"[RUN] Recorded run folder: {run_folder_name}")


def main():
    RUNS_DIR.mkdir(exist_ok=True)
    start_time = time.time()

    # Pass STORY_INDEX from environment into each step subprocess
    story_index = os.environ.get("STORY_INDEX", "")
    extra_env = {"STORY_INDEX": story_index} if story_index != "" else {}

    for step in STEPS:
        success = run_step(step["label"], step["script"], extra_env=extra_env)
        if not success:
            print(f"\nPipeline FAILED at {step['label']}")
            sys.exit(1)

    # Record which run folder was just created
    run_folder = get_newest_run_folder()
    if run_folder:
        record_run_folder(run_folder)

    elapsed = time.time() - start_time
    print(f"\nPipeline completed in {elapsed:.2f}s.")


if __name__ == "__main__":
    main()