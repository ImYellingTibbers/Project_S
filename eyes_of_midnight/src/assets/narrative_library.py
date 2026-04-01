"""
narrative_library.py — Eyes of Midnight

Per-story randomization pools. One item from each list is selected per story run
and injected into the relevant prompt. No example phrases — describe intent only.
"""

from __future__ import annotations
import random
from typing import List


# ============================================================
# Hook Approaches
# Replaces the static "first paragraph of a long Reddit post" framing.
# Varies WHY the narrator is posting and what anchors the opening.
# ============================================================

HOOK_APPROACHES: List[str] = [
    # Triggered by a recent reminder
    (
        "The narrator is writing because something recently reminded them of the event — "
        "a sound, a place, an image they passed. Open with that trigger and what it "
        "brought back. Then establish when and where the events actually happened."
    ),
    # Long silence breaking
    (
        "The narrator has not talked about this — not to anyone. Open with the fact of "
        "that silence and what is making them break it now. Not drama, just the decision "
        "to finally put it somewhere."
    ),
    # Someone else's similar experience
    (
        "The narrator recently came across someone else's account of something that "
        "matched what happened to them — a post, a story, a conversation. That recognition "
        "is why they're writing. Open with that moment of seeing their own experience "
        "reflected somewhere unexpected."
    ),
    # The ordinary life as anchor
    (
        "Open with where the narrator was in their life at the time — the specific job, "
        "routine, or period — before anything unusual enters the picture. Ground the "
        "listener in that normalcy. The events arrive from inside an ordinary life, "
        "not outside it."
    ),
    # The place as anchor
    (
        "Open with the kind of place this happened in — its character, what it was "
        "used for, what brought the narrator there. Not named, just its texture. "
        "The place should feel familiar and unremarkable before anything shifts."
    ),
    # Can't explain it, sharing anyway
    (
        "The narrator has thought about this for a long time and still doesn't have an "
        "explanation. Open with that admission — not for mystery, but because it's "
        "simply true. They've sat with the not-knowing. They're sharing it anyway."
    ),
    # A physical detail that stuck
    (
        "Open with a single physical detail the narrator remembers with unusual clarity "
        "from that time — not the most important thing, just the one their memory keeps "
        "returning to. Establish when and why they were there. Let the detail be the hook."
    ),
    # Tried to move on, mostly succeeded
    (
        "The narrator has mostly put this behind them. They're not in distress. "
        "Open with that calm distance — the fact that life continued and mostly normalized. "
        "Then explain why they're sitting down to write it out now after all that time."
    ),
    # Something they noticed changing in themselves
    (
        "Open with something the narrator noticed changing in themselves after it happened — "
        "a habit, a reaction, a preference they couldn't fully explain. That change is "
        "why the story stayed with them. Establish the time and place from there."
    ),
    # Specific time in their life
    (
        "Open by anchoring this in a specific chapter of the narrator's life — "
        "a particular job, a particular living situation, a particular age. "
        "Not the events yet, just the period. The listener should understand exactly "
        "where this person was before anything went wrong."
    ),
]


# ============================================================
# Act 1 Signal Types
# Replaces the fixed "one concrete action by another person + freeze/flee/lock/watch/leave"
# mandate. Varies the TYPE of first anomaly across runs.
# ============================================================

ACT_1_SIGNAL_TYPES: List[str] = [
    # Behavioral anomaly — another person
    (
        "ACT 1 SIGNAL TYPE — BEHAVIORAL:\n"
        "The first signal comes from another person doing something that is socially or "
        "physically off. Not aggressive. Not explained. Just wrong in a way that registers "
        "in the body before it registers in the mind. One specific action. "
        "The narrator notices it, tries to account for it, and mostly succeeds. "
        "The discomfort should feel minor and dismissible at the time."
    ),
    # Environmental anomaly — the place itself
    (
        "ACT 1 SIGNAL TYPE — ENVIRONMENTAL:\n"
        "The first signal is something about the place that doesn't match what should "
        "be there. An object out of position, a door in the wrong state, something "
        "present that shouldn't be or absent that should. "
        "The narrator notices it with mild curiosity, constructs a reasonable explanation, "
        "and moves on. The explanation should be plausible."
    ),
    # Sensory anomaly
    (
        "ACT 1 SIGNAL TYPE — SENSORY:\n"
        "The first signal is something the narrator perceives — hears, smells, or "
        "physically feels — that has no immediate explanation. Not dramatic. "
        "Not frightening yet. Just specific enough to note and strange enough to "
        "not quite fit any obvious cause. The narrator files it and continues."
    ),
    # Absence anomaly
    (
        "ACT 1 SIGNAL TYPE — ABSENCE:\n"
        "The first signal is something missing — a response that doesn't come, "
        "a person who should be present who isn't, a sound that stops at the wrong "
        "moment, a reply that never arrives. The narrator waits for the normal thing "
        "to happen. It doesn't. They find a way to explain it and keep moving."
    ),
    # Coincidence anomaly
    (
        "ACT 1 SIGNAL TYPE — COINCIDENCE:\n"
        "The first signal is specificity that seems too precise to be random — "
        "something connected to the narrator personally appears somewhere it shouldn't "
        "be, or something happens twice in a way that feels like pattern but could "
        "still be chance. The narrator almost dismisses it. Almost."
    ),
    # Timing anomaly
    (
        "ACT 1 SIGNAL TYPE — TIMING:\n"
        "The first signal is about timing — something happens at the exact wrong moment, "
        "or something that should take a certain amount of time doesn't, or a sequence "
        "of events implies someone knew something they couldn't have known yet. "
        "The narrator notices the timing is off. They try to reconstruct how it could "
        "have happened normally. It almost works."
    ),
]


