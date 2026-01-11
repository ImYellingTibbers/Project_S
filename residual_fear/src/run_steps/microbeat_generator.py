import json
import re
import os
import random
from sys import path
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in path:
    path.insert(0, str(ROOT))

from src.config import RUNS_DIR, PROJECT_VERSION
from src.llm.qwen_instruct_llm import call_llm

# ---------------------------
# Utilities
# ---------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def find_latest_run_folder() -> Path:
    runs = sorted(p for p in RUNS_DIR.iterdir() if p.is_dir())
    if not runs:
        raise RuntimeError("No run folders found")
    return runs[-1]

def extract_json(text: str) -> dict:
    if not text or not text.strip():
        raise RuntimeError("LLM returned empty response")

    text = text.strip()

    # Strip markdown fences
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Force JSON start
    first_brace = text.find("{")
    if first_brace == -1:
        raise RuntimeError(f"LLM returned no JSON object:\n{text[:300]}")

    text = text[first_brace:]

    # ---- REPAIR STEP ----
    # Quote unquoted object keys:  foo: "bar"  →  "foo": "bar"
    text = re.sub(
        r'(?m)(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:',
        r'\1 "\2":',
        text
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Invalid JSON from LLM after repair:\n{text[:500]}"
        ) from e


CONCRETE_VISUAL_TERMS = [
    "door", "hallway", "wall", "window", "ceiling", "floor",
    "shadow", "light", "darkness", "corner", "threshold",
    "frame", "space", "room", "object", "opening", "surface"
]

BANNED_VISUAL_TERMS = [
    "whisper", "sound", "voice", "noise",
    "fear", "dread", "terror", "panic",
    "silence", "presence", "absence",
    "creeping", "encroaching", "closing in",
    "watching", "breathing", "laughing",
    "moving", "shifting", "crawling",
]

def sanitize_visual_adjustment(text: str) -> str:
    lowered = text.lower()
    for term in BANNED_VISUAL_TERMS:
        if term in lowered:
            return ""  # force fallback
    return text


FALLBACK_VISUALS = [
    "uneven wall texture visible under low light",
    "foreground darkened, background partially obscured",
    "hard shadows cast along architectural edges",
    "subtle haze near the ceiling and corners",
]

def ensure_concrete_visual(text: str) -> str:
    if not text:
        return random.choice(FALLBACK_VISUALS)

    lowered = text.lower()
    if not any(t in lowered for t in CONCRETE_VISUAL_TERMS):
        return random.choice(FALLBACK_VISUALS)

    return text


def enforce_microbeat_difference(prev, curr):
    changes = 0
    for key in ("camera_distance", "camera_angle", "distortion_level"):
        if prev.get(key) != curr.get(key):
            changes += 1
    return changes >= 2


# ---------------------------
# Prompt
# ---------------------------

MICROBEAT_PROMPT = """
You are a MICROBEAT PLANNER for short-form horror videos.

Your job is to decide whether a storyboard beat needs visual subdivision at all.
Microbeats are used ONLY when they add narrative emphasis.

--------------------------------
PRIMARY OBJECTIVE (CRITICAL)
--------------------------------
Fewer microbeats are better.

- If a single image could carry the beat, use the MINIMUM allowed microbeats
- Only create additional microbeats if they meaningfully increase tension
- Do NOT subdivide by default

--------------------------------
HARD LIMITS (NON-NEGOTIABLE)
--------------------------------
- Minimum microbeats per beat: 2
- Maximum microbeats per beat: 3
- If unsure, choose fewer

--------------------------------
ABSOLUTE RULES
--------------------------------
- Do NOT invent story events
- Do NOT invent new objects or locations
- Do NOT invent timing or durations
- Do NOT calculate start or end times
- Do NOT merge or drop storyboard beats
- Each microbeat MUST remain faithful to the parent beat’s:
  - location
  - implied threat
  - narrative purpose

- Microbeats may NOT introduce:
  - new locations
  - new story ideas
  - unrelated visual concepts

- Microbeats are refinements, not alternatives.

--------------------------------
WHEN TO ADD A MICROBEAT
--------------------------------
Add an extra microbeat ONLY if:
- The beat contains escalation, realization, or threat increase
- A visual change would help the viewer notice something important
- The moment benefits from closer attention or distortion

--------------------------------
VISUAL RULES
--------------------------------
Microbeats are visual variations only, not new actions.

Each microbeat must differ from the previous one in at least TWO of:
- camera_distance
- camera_angle
- distortion_level
- visual_focus (foreground vs background vs negative space vs obstruction)

PROHIBITED MICROBEAT PATTERNS:
- Same environment, same framing, minor angle changes only
- Repeating the same hallway, room, or corridor without introducing:
  - a new obstruction
  - a new depth layer
  - a new implied threat
  - a new spatial relationship

Each microbeat must reveal NEW visual information or tension.

- Environments and objects only
- No humans, faces, bodies, silhouettes, shadows, or reflections
- No real-world living beings
- Supernatural entities allowed, but must not resemble animals

--------------------------------
PACING CONTEXT (READ ONLY)
--------------------------------
You will be given a pacing zone:
- early  → allow at most 2 microbeats
- middle → allow at most 3 microbeats
- late   → prefer 2 heavier microbeats with increased distortion or obstruction

--------------------------------
OUTPUT (STRICT JSON)
--------------------------------
{
  "microbeats": [
    {
      "microbeat_id": number,
      "visual_adjustment": string,
      "camera_distance": "wide | medium | close",
      "camera_angle": "level | tilted | off-axis",
      "distortion_level": number,
      "attention_weight": "light | normal | heavy"
    }
  ]
}
- microbeat_id starts at 1
- Output JSON only
""".strip()


