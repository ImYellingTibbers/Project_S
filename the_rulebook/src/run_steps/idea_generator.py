from __future__ import annotations

import os
import json
import random
from typing import List, Dict
from dotenv import load_dotenv
import requests

import sys
from pathlib import Path

# ============================================================
# Environment
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found in environment")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL = "meta-llama/llama-3.3-70b-instruct"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}


ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
sys.path.insert(0, str(ASSETS_DIR))

from rules_library import RULES_LIBRARY
from places_library import PLACES_LIBRARY

# ============================================================
# Core LLM Call
# ============================================================

def call_llm(messages: List[Dict], temperature: float, max_tokens: int) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"].get("content")

    if not content or not content.strip():
        raise RuntimeError("LLM returned empty content")

    return content.strip()

# ============================================================
# Step 1 — Select Place
# ============================================================

def select_place() -> Dict:
    """Randomly select a place from the places library."""
    return random.choice(PLACES_LIBRARY)

# ============================================================
# Step 2 — Select Rules
# ============================================================

def select_rules(place: Dict, count: int) -> List[Dict]:
    """
    Randomly select `count` rules from the place's compatible rule IDs.
    Returns the full rule objects in a randomized order.
    The order matters — it becomes the act sequence.
    """
    compatible_ids = place["compatible_rules"]

    # Build a lookup dict from the rules library
    rules_lookup = {rule["id"]: rule for rule in RULES_LIBRARY}

    # Filter to only rules that exist in the library and are compatible
    available_rules = [
        rules_lookup[rule_id]
        for rule_id in compatible_ids
        if rule_id in rules_lookup
    ]

    if len(available_rules) < count:
        raise RuntimeError(
            f"Place '{place['name']}' only has {len(available_rules)} compatible rules "
            f"but {count} were requested."
        )

    selected = random.sample(available_rules, count)

    # Shuffle to determine act order
    random.shuffle(selected)

    return selected

# ============================================================
# Step 3 — Assign Acts
# ============================================================

def assign_acts(rules: List[Dict]) -> List[Dict]:
    """
    Build the full act list for the story.

    Act 1  — Setup (no rule triggered)
    Acts 2 through N — One new rule triggered per act.
                       From act 5 onward, earlier rules may also be active.
    Final act — Resolution (no new rule, narrator reflects and escapes)

    Each act entry contains:
      - act_number
      - type: "setup" | "rule" | "resolution"
      - primary_rule: the new rule being triggered this act (None for setup/resolution)
      - active_rules: all rules established so far that may still be in play
    """
    acts = []
    established_rules = []

    # Act 1 — Setup
    acts.append({
        "act_number": 1,
        "type": "setup",
        "primary_rule": None,
        "active_rules": [],
    })

    # Rule acts
    for i, rule in enumerate(rules):
        act_number = i + 2  # acts start at 2

        # From act 5 onward (index 3+), pass all previously established rules
        # as potentially active — the script generator decides how to layer them
        if act_number >= 5:
            active = list(established_rules)  # copy of all rules so far
        else:
            active = []

        acts.append({
            "act_number": act_number,
            "type": "rule",
            "primary_rule": rule,
            "active_rules": active,
        })

        # Add this rule to established after building the act entry
        established_rules.append(rule)

    # Final act — Resolution
    acts.append({
        "act_number": len(rules) + 2,
        "type": "resolution",
        "primary_rule": None,
        "active_rules": list(established_rules),  # all rules established, narrator reflects
    })

    return acts

# ============================================================
# Step 4 — Generate Narrator Backstory
# ============================================================

