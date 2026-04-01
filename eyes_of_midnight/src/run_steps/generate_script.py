from __future__ import annotations

import os
import json
import time
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
from narrative_library import (
    sample_names,
    pick_hook_approach,
    pick_act1_signal_type,
    pick_act4_mistake_type,
    pick_act5_ending_type,
    pick_antagonist_relationship,
)

from idea_generator import generate_best_horror_idea

CHANNEL_ROOT = Path(__file__).resolve().parents[2]
VIDEO_PLAN_PATH = CHANNEL_ROOT / "video_plan.json"

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
    max_tokens: int = 4000,
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

    max_attempts = 10
    backoff = 15

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=HEADERS,
                json=payload,
                timeout=120,
            )
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_attempts:
                print(
                    f"[LLM] Network error ({type(e).__name__}) — waiting {backoff}s "
                    f"before retry {attempt + 1}/{max_attempts}...",
                    flush=True,
                )
                time.sleep(backoff)
                backoff *= 2
                continue
            raise

        if response.status_code in (429, 500, 502, 503, 504):
            if attempt < max_attempts:
                print(
                    f"[LLM] HTTP {response.status_code} — waiting {backoff}s "
                    f"before retry {attempt + 1}/{max_attempts}...",
                    flush=True,
                )
                time.sleep(backoff)
                backoff *= 2
                continue

        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"].get("content")

        if content is None:
            raise RuntimeError("LLM returned no content (null message)")

        content = content.strip()
        if not content:
            raise RuntimeError("LLM returned empty content")

        return content

    response.raise_for_status()

# ============================================================
# TTS Polish Helper
# ============================================================

def tts_polish_pass(
    text: str,
    enabled: bool = True,
) -> str:
    if not enabled:
        return text

    system = (
        "You are performing a text-to-speech readability pass for a single paragraph.\n\n"
        "STRICT RULES:\n"
        "- Treat this text as ONE paragraph\n"
        "- Do NOT split or merge paragraphs\n"
        "- Do NOT rewrite content\n"
        "- Do NOT add or remove information\n"
        "- Do NOT change word choice EXCEPT:\n"
        "- Numeric expressions may be converted into their natural spoken English equivalents.\n"
        "- Only the numeric portion may change.\n"
        "- No qualifiers may be added (no 'about', 'almost', 'roughly').\n"
        "- No contextual expansion.\n"
        "- No added descriptive language.\n\n"
        "- Preserve original meaning exactly\n\n"
        "ALLOWED CHANGES ONLY:\n"
        "- Adjust punctuation for spoken clarity\n"
        "- Break long sentences into shorter sentences\n"
        "- Convert numbers, times, ordinals, money amounts, and numeric phrases into natural spoken English.\n"
        "- Replace commas with periods when clauses are independent\n"
        "- Absolutely no emojis are allowed, you MUST remove any emojis that are present in the text.\n"
        "- Remove ambiguous pauses that confuse TTS\n\n"
        "FORBIDDEN:\n"
        "- Adding or removing sentences overall\n"
        "- Changing narrative voice\n"
        "- Adding emphasis or drama\n\n"
        "Output ONLY the revised paragraph."
    )

    user = (
        "Apply a TTS readability polish to the following text.\n\n"
        f"{text}"
    )

    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=len(text.split()) + 1000,
    )
    
# ============================================================
# Summarizers
# ============================================================
    
def summarize_act(act_text: str) -> str:
    """Creates a concise summary of the act, focusing on setting, characters, and key events."""
    system = (
        "You are a concise summarizer, extracting core details from a horror story act.\n"
        "Your summary will be used to provide context to the LLM for subsequent acts.\n"
        "Focus exclusively on the setting, key characters (descriptors only - no names!), and a brief overview of the plot events.\n"
        "Do NOT include opinions, interpretations, or emotional tone.\n"
        "Keep the summary brief: approximately 3-5 sentences.\n"
        "Output ONLY the summary text."
    )
    user = f"Summarize the following horror story act:\n{act_text}"
    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=600,
    )
    
