import subprocess
import sys
import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.kill_gpu_users import kill_comfyui, kill_ollama
from src.tools.start_comfyui import start as start_comfyui

ROOT = PROJECT_ROOT
MAX_RUN_RETRIES = 5
SCRIPT_RETRY_START_LABEL = "Step 1 - Idea generator"


# -------------------------
# Utilities
# -------------------------

def kill_gpu_stack():
    print("[runner] Killing GPU / LLM processes")
    kill_gpu_users()
    time.sleep(3)


def run_step(label: str, script_rel_path: str, extra_args: List[str] | None = None) -> int:
    script_path = (ROOT / script_rel_path).resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"{label}: missing {script_path}")

    cmd = [sys.executable, str(script_path)]
    if extra_args:
        cmd += extra_args

    print(f"\n=== {label} ===")
    print("$ " + " ".join(cmd))

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["PYTHONUNBUFFERED"] = "1"   # ensure child scripts flush

    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered
    )

    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")

    return proc.wait()


def latest_run_dir(runs_dir: Path) -> Path:
    run_dirs = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    if not run_dirs:
        raise RuntimeError("No run folders found in runs/")
    return run_dirs[-1]


OLLAMA_LIVE_LOG = ROOT / "ollama_live.log"

def clear_ollama_log():
    if OLLAMA_LIVE_LOG.exists():
        print("[runner] Clearing ollama_live.log")
        OLLAMA_LIVE_LOG.write_text("")


# -------------------------
# Pipeline Step Definitions
# -------------------------

STEP_1_SCRIPTWRITER = {
    "label": "Step 1 - Scriptwriter",
    "script": "src/run_steps/scriptwriter.py",
}

STEP_2_VO_GENERATOR = {
    "label": "Step 2 - VO Generation",
    "script": "src/run_steps/scriptwriter.py",
}

STEP_3_STORYBOARD_1 = {
    "label": "Step 3 - Storyboard 1",
    "script": "src/run_steps/storyboard_1.py",
}

STEP_4_VISUAL_CANON = {
    "label": "Step 4 - Visual Canon",
    "script": "src/run_steps/visual_canon.py",
}

STEP_5_STORYBOARD_2 = {
    "label": "Step 5 - Storyboard 2",
    "script": "src/run_steps/storyboard_2.py",
}

STEP_6_STORYBOARD_3 = {
    "label": "Step 6 - Storyboard 3",
    "script": "src/run_steps/storyboard_3.py",
}

STEP_7_STORYBOARD_4 = {
    "label": "Step 7 - Storyboard 4",
    "script": "src/run_steps/storyboard_4.py",
}

STEP_8_IMAGE_PROMPT_GENERATOR = {
    "label": "Step 8 - Image Prompt Generator",
    "script": "src/run_steps/image_prompt_generator.py",
}

STEP_9_IMAGE_GENERATOR = {
    "label": "Step 9 - Image Generator",
    "script": "src/run_steps/image_generator.py",
    "start_comfyui": True,    # Trigger the start_comfyui() helper
}

# -------------------------
# Pipeline Assembly
# -------------------------

def build_steps(run_id: str | None = None) -> List[Dict[str, Any]]:

    return [
        # STEP_1_SCRIPTWRITER,
        # STEP_2_VO_GENERATOR,
        # STEP_3_STORYBOARD_1,
        # STEP_4_VISUAL_CANON,
        # STEP_5_STORYBOARD_2,
        # STEP_6_STORYBOARD_3,
        STEP_7_STORYBOARD_4,
        STEP_8_IMAGE_PROMPT_GENERATOR,
        # STEP_9_IMAGE_GENERATOR,
    ]

# -------------------------
# Runner
# -------------------------

def main() -> int:
    runs_dir = ROOT / "runs"
    runs_dir.mkdir(exist_ok=True)
    log_file = ROOT / "runs" / "pipeline_log.jsonl"

    for attempt in range(1, MAX_RUN_RETRIES + 1):
        with log_file.open("a", encoding="utf-8") as lf:
            lf.write(json.dumps({
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "attempt": attempt,
                "event": "pipeline_start"
            }) + "\n")

        print(f"\n=== PIPELINE RUN ATTEMPT {attempt} ===")
        print("[runner] Ensuring ComfyUI is not running at pipeline start")
        kill_comfyui()
        retry_from_script = False

        # clear_ollama_log()

        steps = build_steps()

        for step in steps:        
            label = step["label"]
            script = step["script"]

            if step.get("needs_gpu_clean"):
                kill_gpu_stack()

            if step.get("start_comfyui"):
                print("[runner] Starting ComfyUI")
                start_comfyui()

            extra_args = None
            if "extra_args" in step:
                run_id = latest_run_dir(runs_dir).name
                extra_args = step["extra_args"](run_id)
                
            with log_file.open("a", encoding="utf-8") as lf:
                lf.write(json.dumps({
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "attempt": attempt,
                    "event": "step_start",
                    "step": label,
                }) + "\n")

            code = run_step(label, script, extra_args)
            if label == "Step 9 - Image generator (ComfyUI)":
                print("[runner] Image generation complete — killing ComfyUI to free GPU")
                kill_comfyui()

            if label == "Step 1 - Idea generator":
                run_dir_for_attempt = latest_run_dir(runs_dir)
                run_id = run_dir_for_attempt.name

            with log_file.open("a", encoding="utf-8") as lf:
                lf.write(json.dumps({
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "attempt": attempt,
                    "event": "step_end",
                    "step": label,
                    "exit_code": code,
                }) + "\n")

            if code != 0:
                raise SystemExit(f"\nFAILED: {label} (exit {code})")

        print("[runner] Pipeline completed successfully.")
        break


    else:
        raise SystemExit("[runner] Max pipeline retries exceeded.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
