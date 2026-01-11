import subprocess
import time
import sys

RUNS = 4
DELAY_SECONDS = 1200  # 20 minutes

for i in range(1, RUNS + 1):
    print(f"\n=== Batch run {i}/{RUNS} ===")

    result = subprocess.run(
        [sys.executable, "residual_fear/src/run.py"],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print("ERROR detected. Stopping batch.")
        print(result.stderr)
        break

    # if i < RUNS:
    #     time.sleep(DELAY_SECONDS)