# ============================================================
# Step 1: Concept + Hook
# ============================================================

def generate_long_form_hook(idea: str, hook_approach: str) -> str:
    system = (
        "You are writing the opening paragraph of a first-person horror account "
        "intended for spoken YouTube narration.\n\n"
        "This is NOT a teaser, cold open, or in-the-moment scene.\n"
        "This is the narrator setting up the story — grounding the listener before "
        "anything unusual happens.\n\n"
        f"OPENING APPROACH FOR THIS STORY:\n{hook_approach}\n\n"
        "REQUIREMENTS:\n"
        "- First person, past tense, conversational.\n"
        "- 3–5 sentences, ~45–70 words.\n"
        "- Nothing dangerous or frightening has happened yet.\n"
        "- Tone is reflective, not urgent.\n\n"
        "STYLE RULES:\n"
        "- No foreshadowing phrases like 'that was the first mistake' or 'looking back'\n"
        "- No moral lessons\n"
        "- No dramatic framing\n"
        "- No supernatural language\n"
        "- Do not use roles as examples — derive them from the story idea\n"
        "- Do not mention fear yet\n\n"
        "Output ONLY the paragraph text."
    )

    user = (
        f"Core horror idea:\n{idea}\n\n"
        "Write ONLY the opening paragraph.\n"
        "Do not describe the main incident yet.\n"
        "Do not reference later events.\n"
        "Do not use proper nouns.\n"
        "Output ONLY the paragraph text."
    )

    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.65,
        max_tokens=2500,
    )


def generate_concept_and_hook(
    seeded_idea: str | None = None,
    hook_approach: str = "",
    act1_signal_type: str = "",
    act4_mistake_type: str = "",
    act5_ending_type: str = "",
    antagonist_relationship: str = "",
    name_pool: list | None = None,
) -> Dict[str, str]:
    idea = seeded_idea if seeded_idea else generate_best_horror_idea()
    arc = get_random_story_arc()
    hook = generate_long_form_hook(idea, hook_approach)

    system = (
        "You are expanding a realistic first-person horror idea into a full story concept.\n"
        "You must output STRICT JSON ONLY.\n"
        "No commentary. No markdown. No extra text."
    )

    user = (
        f"Core horror idea:\n{idea}\n\n"
        f"Established hook:\n{hook}\n\n"
        f"Threat dynamic for this story:\n{antagonist_relationship}\n\n"
        "Expand this into a long-form horror story concept suitable for a 10–15 minute narration.\n\n"
        "Requirements:\n"
        "- First-person adult narrator\n"
        "- Realistic modern context\n"
        "- No supernatural elements\n"
        "- No full names, exact addresses, or brand names\n"
        "- Broad locations are allowed (regions, states, highways)\n"
        "- Use roles/descriptors only — derive them from the story idea, not generic placeholders\n"
        "- The idea must remain recognizable and central\n"
        "- The threat dynamic above must be honored throughout\n"
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
        max_tokens=4000,
        require_json=True,
    )

    data = json.loads(raw)

    def _str(val) -> str:
        """Flatten LLM values that occasionally come back as dicts/lists instead of strings."""
        if isinstance(val, str):
            return val.strip()
        if isinstance(val, dict):
            # e.g. {"description": "..."} — grab first string value
            for v in val.values():
                if isinstance(v, str):
                    return v.strip()
        return str(val).strip()

    return {
        "TITLE": _str(data["title"]),
        "HOOK": hook.strip(),
        "CORE ANOMALY": _str(data["core_anomaly"]),
        "SETTING": _str(data["setting"]),
        "ARC": arc,
        "ACT1_SIGNAL_TYPE": act1_signal_type,
        "ACT4_MISTAKE_TYPE": act4_mistake_type,
        "ACT5_ENDING_TYPE": act5_ending_type,
        "ANTAGONIST_RELATIONSHIP": antagonist_relationship,
        "NAME_POOL": name_pool or [],
    }

