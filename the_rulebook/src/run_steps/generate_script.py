from __future__ import annotations

import os
import json
import re
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv
import requests

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"
sys.path.insert(0, str(ASSETS_DIR))

from idea_generator import build_story_frame
from narrative_library import (
    sample_names,
    pick_opening_approach,
    pick_handoff_method,
    pick_resolution_ending,
)

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
                timeout=180,
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

    # Final raise if all retries exhausted
    response.raise_for_status()

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
    name_pool: List[str],
    opening_approach: str = "",
    handoff_method: str = "",
    resolution_ending: str = "",
    prev_ending_beat: Optional[str] = None,
    variation_idx: int = 0,
) -> str:
    """
    Assembles the full context string passed into each act writing call.
    Acts 1-4: per-act summaries of all previous acts.
    Acts 5+: single rolling full-story summary.
    Always includes: last 8 paragraphs of prose + rules state.
    """

    lines = []

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
    if name_pool:
        lines.append(
            "SIDE CHARACTER NAMES — if this story requires named background characters, "
            "draw exclusively from this list: " + ", ".join(name_pool) + ".\n"
            "Do not invent names outside this list for any character who appears more "
            "than once or has dialogue. One-time background figures glimpsed briefly "
            "do not need names."
        )
        lines.append("")

    # ---- Summary context ----
    if act_number == 1:
        pass  # No prior context for the first act
    elif act_number <= 4:
        lines.append("PREVIOUS ACT SUMMARIES:")
        for i, summary in enumerate(per_act_summaries, start=1):
            lines.append(f"Act {i}: {summary}")
        lines.append("")
    else:
        lines.append("STORY SO FAR:")
        lines.append(full_story_summary or "Story is underway.")
        lines.append("")

    # ---- Recent prose (always present except act 1) ----
    if recent_prose:
        lines.append("RECENT PROSE (last 8 paragraphs — match this voice exactly):")
        lines.append(recent_prose)
        lines.append("")

    # ---- Rules state ----
    established = rules_state.get("established", [])
    pending = rules_state.get("pending", [])

    if established:
        lines.append("RULES ESTABLISHED SO FAR (narrator has encountered these):")
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
            "OPENING PARAGRAPH — THIS IS THE MOST IMPORTANT PARAGRAPH IN THE STORY:\n"
            "This story is being told by a real person recounting something that happened "
            "to them. Write the opening paragraph the way that person would actually begin "
            "talking — grounded in a specific memory, a specific pressure, or a specific "
            "detail. Not a description of the room. Not the furniture or the lighting. "
            "Whatever is most alive in this narrator's memory about arriving at this place.\n\n"
            f"OPENING STRATEGY FOR THIS STORY:\n{opening_approach}\n\n"
            "After the opening paragraph, establish the physical space — "
            "the narrator has just arrived for their first shift and is taking everything in. "
            "Describe the building, the equipment, the smell, the sounds, the light. "
            "Make it specific to this exact place and role. "
            "Details established here will pay off in later acts — the layout, the exits, "
            "the equipment, the specific quirks of this location.\n\n"
            "Weave the narrator's financial situation into their inner voice naturally — "
            "not as a monologue but as the undercurrent behind every observation. "
            "They need this job. That has to be felt, not stated.\n\n"
            f"THE RULES DOCUMENT ARRIVES THIS WAY:\n{handoff_method}\n"
            "The handoff should feel casual and slightly odd. "
            "No explanation is offered. No context is given. "
            "The narrator is left alone with a list they don't yet take seriously.\n\n"
            "The narrator reads the rules one by one. "
            "Present each rule as numbered, typed or handwritten, oddly specific. "
            "The narrator reacts to each — confusion, mild unease, dismissal, "
            "an internal joke. They are not scared yet. They think it's eccentric "
            "workplace culture, previous employee superstition, or a prank.\n\n"
            "Nothing dangerous happens in this act. "
            "End with the narrator alone, shift beginning, rules set aside. "
            "The last beat should carry a quiet unease — not dread, just the feeling "
            "that something about this place is slightly off in a way they can't name. "
            "Do not name or describe this unease directly. "
            "Show it through a specific physical detail or action."
        )
        lines.append("")
        lines.append(
            "ALL RULES FOR THIS STORY (present these as the rules document, in order):\n"
            "IMPORTANT: Some rules contain bracketed placeholders such as "
            "[specific location], [specific warning sign], or [specific sound]. "
            "Before writing, replace every bracketed placeholder with a specific, "
            "concrete detail derived from this exact place and this narrator's role. "
            "The replacement must be grounded in what a real person in this building "
            "would actually notice and name — not horror tropes, not generic imagery. "
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
            lines.append("ACT DIRECTIVE:")
            lines.append(build_rule_act_directive(variation_idx, prev_ending_beat))

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
            "Write in scene, not in summary. Do not compress time with phrases like "
            "'Over the following months' or 'In the weeks after.' "
            "Every paragraph must be a specific moment the narrator is present inside. "
            "Reflection is shown through what they do and notice, not through telling.\n\n"
            "The narrator is functional. They went back to their life. "
            "But the life they went back to has a different texture now — "
            "ordinary things carry a weight they didn't before.\n\n"
            "Do not end on active danger. End on quiet, persistent unease. "
            "The threat is not present. It doesn't need to be.\n\n"
            "The final lines should imply the cycle continues — "
            "the job will be posted again, someone else will take it, "
            "someone else will get the rules. Not as a twist. As a fact.\n\n"
            f"{resolution_ending}\n\n"
            "The final paragraph must be specific and concrete — one image, one action, "
            "one detail that lands and stays. It should feel inevitable in retrospect "
            "but not telegraphed. This is the last thing the listener hears."
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
        "- The narrator NEVER explains what the rules mean, what the threat is, "
        "or what the experience has taught them. They do not arrive at conclusions. "
        "They survive and move on. Meaning is the listener's job, not the narrator's.\n"
        "- The narrator rationalizes, dismisses, and misinterprets — "
        "this is essential and realistic. They are not a horror protagonist. "
        "They are a tired, financially stressed person trying to get through a shift.\n"
        "- Internal monologue should feel genuine — practical concerns, "
        "embarrassment at overreacting, self-doubt. Not cinematic dread.\n"
        "- BANNED PHRASES — these have become lazy defaults and must not appear "
        "in any act, including the setup act: "
        "'I couldn't shake the feeling', "
        "'my heart hammered/pounded/raced', "
        "'my hands were trembling/shaking', "
        "'a metallic smell/scent', "
        "'the smell of pennies'. "
        "Find a physical response specific to this narrator and this moment. "
        "Every act of fear must be expressed differently.\n"
        "- BANNED ACT STRUCTURES — do not use these dramatic shapes:\n"
        "  * Narrator notices thing → dismisses it → notices again → recalls rule → complies. "
        "This is the default shape. It has already been used. Break it.\n"
        "  * Do not have the narrator stand still weighing options for more than one paragraph.\n"
        "  * Do not end two consecutive acts with the narrator deciding to document, "
        "record, or write down what happened.\n\n"

        "RULE HANDLING — CRITICAL:\n"
        "- A rule is introduced ONCE in Act 1 when the narrator reads the document. "
        "After that it lives in memory only.\n"
        "- When a rule becomes relevant, the narrator does NOT quote it verbatim. "
        "They recall a fragment, an impression, the gist of it — uncertain, partial, "
        "imprecise. The remembered version should feel like something retrieved "
        "under pressure, not recited from memory.\n"
        "- The rationalization phase — where the narrator tries to explain away what "
        "they are experiencing — must be brief. One paragraph maximum. "
        "The narrator dismisses it once, then the situation forces their hand. "
        "Do not let the narrator circle the same doubt for multiple paragraphs.\n"
        "- Never explain why a rule exists. The narrator does not know. "
        "The listener does not know. It stays that way.\n"
        "- Rules are a cage, not a safety net. Following a rule should cost "
        "the narrator something — they have to leave someone, stay still while "
        "something passes, watch without intervening. Survival is not comfortable.\n\n"

        "NARRATOR FACTS — TREAT AS IMMUTABLE:\n"
        "The narrator's name, age, family members and their names, financial situation, "
        "and personal history are established in the STORY CONTEXT above. "
        "These facts do not change between acts. "
        "A spouse named in act one is named the same thing in the resolution. "
        "A detail about a child, an illness, a hobby introduced early must remain "
        "consistent throughout. Do not invent new personal details that contradict "
        "or replace what is already established.\n\n"

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
        "- No markdown formatting of any kind."
    )

    user = (
        f"{context}\n\n"
        f"TARGET LENGTH: approximately {target_words} words.\n"
        "Do not artificially cut off. Write until the act feels complete.\n\n"
        "HARD CONSTRAINT: If this is a rule act, the narrator's rationalization of what "
        "they are experiencing must resolve within a single paragraph. After that one "
        "paragraph, the situation forces their hand. Do not extend doubt across multiple "
        "paragraphs. One dismissal, then action.\n\n"
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
# Banned Phrase Checker
# ============================================================

BANNED_PHRASES = [
    "couldn't shake the feeling",
    "could not shake the feeling",
    "heart hammered",
    "heart pounded",
    "heart raced",
    "hands were trembling",
    "hands were shaking",
    "metallic smell",
    "metallic scent",
    "smell of pennies",
    "scent of pennies",
]


def check_banned_phrases(act_text: str, act_number: int) -> list:
    found = [p for p in BANNED_PHRASES if p in act_text.lower()]
    if found:
        print(f"[ACT {act_number}] WARNING — banned phrases found: {found}", flush=True)
    return found


# ============================================================
# Rule Act Directive Builder
# ============================================================

def build_rule_act_directive(variation_idx: int, prev_ending_beat: Optional[str]) -> str:
    """Build a rule act directive centered on a specific structural variation.
    The variation is the frame, not an addendum — the model gets one coherent shape."""

    base = (
        "This act is built around the PRIMARY RULE above being triggered "
        "for the first time.\n\n"
        "SETUP: Begin with the narrator doing a specific mundane task at this place. "
        "Let normalcy breathe for several paragraphs before anything shifts. "
        "The longer the normal feels real, the harder the turn hits.\n\n"
    )

    variations = [
        # 0 — preemptive compliance
        (
            "CORE TENSION: The narrator senses something is wrong before they can "
            "identify what. They comply with the rule before the situation fully "
            "develops — preemptively, almost instinctively. The horror is in what "
            "they don't get to see. What was behind the door, around the corner, "
            "at the end of the hall — they will never know. End on that absence.\n\n"
            "NOTE: There is no hesitation scene. No weighing of options. "
            "The narrator acts, then understands what they just avoided. "
            "Realisation comes after compliance, not before."
        ),
        # 1 — near failure
        (
            "CORE TENSION: The narrator moves toward the wrong choice. They are "
            "seconds from breaking the rule when something — not supernatural, "
            "just physical reality — stops them. A sound. A smell. Something "
            "shifts in their peripheral vision. They correct. But the near-miss "
            "is the horror. They know now how close the margin is.\n\n"
            "NOTE: The narrator does not stand still weighing options. "
            "They are already moving in the wrong direction when the correction "
            "happens. Speed matters here. The act should feel like a near-accident."
        ),
        # 2 — rule vs urgent need
        (
            "CORE TENSION: Following the rule means the narrator cannot do "
            "something they urgently need to do. Not want — need. Check on "
            "something. Reach something. Leave. The rule and their instinct are "
            "directly opposed and both feel necessary. They choose the rule. "
            "It costs them something real.\n\n"
            "NOTE: The cost must be concrete and specific, not vague unease. "
            "Something they needed to do did not get done because of this rule. "
            "That consequence should be present in the act's final beat."
        ),
        # 3 — ambiguous trigger
        (
            "CORE TENSION: The narrator isn't sure this situation qualifies. "
            "The rule was written for something specific and this might be it "
            "or might be completely ordinary. They cannot tell. They have to "
            "decide without enough information, right now, because hesitating "
            "too long is its own kind of answer.\n\n"
            "NOTE: Do not resolve the ambiguity. The narrator chooses, survives, "
            "and still doesn't know if they were right. That unresolved "
            "uncertainty is what they carry out of this act."
        ),
        # 4 — perfect compliance, still witnesses
        (
            "CORE TENSION: The narrator follows the rule exactly. No hesitation, "
            "no mistakes. They do everything right. And they still see something "
            "they cannot explain. Compliance was not protection — it was just the "
            "minimum requirement to survive. There is more here than the rules "
            "account for.\n\n"
            "NOTE: What the narrator witnesses must be at the edge of confirmation "
            "— almost explainable, but not quite. The act ends with the narrator "
            "having done everything right and feeling worse for it."
        ),
    ]

    closing = (
        "BEFORE WRITING YOUR FINAL PARAGRAPH, confirm all three:\n"
        "1. The narrator is in a specific physical location doing a specific thing.\n"
        "2. The rule encounter has reached a definite outcome — do not end on waiting.\n"
        "3. One concrete thing has changed that the narrator carries into the next act."
    )

    directive = base + variations[variation_idx % len(variations)] + "\n\n" + closing

    if prev_ending_beat:
        directive += (
            f"\n\nPREVIOUS ACT ENDED WITH: {prev_ending_beat}\n"
            "Do NOT end this act the same way. Find a different final beat — "
            "a different physical action, a different emotional register, "
            "a different kind of silence."
        )

    return directive


# ============================================================
# Ending Beat Extractor
# ============================================================

def extract_ending_beat(act_text: str) -> str:
    """Return a 10-word-or-fewer description of how the act ends, for use as a
    prohibition in the next act so consecutive acts don't share the same final beat."""
    system = "You are a story analyst. Be extremely concise."
    user = (
        "In 10 words or fewer, describe the final emotional or physical note of this act. "
        "Focus on what the narrator does or perceives in the last paragraph — "
        "not the theme, the specific action or image.\n\n"
        f"ACT TEXT (last 300 words):\n{' '.join(act_text.split()[-300:])}"
    )
    try:
        return call_llm(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0,
            max_tokens=40,
        )
    except Exception:
        return ""


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
    full_script = ""
    act_texts: Dict[str, str] = {}
    prev_ending_beat: Optional[str] = None

    # Per-story random selections — picked once so they stay consistent across all acts
    import random
    variation_order = list(range(5))
    random.shuffle(variation_order)
    rule_act_count = 0  # tracks how many rule acts have been written

    name_pool = sample_names(12)
    opening_approach = pick_opening_approach()
    handoff_method = pick_handoff_method()
    resolution_ending = pick_resolution_ending()

    print(f"[STORY] Opening approach: {opening_approach[:60]}...", flush=True)
    print(f"[STORY] Handoff method: {handoff_method[:60]}...", flush=True)
    print(f"[STORY] Resolution ending: {resolution_ending[:60]}...", flush=True)
    print(f"[STORY] Name pool: {', '.join(name_pool)}", flush=True)

    # ---- Step 4: Write each act ----
    for act_def in acts:
        act_number = act_def["act_number"]
        act_type = act_def["type"]
        primary_rule = act_def.get("primary_rule")
        active_rules = act_def.get("active_rules", [])

        print(f"[ACT {act_number}/{total_acts}] Writing ({act_type})...", flush=True)

        # Determine structural variation index for rule acts
        if act_type == "rule":
            variation_idx = variation_order[rule_act_count % len(variation_order)]
            rule_act_count += 1
        else:
            variation_idx = 0

        # Calculate target word count
        target_words = get_target_words(act_number, act_type, total_acts)

        # Get recent prose (last 8 paragraphs)
        recent_prose = ""
        if full_script:
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
            name_pool=name_pool,
            opening_approach=opening_approach,
            handoff_method=handoff_method,
            resolution_ending=resolution_ending,
            prev_ending_beat=prev_ending_beat,
            variation_idx=variation_idx,
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
        banned = check_banned_phrases(act_text, act_number)
        needs_retry = actual_words < min_acceptable or bool(banned)

        if needs_retry:
            if actual_words < min_acceptable:
                print(
                    f"[ACT {act_number}/{total_acts}] Too short "
                    f"({actual_words} words, target {target_words}). Retrying...",
                    flush=True,
                )
            if banned:
                print(
                    f"[ACT {act_number}/{total_acts}] Retrying due to banned phrases...",
                    flush=True,
                )
            retry_text = write_act(
                context=context,
                act_number=act_number,
                act_type=act_type,
                target_words=target_words,
            )
            retry_words = len(retry_text.split())
            retry_banned = check_banned_phrases(retry_text, act_number)
            # Prefer retry if: cleaner phrases AND not shorter than original
            retry_better = len(retry_banned) < len(banned) or (
                not retry_banned and retry_words >= min_acceptable
            )
            if retry_better:
                act_text = retry_text
                print(
                    f"[ACT {act_number}/{total_acts}] Retry accepted "
                    f"({retry_words} words, {len(retry_banned)} banned phrases).",
                    flush=True,
                )
            else:
                print(
                    f"[ACT {act_number}/{total_acts}] Retry not better, "
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

        # Extract ending beat so the next act can avoid repeating it
        if act_type == "rule":
            print(f"[ACT {act_number}/{total_acts}] Extracting ending beat...", flush=True)
            prev_ending_beat = extract_ending_beat(act_text)
        else:
            prev_ending_beat = None

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

        if act_number <= 4:
            per_act_summaries.append(summary_result["act_summary"])
        else:
            full_story_summary = summary_result["full_story_summary"]

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
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n+", full_script)
        if p.strip()
    ]

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