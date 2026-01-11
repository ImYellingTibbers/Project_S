from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Shared intelligence lives at project root: Project_S_v1.0/core/...
from core.ideas.idea_fingerprint import canonicalize_idea, signature_hash
from core.ideas.embeddings import embed_text


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def jget(d: Dict[str, Any], path: List[str], default=None):
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def ensure_run_row(cur: sqlite3.Cursor, *, run_id: str, channel_key: str) -> int:
    # If exists, return id
    cur.execute("SELECT id FROM runs WHERE run_id = ?", (run_id,))
    row = cur.fetchone()
    if row:
        return int(row[0])

    created_at = utc_now()
    cur.execute(
        """
        INSERT INTO runs (run_id, channel_key, created_at, schema_versions, seed_id, constraints_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (run_id, channel_key, created_at, json.dumps({}), None, None),
    )
    return int(cur.lastrowid)


def insert_candidate_ideas(cur: sqlite3.Cursor, *, run_pk: int, ideas: List[Dict[str, Any]]):
    # Insert all candidates as non-winners (no embeddings stored for them)
    for idea_obj in ideas:
        idea_text = (idea_obj.get("idea") or "").strip()
        if not idea_text:
            continue
        cur.execute(
            """
            INSERT INTO ideas (
                run_id, idea_text, is_winner, score, score_reason,
                seed_theme, fear_axis, hook_type, pov, sensory_focus,
                idea_canonical, idea_embedding, idea_signature_hash
            )
            VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
            """,
            (
                run_pk,
                idea_text,
                idea_obj.get("score"),
                idea_obj.get("score_reason"),
                idea_obj.get("seed_theme"),
                idea_obj.get("fear_axis"),
                idea_obj.get("hook_type"),
                idea_obj.get("pov"),
                json.dumps(idea_obj.get("sensory_focus")) if idea_obj.get("sensory_focus") is not None else None,
            ),
        )


def promote_winner_and_fingerprint(
    cur: sqlite3.Cursor,
    *,
    run_pk: int,
    winner_text: str,
    seed_theme: Optional[str],
    fear_axis: Optional[str],
):
    # Find a candidate row for this run/idea text; if none exist, insert it.
    cur.execute(
        "SELECT id FROM ideas WHERE run_id = ? AND idea_text = ? ORDER BY id ASC LIMIT 1",
        (run_pk, winner_text),
    )
    row = cur.fetchone()
    if row:
        idea_row_id = int(row[0])
    else:
        cur.execute(
            "INSERT INTO ideas (run_id, idea_text, is_winner) VALUES (?, ?, 1)",
            (run_pk, winner_text),
        )
        idea_row_id = int(cur.lastrowid)

    canonical = canonicalize_idea(
        idea_text=winner_text,
        seed_theme=seed_theme,
        fear_axis=fear_axis,
        hook_type=None,
        pov="first_person",
        environment=None,
        mechanism=None,
    )
    sig = signature_hash({"canonical": canonical})
    emb = embed_text(canonical)

    cur.execute(
        """
        UPDATE ideas
        SET is_winner = 1,
            idea_canonical = ?,
            idea_embedding = ?,
            idea_signature_hash = ?
        WHERE id = ?
        """,
        (canonical, json.dumps(emb), sig, idea_row_id),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True, help="Run folder name under runs/, e.g. 20260105_155634")
    ap.add_argument("--channel-key", default=None, help="Channel key (default: channel folder name)")
    args = ap.parse_args()

    # This file: Project_S_v1.0/residual_fear/src/run_steps/ingest_run.py
    # parents[0]=run_steps, [1]=src, [2]=residual_fear, [3]=Project_S_v1.0
    channel_root = Path(__file__).resolve().parents[2]
    project_root = Path(__file__).resolve().parents[3]

    channel_key = args.channel_key or channel_root.name
    run_id = args.run_id
    run_dir = channel_root / "runs" / run_id

    db_path = project_root / "project_s.db"
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at: {db_path}")

    if not run_dir.exists():
        raise FileNotFoundError(f"Run dir not found: {run_dir}")

    # Required artifacts
    idea_gen_path = run_dir / "idea_generator.json"
    idea_sel_path = run_dir / "idea.json"

    if not idea_gen_path.exists():
        raise FileNotFoundError(f"Missing artifact: {idea_gen_path}")
    if not idea_sel_path.exists():
        raise FileNotFoundError(f"Missing artifact: {idea_sel_path}")

    idea_gen = load_json(idea_gen_path)
    idea_sel = load_json(idea_sel_path)

    candidates = jget(idea_gen, ["data", "ideas"], default=[])
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("idea_generator.json has no candidate ideas at data.ideas")

    winner_text = (jget(idea_sel, ["data", "winner", "idea"], default="") or "").strip()
    if not winner_text:
        raise RuntimeError("idea.json missing winner idea at data.winner.idea")

    # Pull seed fields (best-effort)
    seed_theme = jget(idea_gen, ["data", "seed", "definition", "theme"], default=None)
    fear_axis = jget(idea_gen, ["data", "seed", "definition", "fear_axis"], default=None)

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        run_pk = ensure_run_row(cur, run_id=run_id, channel_key=channel_key)

        insert_candidate_ideas(cur, run_pk=run_pk, ideas=candidates)

        promote_winner_and_fingerprint(
            cur,
            run_pk=run_pk,
            winner_text=winner_text,
            seed_theme=seed_theme,
            fear_axis=fear_axis,
        )

        conn.commit()
    finally:
        conn.close()

    print(f"[ingest] OK: run_id={run_id} channel={channel_key} -> {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
