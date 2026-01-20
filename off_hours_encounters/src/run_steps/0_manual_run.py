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

    root = tk.Tk()
    root.title("Manual Run Creator - Paste Script")

    root.geometry("900x600")

    label = tk.Label(
        root,
        text="Paste your full YouTube Shorts script below, then click 'Create Run'.",
        font=("Arial", 12),
        pady=10,
    )
    label.pack()

    text_box = tk.Text(root, wrap="word", font=("Consolas", 11))
    text_box.pack(expand=True, fill="both", padx=12, pady=8)

    status_label = tk.Label(root, text="", font=("Arial", 10), fg="gray")
    status_label.pack(pady=(0, 10))

    def on_create_run():
        script_text = text_box.get("1.0", "end").strip()

        if not script_text:
            messagebox.showerror("Error", "Script is empty. Paste your script first.")
            return

        run_id = make_run_id()
        run_folder = RUNS_DIR / run_id

        try:
            out_path = write_script_json(run_folder, script_text, run_id)
        except FileExistsError:
            messagebox.showerror("Error", f"Run folder already exists: {run_folder}")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create run:\n{e}")
            return

        status_label.config(text=f"Created run: {run_folder}")
        messagebox.showinfo("Success", f"Run created!\n\nscript.json saved to:\n{out_path}")

        # Close the window after success
        root.destroy()

    button = tk.Button(
        root,
        text="Create Run",
        font=("Arial", 12),
        command=on_create_run,
        padx=20,
        pady=10,
    )
    button.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()
