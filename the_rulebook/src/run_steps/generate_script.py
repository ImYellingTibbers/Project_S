from __future__ import annotations

import os
import json
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv
import requests

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
sys.path.insert(0, str(ASSETS_DIR))

from idea_generator import build_story_frame

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
    temperature: float = 0.7,
    max_tokens: int = 4000,
    require_json: bool = False,
) -> str:
    import time

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if require_json:
        payload["response_format"] = {"type": "json_object"}

    max_retries = 5
    base_wait = 10  # seconds

    for attempt in range(1, max_retries + 1):
        response = requests.post(
            OPENROUTER_URL,
            headers=HEADERS,
            json=payload,
            timeout=180,
        )

        if response.status_code == 429:
            wait = base_wait * (2 ** (attempt - 1))  # 10, 20, 40, 80, 160
            print(
                f"[LLM] Rate limited (429). Waiting {wait}s before retry "
                f"({attempt}/{max_retries})...",
                flush=True,
            )
            time.sleep(wait)
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

    raise RuntimeError(f"LLM call failed after {max_retries} retries due to rate limiting.")

# ============================================================
# TTS Polish
# ============================================================

def tts_polish_pass(text: str, enabled: bool = True) -> str:
    if not enabled:
        return text

    system = (
        "You are performing a text-to-speech readability pass on a block of prose.\n\n"
        "STRICT RULES:\n"
        "- Do NOT rewrite content.\n"
        "- Do NOT add or remove information.\n"
        "- Do NOT change word choice EXCEPT to convert numeric expressions into "
        "their natural spoken English equivalents.\n"
        "- No qualifiers may be added (no 'about', 'almost', 'roughly').\n"
        "- Preserve original meaning exactly.\n\n"
        "ALLOWED CHANGES ONLY:\n"
        "- Adjust punctuation for spoken clarity.\n"
        "- Break long sentences into shorter ones where natural.\n"
        "- Convert numbers, times, ordinals, money amounts into natural spoken English.\n"
        "- Replace commas with periods when clauses are independent.\n"
        "- Remove any emojis entirely.\n"
        "- Remove ambiguous pauses that confuse TTS.\n\n"
        "FORBIDDEN:\n"
        "- Adding or removing sentences overall.\n"
        "- Changing narrative voice.\n"
        "- Adding emphasis or drama.\n\n"
        "Output ONLY the revised prose."
    )

    user = f"Apply a TTS readability polish to the following text.\n\n{text}"

    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=len(text.split()) + 1200,
    )

# ============================================================
# Summarizer + Rules State Updater
# (single call, two outputs)
# ============================================================