def generate_narrator_backstory_raw(place: Dict) -> str:
    system = (
        "You are generating a narrator backstory for a first-person horror story.\n\n"
        "The narrator is an ordinary person who took a job out of financial desperation.\n"
        "The backstory must feel grounded, specific, and real — like something that could "
        "actually happen to someone.\n\n"
        "STRICT CONSTRAINTS:\n"
        "- The narrator must be a male adult (25-55 years old).\n"
        "- The financial situation must be specific and relatable (medical bills, eviction, "
        "divorce, job loss, supporting family, student debt).\n"
        "- The reason they took THIS specific job must make sense given their situation.\n"
        "- No prior horror experience. No special knowledge. Just a regular person.\n"
        "- The backstory must create sympathy — the listener should root for this person.\n"
        "- Do NOT use any of these names: John, Jane, Amanda, Sarah, Emily, Michael, "
        "David, Jessica, Ashley, Chris, Jennifer, Ryan, Tyler, Madison, "
        "or any other common placeholder name.\n"
        "- Choose a name that feels specific and real but is not on this list.\n\n"
        "OUTPUT FORMAT — respond with a JSON object only, no other text:\n"
        "{\n"
        "  \"first_name\": \"string\",\n"
        "  \"age\": integer,\n"
        "  \"financial_situation\": \"one specific sentence describing their situation\",\n"
        "  \"reason_for_job\": \"one specific sentence explaining why they took this job\",\n"
        "  \"one_personal_detail\": \"one small humanizing detail (hobby, family, habit)\"\n"
        "}"
    )

    user = (
        f"Generate a narrator backstory for someone who just took a job as "
        f"{place['role']} at {place['name']}.\n"
        "Make their financial desperation specific and believable.\n"
        "Output valid JSON only."
    )

    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.9,
        max_tokens=300,
    )


def judge_narrator_backstory(backstory: Dict, place: Dict) -> bool:
    system = (
        "You are a strict binary judge for narrator backstories in horror stories.\n\n"
        "Your job is to decide whether the backstory PASSES or FAILS.\n"
        "Do NOT suggest improvements. Do NOT explain reasoning.\n\n"
        "PASS ONLY IF ALL CONDITIONS ARE MET:\n"
        "- The narrator is an adult between 25 and 55 years old.\n"
        "- The financial situation is specific — not vague (e.g. 'needed money' FAILS, "
        "'behind on rent after being laid off from warehouse job' PASSES).\n"
        "- The reason for taking the job makes logical sense given their situation.\n"
        "- The personal detail is humanizing and specific — not generic.\n"
        "- The backstory would create sympathy in a listener.\n"
        "- No horror tropes, chosen ones, or special knowledge in the backstory.\n\n"
        "FAIL if any condition is violated.\n\n"
        "OUTPUT RULES:\n"
        "- Output ONLY one word: PASS or FAIL."
    )

    user = (
        f"Place: {place['name']}\n"
        f"Role: {place['role']}\n"
        f"Backstory:\n{json.dumps(backstory, indent=2)}"
    )

    verdict = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=5,
    )

    return verdict.strip().upper() == "PASS"


def generate_narrator_backstory(place: Dict, max_retries: int = 3) -> Dict:
    last_backstory = None

    for attempt in range(1, max_retries + 1):
        raw = generate_narrator_backstory_raw(place)

        # Strip markdown code fences if the model wraps in ```json
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        try:
            backstory = json.loads(cleaned)
        except json.JSONDecodeError:
            # Malformed JSON — retry
            continue

        last_backstory = backstory

        try:
            if judge_narrator_backstory(backstory, place):
                return backstory
        except Exception:
            pass

    # Fallback — return last parsed backstory even if it failed the judge
    if last_backstory:
        return last_backstory

    # Last resort — return a minimal valid backstory so the pipeline doesn't die
    return {
        "first_name": "Riley",
        "age": 34,
        "financial_situation": "Three months behind on rent after a sudden layoff.",
        "reason_for_job": "It was the only overnight position hiring that week.",
        "one_personal_detail": "Keeps a small photo of their dog in their wallet.",
    }

# ============================================================
# Step 5 — Assemble Story Frame
# ============================================================

def build_story_frame() -> Dict:
    """
    Master function. Assembles the complete story frame that will be
    passed to the script generator.

    Returns a structured object containing everything the script
    generator needs to write the full story.
    """

    # Randomly choose how many rules this story will use (8, 9, or 10)
    rule_count = random.randint(8, 10)

    # Select place
    place = select_place()

    # Select and order rules
    rules = select_rules(place, rule_count)

    # Build act structure
    acts = assign_acts(rules)

    # Generate narrator
    narrator = generate_narrator_backstory(place)

    # Assemble the frame
    story_frame = {
        "place": {
            "id": place["id"],
            "name": place["name"],
            "role": place["role"],
            "category": place["category"],
        },
        "narrator": narrator,
        "rule_count": rule_count,
        "act_count": len(acts),
        "rules_in_order": [
            {
                "id": rule["id"],
                "name": rule["name"],
                "template": rule["template"],
                "consequence_tone": rule["consequence_tone"],
                "story_moment": rule["story_moment"],
            }
            for rule in rules
        ],
        "acts": acts,
    }

    return story_frame


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    frame = build_story_frame()
    print(json.dumps(frame, indent=2))