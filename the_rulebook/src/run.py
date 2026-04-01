import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_ROOT / "runs"

STEP_0 = {"label": "Step 0 - Kill GPU Users", "script": "tools/kill_gpu_users.py"}
STEP_1 = {"label": "Step 1 - Generate Script", "script": "run_steps/generate_script.py"}
STEP_2 = {"label": "Step 2 - Create VO", "script": "run_steps/create_vo.py"}
STEP_3 = {"label": "Step 3 - Generate Images", "script": "run_steps/generate_images.py"}
STEP_4 = {"label": "Step 4 - Render Video", "script": "run_steps/render_video.py"}
STEP_5 = {"label": "Step 5 - Generate Metadata", "script": "run_steps/generate_metadata.py"}

STEPS = [
    STEP_0,
    STEP_1,
    STEP_2,
    STEP_3,
    STEP_4,
    STEP_5,
]

# Steps that get one automatic retry after a kill_all() if they fail.
RETRYABLE_STEPS = {"Step 3 - Generate Images"}

sys.path.insert(0, str(PROJECT_ROOT))
from tools.kill_gpu_users import kill_all


def run_step(label, script_rel_path):
    script_path = (PROJECT_ROOT / script_rel_path).resolve()
    if not script_path.exists():
        print(f"❌ Error: {label} missing at {script_path}")
        return False

    print(f"\n=== {label} ===")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["PYTHONUNBUFFERED"] = "1"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        env=env,
    )
    return result.returncode == 0


def main():
    RUNS_DIR.mkdir(exist_ok=True)
    start_time = time.time()

    for step in STEPS:
        label = step["label"]
        success = run_step(label, step["script"])

        if not success and label in RETRYABLE_STEPS:
            print(f"\n⚠️  {label} failed — clearing GPU stack and retrying...")
            kill_all()
            time.sleep(15)
            print(f"\n=== {label} (retry) ===")
            success = run_step(label, step["script"])

        if not success:
            print(f"\n🛑 Pipeline FAILED at {label}")
            sys.exit(1)

    elapsed = time.time() - start_time
    print(f"\n✅ Pipeline completed successfully in {elapsed:.2f}s.")


if __name__ == "__main__":
    main()