def summarize_and_update_rules(
    act_text: str,
    act_number: int,
    primary_rule: Optional[Dict],
    rules_state: Dict,
    existing_per_act_summaries: List[str],
    existing_full_story_summary: Optional[str],
) -> Dict:
    """
    After each act is written, this call does two things:
    1. Produces a summary of the act (3-5 sentences for acts 1-4,
       or updates the rolling full-story summary for acts 5+)
    2. Updates the rules state object to mark the primary rule as established

    Returns:
    {
        "act_summary": "...",           # always — summary of this specific act
        "full_story_summary": "...",    # only for acts 5+ — rolling compressed summary
        "rules_state": { ... }          # updated rules state
    }
    """

    is_early = act_number <= 4

    if is_early:
        summary_instruction = (
            "Write a summary of this act in 3-5 sentences.\n"
            "Focus on: what happened, which rule was triggered and how, "
            "and the narrator's current emotional state.\n"
            "Do not editorialize. Be factual and specific."
        )
    else:
        prior_context = existing_full_story_summary or ""
        summary_instruction = (
            "Update the full story summary to include the events of this act.\n"
            "The updated summary must be no more than 10 sentences total.\n"
            "Compress earlier events as needed to stay within that limit.\n"
            "Prioritize: active rules, narrator's current state, and the most "
            "recent escalations.\n"
            f"Current full story summary to update:\n{prior_context}"
        )

    # Build the current rules context for the prompt
    established = rules_state.get("established", [])
    pending = rules_state.get("pending", [])

    rules_context = ""
    if established:
        rules_context += "ESTABLISHED RULES SO FAR:\n"
        for r in established:
            rules_context += f"- [{r['id']}] {r['name']}: {r['trigger_note']}\n"
    if primary_rule:
        rules_context += (
            f"\nPRIMARY RULE THIS ACT:\n"
            f"- [{primary_rule['id']}] {primary_rule['name']}: {primary_rule['template']}\n"
        )

    system = (
        "You are a story analyst for a horror fiction pipeline.\n"
        "You will be given an act of a horror story and must produce a JSON response.\n"
        "Output ONLY valid JSON. No commentary, no markdown fences."
    )

    user = (
        f"ACT NUMBER: {act_number}\n\n"
        f"{rules_context}\n\n"
        f"ACT TEXT:\n{act_text}\n\n"
        f"TASK 1 — SUMMARIZE:\n{summary_instruction}\n\n"
        "TASK 2 — UPDATE RULES STATE:\n"
        "Based on the act text, confirm how the primary rule was triggered.\n"
        "Write a single sentence (max 20 words) describing specifically how "
        "the rule manifested in this act.\n\n"
        "OUTPUT FORMAT — respond with this exact JSON schema:\n"
        "{\n"
        '  "act_summary": "string — summary of this act",\n'
        '  "full_story_summary": "string — updated rolling summary (acts 5+ only, '
        'empty string for acts 1-4)",\n'
        '  "primary_rule_trigger_note": "string — one sentence on how the rule triggered"\n'
        "}"
    )

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=1200,
        require_json=True,
    )

    # Parse response
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback if JSON is malformed
        parsed = {
            "act_summary": f"Act {act_number} summary unavailable.",
            "full_story_summary": existing_full_story_summary or "",
            "primary_rule_trigger_note": "Rule was triggered during this act.",
        }

    # Update rules state
    updated_rules_state = {
        "established": list(established),
        "pending": list(pending),
    }

    if primary_rule:
        # Move primary rule from pending to established
        updated_rules_state["pending"] = [
            r for r in pending if r["id"] != primary_rule["id"]
        ]
        updated_rules_state["established"].append({
            "id": primary_rule["id"],
            "name": primary_rule["name"],
            "template": primary_rule["template"],
            "trigger_note": parsed.get(
                "primary_rule_trigger_note",
                "Rule was triggered during this act."
            ),
        })

    return {
        "act_summary": parsed.get("act_summary", f"Act {act_number}."),
        "full_story_summary": parsed.get("full_story_summary", ""),
        "rules_state": updated_rules_state,
    }

# ============================================================
# Locked Facts Generator
# (called once after act 1 — never updated)
# ============================================================

