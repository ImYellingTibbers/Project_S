import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_ROOT / "runs"

STEPS = [
    # {"label": "Step 0 - Script Creator", "script": "run_steps/0_manual_run.py"},
    # {"label": "Step 1 - Script Generator", "script": "run_steps/1_script_generator.py"},
    # {"label": "Step 2 - Image Generator", "script": "run_steps/2_image_generator_comfy.py"},
    # {"label": "Step 3 - Voice Over Generator", "script": "run_steps/3_vo_generator.py"},
    # {"label": "Step 4 - Timing Planner", "script": "run_steps/4_timing_planner.py"},
    {"label": "Step 5 - Video Assembly", "script": "run_steps/5_video_assembly.py"},
    {"label": "Step 6 - Captions", "script": "run_steps/6_add_captions.py"},
]

def run_step(label, script_rel_path):
    script_path = (PROJECT_ROOT / script_rel_path).resolve()
    if not script_path.exists():
        print(f"❌ Error: {label} missing at {script_path}")
        return False

    print(f"\n=== {label} ===")
    cmd = [sys.executable, str(script_path)]
    env = {"PYTHONPATH": str(PROJECT_ROOT), "PYTHONUNBUFFERED": "1"}
    
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return result.returncode == 0

def main():
    RUNS_DIR.mkdir(exist_ok=True)
    start_time = time.time()

    for step in STEPS:
        success = run_step(step["label"], step["script"])
        if not success:
            print(f"\n🛑 Pipeline FAILED at {step['label']}")
            sys.exit(1)

    elapsed = time.time() - start_time
    print(f"\n✅ Pipeline completed successfully in {elapsed:.2f}s.")

if __name__ == "__main__":
    main()