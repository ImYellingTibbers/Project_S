import subprocess
import time
import requests
import os
import signal
from pathlib import Path

# ---- Configuration ----
COMFY_DIR = os.path.expanduser("~/ai/ComfyUI")
COMFY_URL = "http://127.0.0.1:8188"
READY_ENDPOINT = "/system_stats"
TIMEOUT = 180

# 🔴 HARD PIN the venv python that you just proved works
PYTHON_BIN = os.path.expanduser("~/ai/ComfyUI/venv/bin/python")

COMFY_CMD = [
    PYTHON_BIN,
    "main.py",
    "--normalvram",
    "--disable-pinned-memory",
    "--disable-async-offload",
    "--force-fp16",
]

# -----------------------
def _ready():
    try:
        r = requests.get(COMFY_URL + READY_ENDPOINT, timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def start():
    if _ready():
        print("[comfyui] Already running")
        return

    print("[comfyui] Starting ComfyUI")
    print("[comfyui] Using python:", PYTHON_BIN)

    proc = subprocess.Popen(
        COMFY_CMD,
        cwd=COMFY_DIR,
        stdout=None,   # <-- DO NOT SUPPRESS
        stderr=None,
        start_new_session=True,
    )

    start_time = time.time()
    while time.time() - start_time < TIMEOUT:
        if _ready():
            print("[comfyui] Ready")
            return
        time.sleep(2)

    print("[comfyui] Startup timeout reached, terminating")

    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except Exception:
        pass

    raise RuntimeError("ComfyUI failed to start within timeout")


if __name__ == "__main__":
    start()