# ============================================================
# Step 2: Act Structure
# ============================================================

def generate_act_outline(concept: Dict[str, str]) -> List[Dict[str, str]]:
    idea = concept["CORE ANOMALY"]
    reference_block = get_random_reference_block()

    antagonist_relationship = concept.get("ANTAGONIST_RELATIONSHIP", "")

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
        f"Threat dynamic for this story:\n{antagonist_relationship}\n\n"
        "The story MUST follow this narrative progression:\n\n"
        f"{idea}\n\n"
        "1. Signal: an anomaly appears with no immediate cost\n"
        "2. Pattern: repetition and specificity emerge\n"
        "3. Personalization: the anomaly targets the narrator personally\n"
        "4. Mistake: the narrator takes a logical action that worsens the situation\n"
        "5. Binding: the narrator is left in a permanent, unresolved state\n\n"
        "The threat dynamic above must shape how the story escalates — "
        "the kind of threat this is determines what the narrator can and cannot do about it.\n"
        "Do NOT collapse, merge, or skip phases.\n"
        "Each act must escalate tension and reveal new implications.\n"
        "Pacing must support spoken narration."
    )

    user = (
        "Create a 5-act structure for a 10–15 minute spoken horror story.\n"
        "Each act MUST include a target word count.\n\n"
        "Acts:\n"
        "- Act 1: ~220-250 words (hook + anomaly introduction)\n"
        "- Act 2: ~220-250 words (escalation + pattern recognition)\n"
        "- Act 3: ~220-250 words (personal cost + discovery)\n"
        "- Act 4: ~220-250 words (mistake + confrontation)\n"
        "- Act 5: ~200-240 words (aftermath + unresolved dread)\n\n"
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
        max_tokens=2000,
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

def write_act(
    act: Dict[str, str],
    context: str,
    concept: Dict[str, str],
    act_number: int,
    target_words: int,
) -> str:
    system = (
        "You are writing a continuous first-person horror account intended for spoken narration.\n\n"
        "This is for a longform YouTube horror story channel.\n"
        "The story must be truly scary, not just unsettling, don't hold back.\n"
        "There must be a real, dangerous threat capable of causing serious harm or death.\n"
        "Keep it realistic and monetization safe (no graphic gore, no explicit sexual violence).\n\n"
        "Write naturally, as if recalling a real event without awareness of structure or rules.\n"
        "Maintain a grounded, conversational tone.\n"
        "Do not explain or analyze events in a generalized or instructional way.\n"
        "Brief hindsight framing is allowed if it reflects uncertainty, rationalization, or memory gaps.\n"
        "Let scenes unfold through memory, action, and reaction.\n\n"
        "The story is realistic and non-supernatural.\n"
        "The narrator does not know the full truth.\n\n"
        "IMPORTANT:\n"
        "- Write as if this is a real experience being recalled.\n"
        "- Prioritize flow, causality, and lived detail over compliance.\n\n"
        "After the midpoint of the story, do not introduce new recurring motifs. "
        "Only reuse, intensify, or recontextualize motifs already established.\n\n"
        "OUTPUT RULE:\n"
        "- Output ONLY prose. No labels. No explanations."
    )

    # Create Summary of Previous Act
    previous_act_summary = summarize_act(context)

    # Get last 8 paragraphs from previous context.
    previous_paragraphs = "\n\n".join(context.split("\n\n")[-8:]) if context else ""

    user = (
        f"Core idea:\n{concept['CORE ANOMALY']}\n\n"
        f"Previous act summary:\n{previous_act_summary}\n\n"
        f"Recent paragraphs from previous act:\n{previous_paragraphs}\n\n"
        f"Write the following act as prose:\n"
        f"Act purpose:\n{act.get('PURPOSE', '')}\n\nKey events to cover:\n{act.get('KEY EVENTS', '')}\n\n"
        "Maintain a consistent narrative voice.\n\n"
        f"TARGET LENGTH:\n"
        f"- Write approximately {target_words} words.\n"
        f"- Do not artificially cut off the act to meet a number.\n\n"
        "Write this act according to the outline below.\n"
        "Do not summarize or foreshadow future acts.\n"
        "Stay inside the narrator's limited perspective.\n"
        "At least once in this act, the narrator must draw a reasonable but incorrect conclusion about what is happening.\n"
        "Do not correct it within the same paragraph.\n\n"
    )

    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=2000,
    )
    
    
