import json
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime, timezone
from sys import path

# ---- project root bootstrap ----
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

RUNS_DIR = ROOT / "runs"
SCHEMA_VERSION = "1.0"

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_script_json(run_folder: Path, script_text: str, run_id: str) -> Path:
    run_folder.mkdir(parents=True, exist_ok=False)

    payload = {
        "schema": {"name": "script", "version": SCHEMA_VERSION},
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "script": script_text.strip(),
    }

    out_path = run_folder / "script.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def main():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    print("\nPaste your full script below.")
    print("When finished, press Ctrl+D (Linux/macOS) or Ctrl+Z + Enter (Windows).\n")

    try:
        script_text = ""
        while True:
            line = input()
            script_text += line + "\n"
    except EOFError:
        pass

    script_text = script_text.strip()

    if not script_text:
        print("❌ Script is empty. Aborting.")
        return

    run_id = make_run_id()
    run_folder = RUNS_DIR / run_id

    try:
        out_path = write_script_json(run_folder, script_text, run_id)
    except Exception as e:
        print(f"❌ Failed to create run: {e}")
        return

    print(f"\n✅ Run created: {run_folder}")
    print(f"📄 script.json saved to: {out_path}")



if __name__ == "__main__":
    main()
