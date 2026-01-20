"""
src/run_steps/image_prompt_generator.py

STAGE: IMAGE PROMPT GENERATOR (COMPILER)
---------------------------------------
Inputs:
  - runs/<run_id>/storyboard_4.json
  - runs/<run_id>/visual_canon.json

Output:
  - runs/<run_id>/image_prompts.json

Purpose:
  - Compile each scene_description into a final image prompt:
    scene text + injected canon + injected style.
  - No creative planning here; this is just compilation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from sys import path as sys_path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys_path:
    sys_path.insert(0, str(ROOT))

from src.run_steps._common_utils import utc_now_iso, read_json, write_json, find_latest_run_folder

SCHEMA_NAME = "image_prompts"
SCHEMA_VERSION = "2.0"


def compile_prompt(scene: Dict[str, Any], canon: Dict[str, Any]) -> Dict[str, str]:
    style = canon.get("style_canon", {}) or {}
    char_canon = canon.get("character_canon", {}) or {}
    loc_canon = canon.get("location_canon", {}) or {}
    prop_canon = canon.get("prop_canon", {}) or {}

    chars = scene.get("characters_present", []) or []
    locs = scene.get("location_ids", []) or []
    props = scene.get("prop_ids", []) or []
    scene_text = str(scene.get("scene_description", "")).strip()

    lines: List[str] = []

    gstyle = str(style.get("global_style_prompt", "")).strip()
    fmt = str(style.get("format", "")).strip()
    if gstyle:
        lines.append(f"GLOBAL STYLE: {gstyle}")
    if fmt:
        lines.append(f"FORMAT: {fmt}")

    if chars:
        lines.append("")
        lines.append("CHARACTER CANON:")
        for c in chars:
            desc = str(char_canon.get(c, "")).strip()
            if desc:
                lines.append(f"- {c}: {desc}")

    if locs:
        lines.append("")
        lines.append("LOCATION CANON:")
        for l in locs:
            desc = str(loc_canon.get(l, "")).strip()
            if desc:
                lines.append(f"- {l}: {desc}")

    if props:
        lines.append("")
        lines.append("PROP CANON:")
        for p in props:
            desc = str(prop_canon.get(p, "")).strip()
            if desc:
                lines.append(f"- {p}: {desc}")

    lines.append("")
    lines.append("SCENE:")
    lines.append(scene_text)

    return {
        "prompt_base": scene_text,
        "prompt_final": "\n".join(lines).strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, default=None)
    args = parser.parse_args()

    RUNS_DIR = ROOT / "runs"

    if args.run_id:
        run_folder = RUNS_DIR / args.run_id
    else:
        run_folder = find_latest_run_folder(RUNS_DIR)

    sb4 = read_json(run_folder / "storyboard_4.json")
    canon = read_json(run_folder / "visual_canon.json")

    scenes_out: List[Dict[str, Any]] = []

    for ch in sb4.get("chapters", []):
        for s in ch.get("scenes", []):
            compiled = compile_prompt(s, canon)
            scenes_out.append(
                {
                    "global_scene_index": s.get("global_scene_index"),
                    "chapter_index": s.get("chapter_index"),
                    "scene_in_chapter": s.get("scene_in_chapter"),
                    "scene_role": s.get("scene_role"),
                    "characters_present": s.get("characters_present", []),
                    "location_ids": s.get("location_ids", []),
                    "prop_ids": s.get("prop_ids", []),
                    "prompt_base": compiled["prompt_base"],
                    "prompt_final": compiled["prompt_final"],
                }
            )

    out: Dict[str, Any] = {
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        "run_id": args.run_id,
        "created_at": utc_now_iso(),
        "total_scenes": len(scenes_out),
        "scenes": scenes_out,
    }

    write_json(run_folder / "image_prompts.json", out)
    print(f"[SUCCESS] image_prompts.json saved | scenes={len(scenes_out)} | run={args.run_id}")


if __name__ == "__main__":
    main()
