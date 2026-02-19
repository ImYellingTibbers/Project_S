import subprocess
import sys
import os

RUNS = 3

env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"

for i in range(1, RUNS + 1):
    print(f"\n=== Batch run {i}/{RUNS} ===")

    proc = subprocess.Popen(
        [sys.executable, "residual_fear/src/run.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")

    code = proc.wait()
    if code != 0:
        print("ERROR detected. Stopping batch.")
        break
