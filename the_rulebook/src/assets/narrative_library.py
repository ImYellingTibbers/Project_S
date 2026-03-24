"""
narrative_library.py

Per-story randomization pools for the Rulebook pipeline.
One item from each list is selected per story run and injected into the prompt.
Never include quoted example phrases — the LLM will copy them verbatim.
"""

from __future__ import annotations
import random
from typing import List


# ============================================================
# Opening Approaches
# One is picked per story and replaces the A/B/C option block
# in the setup directive. Described as strategy, never example.
# ============================================================

OPENING_APPROACHES: List[str] = [
    # Financial pressure first
    (
        "Open with the specific financial pressure that made this job the only option — "
        "the dollar amount, the deadline, the thing that would fall apart without this income. "
        "Introduce the place through the narrator's desperation. They arrive looking for "
        "relief, not trouble. The building registers as a solution before it registers as "
        "anything else. Let the financial situation shape every first impression."
    ),
    # First wrong sensory detail
    (
        "Open with a single sensory detail the narrator registered as wrong on arrival — "
        "not identified, not named, just noted and filed. Something that didn't belong to "
        "the category this place should occupy. Let the building assemble itself around "
        "that first discrepancy as the narrator works to explain it away. "
        "The detail itself should be mundane. The wrongness is in its placement."
    ),
    # The handoff person
    (
        "Open with the person who completed the handoff — not their appearance, "
        "but their manner and their exit. What they did. What they didn't do. "
        "The speed with which they left. One specific thing they said or failed to say "
        "that the narrator only understood later. Let the place arrive through the gap "
        "that person left behind. Their absence is the first thing the narrator has to manage."
    ),
    # Mid-action arrival
    (
        "Open with the narrator already inside, already working, already several minutes "
        "into the first task. No arrival scene — the listener catches up as the narrator does. "
        "Context and backstory arrive through internal voice while their hands are occupied. "
        "The place assembles itself through motion rather than description. "
        "The narrator is too focused on the task to frame what they've walked into."
    ),
    # Gap between expectation and reality
    (
        "Open on the gap between what the narrator expected and what they found. "
        "Something specific about the place that contradicted the job listing, the phone "
        "interview, or the mental picture they'd constructed beforehand. Not sinister — "
        "just off. The narrator tries to revise their expectation to fit the reality. "
        "The place resists easy revision."
    ),
    # Something written before the shift
    (
        "Open with something the narrator encountered in writing before the shift began — "
        "a sign, a notice, a posted policy, a prior worker's note left somewhere visible. "
        "Something that should have been routine but left an unanswered question "
        "they carried through the front door. Let that question sit unanswered. "
        "The narrator doesn't pursue it. They file it and get to work."
    ),
    # The internal story they told themselves
    (
        "Open with the story the narrator told themselves to justify taking this job — "
        "the rationalizations, the minimizations, what they consciously decided not to "
        "think about. Let that internal narrative carry the opening paragraphs, and let "
        "the place begin quietly contradicting it before anything unusual has happened. "
        "The narrator's self-reassurance is the first thing the story undermines."
    ),
    # Last ordinary moment before arrival
    (
        "Open with the last ordinary thing the narrator did before the shift — something "
        "unremarkable that felt unremarkable at the time. Then arrive at the place. "
        "The contrast between that ordinary moment and the first impression of the building "
        "is the opening beat. Not dramatic. Just the seam between their regular life "
        "and this one. Let the narrator notice it briefly, then get to work."
    ),
    # The most vivid memory
    (
        "Open with the single most physically persistent memory the narrator has of "
        "walking in for the first time — not the most important detail, just the one "
        "their memory keeps returning to involuntarily. Why that particular thing stuck "
        "is part of what gets unpacked. Let the rest of the arrival build around the "
        "question of why that image is the one that survived everything else."
    ),
    # Evidence of the previous occupant
    (
        "Open with evidence that someone was here before the narrator — not explained, "
        "just present. Something left behind that implies the previous person's departure "
        "didn't allow for a complete cleanup. Let the narrator construct a comfortable, "
        "ordinary explanation for it. The explanation should feel plausible. "
        "The narrator believes it. Move on."
    ),
    # The threshold moment
    (
        "Open on the threshold moment — the specific sensory shift between outside and "
        "inside on the first entry. What the building does to sound, temperature, light, "
        "or smell the moment the narrator crosses in. Let that threshold carry weight "
        "without explanation. The narrator registers the change, attributes it to "
        "something structural or practical, and keeps moving."
    ),
    # The approach
    (
        "Open during the approach — the narrator in transit toward the place for the "
        "first time. What they were thinking about. What they noticed about the neighborhood, "
        "the parking, the exterior. Let the building's first impression arrive gradually "
        "through approach, not in a single establishing moment. Arrival is earned, not given."
    ),
]


