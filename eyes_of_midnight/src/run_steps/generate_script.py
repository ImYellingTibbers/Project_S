from __future__ import annotations

import os
import json
from typing import Dict, List
from dotenv import load_dotenv
import requests
import re

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
sys.path.insert(0, str(ASSETS_DIR))

from reference_scripts import get_random_reference_block
from story_arcs import get_random_story_arc

from idea_generator import generate_best_horror_idea

# ============================================================
# Environment
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found in environment")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemma-3-27b-it"

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

# ============================================================
# Core LLM Call
# ============================================================

def call_llm(
    messages: List[Dict],
    temperature: float = 0.6,
    max_tokens: int = 2048,
    require_json: bool = False,
) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if require_json:
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(
        OPENROUTER_URL,
        headers=HEADERS,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"].get("content")

    if content is None:
        raise RuntimeError("LLM returned no content (null message)")

    content = content.strip()
    if not content:
        raise RuntimeError("LLM returned empty content")

    return content

# ============================================================
# Step 1: Concept + Hook
# ============================================================

def generate_long_form_hook(idea: str) -> str:
    system = (
        "You are writing the opening paragraph of a realistic first-person horror story.\n\n"
        "This is NOT a teaser, summary, or reflection.\n"
        "This is how the narrator actually starts telling the story.\n\n"
        "HOOK REQUIREMENTS:\n"
        "- First person\n"
        "- Sounds like someone explaining how something started\n"
        "- Natural, conversational, understated\n"
        "- 2–4 sentences\n"
        "- ~25–35 words\n\n"
        "CONTENT RULES:\n"
        "- Begin in a specific moment, situation, or routine\n"
        "- Include ONE concrete action the narrator took that mattered\n"
        "- The narrator does NOT yet understand the full danger\n"
        "- Unease should be present but not named\n\n"
        "STYLE CONSTRAINTS:\n"
        "- No dramatic framing or moral lessons\n"
        "- No explicit hindsight language like 'I should have known' or 'looking back'\n"
        "- No abstract metaphors\n"
        "- No supernatural elements\n\n"
        "This hook must feel like the first paragraph of a true account someone is about to explain."
    )

    user = (
        f"Core horror idea:\n{idea}\n\n"
        "Write the opening paragraph of the story.\n"
        "Do not summarize the story.\n"
        "Do not explain consequences.\n"
        "Do not reference future events.\n"
        "Do not use proper nouns.\n"
        "Output ONLY the paragraph text."
    )

    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.5,
        max_tokens=120,
    )


def generate_concept_and_hook() -> Dict[str, str]:
    idea = generate_best_horror_idea()
    arc = get_random_story_arc()
    hook = generate_long_form_hook(idea)

    system = (
        "You are expanding a realistic first-person horror idea into a full story concept.\n"
        "You must output STRICT JSON ONLY.\n"
        "No commentary. No markdown. No extra text."
    )

    user = (
        f"Core horror idea:\n{idea}\n\n"
        f"Established hook:\n{hook}\n\n"
        "Expand this into a long-form horror story concept suitable for a 10–15 minute narration.\n\n"
        "Requirements:\n"
        "- First-person adult narrator\n"
        "- Realistic modern context\n"
        "- No supernatural elements\n"
        "- No proper nouns (no full names, no exact street names, no brand names)\n"
        "- Use roles/descriptors only (e.g., 'a coworker', 'my landlord')\n"
        "- The idea must remain recognizable and central\n"
        "- Do NOT rewrite or replace the hook\n\n"
        "Output EXACTLY this JSON schema:\n"
        "{\n"
        '  "title": "...",\n'
        '  "core_anomaly": "...",\n'
        '  "setting": "..."\n'
        "}\n"
    )

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.5,
        max_tokens=400,
        require_json=True,
    )

    data = json.loads(raw)

    return {
        "TITLE": data["title"].strip(),
        "HOOK": hook.strip(),
        "CORE ANOMALY": data["core_anomaly"].strip(),
        "SETTING": data["setting"].strip(),
        "ARC": arc,
    }

