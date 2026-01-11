import os
import json
import re
import random
from sys import path
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from core.ideas.idea_fingerprint import canonicalize_idea, signature_hash
from core.ideas.embeddings import embed_text
from core.ideas.cluster_filter import cluster_embeddings, should_reject_candidate

from dotenv import load_dotenv

from residual_fear.src.config import RUNS_DIR, SCHEMA_VERSION, IDEA_GENERATOR_LLM_MODEL
from residual_fear.src.llm.qwen_instruct_llm import call_llm
SEEDS_PATH = ROOT / "residual_fear" / "src" / "assets" / "idea_seeds.json"


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

IMMEDIATE_VIOLATION_MARKERS = [
    # body / personal space
    "on my bed",
    "in my room",
    "in my closet",
    "next to me",
    "inside my house",
    "outside my door",
    "under my bed",

    # concrete physical presence
    "appears",
    "keeps appearing",
    "shows up",
    "is always there",
    "won't leave",
    "moves closer",

    # daily repetition
    "every night",
    "every morning",
    "each day",
    "every time I",
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


def _validate_ideas_payload(model_json: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
    ideas = model_json.get("ideas")
    if not isinstance(ideas, list) or not ideas:
        return False, "Model JSON missing 'ideas' list", []

    warnings: List[str] = []
    valid_ideas: List[Dict[str, Any]] = []

    for i, item in enumerate(ideas):
        if not isinstance(item, dict):
            warnings.append(f"ideas[{i}] is not an object")
            continue

        idea_text = item.get("idea", "")
        if not isinstance(idea_text, str) or not idea_text.strip():
            warnings.append(f"ideas[{i}] missing or empty idea")
            continue

        hits = _find_banned_hits(idea_text)
        if hits:
            warnings.append(
                f"ideas[{i}] dropped due to banned terms {hits}: '{idea_text}'"
            )
            continue
        
        visual_hits = [
            m for m in IMMEDIATE_VIOLATION_MARKERS
            if m in idea_text.lower()
        ]
        item["visual_violation_score"] = len(visual_hits)

        if _mentions_female_protagonist(idea_text):
            warnings.append(
                f"ideas[{i}] dropped due to female protagonist: '{idea_text}'"
            )
            continue

        if re.search(r"\b(has been|keeps|won't stop|every night|for weeks)\b", idea_text.lower()):
            item["ongoing_bonus"] = True

        valid_ideas.append(item)

    model_json["ideas"] = sorted(
        valid_ideas,
        key=lambda x: x.get("visual_violation_score", 0),
        reverse=True
    )

    if len(valid_ideas) < 3:
        return False, f"Only {len(valid_ideas)} valid ideas after filtering", warnings

    return True, "ok", warnings


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
    return f"""
CORE MECHANISM (MUST BE PRESENT):
{seed.get("mechanism")}

ESCALATION REQUIREMENT (MUST BE IMPLIED):
{seed.get("escalation")}

CONSEQUENCE IF IGNORED (MUST BE CLEAR):
{seed.get("consequence")}

SUPERNATURAL CONTEXT (ALLOWED, NOT EXPLAINED):
{seed.get("supernatural_allowance")}
""".strip()




PROMPT = """
You are generating ideas for an automated YouTube horror shorts pipeline.

Each idea MUST describe a situation that becomes more dangerous or irreversible if ignored.
Safe or purely atmospheric anomalies are not acceptable.

IDEAS SHOULD:
- Begin with something already wrong
- Imply that the narrator has already failed to stop the situation
- Imply escalation over time
- Make it clear that continuing the situation will cause harm, loss, or permanent change
- Make it clear WHY the narrator can no longer stay silent about it
- Imply that not telling anyone makes the situation worse
- Each idea must include an implicit consequence for silence (If the narrator does nothing, something bad continues or worsens.)

IDEAS SHOULD NOT:
- Be easily ignored without consequence
- Be resolved by simply leaving or waiting
- Exist only as a strange but harmless occurrence

All ideas must be easy to visualize as a short sequence of AI-generated images.
Prefer single locations, few characters, and simple physical evidence of something being wrong.
Avoid crowds, complex action, abstract metaphors, or rapid scene changes.

IDEA CONSTRAINTS (NON-NEGOTIABLE):

{IDEA_SEED_TEXT}

IMPORTANT:
- Do NOT mention filming, cameras, actors, budgets, or production cost.
- Keep everything monetization-safe: implied horror only, no graphic gore, no sexual violence, no hate or harassment.
- Supernatural explanations are allowed, but must remain implied or observed only.
- Do NOT name demons, monsters, or lore explicitly.
- Do NOT use mirrors or reflections as a plot device.
- All ideas must feature a male main character.
- Do NOT use women as the primary subject of the story.

TASK:
Generate 6–8 horror YouTube Shorts ideas.

RULES:
- Each idea must be 1–2 sentences.
- Each idea must clearly imply escalation or consequence.
- Avoid comedy.
- Avoid readable text as a plot device.
- Avoid relying on identical images or repeated static comparisons.
- Return ONLY valid JSON. Do not include commentary, markdown, or explanations.
- Return ONLY valid JSON in this exact format:

{{
  "ideas": [
    {{"id": 1, "idea": "..."}}
  ]
}}
"""

def _mentions_female_protagonist(text: str) -> bool:
    """
    Reject ONLY if the primary narrator / subject is female.
    Allow female secondary characters (wife, daughter, mother, etc).
    """
    t = text.lower()

    # Hard reject if first-person female narrator
    if re.search(r"\b(i am|i'm)\s+(a\s+)?(woman|girl|mother|wife)\b", t):
        return True

    # Hard reject if third-person female is the main subject
    female_subject_patterns = [
        r"^a\s+(woman|girl)\b",
        r"^the\s+(woman|girl)\b",
    ]

    return any(re.search(p, t) for p in female_subject_patterns)


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

    raw = ""
    model_json: Dict[str, Any] = {}
    accumulated_ideas: List[Dict[str, Any]] = []
    seen_canonicals: set[str] = set()

    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = (
            "You are a precise and structured horror content ideation assistant.\n\n"
            + PROMPT.format(IDEA_SEED_TEXT=seed_prompt_text)
        )

        raw = call_llm(prompt)
        try:
            model_json = json.loads(raw)
        except json.JSONDecodeError:
            # retry
            print(f"[idea_generator] Attempt {attempt}/{MAX_ATTEMPTS} failed: invalid JSON.")
            continue

        ok, reason, warnings = _validate_ideas_payload(model_json)
        for w in warnings:
            print(f"[idea_generator][warning] {w}")
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

                sig = signature_hash(canonical)

                # Hard reject: exact duplicate
                if sig in past_hashes:
                    continue

                emb = embed_text(idea_text)

                # Cluster-aware reject
                if should_reject_candidate(
                    emb,
                    past_embeddings,
                    cluster_labels,
                ):
                    continue

                canonical_key = canonical

                if canonical_key in seen_canonicals:
                    continue

                seen_canonicals.add(canonical_key)
                accumulated_ideas.append(idea_obj)


            if len(accumulated_ideas) < 6 and attempt < MAX_ATTEMPTS:
                print(
                    f"[idea_generator] Accumulated {len(accumulated_ideas)} ideas (<6). Continuing accumulation."
                )
                continue

            model_json["ideas"] = accumulated_ideas[:8]
            break


        print(f"[idea_generator] Attempt {attempt}/{MAX_ATTEMPTS} rejected: {reason}")

        # Add a small correction nudge next attempt (keep it simple, avoid changing format)
        # We do this by appending guidance into PROMPT for the next try without restructuring flow.
        # (We keep PROMPT constant above; instead we rely on repeated attempts with the same constraints.)
        if attempt == MAX_ATTEMPTS and len(accumulated_ideas) < 6:
            raise RuntimeError(
                f"Failed to generate valid ideas after {MAX_ATTEMPTS} attempts. "
                f"Only {len(accumulated_ideas)} accumulated."
            )

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