def generate_locked_facts(
    act_text: str,
    narrator: Dict,
    place: Dict,
) -> str:
    """
    Extracts immutable story facts from the setup act.
    Called exactly once after act 1 completes.
    Passed verbatim into every subsequent act. Never modified.
    """

    system = (
        "You are extracting locked continuity facts from the opening act of a horror story.\n"
        "These facts will be injected into every subsequent act to prevent contradictions.\n"
        "Be specific and concrete. Vague entries cause continuity errors.\n"
        "Output ONLY valid JSON. No commentary, no markdown fences."
    )

    user = (
        f"NARRATOR INFO (ground truth from story frame):\n"
        f"Name: {narrator['first_name']}, Age: {narrator['age']}\n"
        f"Financial situation: {narrator['financial_situation']}\n"
        f"Reason for job: {narrator['reason_for_job']}\n"
        f"Personal detail: {narrator['one_personal_detail']}\n\n"
        f"PLACE: {place['name']}\n"
        f"NARRATOR ROLE: {place['role']}\n\n"
        f"SETUP ACT TEXT:\n{act_text}\n\n"
        "Extract the following. If something is not explicitly in the act text, "
        "derive it from the narrator info above. Be specific — vague entries cause drift.\n\n"
        "OUTPUT FORMAT — respond with this exact JSON schema:\n"
        "{\n"
        '  "narrator_name": "first name only",\n'
        '  "narrator_age": "age as words e.g. thirty-two",\n'
        '  "narrator_situation": "1-2 sentences on financial pressure and why they need this job",\n'
        '  "narrator_personal_history": "bullet list of every personal memory, relationship, '
        "or biographical detail introduced in the act. One bullet per detail. Include: "
        "family members mentioned and their status (living/deceased), past jobs or hobbies, "
        "any sensory memory tied to a specific person (e.g. blues music reminds them of their "
        "FATHER — not grandfather, not uncle — be exact), any loss or grief introduced. "
        'Format each as: - [detail]",\n'
        '  "named_characters": "every named person who appeared, their role, gender, and '
        "last known status. Format: Name — role, gender, status. One per line. "
        'Only include characters who actually appeared in the act.",\n'
        '  "place_details": "specific physical details established: layout, key rooms, '
        'equipment, smells, sounds, lighting. 2-3 sentences.",\n'
        '  "rules_document_name": "exact name the rules document was called in the act",\n'
        '  "shift_hours": "when shift starts and ends as established in act, or unknown"\n'
        "}"
    )

    raw = call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=900,
        require_json=True,
    )

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = {
            "narrator_name": narrator["first_name"],
            "narrator_age": str(narrator["age"]),
            "narrator_situation": narrator["financial_situation"],
            "narrator_personal_history": f"- {narrator['one_personal_detail']}",
            "named_characters": "None established.",
            "place_details": f"{place['name']}.",
            "rules_document_name": "Night Shift Rules",
            "shift_hours": "Unknown",
        }

    # Normalize any list fields to strings — LLM sometimes returns arrays
    for key in ("narrator_personal_history", "named_characters"):
        val = parsed.get(key, "")
        if isinstance(val, list):
            parsed[key] = "\n".join(str(item) for item in val)
        elif not isinstance(val, str):
            parsed[key] = str(val)

    lines = [
        "=" * 60,
        "LOCKED FACTS — DO NOT CONTRADICT THESE UNDER ANY CIRCUMSTANCES.",
        "These are established canon. Do not restate, re-introduce, or",
        "re-explain any of these as if the narrator is discovering them",
        "for the first time. The narrator already knows all of this.",
        "=" * 60,
        "",
        f"Narrator: {parsed.get('narrator_name')}, {parsed.get('narrator_age')} years old.",
        f"Situation: {parsed.get('narrator_situation')}",
        f"Place: {place['name']} | Role: {place['role']}",
        f"Shift hours: {parsed.get('shift_hours')}",
        f"Rules document called: {parsed.get('rules_document_name')}",
        "",
        "NARRATOR PERSONAL HISTORY — established in act 1.",
        "Do not repeat these as new discoveries. Do not contradict them.",
        "If music, smells, or other sensory details recur, they must reference",
        "the SAME person/memory established here — not a different family member:",
        parsed.get("narrator_personal_history", "None recorded."),
        "",
        "NAMED CHARACTERS — gender and role are fixed, do not change:",
        parsed.get("named_characters", "None established."),
        "",
        "PHYSICAL SPACE — established in act 1, use these details, do not reinvent:",
        parsed.get("place_details", ""),
        "=" * 60,
    ]

    return "\n".join(lines)


# ============================================================
# Context Builder
# ============================================================

