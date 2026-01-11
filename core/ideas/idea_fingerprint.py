import hashlib
import json
from typing import Dict, List


def canonicalize_idea(
    *,
    idea_text: str,
    seed_theme: str | None,
    fear_axis: str | None,
    hook_type: str | None,
    pov: str | None,
    environment: str | None,
    mechanism: str | None,
) -> str:
    """
    Produce a normalized, low-variance description of the idea.
    This is NOT prose. It is semantic compression.
    """

    parts = [
        f"idea:{idea_text.strip().lower()}",
        f"environment:{environment or 'unknown'}",
        f"mechanism:{mechanism or 'unknown'}",
        f"seed_theme:{seed_theme or 'unknown'}",
        f"fear_axis:{fear_axis or 'unknown'}",
        f"hook:{hook_type or 'unknown'}",
        f"pov:{pov or 'unknown'}",
    ]

    return "; ".join(parts)


def signature_hash(structure: Dict) -> str:
    """
    Deterministic structural hash.
    Order-independent.
    """
    normalized = json.dumps(structure, sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
