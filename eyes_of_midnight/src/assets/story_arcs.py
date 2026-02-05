from __future__ import annotations

import random
from typing import Dict, List

# ============================================================
# Public API
# ============================================================

def get_random_story_arc() -> Dict[str, str]:
    """
    Returns a single randomly selected story arc definition.
    """
    if not STORY_ARCS:
        raise RuntimeError("STORY_ARCS is empty")

    return random.choice(STORY_ARCS)


# ============================================================
# Story Arc Definitions
# ============================================================

STORY_ARCS: List[Dict[str, str]] = [
    {
        "name": "Normalization of Access",
        "theme": "Access gained through politeness, help, and reasonable accommodation",

        "act_1_rules": (
            "Act 1 may only show minor boundary softening, favors, or access granted voluntarily. "
            "No proof, no confrontation, no surveillance, no certainty."
        ),
        "act_1_focus": (
            "Keys, permissions, routines, or access granted for reasonable reasons. "
            "The narrator rationalizes everything."
        ),

        "act_2_rules": (
            "Act 2 may show access being used more frequently or confidently. "
            "Still no explicit wrongdoing, no direct intrusion while observed, no admissions."
        ),
        "act_2_focus": (
            "The antagonist behaves as if access is assumed rather than requested. "
            "The narrator begins adjusting behavior in response."
        ),

        "act_3_rules": (
            "Act 3 may introduce personal cost and discomfort caused by that access. "
            "Still no explicit confrontation or proof."
        ),
        "act_3_focus": (
            "The narrator realizes access is shaping their decisions, routines, or sense of safety."
        ),

        "act_4_rules": (
            "Act 4 may include confrontation or an attempt to revoke access. "
            "Consequences escalate, but intent may remain unspoken."
        ),
        "act_4_focus": (
            "The narrator attempts to regain control and discovers access cannot be cleanly undone."
        ),

        "act_5_rules": (
            "Act 5 leaves access unresolved or permanently altered. "
            "No clean resolution or reassurance."
        ),
        "act_5_focus": (
            "The narrator lives with the knowledge that access still exists or could return."
        ),
    },

    {
        "name": "Routine Mapping",
        "theme": "Life patterns learned through casual observation",

        "act_1_rules": (
            "Act 1 may include only casual questions, coincidence-level observations, "
            "and socially acceptable interest. No tracking, no following."
        ),
        "act_1_focus": (
            "Small talk about schedules, habits, routes, preferences. "
            "Everything remains deniable."
        ),

        "act_2_rules": (
            "Act 2 may show pattern recognition without explicit surveillance. "
            "The antagonist knows things at the right time."
        ),
        "act_2_focus": (
            "Correct timing, anticipation, and convenience that feels too accurate."
        ),

        "act_3_rules": (
            "Act 3 introduces emotional cost from being anticipated. "
            "Still no proof of tracking."
        ),
        "act_3_focus": (
            "The narrator alters routines to test whether patterns are known."
        ),

        "act_4_rules": (
            "Act 4 may reveal failed attempts to escape or disrupt routines."
        ),
        "act_4_focus": (
            "The narrator realizes pattern changes do not restore privacy."
        ),

        "act_5_rules": (
            "Act 5 leaves the narrator permanently aware of being predictable."
        ),
        "act_5_focus": (
            "Normal life resumes, but routine feels exposed and unsafe."
        ),
    },

    {
        "name": "Subtle Replacement",
        "theme": "Personal items quietly substituted, improved, or corrected",

        "act_1_rules": (
            "Act 1 may include one or two minor item substitutions. "
            "Narrator assumes misplacement or mistake."
        ),
        "act_1_focus": (
            "Objects are familiar but slightly wrong. "
            "No indication of intent."
        ),

        "act_2_rules": (
            "Act 2 may show replacements becoming consistent or anticipatory."
        ),
        "act_2_focus": (
            "Items appear before the narrator realizes they are needed."
        ),

        "act_3_rules": (
            "Act 3 introduces loss of trust in personal space or memory."
        ),
        "act_3_focus": (
            "The narrator stops relying on their own recollection."
        ),

        "act_4_rules": (
            "Act 4 may include an attempt to remove or reject replacements."
        ),
        "act_4_focus": (
            "Removed items reappear or are replaced again."
        ),

        "act_5_rules": (
            "Act 5 leaves the narrator unsure which possessions are truly theirs."
        ),
        "act_5_focus": (
            "Ownership and familiarity no longer overlap."
        ),
    },

    {
        "name": "Authority Drift",
        "theme": "Control established through reasonable correction",

        "act_1_rules": (
            "Act 1 may show helpful suggestions or corrections only. "
            "Narrator complies willingly."
        ),
        "act_1_focus": (
            "Advice framed as efficiency, safety, or improvement."
        ),

        "act_2_rules": (
            "Act 2 may show corrections becoming expectations."
        ),
        "act_2_focus": (
            "The antagonist behaves as though authority is assumed."
        ),

        "act_3_rules": (
            "Act 3 introduces emotional cost from deferring judgment."
        ),
        "act_3_focus": (
            "The narrator questions their own decisions."
        ),

        "act_4_rules": (
            "Act 4 may include resistance or disagreement."
        ),
        "act_4_focus": (
            "The narrator is treated as unreasonable for pushing back."
        ),

        "act_5_rules": (
            "Act 5 leaves authority unresolved or internalized."
        ),
        "act_5_focus": (
            "The narrator continues self-correcting even when alone."
        ),
    },

    {
        "name": "Witness Displacement",
        "theme": "Reality disagreements dismissed as memory error",

        "act_1_rules": (
            "Act 1 may contain only one minor disagreement about reality. "
            "Others dismiss it casually."
        ),
        "act_1_focus": (
            "The narrator doubts their perception."
        ),

        "act_2_rules": (
            "Act 2 may include repeated disagreements across different contexts."
        ),
        "act_2_focus": (
            "The narrator stops raising concerns."
        ),

        "act_3_rules": (
            "Act 3 introduces isolation and internalized doubt."
        ),
        "act_3_focus": (
            "Memory becomes unreliable by consensus."
        ),

        "act_4_rules": (
            "Act 4 may include proof that is dismissed or reframed."
        ),
        "act_4_focus": (
            "Evidence fails to restore certainty."
        ),

        "act_5_rules": (
            "Act 5 leaves reality socially overridden."
        ),
        "act_5_focus": (
            "The narrator learns disagreement has consequences."
        ),
    },
]