def build_act_context(
    act_number: int,
    act_type: str,
    primary_rule: Optional[Dict],
    active_rules: List[Dict],
    rules_state: Dict,
    per_act_summaries: List[str],
    full_story_summary: Optional[str],
    recent_prose: str,
    narrator: Dict,
    place: Dict,
    total_acts: int,
    locked_facts: Optional[str] = None,
    full_script_so_far: Optional[str] = None,
) -> str:
    """
    Assembles the full context string passed into each act writing call.
    Acts 1-4: locked facts + per-act summaries + last 8 paragraphs of prose.
    Acts 5+:  locked facts + full script so far (replaces rolling summary).
    """

    lines = []

    # ---- Locked facts (act 2 onward — immutable continuity anchor) ----
    if locked_facts and act_number > 1:
        lines.append(locked_facts)
        lines.append("")

    # ---- Narrator + Place (always present) ----
    lines.append("STORY CONTEXT:")
    lines.append(f"Place: {place['name']}")
    lines.append(f"Narrator role: {place['role']}")
    lines.append(
        f"Narrator: {narrator['first_name']}, {narrator['age']} years old. "
        f"{narrator['financial_situation']} {narrator['reason_for_job']} "
        f"{narrator['one_personal_detail']}"
    )
    lines.append("")

    # ---- Story history ----
    if act_number == 1:
        pass  # No prior context for the first act

    elif act_number <= 4:
        lines.append("PREVIOUS ACT SUMMARIES:")
        for i, summary in enumerate(per_act_summaries, start=1):
            lines.append(f"Act {i}: {summary}")
        lines.append("")

        if recent_prose:
            lines.append("RECENT PROSE (last 8 paragraphs — match this voice exactly):")
            lines.append(recent_prose)
            lines.append("")

    else:
        # Acts 5+: full script passthrough replaces rolling summary entirely
        if full_script_so_far:
            lines.append(
                "FULL STORY SO FAR — READ THIS CAREFULLY BEFORE WRITING.\n"
                "Do not repeat any sensory trigger, emotional beat, personal memory "
                "callback, or plot detail that already appears in this text.\n"
                "Do not re-introduce anything established here as if it is new.\n"
                "Do not re-establish any rules that have already been triggered.\n"
                "The narrator is continuing from where this story left off.\n"
                "Match the voice and tone of the final paragraphs exactly."
            )
            lines.append("")
            lines.append(full_script_so_far)
            lines.append("")

    # ---- Rules state ----
    established = rules_state.get("established", [])
    pending = rules_state.get("pending", [])

    if established:
        lines.append(
            "RULES AND HOW THEY HAVE MANIFESTED — "
            "do not repeat these exact manifestations. Each encounter must be distinct:"
        )
        for r in established:
            lines.append(f"- [{r['id']}] {r['name']}: {r['trigger_note']}")
        lines.append("")

    if pending:
        lines.append("RULES NOT YET ENCOUNTERED (do NOT reference or trigger these yet):")
        for r in pending:
            lines.append(f"- [{r['id']}] {r['name']}")
        lines.append("")

    # ---- This act's directive ----
    lines.append(f"THIS IS ACT {act_number} OF {total_acts}.")
    lines.append(f"ACT TYPE: {act_type.upper()}")
    lines.append("")

    if act_type == "setup":
        lines.append("ACT DIRECTIVE:")
        lines.append(
            "This is the opening act. Spend real time establishing the physical space — "
            "the narrator has just arrived for their first shift and is taking everything in. "
            "Describe the building, the equipment, the smell, the sounds, the light. "
            "Make it specific enough that a listener could picture exactly where they are. "
            "Details established here will pay off in later acts — the layout, the exits, "
            "the equipment, the specific quirks of the place.\n\n"
            "Weave the narrator's financial situation into their inner voice naturally — "
            "not as a monologue but as the undercurrent behind every decision. "
            "They need this job. That has to be felt, not stated.\n\n"
            "Introduce the rules document organically — handed over by a departing coworker, "
            "found taped to a desk, left in a folder with a key. "
            "The handoff should feel casual and slightly odd — the person giving them the rules "
            "doesn't explain anything, doesn't linger. They just leave.\n\n"
            "The narrator reads the rules aloud or to themselves, one by one. "
            "Present each rule as numbered, typed or handwritten, oddly specific. "
            "The narrator reacts to each one — confusion, mild unease, dismissal, "
            "a joke to themselves. They are not scared yet. They think it's eccentric "
            "workplace culture, previous employee superstition, or a prank.\n\n"
            "Nothing dangerous happens in this act. "
            "End with the narrator alone, shift beginning, rules set aside. "
            "The last beat should carry a quiet unease — not dread, just the feeling "
            "that something about this place is slightly off in a way they can't name."
        )
        lines.append("")
        lines.append(
            "ALL RULES FOR THIS STORY (present these as the rules document, in order):\n"
            "IMPORTANT: Some rules contain bracketed placeholders such as "
            "[specific location], [specific warning sign], or [specific sound]. "
            "Before writing, replace every bracketed placeholder with a specific, "
            "concrete detail that fits this exact place and narrator. "
            "The rules must read as if a real person wrote them for this specific building. "
            "No brackets should appear in the final prose."
        )
        all_rules = established + [
            {"id": r["id"], "name": r["name"], "template": r["template"]}
            for r in pending
        ]
        for r in all_rules:
            lines.append(f"- [{r['id']}] {r['template']}")

    elif act_type == "rule":
        if primary_rule:
            lines.append("PRIMARY RULE THIS ACT:")
            lines.append(f"Rule ID: {primary_rule['id']}")
            lines.append(f"Rule name: {primary_rule['name']}")
            lines.append(f"Rule text: {primary_rule['template']}")
            lines.append(f"Consequence tone: {primary_rule['consequence_tone']}")
            lines.append(f"Story moment: {primary_rule['story_moment']}")
            lines.append("")
            lines.append(
                "ACT DIRECTIVE:\n"
                "This act is built entirely around the PRIMARY RULE above being triggered "
                "for the first time.\n\n"
                "SETUP: The act should begin with the narrator doing ordinary work — "
                "a mundane task specific to this place. Let that normalcy breathe for "
                "several paragraphs before anything shifts. The longer the normal feels "
                "real, the harder the turn hits.\n\n"
                "TRIGGER: The narrator encounters the exact situation the rule was written for. "
                "They do not immediately recognize it as the rule. They first try to explain "
                "it rationally — a practical concern, a misperception, fatigue. "
                "Only when it becomes undeniable does the rule surface in their memory. "
                "When it does, they recall it imperfectly — a fragment, the gist, "
                "the feeling of having read it — NOT a verbatim recitation.\n\n"
                "COST: Following the rule must cost something real. "
                "The narrator has to make a choice that is uncomfortable, "
                "that goes against instinct, that they will second-guess. "
                "They do not get to follow the rule and feel safe. "
                "They follow it and survive, but something is lost — "
                "certainty, composure, a piece of their confidence that this is fine.\n\n"
                "AMBIGUITY: The threat is never seen directly. Never explained. "
                "Never touches the narrator. What they experience could almost — "
                "almost — have another explanation. But it can't quite.\n\n"
                "END STATE: The narrator has survived this act but is more unsettled "
                "than before. They cannot go back to dismissing the rules. "
                "They believe them now, even if they don't understand them."
            )

        if active_rules:
            lines.append("")
            lines.append(
                "ACTIVE RULES (previously triggered — the narrator knows these are real now. "
                "Layer one or two into this act where they create additional pressure. "
                "Do not force all of them. Do not reference them by number or quote them. "
                "They are felt, not recited):"
            )
            for r in active_rules:
                trigger_note = next(
                    (e["trigger_note"] for e in established if e["id"] == r["id"]),
                    r.get("consequence_tone", "")
                )
                lines.append(f"- [{r['id']}] {r['name']}: {trigger_note}")

    elif act_type == "resolution":
        lines.append("ACT DIRECTIVE:")
        lines.append(
            "This is the final act. The immediate danger of the shift is over. "
            "The narrator is leaving or has left. Do not wrap things up neatly.\n\n"
            "The narrator does NOT explain what the rules were protecting against. "
            "They do not understand it. The listener does not get an answer. "
            "Any attempt to explain or theorize should feel hollow and unsatisfying — "
            "because it is. Some things don't have explanations.\n\n"
            "Show the cost of survival — not through drama but through the small, "
            "permanent changes in how the narrator moves through the world now. "
            "Something they can't stop doing. Something they can no longer do. "
            "A habit that formed without them deciding to form it. "
            "These should feel specific and involuntary, not chosen coping mechanisms.\n\n"
            "The narrator is functional. They went back to their life. "
            "But the life they went back to has a different texture now — "
            "ordinary things carry a weight they didn't before.\n\n"
            "Do not end on active danger. End on quiet, persistent unease. "
            "The threat is not present. It doesn't need to be.\n\n"
            "The final lines should imply the cycle continues — "
            "the job will be posted again, someone else will take it, "
            "someone else will get the rules. Not as a twist. As a fact."
        )
        if active_rules:
            lines.append("")
            lines.append(
                "RULES THAT MARKED THE NARRATOR (do not list these explicitly — "
                "show their residue in behavior, in reflexes, in what the narrator "
                "now avoids or checks or can't stop noticing):"
            )
            for r in active_rules:
                lines.append(f"- [{r['id']}] {r['name']}")

    return "\n".join(lines)


