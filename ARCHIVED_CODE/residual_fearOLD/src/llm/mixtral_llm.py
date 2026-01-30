import requests
import time
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "mixtral:8x7b"


def _log_llm_call(duration_s: float, status: int):
    base_dir = Path(__file__).resolve().parents[2]
    log_file = base_dir / "ollama_live.log"

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(
            f"[OLLAMA] {ts} | {status} | {duration_s:.3f}s | POST /api/generate ({MODEL})\n"
        )


def call_llm(prompt: str) -> str:
    start = time.time()
    r = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_gpu": -1,
                "num_thread": 1,
            },
        },
        timeout=900,
    )
    duration = time.time() - start

    _log_llm_call(duration, r.status_code)

    r.raise_for_status()
    data = r.json()

    if "response" not in data:
        raise RuntimeError(f"Bad Ollama response: {data}")

    return data["response"].strip()