# ============================================================
# Rules Document Handoff Methods
# One is picked per story and replaces the triple-option block
# in the setup directive.
# ============================================================

HANDOFF_METHODS: List[str] = [
    (
        "The rules are left on the workstation by whoever had the previous shift — "
        "dropped without explanation, no ceremony. That person is already at the exit "
        "before the narrator can ask a question. The rules are just there."
    ),
    (
        "The rules arrive in a sealed envelope with the narrator's name written on it, "
        "left with the keys or at the front desk. No cover note inside. "
        "The envelope was clearly prepared in advance — as if someone knew the "
        "narrator was coming and expected them to find it without guidance."
    ),
    (
        "The rules are handwritten in a logbook that was left open to the right page. "
        "The entries before them are ordinary — routine shift logs in normal handwriting. "
        "The rules appear mid-page, in different handwriting, as if added by someone "
        "who wasn't the original author of the logbook."
    ),
    (
        "The rules are taped inside a cabinet, a drawer, or behind a door — not displayed, "
        "found only because the narrator was looking for something else. "
        "Handwritten, with corrections. Some items are crossed out and rewritten "
        "in a different hand or different ink, as if the original version needed revision."
    ),
    (
        "The rules are printed and laminated, mounted near the station or equipment "
        "the narrator will spend the most time at. No title. Just numbered items "
        "formatted like a standard safety checklist. The laminate is worn at the "
        "edges — they have been there long enough to fade."
    ),
    (
        "The rules arrive as a text or written message from whoever handles the hiring — "
        "sent the night before or the morning of the first shift, with no framing or "
        "explanation attached. Just the list and a short line below it. "
        "The narrator assumed it was a liability formality."
    ),
    (
        "The rules are recited aloud by the person completing the handoff — not handed "
        "over as a document, just spoken quickly from memory while they're doing "
        "something else. The narrator has to write them down themselves as they go. "
        "The person reciting doesn't slow down, doesn't explain, doesn't confirm "
        "the narrator got everything right."
    ),
    (
        "The rules are found folded and tucked inside another document — the employee "
        "manual, a binder of procedures, a health and safety packet. Between two sections "
        "with no obvious relation to each other. No indication of who put them there or "
        "when. The document they're inserted into looks old."
    ),
    (
        "The rules are written on a whiteboard or dry-erase surface in the break room "
        "or back office — not permanent, but written clearly, as if updated regularly. "
        "The narrator notices them while looking for somewhere to put their bag. "
        "No one mentions them during the handoff."
    ),
    (
        "The rules come attached to the end of the standard onboarding paperwork — "
        "stapled on as a final page, unnumbered in the packet's sequence, formatted "
        "differently from everything before them. Easy to miss. "
        "The narrator almost didn't read them."
    ),
]


# ============================================================
# Resolution Ending Types
# One is picked per story and anchors the final act's closing beat.
# ============================================================