# ============================================================
# Step 2: Act Structure
# ============================================================

def generate_act_outline(concept: Dict[str, str]) -> List[Dict[str, str]]:
    idea = concept["CORE ANOMALY"]
    reference_block = get_random_reference_block()

    system = (
        "You are outlining a long-form horror narrative.\n\n"
        "Below are COMPLETE example narrations provided ONLY to show:\n"
        "- overall length expectations\n"
        "- escalation pacing\n"
        "- act balance\n\n"
        "DO NOT reuse plot elements, scenes, phrasing, or character details.\n"
        "DO NOT imitate sentence structure or wording.\n"
        "Use them ONLY as structural references.\n\n"
        f"{reference_block}\n\n"
        "The story MUST follow this narrative progression:\n\n"
        "This story is based on the following real-world horror idea and must not introduce new anomalies:\n"
        f"{idea}\n\n"
        "1. Signal: an anomaly appears with no immediate cost\n"
        "2. Pattern: repetition and specificity emerge\n"
        "3. Personalization: the anomaly targets the narrator personally\n"
        "4. Mistake: the narrator takes a logical action that worsens the situation\n"
        "5. Binding: the narrator is left in a permanent, unresolved state\n\n"
        "Do NOT collapse, merge, or skip phases.\n"
        "Each act must escalate tension and reveal new implications.\n"
        "Pacing must support spoken narration."
    )

    user = (
        "Create a 5-act structure for a 10–15 minute spoken horror story.\n"
        "Each act MUST include a target word count.\n\n"
        "Acts:\n"
        "- Act 1: ~180-220 words (hook + anomaly introduction)\n"
        "- Act 2: ~200-240 words (escalation + pattern recognition)\n"
        "- Act 3: ~220-260 words (personal cost + discovery)\n"
        "- Act 4: ~220-260 words (mistake + confrontation)\n"
        "- Act 5: ~180-220 words (aftermath + unresolved dread)\n\n"
        "Each act should include:\n"
        "- ACT NAME\n"
        "- TARGET WORD COUNT\n"
        "- PURPOSE\n"
        "- KEY EVENTS\n\n"
        "STRICT OUTLINE CONSTRAINTS:\n"
        "- For EACH act:\n"
        "  - PURPOSE must be ONE sentence, max 25 words\n"
        "  - KEY EVENTS must be 3–5 bullet points\n"
        "- Each bullet point must be ONE short sentence (max 20 words)\n"
        "- Do NOT add sub-bullets, examples, or elaboration\n"
        "- Do NOT include themes, commentary, or tone notes outside the acts\n"
        "- You MUST output all five acts in order: Act 1 through Act 5\n"
        "Do not write prose. Outline only."
    )

    text = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.5,
        max_tokens=800,
    )

    act_pattern = re.compile(r"\bACT\s+([1-5])\b", re.IGNORECASE)

    acts_by_number: Dict[int, Dict[str, str]] = {}
    current_act_num = None
    current_block: List[str] = []

    for line in text.splitlines():
        match = act_pattern.search(line)
        if match:
            # flush previous act
            if current_act_num is not None:
                acts_by_number[current_act_num] = {
                    "ACT": f"ACT {current_act_num}",
                    "RAW": "\n".join(current_block).strip()
                }
                current_block = []

            current_act_num = int(match.group(1))
        elif current_act_num is not None:
            current_block.append(line)

    # flush final act
    if current_act_num is not None and current_block:
        acts_by_number[current_act_num] = {
            "ACT": f"ACT {current_act_num}",
            "RAW": "\n".join(current_block).strip()
        }

    # Validate completeness
    missing = [n for n in range(1, 6) if n not in acts_by_number]
    if missing:
        raise RuntimeError(
            f"Act outline parsing failed. Missing acts: {missing}\n"
            f"Raw outline text:\n{text}"
        )

    # Convert to ordered list
    acts = [acts_by_number[n] for n in range(1, 6)]

    return acts

