from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def get_script_text(script_json: Dict[str, Any]) -> str:
    # Supports flexible script.json shapes.
    for k in ("script", "text", "story", "content"):
        v = script_json.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

def extract_json_from_llm(raw: str) -> Dict[str, Any]:
    # Minimal JSON extraction (no heavy repairs by design).
    if not isinstance(raw, str):
        raise RuntimeError("LLM returned non-text response")
    s = raw.strip()

    # strip outer code fences
    if s.startswith("```"):
        # keep the middle section if present
        parts = s.split("```")
        if len(parts) >= 3:
            s = parts[1]
        else:
            s = s.strip("`")
        s = s.strip()

    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("LLM did not return a JSON object")

    return json.loads(s[start:end+1])


def find_latest_run_folder(runs_dir: Path) -> Path:
    if not runs_dir.exists():
        raise RuntimeError(f"Runs directory not found: {runs_dir}")

    runs = sorted([p for p in runs_dir.iterdir() if p.is_dir()])
    if not runs:
        raise RuntimeError("No run folders found")

    return runs[-1]