# ============================================================
# Act 5 Ending Types
# Replaces the fixed "behavioral change + avoidance + unresolved detail + can't shake it"
# template. Varies how the aftermath is framed.
# ============================================================

ACT_5_ENDING_TYPES: List[str] = [
    # Automatic behavior
    (
        "ACT 5 ENDING TYPE — AUTOMATIC BEHAVIOR:\n"
        "End on something the narrator now does without deciding to — a physical check, "
        "a small action, a habit that formed in the aftermath and never left. "
        "They do it without thinking. They've stopped questioning it. "
        "The final image is that behavior happening in an ordinary moment."
    ),
    # The avoided thing
    (
        "ACT 5 ENDING TYPE — AVOIDANCE:\n"
        "End on a specific kind of place, person-type, or situation the narrator "
        "no longer enters or engages with. Not dramatically — just practically, "
        "the way you stop using a road that's always backed up. "
        "They've routed their life around something without making a decision about it."
    ),
    # The recurring sensory intrusion
    (
        "ACT 5 ENDING TYPE — SENSORY INTRUSION:\n"
        "End on something ordinary that still briefly misreads before the narrator "
        "corrects themselves. A sound, a smell, a particular quality of light. "
        "It lasts a second. They correct. They've gotten good at the correction. "
        "The final image is that moment of misread and recovery in an everyday context."
    ),
    # The detail that doesn't fit
    (
        "ACT 5 ENDING TYPE — THE LOOSE END:\n"
        "End on one specific detail from the events that has no explanation — "
        "not the most important thing, just the one that surfaces sometimes when "
        "the narrator isn't looking for it. They've accepted they won't understand it. "
        "It comes up anyway. The final image is that detail arriving uninvited."
    ),
    # A shifted relationship
    (
        "ACT 5 ENDING TYPE — RELATIONSHIP CHANGE:\n"
        "End on a relationship that's different now because of what the narrator learned "
        "about paying attention. Closer to someone they used to take for granted, "
        "or more careful around someone they used to trust without question. "
        "Not a lesson. Just a permanent small adjustment in how they occupy "
        "the space next to that person."
    ),
    # The open question
    (
        "ACT 5 ENDING TYPE — THE QUESTION:\n"
        "End on a question the narrator never got answered — not a mystery hook, "
        "just a genuine gap. Something they would have needed to know to fully understand "
        "what happened, and that they never found out. They've made peace with not knowing. "
        "The question still surfaces. The final image is the narrator encountering it again."
    ),
    # The thing they still do
    (
        "ACT 5 ENDING TYPE — THE RETAINED HABIT:\n"
        "End on something the narrator kept from the experience — a practice, "
        "a small precaution, a way of paying attention they didn't have before. "
        "Not presented as wisdom. Just as something that stayed. They do it still. "
        "The final image is that practice in an ordinary moment."
    ),
]


# ============================================================
# Side Character Name Pool
# Sampled per story, injected into each act context.
# Consistent pool across all acts so characters can recur.
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


# ============================================================
# Antagonist Relationship Types
# Picked once per story. Injected into concept generation, the act outline,
# and all act contexts so the threat dynamic stays coherent across the whole story.
# ============================================================