# ============================================================
# Step 3: Write Each Act
# ============================================================

def write_act(act: Dict[str, str], context: str, concept: Dict[str, str], act_number: int) -> str:
    system = (
        "You are writing immersive horror prose for spoken narration.\n"
        "Language must be natural, restrained, and emotionally believable.\n"
        "Avoid explaining the horror. Show consequences instead.\n\n"
        "Each act MUST reflect its emotional phase:\n"
        "- Act 1: mild unease, rationalization, subtle discomfort\n"
        "- Act 2: anxiety, vigilance, pattern awareness\n"
        "- Act 3: isolation, sleep disruption, emotional cost\n"
        "- Act 4: panic, urgency, loss of composure\n"
        "- Act 5: exhaustion, resignation, unresolved dread\n\n"
        "IMPORTANT CLARIFICATION:\n"
        "- Physical danger MAY occur before Act 4 if it is contained, interrupted, or escaped\n"
        "- Containment examples: locked doors, distance, witnesses, speed, police arrival\n"
        "- Danger is NOT resolution if the threat remains unidentified or unresolved\n\n"
        "Do NOT reuse events, locations, situations, or phrasing from any prior examples."
    )

    user = (
        f"Context so far:\n{context}\n\n"
        f"Core idea that must remain central:\n{concept['CORE ANOMALY']}\n\n"
        f"Write the following act as prose:\n"
        f"{json.dumps(act, indent=2)}\n\n"
        "CRITICAL CONSTRAINTS:\n"
        "- Write CLOSE to the target word count specified above\n"
        "- Do NOT underwrite\n"
        "- Do NOT restate the core anomaly; only show its effects\n"
        "- Natural pacing, spoken narration\n"
        "- First person\n"
        "- No proper nouns (no full names, no exact addresses, no brand names)\n"
        "- Keep antagonist deniable: no explicit admissions like 'I was watching you'\n"
        "- Implicit intent is allowed if inferred through actions, timing, or proximity\n"
        "- No exposition dumps\n"
        "- No moralizing\n"
        "- End the act with unease, not resolution\n\n"
        "- At least once, the narrator consciously chooses not to tell someone or not to say something aloud\n"
        f"ACT-SCOPE HARD RULES:\n"
        f"- Follow ONLY the scope rules for Act {act_number}.\n"
        f"- Do NOT introduce events reserved for later acts.\n"
        f"- Do NOT resolve or climax early.\n\n"
    )

    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=1500,
    )
    
    
def _arc_key(arc: Dict[str, str], act_number: int, suffix: str) -> str:
    return arc[f"act_{act_number}_{suffix}"]
    
