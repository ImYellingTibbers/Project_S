import os
import json
import re
import random
from sys import path
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
import sqlite3

from core.ideas.idea_fingerprint import canonicalize_idea, signature_hash
from core.ideas.embeddings import embed_text
from core.ideas.cluster_filter import cluster_embeddings, should_reject_candidate

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, SCHEMA_VERSION, IDEA_GENERATOR_LLM_MODEL
SEEDS_PATH = ROOT / "src" / "assets" / "idea_seeds.json"


# ----------------------------
# Config (keep dumb)
# ----------------------------
CHANNEL_ID = "horror_shorts"
SCHEMA_NAME = "idea_generator"

MAX_ATTEMPTS = 4


# ----------------------------
# Banned content (idea + script enforcement lives upstream)
# ----------------------------
# Hard-banned: reliably causes image generation brittleness or unwanted content patterns.
BANNED_TERMS = [
    # Mirrors/reflections (per your direction: cut mirrors entirely)
    "mirror",
    "mirrors",
    "reflection",
    "reflections",
    "reflective",
    "looking glass",
    "in the mirror",
    "through the mirror",
    "mirror wall",
    "mirrored",

    # Readable text as plot device (causes unreadable-text failure modes)
    "the note said",
    "the letter said",
    "the sign said",
    "it said",
    "written on",
    "read the note",
    "read the letter",
    "read the sign",
    "text message",
    "sms",
    "email",
    "headline",
    "newspaper",
    "license plate",
    "street sign",

    # Identity traps that break consistency / create uncanny faces
    "doppelganger",
    "doppelgänger",
    "twin",
    "twins",
    "identical face",
    "exact same face",
    "portrait",

    # Crowd / many faces requirements
    "crowd",
    "audience",
    "packed room",
    "dozens of people",
    "faces in the window",
    "people staring",

    # Real brands / celebs / place names (already in prompt, but enforce anyway)
    "facebook",
    "instagram",
    "tiktok",
    "google",
    "apple",
    "mcdonald",
    "walmart",
    "coca-cola",
    "starbucks",
    "new york",
    "los angeles",
    "london",

    # Graphic gore / monetization landmines (belt + suspenders)
    "dismember",
    "dismembered",
    "exposed organs",
    "guts",
    "blood spray",
    "torture",
    "sexual assault",
]

# Optional: normalize common variants before matching
NORMALIZE_REPLACEMENTS = [
    ("\u2019", "'"),  # curly apostrophe
    ("\u201c", '"'),
    ("\u201d", '"'),
]


def _normalize_text(s: str) -> str:
    t = s or ""
    for a, b in NORMALIZE_REPLACEMENTS:
        t = t.replace(a, b)
    return t


def _find_banned_hits(text: str) -> List[str]:
    t = _normalize_text(text).lower()

    hits: List[str] = []
    for term in BANNED_TERMS:
        term_l = term.lower()

        # For single-word bans like "mirror", match on word boundaries.
        # For phrases like "in the mirror", do substring match.
        if " " in term_l:
            if term_l in t:
                hits.append(term)
        else:
            if re.search(rf"\b{re.escape(term_l)}\b", t):
                hits.append(term)

    return hits


def _validate_ideas_payload(model_json: Dict[str, Any]) -> Tuple[bool, str]:
    ideas = model_json.get("ideas")
    if not isinstance(ideas, list) or not ideas:
        return False, "Model JSON missing 'ideas' list"

    if not (6 <= len(ideas) <= 8):
        return False, f"Expected 6–8 ideas, got {len(ideas)}"

    for i, item in enumerate(ideas):
        if not isinstance(item, dict):
            return False, f"ideas[{i}] is not an object"
        if "idea" not in item or not isinstance(item["idea"], str) or not item["idea"].strip():
            return False, f"ideas[{i}].idea missing or empty"
        # Hard-ban enforcement
        hits = _find_banned_hits(item["idea"])
        if hits:
            return False, f"ideas[{i}] contains banned term(s): {hits} | idea='{item['idea']}'"
        
        if _mentions_female_protagonist(item["idea"]):
            return False, f"ideas[{i}] features a female protagonist, which is not allowed"


    return True, "ok"