ANTAGONIST_RELATIONSHIP_TYPES: List[str] = [
    # Stranger with personal knowledge
    (
        "THREAT DYNAMIC — STRANGER WITH PERSONAL KNOWLEDGE:\n"
        "The threat comes from someone the narrator does not recognize or cannot place. "
        "The horror is that this person behaves as if they have specific, personal "
        "information about the narrator. There is no obvious explanation for how. "
        "The narrator cannot find a prior connection no matter how far back they look."
    ),
    # Peripheral acquaintance
    (
        "THREAT DYNAMIC — PERIPHERAL ACQUAINTANCE:\n"
        "The threat is connected to someone the narrator knows, or has known, in a "
        "limited and casual way — someone from the edge of their regular life. "
        "Not close. The narrator has to reckon with how much access this person "
        "had without the narrator ever registering it."
    ),
    # Past connection resurfacing
    (
        "THREAT DYNAMIC — PAST CONNECTION:\n"
        "The threat is linked to someone or something from an earlier chapter of the "
        "narrator's life — a period, a place, or a relationship they had moved past. "
        "The resurfacing is specific enough to be intentional. "
        "The connection was never as finished as the narrator believed."
    ),
    # Systemic or coordinated
    (
        "THREAT DYNAMIC — SYSTEMIC OR COORDINATED:\n"
        "The threat does not resolve to a single identifiable person. "
        "The pattern implies access, coordination, or institutional knowledge "
        "the narrator cannot map to one source. Each time they think they've "
        "located the center, the threat continues from somewhere else."
    ),
    # Ambiguous — one person or several
    (
        "THREAT DYNAMIC — AMBIGUOUS SOURCE:\n"
        "The narrator cannot determine whether this is one person or multiple people, "
        "or whether the people involved are connected. Evidence points in different "
        "directions. The narrator leaves this story not knowing. "
        "That uncertainty is permanent, not a mystery to be resolved."
    ),
    # Someone trusted
    (
        "THREAT DYNAMIC — BREACH OF TRUST:\n"
        "The threat involves someone the narrator had reason to trust — "
        "not necessarily a close relationship, but someone in a position "
        "where trust was reasonable and given. The story is partly about "
        "what it means to have extended that trust and to have been wrong."
    ),
]


# ============================================================
# Act 4 Mistake Types
# Replaces the fixed "ONE failed attempt to regain control" mandate.
# Describes the CATEGORY of mistake — leaves the how entirely to the LLM.
# ============================================================

ACT_4_MISTAKE_TYPES: List[str] = [
    # Misplaced trust
    (
        "ACT 4 MISTAKE TYPE — MISPLACED TRUST:\n"
        "The narrator seeks help, verification, or support from someone they "
        "believed was safe to tell. That disclosure doesn't resolve anything — "
        "it either does nothing, introduces a new problem, or lands in a way "
        "the narrator didn't anticipate. They end this act more exposed than before."
    ),
    # Official channel
    (
        "ACT 4 MISTAKE TYPE — OFFICIAL CHANNEL:\n"
        "The narrator takes the situation somewhere formal — a process, a system, "
        "a person whose role it is to handle this kind of thing. "
        "The response is inadequate, dismissive, or creates unintended consequences. "
        "The act of reporting changes the narrator's position without making them safer."
    ),
    # Direct confrontation
    (
        "ACT 4 MISTAKE TYPE — CONFRONTATION:\n"
        "The narrator moves directly toward the source of the threat — "
        "addresses it, challenges it, or tries to cut it off at its origin. "
        "This confirms to the threat that the narrator knows and is acting. "
        "The dynamic shifts in a direction the narrator didn't account for."
    ),
    # Documentation attempt
    (
        "ACT 4 MISTAKE TYPE — DOCUMENTATION:\n"
        "The narrator tries to create a record — to capture, prove, or preserve "
        "evidence of what is happening. Something about that attempt fails or "
        "works against them. The evidence doesn't hold, isn't believed, or the "
        "act of documenting reveals something the narrator wasn't ready to reveal."
    ),
    # Evasion that gave information away
    (
        "ACT 4 MISTAKE TYPE — EVASION:\n"
        "The narrator tries to remove themselves from the situation — "
        "changes a pattern, leaves a place, cuts off a contact. "
        "The act of evading gives something away: that the narrator knows, "
        "where they went instead, or that the threat is not fixed to a location."
    ),
]


def sample_names(n: int = 12) -> List[str]:
    """Return n randomly sampled names for injection into act context."""
    return random.sample(_ALL_NAMES, min(n, len(_ALL_NAMES)))


def pick_hook_approach() -> str:
    return random.choice(HOOK_APPROACHES)


def pick_act1_signal_type() -> str:
    return random.choice(ACT_1_SIGNAL_TYPES)


def pick_act4_mistake_type() -> str:
    return random.choice(ACT_4_MISTAKE_TYPES)


def pick_act5_ending_type() -> str:
    return random.choice(ACT_5_ENDING_TYPES)


def pick_antagonist_relationship() -> str:
    return random.choice(ANTAGONIST_RELATIONSHIP_TYPES)