def judge_act_scope(act_text: str, arc: Dict[str, str], act_number: int) -> bool:
    system = (
        "You are a strict scope judge for a horror story act.\n\n"
        "Your job is to decide whether the act STAYS WITHIN ITS ASSIGNED ARC PHASE.\n"
        "Do NOT judge quality, prose, tone, or scariness.\n\n"
        f"This is ACT {act_number}.\n\n"
        "PASS ONLY IF:\n"
        "- The act follows the ARC RULES provided\n"
        "- The act does NOT resolve, climax, or escalate beyond its phase\n"
        "- The act does NOT introduce events meant for later acts\n\n"
        "- Expressions of internal discomfort, anxiety, or unease are allowed if no external escalation occurs\n"
        "FAIL IF:\n"
        "- The act includes confrontation intended to resolve or expose the antagonist\n"
        "- The act includes accusation that forces explanation or admission\n"
        "- The act introduces irreversible consequences meant for later acts\n"
        "- The antagonist explicitly admits intent, motive, or surveillance\n"
        "- The act resolves uncertainty rather than deepening it\n\n"
        "OUTPUT RULES:\n"
        "- Output ONLY one word: PASS or FAIL."
    )

    act_rules = _arc_key(arc, act_number, "rules")
    act_focus = _arc_key(arc, act_number, "focus")

    user = (
        f"ARC RULES:\n{act_rules}\n\n"
        f"ARC FOCUS:\n{act_focus}\n\n"
        "EXTRA SCOPE GUARDS:\n"
        "- No explicit admissions by the antagonist unless explicitly allowed by this act.\n"
        + ( "- No confrontation or accusation in Act 1.\n" if act_number == 1 else "" ) +
        "\n"
        f"ACT TEXT:\n{act_text}"
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

# ============================================================
# Main Orchestration
# ============================================================

def generate_full_story() -> str:
    concept = generate_concept_and_hook()
    acts = generate_act_outline(concept)

    full_script = f"{concept['HOOK']}\n\n"
    
    # ============================================================
    # ACT 1
    # ============================================================

    act_1 = acts[0]
    arc = concept["ARC"]

    act_1_context = (
        f"{concept['HOOK']}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 1 RULES: {arc['act_1_rules']}\n"
        f"ACT 1 FOCUS: {arc['act_1_focus']}\n\n"
        "ACT 1 MANDATE:\n"
        "- Introduce an event or behavior that is IMMEDIATELY wrong or unsafe.\n"
        "- The narrator recognizes danger in the moment.\n"
        "- This is not subtle, symbolic, or 'almost-right'. It is socially or physically invalid.\n\n"
        "ACT 1 REQUIRED ELEMENTS:\n"
        "- One concrete action by another person that forces a physical or instinctive response.\n"
        "- The narrator reacts by freezing, fleeing, locking, watching, or leaving.\n\n"
        "ACT 1 CONSTRAINTS:\n"
        "- Do NOT explain motives.\n"
        "- Do NOT resolve the situation.\n"
        "- The narrator may escape, interrupt, or evade — but the threat remains active.\n\n"
        "ACT 1 END STATE:\n"
        "- The narrator knows something is wrong and cannot unsee it.\n"
    )

    act_1_text = None

    for _ in range(3):
        candidate = write_act(act_1, act_1_context, concept, act_number=1)
        if judge_act_scope(candidate, arc, act_number=1):
            act_1_text = candidate
            break

    if act_1_text is None:
        act_1_text = candidate  # fallback, never hard-fail

    full_script += "\n\n" + act_1_text
    
    # ============================================================
    # ACT 2
    # ============================================================

    act_2 = acts[1]

    act_2_context = (
        f"{full_script}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 2 RULES: {arc['act_2_rules']}\n"
        f"ACT 2 FOCUS: {arc['act_2_focus']}\n\n"
        "ACT 2 MANDATE:\n"
        "- The earlier danger escalates or follows the narrator.\n"
        "- The narrator is no longer unsure — they are actively avoiding or managing risk.\n\n"
        "ACT 2 REQUIRED EVENTS:\n"
        "- At least one moment where the narrator changes route, routine, or behavior to stay safe.\n"
        "- At least one anomaly contradicts earlier assumptions.\n"
        "- At least one moment where the antagonist closes distance OR anticipates movement, but not perfectly.\n\n"
        "ACT 2 CONSTRAINTS:\n"
        "- No explanations.\n"
        "- No authority intervention that resolves anything.\n"
        "- The narrator may narrowly escape or interrupt a dangerous situation.\n\n"
        "ACT 2 END STATE:\n"
        "- The narrator understands this is not coincidence.\n"
    )
    
    act_2_text = None

    for _ in range(3):
        candidate = write_act(act_2, act_2_context, concept, act_number=2)
        if judge_act_scope(candidate, arc, act_number=2):
            act_2_text = candidate
            break

    if act_2_text is None:
        act_2_text = candidate  # fallback, never hard-fail

    full_script += "\n\n" + act_2_text
    
    # ============================================================
    # ACT 3
    # ============================================================

    act_3 = acts[2]

    act_3_context = (
        f"{full_script}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 3 RULES: {arc['act_3_rules']}\n"
        f"ACT 3 FOCUS: {arc['act_3_focus']}\n\n"
        "ACT 3 MANDATE:\n"
        "- The narrator is forced into an immediate survival decision.\n"
        "- Physical danger is real and present, not implied.\n\n"
        "ACT 3 REQUIRED EVENTS:\n"
        "- A moment of flight, hiding, locking, barricading, or escaping.\n"
        "- The narrator misinterprets at least one critical detail in the moment.\n"
        "- The narrator acts on instinct, not logic.\n\n"
        "ACT 3 CONSTRAINTS:\n"
        "- No resolution.\n"
        "- Any discovery must raise more questions than it answers.\n"
        "- Escape does NOT mean safety.\n"
        "- The antagonist remains unaccounted for.\n\n"
        "ACT 3 END STATE:\n"
        "- The narrator survives the moment, but knows the situation is not over.\n"
    )

    act_3_text = None

    for _ in range(3):
        candidate = write_act(act_3, act_3_context, concept, act_number=3)
        if judge_act_scope(candidate, arc, act_number=3):
            act_3_text = candidate
            break

    if act_3_text is None:
        act_3_text = candidate

    full_script += "\n\n" + act_3_text
    
    # ============================================================
    # ACT 4
    # ============================================================

    act_4 = acts[3]

    act_4_context = (
        f"{full_script}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 4 RULES: {arc['act_4_rules']}\n"
        f"ACT 4 FOCUS: {arc['act_4_focus']}\n\n"
        "ACT 4 MANDATE:\n"
        "- The narrator gains certainty they are unsafe, not why.\n"
        "- This certainty comes from actions, not confessions.\n\n"
        "ACT 4 REQUIRED EVENTS:\n"
        "- A failed attempt to regain control (reporting, confronting, documenting, testing).\n"
        "- A demonstration that the antagonist anticipated or neutralized this attempt.\n\n"
        "ACT 4 CONSTRAINTS:\n"
        "- No clean confrontation.\n"
        "- The antagonist must not verbally confirm the narrator’s interpretation.\n"
        "- Any response must minimize, deflect, or reframe.\n"
        "- No removal of threat.\n"
        "- No explanation of how the antagonist knows what they know.\n\n"
        "ACT 4 END STATE:\n"
        "- The narrator knows they are being targeted.\n"
    )

    act_4_text = None

    for _ in range(3):
        candidate = write_act(act_4, act_4_context, concept, act_number=4)
        if judge_act_scope(candidate, arc, act_number=4):
            act_4_text = candidate
            break

    if act_4_text is None:
        act_4_text = candidate

    full_script += "\n\n" + act_4_text

    # ============================================================
    # ACT 5
    # ============================================================

    act_5 = acts[4]

    act_5_context = (
        f"{full_script}\n\n"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 5 RULES: {arc['act_5_rules']}\n"
        f"ACT 5 FOCUS: {arc['act_5_focus']}\n\n"
        "ACT 5 MANDATE:\n"
        "- The danger is no longer active in the moment, but never resolved.\n"
        "- The narrator has changed permanently.\n\n"
        "ACT 5 REQUIRED ELEMENTS:\n"
        "- Ongoing vigilance, avoidance, or altered behavior.\n"
        "- At least one new habit formed to avoid future violations.\n"
        "- This habit unintentionally enables continued control.\n"
        "- Evidence the antagonist could still reappear.\n\n"
        "ACT 5 ENDING RULE:\n"
        "- End on a behavioral detail, not an explanation.\n"
        "- The last line should imply continued threat.\n"
    )

    act_5_text = None

    for _ in range(3):
        candidate = write_act(act_5, act_5_context, concept, act_number=5)
        if judge_act_scope(candidate, arc, act_number=5):
            act_5_text = candidate
            break

    if act_5_text is None:
        act_5_text = candidate

    full_script += "\n\n" + act_5_text


    return full_script


if __name__ == "__main__":
    script = generate_full_story()
    print(script)