# ---------------------------
# Main
# ---------------------------

def main():
    load_dotenv()

    run_folder = find_latest_run_folder()

    storyboard = json.loads(
        (run_folder / "storyboard.json").read_text(encoding="utf-8")
    )

    all_microbeats = []
    had_beats = False

    for beat in storyboard["beats"]:
        timing = beat.get("timing_scope")
        if not timing:
            raise RuntimeError(f"Beat {beat['beat_id']} missing timing_scope")

        user_payload = {
            "beat_id": beat["beat_id"],
            "camera_bias": beat.get("camera_bias"),
            "timing_scope": timing,  # reference only
            "pacing": beat.get("pacing"),
            "framing": beat["framing"],
            "location": beat["location"],
            "visual_intent": beat["visual_intent"],
            "storyboard_description": beat["storyboard_description"],
        }



        prompt = (
            "You plan microbeats for short-form video pacing.\n\n"
            + MICROBEAT_PROMPT
            + "\n\nINPUT:\n"
            + json.dumps(user_payload, indent=2)
        )

        raw = call_llm(prompt)
        result = extract_json(raw)


        microbeats = result.get("microbeats")

        if not isinstance(microbeats, list) or not microbeats:
            raise RuntimeError(f"Invalid microbeats for beat {beat['beat_id']}")

        for mb in microbeats:
            raw = mb.get("visual_adjustment", "")
            clean = sanitize_visual_adjustment(raw)
            mb["visual_adjustment"] = ensure_concrete_visual(clean)
            
        # ---- Force obstruction in one microbeat per beat ----
        obstruction_terms = [
            "foreground partially obscured",
            "view partially blocked by architecture",
            "frame partially occluded by darkness",
        ]

        if microbeats:
            target = microbeats[-1]
            target["visual_adjustment"] = ensure_concrete_visual(
                random.choice(obstruction_terms)
            )

        # ---- HARD SAFETY CAPS ----
        MIN_MICROBEATS = 2
        MAX_MICROBEATS = 3

        # Enforce minimum microbeats (duplicate with subtle variation if needed)
        if len(microbeats) < MIN_MICROBEATS:
            base = dict(microbeats[0])

            VARIATIONS = [
                "shadows deepen along the edges of the frame",
                "light source appears weaker and lower in the scene",
                "foreground darkens, background recedes into haze",
                "contrast increases, obscuring fine details",
            ]

            v_idx = 0
            while len(microbeats) < MIN_MICROBEATS:
                microbeats.append({
                    **base,
                    "microbeat_id": len(microbeats) + 1,
                    "visual_adjustment": ensure_concrete_visual(
                        VARIATIONS[v_idx % len(VARIATIONS)]
                    ),
                })
                v_idx += 1


        # Enforce maximum microbeats
        if len(microbeats) > MAX_MICROBEATS:
            microbeats = microbeats[:MAX_MICROBEATS]

        # Ensure IDs are sequential after all adjustments
        for idx, mb in enumerate(microbeats, start=1):
            mb["microbeat_id"] = idx

        # ---- CAMERA + EARLY-BEAT DIVERGENCE ----
        bias = beat.get("camera_bias")
        pacing_zone = beat.get("pacing", {}).get("zone")

        for i, mb in enumerate(microbeats):
            if bias == "wide":
                mb["camera_distance"] = "wide"
            elif bias == "medium":
                mb["camera_distance"] = "medium"
            else:
                mb["camera_distance"] = "close"

            # Align framing with enforced camera distance
            mb["framing"] = mb["camera_distance"]

            if i > 0:
                mb["camera_angle"] = "off-axis"

                # ---- EARLY-BEAT DIVERSITY (CRITICAL) ----
                if pacing_zone == "early":
                    mb["visual_adjustment"] = ensure_concrete_visual(
                        mb["visual_adjustment"]
                        + ", different focal depth and altered light direction"
                    )

        # ---- ENFORCE MICROBEAT VISUAL DIFFERENCE (CRITICAL) ----
        for i in range(1, len(microbeats)):
            prev = microbeats[i - 1]
            curr = microbeats[i]

            if not enforce_microbeat_difference(prev, curr):
                # Force additional differentiation deterministically
                if curr.get("camera_distance") == prev.get("camera_distance"):
                    curr["camera_distance"] = (
                        "close" if prev["camera_distance"] != "close" else "wide"
                    )

                if curr.get("camera_angle") == prev.get("camera_angle"):
                    curr["camera_angle"] = (
                        "off-axis" if prev["camera_angle"] != "off-axis" else "tilted"
                    )

                if curr.get("distortion_level") == prev.get("distortion_level"):
                    curr["distortion_level"] = min(
                        5, (curr.get("distortion_level") or 1) + 1
                    )

        had_beats = True
        all_microbeats.append({
            "beat_id": beat["beat_id"],
            "timing_scope": timing,
            "pacing": beat.get("pacing"),
            "microbeats": microbeats,
        })

    out = {
        "schema": {
            "name": "microbeat_plan",
            "version": PROJECT_VERSION,
        },
        "run_id": storyboard["run_id"],
        "created_at": utc_now_iso(),
        "beats": all_microbeats if had_beats else [],
    }


    (run_folder / "microbeat_plan.json").write_text(
        json.dumps(out, indent=2),
        encoding="utf-8",
    )

    print("Wrote microbeat_plan.json")


if __name__ == "__main__":
    main()