# ============================================================
# Act Writer
# ============================================================

def write_act(
    context: str,
    act_number: int,
    act_type: str,
    target_words: int,
) -> str:

    system = (
        "You are writing a single act of a long-form first-person horror story "
        "intended for spoken YouTube narration. This story will be approximately "
        "one hour long when complete. Your act must carry its full weight.\n\n"

        "FORMAT:\n"
        "- First person, past tense, conversational.\n"
        "- Written as if the narrator is recalling real events years later.\n"
        "- Grounded, specific, physical detail — smells, temperatures, sounds, "
        "textures. Not atmospheric abstraction.\n"
        "- The narrator does not know the full truth of what is happening.\n"
        "- Horror comes from the rules being real and consequential, "
        "not from monsters, gore, or supernatural explanation.\n\n"

        "VOICE RULES:\n"
        "- Never break the fourth wall or acknowledge story structure.\n"
        "- No foreshadowing phrases like 'that was my first mistake' or "
        "'looking back, I should have known'.\n"
        "- No moral lessons or tidy conclusions within the act.\n"
        "- The narrator rationalizes, dismisses, and misinterprets — "
        "this is essential and realistic. They are not a horror protagonist. "
        "They are a tired, financially stressed person trying to get through a shift.\n"
        "- Internal monologue should feel genuine — practical concerns, "
        "embarrassment at overreacting, self-doubt. Not cinematic dread.\n\n"

        "RULE HANDLING — CRITICAL:\n"
        "- A rule is introduced ONCE in Act 1 when the narrator reads the document. "
        "After that it lives in memory only.\n"
        "- When a rule becomes relevant, the narrator does NOT quote it verbatim. "
        "They recall a fragment, a feeling, the gist of it. "
        "Example: not 'Rule 4 stated: if your shadow behaves differently...' "
        "but 'something about shadows — don't go to the shed if — I couldn't "
        "remember the exact wording.'\n"
        "- Never explain why a rule exists. The narrator does not know. "
        "The listener does not know. It stays that way.\n"
        "- Rules are a cage, not a safety net. Following a rule should cost "
        "the narrator something — they have to leave someone, stay still while "
        "something passes, watch without intervening. Survival is not comfortable.\n\n"

        "THREAT RULES — CRITICAL:\n"
        "- The threat is NEVER seen directly or described clearly.\n"
        "- The threat NEVER physically touches the narrator.\n"
        "- The threat is NEVER explained, named, or given an origin.\n"
        "- What the narrator experiences is always at the edge of confirmation — "
        "something that could almost be explained away, but can't quite be.\n"
        "- No introduced characters unless they serve a structural purpose "
        "that continues through the rest of the story. "
        "The narrator should be isolated. Isolation is load-bearing.\n\n"

        "LENGTH RULES — CRITICAL:\n"
        "- You must write the full target word count. Do not stop early.\n"
        "- If you feel the act wrapping up before the target, zoom in further — "
        "slow down time, linger in the physical space, follow the narrator's "
        "thought process in more granular detail.\n"
        "- An act should feel like it earns its length, not pads it.\n\n"

        "OUTPUT RULE:\n"
        "- Output ONLY prose paragraphs separated by blank lines.\n"
        "- No act labels, headers, or metadata.\n"
        "- No markdown formatting of any kind.\n"
        "- PARAGRAPH LENGTH — CRITICAL: Every paragraph must be at least 3-4 sentences "
        "and at least 60 words. Do NOT write single-sentence paragraphs. Do NOT use "
        "dramatic one-liners as standalone paragraphs (e.g. 'Silence.' or 'I froze.' "
        "or 'It was gone.'). These must be folded into the surrounding paragraph. "
        "Short punchy lines belong inside longer paragraphs, not as their own blocks. "
        "The goal is 8-12 substantial paragraphs per act, not 40-60 fragments."
    )

    user = (
        f"{context}\n\n"
        f"TARGET LENGTH: approximately {target_words} words.\n"
        "Do not artificially cut off. Write until the act feels complete.\n\n"
        "Write this act now."
    )

    return call_llm(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.72,
        max_tokens=max(2500, target_words * 2),
    )