RESOLUTION_ENDINGS: List[str] = [
    (
        "ENDING TYPE FOR THIS STORY — close on an involuntary behavior the narrator "
        "developed without choosing. Something they now do automatically in environments "
        "that share any quality with that place. Not a ritual, not deliberate — "
        "a reflex that formed without their permission. They've noticed it. "
        "They haven't stopped it."
    ),
    (
        "ENDING TYPE FOR THIS STORY — close on a place in the narrator's ordinary life "
        "they can no longer enter without a specific internal cost. Not paralysis, not "
        "fear — just a recalibration that takes a moment every time. They've adjusted "
        "their routes or habits around it. The adjustment has become invisible to them."
    ),
    (
        "ENDING TYPE FOR THIS STORY — close on a sensory trigger: something specific "
        "and ordinary that returns the narrator to the shift when it appears in daily "
        "life. They don't dwell. It arrives, lasts a few seconds, and they move on. "
        "It has happened enough times that it no longer surprises them."
    ),
    (
        "ENDING TYPE FOR THIS STORY — close on a relationship that is different now "
        "because the narrator couldn't explain what happened. Someone they're more "
        "careful around, or closer to, because of what the experience made clear. "
        "Not dramatic. A small permanent shift in the quality of that one connection."
    ),
    (
        "ENDING TYPE FOR THIS STORY — close on a compulsive check the narrator now "
        "performs in unfamiliar environments. Not because they're afraid — because "
        "they need to confirm something specific before they can settle. "
        "The check takes seconds. They do it every time. "
        "They've stopped noticing that they do."
    ),
    (
        "ENDING TYPE FOR THIS STORY — close on something the narrator no longer does "
        "that they used to do before. A habit, a small ordinary pleasure that doesn't "
        "work the same way anymore. They don't grieve it. They've simply stopped trying. "
        "The absence has filled in the way scar tissue fills in."
    ),
    (
        "ENDING TYPE FOR THIS STORY — close on evidence, encountered incidentally in "
        "daily life, that the cycle continues without the narrator. Not a reveal. "
        "Not a twist. A fact they encounter and absorb the way they absorb other "
        "ordinary facts. The place is still there. Someone else is there now."
    ),
    (
        "ENDING TYPE FOR THIS STORY — close on a moment where the narrator is in a "
        "completely ordinary situation and something normal briefly registers as not "
        "normal. They catch it. They evaluate it. It passes. The act of catching and "
        "evaluating has become so practiced that it no longer interrupts what they "
        "were doing."
    ),
]


# ============================================================
# Side Character Name Pool
# A subset is sampled per story and included in every act's context.
# The LLM draws from this pool when it needs to name a character.
# Consistent pool across all acts allows characters to recur.
# ============================================================

_ALL_NAMES: List[str] = [
    # Male
    "Arlen", "Benji", "Cal", "Darek", "Edison", "Felix", "Garrett", "Hector",
    "Ira", "Jerome", "Kenji", "Lyle", "Maddox", "Nate", "Obie", "Pavel",
    "Quincy", "Reuben", "Sergio", "Tobias", "Vince", "Weston", "Yusuf",
    "Abel", "Boyd", "Clark", "Dillard", "Efrem", "Glenn", "Harvey",
    "Ivan", "Jules", "Kurt", "Marcus", "Ned", "Pell", "Rowan", "Samit",
    "Tad", "Uri", "Vaughn", "Walt", "Xander", "Zeb", "Alton", "Birch",
    "Crane", "Dex", "Emmet", "Fitch", "Gord", "Hal", "Idris", "Jasper",
    "Kaz", "Lorne", "Mort", "Nim", "Oren", "Pryce", "Rand", "Silas",
    "Theron", "Uwe", "Vito", "Ward", "Yates", "Zane",
    # Female
    "Ada", "Bette", "Cassie", "Denise", "Elma", "Fran", "Gloria", "Hattie",
    "Irene", "Josie", "Kira", "Luz", "Mona", "Nessa", "Olga", "Petra",
    "Rosie", "Selma", "Trudy", "Una", "Vera", "Willa", "Yolanda",
    "Alma", "Bev", "Connie", "Dawn", "Edna", "Flora", "Greta", "Helen",
    "Ines", "June", "Kay", "Lena", "Mae", "Norma", "Prue", "Rae",
    "Stella", "Tam", "Ula", "Val", "Winnie", "Zara", "Agnes", "Bea",
    "Cleo", "Dora", "Effie", "Gwen", "Hilde", "Ilse", "Jen", "Kit",
    "Loretta", "Midge", "Nell", "Opal", "Pearl", "Rue", "Sable", "Tess",
    "Ursa", "Viv", "Wren", "Yael",
]


def sample_names(n: int = 12) -> List[str]:
    """Return n randomly sampled names for injection into act context."""
    return random.sample(_ALL_NAMES, min(n, len(_ALL_NAMES)))


def pick_opening_approach() -> str:
    return random.choice(OPENING_APPROACHES)


def pick_handoff_method() -> str:
    return random.choice(HANDOFF_METHODS)


def pick_resolution_ending() -> str:
    return random.choice(RESOLUTION_ENDINGS)