def load_idea_seeds() -> Dict[str, Any]:
    if not SEEDS_PATH.exists():
        raise RuntimeError(f"Idea seeds file not found: {SEEDS_PATH}")
    with open(SEEDS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def choose_random_seed(seeds_json: Dict[str, Any]) -> Dict[str, Any]:
    seeds = seeds_json.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise RuntimeError("No seeds found in idea_seeds.json")
    return random.choice(seeds)


def seed_to_prompt_text(seed: Dict[str, Any]) -> str:
    lines = []
    for k, v in seed.items():
        if k == "id":
            continue
        if isinstance(v, list):
            lines.append(f"- {k.replace('_', ' ').capitalize()}: {', '.join(v)}")
        else:
            lines.append(f"- {k.replace('_', ' ').capitalize()}: {v}")
    return "\n".join(lines)



PROMPT = """
You are generating ideas for an automated youtube horror shorts pipeline.

All ideas must be easy to visualize as a short sequence of AI-generated images.
Prefer single locations, few characters, clear physical anomalies, and visually repeatable elements.
Avoid ideas that rely on crowds, complex action, abstract metaphors, or rapid scene changes.

IDEA SEED (IMPORTANT CONTEXT):

{IDEA_SEED_TEXT}

This seed is not a story. It defines the creative lane all ideas must fit within.

IMPORTANT:
- Do NOT mention filming, cameras, actors, budgets, or production cost.
- Keep everything monetization-safe: implied horror, no graphic gore, no self-harm, no sexual violence, no hate/harassment, no real brands/celebrities, no real place names.
- Do NOT use mirrors or reflections as a plot device. Do not mention mirrors, reflections, or reflective surfaces.
- All ideas must feature a male main character (the narrator is male).
- Do NOT use women as the primary subject of the story.

TASK:
Generate 6–8 horror youtube short ideas.

RULES:
- Each idea must be 1–2 sentences.
- Make them unsettling and easy to understand quickly.
- Avoid comedy and excessive gore.
- Avoid making readable text (notes, letters, signs, screens) central to the idea.
- Avoid making consistent images/settings (photos/pictures of the same person over and over, portraits, paintings, furniture/objects moving/slightly changing) central to the idea.
- Avoid using specific shadow references, shadows shifting or moving is fine, character outlines of shadows and similar is prohibited
- Allow for supernatural or unexplainable scenarios
Return ONLY valid JSON in this exact format:
{{
  "ideas": [
    {{"id": 1, "idea": "..."}}
  ]
}}
"""

def _mentions_female_protagonist(text: str) -> bool:
    t = text.lower()
    female_terms = [
        "a woman", "the woman", "she ", " her ", "herself",
        "girl", "mother", "daughter", "wife", "girlfriend"
    ]
    return any(term in t for term in female_terms)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_past_winning_ideas(db_path: Path) -> List[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT idea_canonical, idea_embedding, idea_signature_hash
        FROM ideas
        WHERE is_winner = 1
          AND idea_embedding IS NOT NULL
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "canonical": r["idea_canonical"],
            "embedding": json.loads(r["idea_embedding"])
            if isinstance(r["idea_embedding"], str)
            else r["idea_embedding"],
            "hash": r["idea_signature_hash"],
        }
        for r in rows
    ]


def build_run_id(channel_id: str) -> str:
    # e.g. 20251229_141233__horror_shorts
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}__{channel_id}"


def main() -> int:
    load_dotenv()
    seeds_json = load_idea_seeds()
    chosen_seed = choose_random_seed(seeds_json)
    seed_prompt_text = seed_to_prompt_text(chosen_seed)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found in .env")

    client = OpenAI(api_key=api_key)

    raw = ""
    model_json: Dict[str, Any] = {}

    for attempt in range(1, MAX_ATTEMPTS + 1):
        resp = client.chat.completions.create(
            model=IDEA_GENERATOR_LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise and structured horror content ideation assistant."},
                {"role": "user", "content": PROMPT.format(IDEA_SEED_TEXT=seed_prompt_text)},
            ],
        )

        raw = resp.choices[0].message.content or ""
        try:
            model_json = json.loads(raw)
        except json.JSONDecodeError:
            # retry
            print(f"[idea_generator] Attempt {attempt}/{MAX_ATTEMPTS} failed: invalid JSON.")
            continue

        ok, reason = _validate_ideas_payload(model_json)
        if ok:
            # ---- DB-based idea filtering (read-only) ----
            DB_PATH = Path(__file__).resolve().parents[3] / "project_s.db"
            past_winners = load_past_winning_ideas(DB_PATH)

            past_embeddings = [w["embedding"] for w in past_winners]
            past_hashes = {w["hash"] for w in past_winners}
            cluster_labels = (
                cluster_embeddings(past_embeddings)
                if past_embeddings
                else []
            )

            filtered = []

            for idea_obj in model_json.get("ideas", []):
                idea_text = idea_obj["idea"]

                canonical = canonicalize_idea(
                    idea_text=idea_text,
                    seed_theme=chosen_seed.get("theme"),
                    fear_axis=chosen_seed.get("fear_axis"),
                    hook_type=None,
                    pov="first_person",
                    environment=None,
                    mechanism=None,
                )

                sig = signature_hash({"canonical": canonical})

                # Hard reject: exact duplicate
                if sig in past_hashes:
                    continue

                emb = embed_text(canonical)

                # Cluster-aware reject
                if should_reject_candidate(
                    emb,
                    past_embeddings,
                    cluster_labels,
                ):
                    continue

                filtered.append(idea_obj)

            if len(filtered) < 6:
                print(f"[idea_generator] Filter left {len(filtered)} ideas (<6). Retrying generation.")
                continue

            model_json["ideas"] = filtered[:8]
            break


        print(f"[idea_generator] Attempt {attempt}/{MAX_ATTEMPTS} rejected: {reason}")

        # Add a small correction nudge next attempt (keep it simple, avoid changing format)
        # We do this by appending guidance into PROMPT for the next try without restructuring flow.
        # (We keep PROMPT constant above; instead we rely on repeated attempts with the same constraints.)
        if attempt == MAX_ATTEMPTS:
            raise RuntimeError(f"Failed to generate valid ideas after {MAX_ATTEMPTS} attempts. Last reason: {reason}")

    out = {
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        "channel_id": CHANNEL_ID,
        "run_id": build_run_id(CHANNEL_ID),
        "created_at": utc_now_iso(),
        "data": {
            "seed": {
                "id": chosen_seed.get("id"),
                "definition": chosen_seed
            },
            "constraints": {
                "avoid_excess_gore": True,
                "avoid_self_harm": True,
                "avoid_sexual_violence": True,
                "keep_it_monetization_safe": True,
                "ban_mirrors_reflections": True,
                "avoid_readable_text_plot_device": True,
                "avoid_consistent_image_plot_device": True
            },
            "ideas": model_json.get("ideas", [])
        },
    }

    # Per-run folder
    run_folder = RUNS_DIR / out["run_id"].split("__")[0]  # timestamp only
    run_folder.mkdir(parents=True, exist_ok=True)

    output_path = run_folder / "idea_generator.json"
    output_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"Wrote: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