# ============================================================
# Word Target Calculator
# ============================================================

def get_target_words(act_number: int, act_type: str, total_acts: int) -> int:
    """
    Early acts (setup + first 2 rule acts): 550-600 words — grounding, no layering yet.
    Middle acts (rule acts with active rules layering): 700-800 words — escalation.
    Resolution act: 500-550 words — reflection, wind-down.
    Slight variation so no two acts feel identical in length.
    """
    import random

    if act_type == "setup":
        return random.randint(550, 600)
    elif act_type == "resolution":
        return random.randint(500, 550)
    elif act_number <= 4:
        # Early rule acts — shorter, one rule at a time, clean triggers
        return random.randint(560, 620)
    elif act_number <= 7:
        # Mid acts — active rules beginning to layer
        return random.randint(680, 750)
    else:
        # Late acts — full layering, maximum tension
        return random.randint(740, 820)

# ============================================================
# Main Orchestration
# ============================================================

def generate_full_story() -> Dict:
    """
    Master orchestration function.
    1. Calls idea generator to get story frame
    2. Initializes rules state
    3. Iterates through each act — write, TTS polish, summarize, update state
    4. Returns full script and all act texts
    """

    # ---- Step 1: Get story frame ----
    print("[IDEA] Generating story frame...", flush=True)
    story_frame = build_story_frame()

    place = story_frame["place"]
    narrator = story_frame["narrator"]
    acts = story_frame["acts"]
    rules_in_order = story_frame["rules_in_order"]
    total_acts = story_frame["act_count"]

    print(f"[IDEA] Place: {place['name']}", flush=True)
    print(f"[IDEA] Narrator: {narrator['first_name']}, {narrator['age']}", flush=True)
    print(f"[IDEA] Rules: {story_frame['rule_count']} | Acts: {total_acts}", flush=True)

    # ---- Step 2: Initialize rules state ----
    # All rules start as pending
    rules_state = {
        "established": [],
        "pending": [
            {
                "id": r["id"],
                "name": r["name"],
                "template": r["template"],
                "consequence_tone": r["consequence_tone"],
                "story_moment": r["story_moment"],
            }
            for r in rules_in_order
        ],
    }

    # ---- Step 3: Initialize tracking variables ----
    per_act_summaries: List[str] = []
    full_story_summary: Optional[str] = None
    locked_facts: Optional[str] = None
    full_script = ""
    act_texts: Dict[str, str] = {}

    # ---- Step 4: Write each act ----
    for act_def in acts:
        act_number = act_def["act_number"]
        act_type = act_def["type"]
        primary_rule = act_def.get("primary_rule")
        active_rules = act_def.get("active_rules", [])

        print(f"[ACT {act_number}/{total_acts}] Writing ({act_type})...", flush=True)

        # Calculate target word count
        target_words = get_target_words(act_number, act_type, total_acts)

        # Get recent prose (last 8 paragraphs) — used for acts 2-4 only
        recent_prose = ""
        if full_script and act_number <= 4:
            paragraphs = [
                p.strip()
                for p in re.split(r"\n\s*\n+", full_script)
                if p.strip()
            ]
            recent_prose = "\n\n".join(paragraphs[-8:])

        # Build context for this act
        context = build_act_context(
            act_number=act_number,
            act_type=act_type,
            primary_rule=primary_rule,
            active_rules=active_rules,
            rules_state=rules_state,
            per_act_summaries=per_act_summaries,
            full_story_summary=full_story_summary,
            recent_prose=recent_prose,
            narrator=narrator,
            place=place,
            total_acts=total_acts,
            locked_facts=locked_facts,
            full_script_so_far=full_script if act_number >= 5 else None,
        )

        # Write the act — retry once if it comes in more than 20% under target
        act_text = write_act(
            context=context,
            act_number=act_number,
            act_type=act_type,
            target_words=target_words,
        )

        actual_words = len(act_text.split())
        min_acceptable = int(target_words * 0.80)

        if actual_words < min_acceptable:
            print(
                f"[ACT {act_number}/{total_acts}] Too short "
                f"({actual_words} words, target {target_words}). Retrying...",
                flush=True,
            )
            retry_text = write_act(
                context=context,
                act_number=act_number,
                act_type=act_type,
                target_words=target_words,
            )
            retry_words = len(retry_text.split())
            # Take whichever attempt is longer
            if retry_words > actual_words:
                act_text = retry_text
                print(
                    f"[ACT {act_number}/{total_acts}] Retry accepted "
                    f"({retry_words} words).",
                    flush=True,
                )
            else:
                print(
                    f"[ACT {act_number}/{total_acts}] Retry not longer, "
                    f"keeping original ({actual_words} words).",
                    flush=True,
                )

        # TTS polish
        print(f"[ACT {act_number}/{total_acts}] Polishing for TTS...", flush=True)
        act_text = tts_polish_pass(act_text, enabled=True)

        # Store act text
        act_key = f"act_{act_number}"
        act_texts[act_key] = act_text
        full_script += ("\n\n" if full_script else "") + act_text

        # Skip summarizer for resolution act — story is complete
        if act_type == "resolution":
            print(f"[ACT {act_number}/{total_acts}] Complete (resolution).", flush=True)
            break

        # Summarize and update rules state
        print(f"[ACT {act_number}/{total_acts}] Summarizing...", flush=True)
        summary_result = summarize_and_update_rules(
            act_text=act_text,
            act_number=act_number,
            primary_rule=primary_rule,
            rules_state=rules_state,
            existing_per_act_summaries=per_act_summaries,
            existing_full_story_summary=full_story_summary,
        )

        # Update tracking state
        rules_state = summary_result["rules_state"]

        # Acts 2-4: keep per-act summaries. Acts 5+: full script passed directly,
        # rolling summary no longer needed.
        if act_number <= 4:
            per_act_summaries.append(summary_result["act_summary"])

        # Generate locked facts exactly once after act 1 completes
        if act_number == 1 and locked_facts is None:
            print("[ACT 1] Extracting locked facts...", flush=True)
            locked_facts = generate_locked_facts(
                act_text=act_text,
                narrator=narrator,
                place=place,
            )
            print("[ACT 1] Locked facts extracted.", flush=True)

        print(f"[ACT {act_number}/{total_acts}] Done.", flush=True)

    return {
        "story_frame": story_frame,
        "act_texts": act_texts,
        "full_script": full_script,
    }