def _arc_key(arc: Dict[str, str], act_number: int, suffix: str) -> str:
    return arc[f"act_{act_number}_{suffix}"]
    
def judge_act_scope(act_text: str, arc: Dict[str, str], act_number: int) -> bool:
    system = (
        "You are checking whether an act violates its narrative phase.\n\n"
        "Judge ONLY based on major events, not tone, prose, or emotion.\n"
        "Do NOT penalize natural reflection, memory, or internal narration.\n\n"
        "FAIL ONLY IF:\n"
        "- A future act's core event clearly occurs early\n"
        "- The central anomaly is explained or resolved\n"
        "- The antagonist explicitly admits intent\n\n"
        "PASS if escalation remains incomplete.\n\n"
        "Output ONLY: PASS or FAIL."
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
        max_tokens=500,
    )

    return verdict.strip().upper() == "PASS"

# ============================================================
# Main Orchestration
# ============================================================

def generate_full_story(seeded_idea: str | None = None) -> str:
    hook_approach = pick_hook_approach()
    act1_signal_type = pick_act1_signal_type()
    act4_mistake_type = pick_act4_mistake_type()
    act5_ending_type = pick_act5_ending_type()
    antagonist_relationship = pick_antagonist_relationship()
    name_pool = sample_names(12)

    print(f"[STORY] Threat dynamic: {antagonist_relationship[:60]}...", flush=True)
    print(f"[STORY] Hook approach: {hook_approach[:60]}...", flush=True)
    print(f"[STORY] Act 1 signal type: {act1_signal_type[:60]}...", flush=True)
    print(f"[STORY] Act 4 mistake type: {act4_mistake_type[:60]}...", flush=True)
    print(f"[STORY] Act 5 ending type: {act5_ending_type[:60]}...", flush=True)
    print(f"[STORY] Name pool: {', '.join(name_pool)}", flush=True)

    concept = generate_concept_and_hook(
        seeded_idea=seeded_idea,
        hook_approach=hook_approach,
        act1_signal_type=act1_signal_type,
        act4_mistake_type=act4_mistake_type,
        act5_ending_type=act5_ending_type,
        antagonist_relationship=antagonist_relationship,
        name_pool=name_pool,
    )
    acts = generate_act_outline(concept)

    full_script = f"{concept['HOOK']}\n"
    
    # ============================================================
    # ACT 1
    # ============================================================

    act_1 = acts[0]
    arc = concept["ARC"]

    name_pool = concept.get("NAME_POOL", [])
    name_pool_line = (
        "IF NAMED CHARACTERS APPEAR — draw names only from this list: "
        + ", ".join(name_pool) + ".\n"
        "Do not invent names outside this list for any character who recurs or has dialogue.\n\n"
    ) if name_pool else ""

    relationship_line = concept.get("ANTAGONIST_RELATIONSHIP", "")
    if relationship_line:
        relationship_line = relationship_line + "\n\n"

    act_1_context = (
        f"{concept['HOOK']}\n\n"
        f"{name_pool_line}"
        f"{relationship_line}"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 1 RULES: {arc['act_1_rules']}\n"
        f"ACT 1 FOCUS: {arc['act_1_focus']}\n\n"
        "ACT 1 OPENING NOTE:\n"
        "- Begin with routine continuation before the anomaly appears.\n\n"
        "ACT 1 MANDATE:\n"
        "- Introduce something that is unusual or off in a way the narrator cannot immediately explain.\n"
        "- The narrator notices it, tries to account for it, and mostly succeeds.\n"
        "- This is not subtle or symbolic. It is physically or socially invalid in a specific way.\n\n"
        f"{concept['ACT1_SIGNAL_TYPE']}\n\n"
        "ACT 1 CONSTRAINTS:\n"
        "- Do NOT explain motives.\n"
        "- Do NOT resolve the situation.\n"
        "- The narrator may escape, interrupt, or evade — but the threat remains active.\n\n"
        "ACT 1 END STATE:\n"
        "- The narrator knows something is wrong and cannot unsee it.\n"
    )

    act_1_text = None

    for _ in range(3):
        candidate = write_act(
            act_1,
            act_1_context,
            concept,
            act_number=1,
            target_words=235,
        )
        if judge_act_scope(candidate, arc, act_number=1):
            act_1_text = candidate
            break

    if act_1_text is None:
        act_1_text = candidate  # fallback, never hard-fail
        
    # TTS Polish Pass        
    act_1_text = tts_polish_pass(
        act_1_text,
        enabled=True,
    )

    full_script += "\n\n" + act_1_text
    
    # ============================================================
    # ACT 2
    # ============================================================

    act_2 = acts[1]

    act_2_context = (
        "\n\n".join(full_script.split("\n\n")[-8:]) + "\n\n"
        f"{name_pool_line}"
        f"{relationship_line}"
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
        candidate = write_act(
            act_2,
            act_2_context,
            concept,
            act_number=2,
            target_words=235,
        )
        if judge_act_scope(candidate, arc, act_number=2):
            act_2_text = candidate
            break

    if act_2_text is None:
        act_2_text = candidate  # fallback, never hard-fail
    
    # TTS Polish Pass        
    act_2_text = tts_polish_pass(
        act_2_text,
        enabled=True,
    )

    full_script += "\n\n" + act_2_text
    
    # ============================================================
    # ACT 3
    # ============================================================

    act_3 = acts[2]

    act_3_context = (
        "\n\n".join(full_script.split("\n\n")[-8:]) + "\n\n"
        f"{name_pool_line}"
        f"{relationship_line}"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 3 RULES: {arc['act_3_rules']}\n"
        f"ACT 3 FOCUS: {arc['act_3_focus']}\n\n"
        "ACT 3 MANDATE:\n"
        "- The narrator is forced into an immediate survival decision.\n"
        "- A concrete, time-bound danger event occurs in this act.\n"
        "- The narrator narrowly avoids harm through chance, interruption, or escape.\n"
        "- The outcome leaves physical evidence, witnesses, or lasting consequences.\n\n"
        "ACT 3 REQUIRED EVENTS:\n"
        "- ONE concrete, time-bound danger event related to the existing anomaly.\n\n"
        "ACT 3 CONSTRAINTS:\n"
        "- No resolution.\n"
        "- Any discovery must raise more questions than it answers.\n"
        "- Escape does NOT mean safety.\n"
        "- The antagonist remains unaccounted for.\n\n"
        "ACT 3 END STATE:\n"
        "- The narrator survives the moment, but knows the situation is not over.\n"
    )

    act_3_text = None

    for _ in range(2):
        candidate = write_act(
            act_3,
            act_3_context,
            concept,
            act_number=3,
            target_words=235,
        )
        if judge_act_scope(candidate, arc, act_number=3):
            act_3_text = candidate
            break

    if act_3_text is None:
        act_3_text = candidate
        
    # TTS Polish Pass        
    act_3_text = tts_polish_pass(
        act_3_text,
        enabled=True,
    )

    full_script += "\n\n" + act_3_text
    
    # ============================================================
    # ACT 4
    # ============================================================

    act_4 = acts[3]

    act_4_context = (
        "\n\n".join(full_script.split("\n\n")[-8:]) + "\n\n"
        f"{name_pool_line}"
        f"{relationship_line}"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 4 RULES: {arc['act_4_rules']}\n"
        f"ACT 4 FOCUS: {arc['act_4_focus']}\n\n"
        "ACT 4 MANDATE:\n"
        "- The narrator acts — makes a move toward resolution, safety, or understanding.\n"
        "- That move does not go as hoped. The situation is not resolved.\n\n"
        f"{concept['ACT4_MISTAKE_TYPE']}\n\n"
        "ACT 4 CONSTRAINTS:\n"
        "- No clean answers from the threat — no verbal confirmation, no admission.\n"
        "- The threat is not removed.\n"
        "- The narrator ends this act more aware of their position, not safer.\n\n"
        "ACT 4 END STATE:\n"
        "- The narrator knows they are being targeted. They do not know why, or what comes next.\n"
    )

    act_4_text = None

    for _ in range(2):
        candidate = write_act(
            act_4,
            act_4_context,
            concept,
            act_number=4,
            target_words=235,
        )
        if judge_act_scope(candidate, arc, act_number=4):
            act_4_text = candidate
            break

    if act_4_text is None:
        act_4_text = candidate
    
    # TTS Polish Pass        
    act_4_text = tts_polish_pass(
        act_4_text,
        enabled=True,
    )

    full_script += "\n\n" + act_4_text

    # ============================================================
    # ACT 5
    # ============================================================

    act_5 = acts[4]

    act_5_context = (
        "\n\n".join(full_script.split("\n\n")[-8:]) + "\n\n"
        f"{name_pool_line}"
        f"{relationship_line}"
        f"STORY ARC: {arc['name']}\n"
        f"ARC THEME: {arc['theme']}\n"
        f"ACT 5 RULES: {arc['act_5_rules']}\n"
        f"ACT 5 FOCUS: {arc['act_5_focus']}\n\n"
        "ACT 5 MANDATE:\n"
        "- The narrator has survived and is telling this from a remove in time.\n"
        "- The threat was never fully explained or confronted.\n\n"
        f"{concept['ACT5_ENDING_TYPE']}\n\n"
        "ACT 5 ENDING RULE:\n"
        "- Do not end with acceptance or closure.\n"
        "- The final image must be specific and concrete — one thing, grounded in a real moment.\n"
        "- The last line should land and stay.\n"
    )

    act_5_text = None

    for _ in range(2):
        candidate = write_act(
            act_5,
            act_5_context,
            concept,
            act_number=5,
            target_words=220,
        )
        if judge_act_scope(candidate, arc, act_number=5):
            act_5_text = candidate
            break

    if act_5_text is None:
        act_5_text = candidate
    
    # TTS Polish Pass        
    act_5_text = tts_polish_pass(
        act_5_text,
        enabled=True,
    )

    full_script += "\n\n" + act_5_text


    return {
        "act_1": act_1_text,
        "act_2": act_2_text,
        "act_3": act_3_text,
        "act_4": act_4_text,
        "act_5": act_5_text,
        "full_script": full_script,
    }


def build_visual_chunks(paragraph_count: int) -> list[dict]:
    """
    Split paragraphs into visual chunks using strict rules:
    - Base size: 3 paragraphs
    - Remainder 1: last chunk becomes 4
    - Remainder 2: first and last chunks become 4
    """

    indices = list(range(paragraph_count))
    chunks = []

    remainder = paragraph_count % 3

    i = 0

    if remainder == 2 and paragraph_count >= 4:
        chunks.append(indices[0:4])
        i = 4

    while i < paragraph_count:
        remaining = paragraph_count - i

        if remainder == 1 and remaining == 4:
            chunks.append(indices[i:i+4])
            break

        chunks.append(indices[i:i+3])
        i += 3

    return [
        {
            "chunk_id": idx,
            "paragraph_start": c[0],
            "paragraph_end": c[-1],
            "paragraph_ids": c,
        }
        for idx, c in enumerate(chunks)
    ]


if __name__ == "__main__":
    from datetime import datetime

    # ------------------------------------------------------------
    # Load story seed from video_plan.json if available
    # ------------------------------------------------------------
    story_seed: str | None = None
    story_mini_title: str | None = None

    story_index = int(os.environ.get("STORY_INDEX", "-1"))

    if VIDEO_PLAN_PATH.exists() and story_index >= 0:
        plan = json.loads(VIDEO_PLAN_PATH.read_text(encoding="utf-8"))
        stories = plan.get("stories", [])
        if story_index < len(stories):
            story_seed = stories[story_index]["seed"]
            story_mini_title = stories[story_index]["mini_title"]
            print(f"[SCRIPT] Using seeded idea (story {story_index + 1}): {story_seed[:80]}...")
        else:
            print(f"[SCRIPT] Warning: story_index {story_index} out of range, generating idea freely.")
    else:
        print("[SCRIPT] No video_plan.json or STORY_INDEX found — generating idea freely.")

    # ------------------------------------------------------------
    # Run folder setup
    # ------------------------------------------------------------
    RUNS_ROOT = Path(__file__).resolve().parents[2] / "runs"
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = RUNS_ROOT / run_id

    script_dir = run_dir / "script"
    paragraph_dir = script_dir / "paragraphs"

    script_dir.mkdir(parents=True, exist_ok=True)
    paragraph_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    # Generate script
    # ------------------------------------------------------------
    result = generate_full_story(seeded_idea=story_seed)
    full_script = result["full_script"].strip()
    
    acts_dir = script_dir / "acts"
    acts_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 6):
        act_key = f"act_{i}"
        act_text = result[act_key].strip()

        act_path = acts_dir / f"{act_key}.txt"
        act_path.write_text(act_text, encoding="utf-8")

    # Write full script
    full_script_path = script_dir / "full_script.txt"
    full_script_path.write_text(full_script, encoding="utf-8")

    # ------------------------------------------------------------
    # Split into paragraphs
    # Rule: 2+ newlines = paragraph break
    # ------------------------------------------------------------
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n+", full_script)
        if p.strip()
    ]
    
    for idx, paragraph in enumerate(paragraphs):
        p_path = paragraph_dir / f"p{idx:03d}.txt"
        p_path.write_text(paragraph, encoding="utf-8")
    
    paragraph_index = []

    for idx in range(len(paragraphs)):
        paragraph_index.append({
            "paragraph_id": idx,
            "filename": f"p{idx:03d}.txt",
            "text": paragraphs[idx]
        })

    paragraph_index_path = script_dir / "paragraph_index.json"
    paragraph_index_path.write_text(
        json.dumps(
            {
                "paragraph_count": len(paragraphs),
                "paragraphs": paragraph_index,
            },
            indent=2
        ),
        encoding="utf-8",
    )
    
    # ------------------------------------------------------------
    # Visual chunk plan (image timing groups)
    # ------------------------------------------------------------
    visual_chunks = build_visual_chunks(len(paragraphs))

    visual_chunks_path = script_dir / "visual_chunks.json"
    visual_chunks_path.write_text(
        json.dumps(
            {
                "total_paragraphs": len(paragraphs),
                "base_chunk_size": 3,
                "chunks": visual_chunks,
            },
            indent=2
        ),
        encoding="utf-8",
    )

    # Save story identity for the stitcher
    identity = {
        "story_index": story_index,
        "mini_title": story_mini_title or result.get("title", ""),
        "run_id": run_id,
    }
    (script_dir / "story_identity.json").write_text(
        json.dumps(identity, indent=2), encoding="utf-8"
    )

    print(f"[SCRIPT] run created: {run_dir.resolve()}", flush=True)
    print(f"[SCRIPT] paragraphs written: {len(paragraphs)}", flush=True)