# ============================================================
# Visual Chunk Builder
# ============================================================

def build_visual_chunks(paragraph_count: int) -> List[Dict]:
    """
    Split paragraphs into visual chunks for image timing.
    Base size: 3 paragraphs.
    Remainder 1: last chunk becomes 4.
    Remainder 2: first and last chunks become 4.
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
            chunks.append(indices[i:i + 4])
            break
        chunks.append(indices[i:i + 3])
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

# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    from datetime import datetime

    # ---- Run folder setup ----
    RUNS_ROOT = Path(__file__).resolve().parents[2] / "runs"
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = RUNS_ROOT / run_id

    script_dir = run_dir / "script"
    paragraph_dir = script_dir / "paragraphs"
    acts_dir = script_dir / "acts"

    script_dir.mkdir(parents=True, exist_ok=True)
    paragraph_dir.mkdir(parents=True, exist_ok=True)
    acts_dir.mkdir(parents=True, exist_ok=True)

    # ---- Generate ----
    result = generate_full_story()
    full_script = result["full_script"].strip()
    story_frame = result["story_frame"]
    act_texts = result["act_texts"]

    # ---- Write story frame ----
    frame_path = script_dir / "story_frame.json"
    frame_path.write_text(
        json.dumps(story_frame, indent=2),
        encoding="utf-8",
    )

    # ---- Write individual acts ----
    for act_key, act_text in act_texts.items():
        act_path = acts_dir / f"{act_key}.txt"
        act_path.write_text(act_text.strip(), encoding="utf-8")

    # ---- Write full script ----
    full_script_path = script_dir / "full_script.txt"
    full_script_path.write_text(full_script, encoding="utf-8")

    # ---- Split into paragraphs ----
    raw_paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n+", full_script)
        if p.strip()
    ]

    # ---- Merge short paragraphs into preceding paragraph ----
    # Prevents single-sentence fragments from becoming their own TTS files and image chunks.
    MIN_PARAGRAPH_WORDS = 40
    paragraphs = []
    for p in raw_paragraphs:
        if paragraphs and len(p.split()) < MIN_PARAGRAPH_WORDS:
            paragraphs[-1] = paragraphs[-1] + " " + p
        else:
            paragraphs.append(p)

    print(f"[SCRIPT] Paragraphs before merge: {len(raw_paragraphs)}", flush=True)
    print(f"[SCRIPT] Paragraphs after merge:  {len(paragraphs)}", flush=True)

    for idx, paragraph in enumerate(paragraphs):
        p_path = paragraph_dir / f"p{idx:03d}.txt"
        p_path.write_text(paragraph, encoding="utf-8")

    paragraph_index = [
        {
            "paragraph_id": idx,
            "filename": f"p{idx:03d}.txt",
            "text": paragraphs[idx],
        }
        for idx in range(len(paragraphs))
    ]

    paragraph_index_path = script_dir / "paragraph_index.json"
    paragraph_index_path.write_text(
        json.dumps(
            {
                "paragraph_count": len(paragraphs),
                "paragraphs": paragraph_index,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # ---- Visual chunk plan ----
    visual_chunks = build_visual_chunks(len(paragraphs))

    visual_chunks_path = script_dir / "visual_chunks.json"
    visual_chunks_path.write_text(
        json.dumps(
            {
                "total_paragraphs": len(paragraphs),
                "base_chunk_size": 3,
                "chunks": visual_chunks,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\n[SCRIPT] Run complete: {run_dir.resolve()}", flush=True)
    print(f"[SCRIPT] Total acts: {len(act_texts)}", flush=True)
    print(f"[SCRIPT] Total paragraphs: {len(paragraphs)}", flush=True)
    print(f"[SCRIPT] Estimated runtime: ~{len(full_script.split()) // 130} minutes", flush=True)