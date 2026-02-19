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
#
# DESIGN PRINCIPLES:
#   - Arcs define NARRATIVE STRUCTURE only. Setting comes from the idea generator.
#   - Each arc must be capable of producing horror across any setting.
#   - No two arcs share the same emotional escalation mechanism.
#   - Act 3 must always contain a concrete, physical danger event — never a feeling.
#   - Act 5 always ends on changed behavior or unanswered question, never resolution.
#
# ============================================================

STORY_ARCS: List[Dict[str, str]] = [

    # ----------------------------------------------------------------
    # ARC 1: SINGLE ENCOUNTER ESCALATION
    # The entire story unfolds within one night or one continuous
    # encounter. No prior relationship with the threat. The narrator
    # goes from comfortable to surviving within hours.
    # Emotional engine: COMFORT → ANOMALY → SURVIVAL → AFTERMATH
    # ----------------------------------------------------------------
    {
        "name": "Single Encounter Escalation",
        "theme": "One encounter that escalates faster than the narrator can process",

        "act_1_rules": (
            "Establish the narrator in a setting for a mundane, relatable reason. "
            "The narrator feels safe — even slightly bored or routine. "
            "End Act 1 with the narrator fully settled, comfortable, with zero sense of threat. "
            "Do NOT introduce the antagonist or any threatening element in Act 1."
        ),
        "act_1_focus": (
            "Setting, purpose, and comfort only. "
            "Establish the physical space in enough concrete detail that later events feel grounded. "
            "The narrator's guard should be completely down by the end of this act."
        ),

        "act_2_rules": (
            "Introduce ONE anomaly that cannot be explained away. "
            "It must be physical and specific — a sound, a figure, something moved, "
            "something that should not be there. "
            "The narrator attempts exactly one rational explanation. That explanation fails. "
            "End Act 2 with the narrator uneasy but not yet in active danger. No confrontation yet."
        ),
        "act_2_focus": (
            "The moment the narrator's comfort is cracked by something specific. "
            "The failure of their rationalization. "
            "Unease, not fear. They are still trying to explain it away."
        ),

        "act_3_rules": (
            "The threat becomes immediate and physical within the same encounter. "
            "The narrator must make a survival decision: hide, flee, confront, or call for help. "
            "That decision must have a cost — something goes wrong even if they survive. "
            "The threat must not be fully seen, caught, or explained by the end of this act."
        ),
        "act_3_focus": (
            "Adrenaline and instinct. The narrator stops thinking and starts reacting. "
            "At least one moment where the wrong choice would have ended very badly. "
            "Fast pacing. Immediate stakes."
        ),

        "act_4_rules": (
            "Cover the immediate aftermath: returning in daylight, authorities, physical evidence. "
            "Answers must remain incomplete — evidence raises more questions than it resolves. "
            "The threat remains unaccounted for. No capture, no confirmed explanation."
        ),
        "act_4_focus": (
            "The gap between what happened and what can be proven. "
            "Physical evidence that confirms something real occurred. "
            "The narrator trying to reconstruct it and finding the pieces do not fully fit."
        ),

        "act_5_rules": (
            "Narrate from a remove in time — weeks, months, or years later. "
            "The danger is over. Focus entirely on what permanently changed. "
            "End on a specific behavior, avoidance, or lingering question. "
            "Do NOT introduce new threats in Act 5."
        ),
        "act_5_focus": (
            "What the narrator no longer does, visits, or feels safe attempting. "
            "One unanswered question that still surfaces at quiet moments. "
            "Quiet unease, not active fear."
        ),
    },


    # ----------------------------------------------------------------
    # ARC 2: WRONG PLACE WITNESS
    # The narrator stumbles into a situation they were never meant
    # to see. They did nothing wrong — they simply arrived at the
    # wrong moment. Being noticed is what makes leaving dangerous.
    # Emotional engine: CURIOSITY → REALIZATION → FLIGHT → RECKONING
    # ----------------------------------------------------------------
    {
        "name": "Wrong Place Witness",
        "theme": "They were never supposed to see it — and then they were noticed",

        "act_1_rules": (
            "Establish the narrator in transit or in an unfamiliar place for a legitimate reason. "
            "Something minor catches their attention — not threatening, just slightly out of place. "
            "The narrator makes a routine, well-intentioned choice to stop, help, or look closer. "
            "Do NOT reveal what the situation actually is in Act 1."
        ),
        "act_1_focus": (
            "Legitimate purpose. Ordinary surroundings. "
            "One small detail that feels slightly off but is easy to rationalize. "
            "The narrator's helpfulness or curiosity draws them in. Their guard is completely down."
        ),

        "act_2_rules": (
            "A second person, vehicle, or detail makes the full pattern visible. "
            "The narrator realizes they have stumbled into something — and that they've been noticed. "
            "Leaving now is complicated: socially, physically, or situationally. "
            "The narrator has not yet tried to leave. They are still trying to seem normal."
        ),
        "act_2_focus": (
            "The moment the narrator understands this is not what it looked like. "
            "The situation has already closed around them before they fully processed it. "
            "Rising dread. The narrator is performing calm while calculating their exit."
        ),

        "act_3_rules": (
            "The narrator attempts to exit. That exit is actively or passively resisted. "
            "They get out — but not cleanly. Something goes wrong during the escape: "
            "something is left behind, someone is hurt, or they are followed. "
            "The escape must feel narrow and costly, not clean or triumphant."
        ),
        "act_3_focus": (
            "Speed, fear, and instinct. "
            "The narrator making a fast decision with incomplete information. "
            "The exit is earned through luck as much as skill."
        ),

        "act_4_rules": (
            "Reveal what the narrator was actually inside of — from news, a phone call, "
            "a return visit, or police contact. Not from speculation. "
            "The full picture must be worse than what the narrator guessed in the moment. "
            "Their survival was partly luck. Others may not have survived."
        ),
        "act_4_focus": (
            "Recontextualization. What it actually was. "
            "The gap between what the narrator understood during the encounter "
            "and how close they came to not making it out. "
            "Guilt, relief, or the strange combination of both."
        ),

        "act_5_rules": (
            "Reflect on what followed — guilt, luck, or permanent behavioral change. "
            "If others were harmed, the narrator lives with partial responsibility. "
            "No confirmed justice. No tidy resolution. "
            "End on the specific ordinary action the narrator can no longer do casually."
        ),
        "act_5_focus": (
            "The cost of having been in the wrong place and survived it. "
            "The routine thing — stopping to help, taking a shortcut, staying late — "
            "that the narrator now second-guesses every time."
        ),
    },


    # ----------------------------------------------------------------
    # ARC 3: DISCOVERED PRESENCE
    # The narrator finds evidence that someone has been occupying a
    # space they believed was private — for longer than anyone knew.
    # The horror is historical before it becomes immediate.
    # Emotional engine: WRONGNESS → PATTERN → CONFIRMATION → LOSS OF SAFETY
    # ----------------------------------------------------------------
    {
        "name": "Discovered Presence",
        "theme": "Someone had been there — in that space — long before anyone noticed",

        "act_1_rules": (
            "Establish the narrator in a space they believe is private and controlled. "
            "One small detail is slightly wrong — something most people would not catch. "
            "The narrator notices, forms an immediate plausible explanation, and moves on. "
            "Life continues completely normally after this dismissal."
        ),
        "act_1_focus": (
            "Familiarity and assumed privacy. The narrator feels ownership of this space. "
            "The small wrongness must be concrete and specific — not atmospheric. "
            "The explanation they give themselves must sound reasonable."
        ),

        "act_2_rules": (
            "A second wrongness appears that connects to the first. "
            "The narrator cannot explain both away at once. "
            "Something has been touched, moved, used, or left behind. "
            "The narrator begins checking the space more carefully than they ever have. "
            "No direct contact with another person yet — only mounting evidence of one."
        ),
        "act_2_focus": (
            "Pattern recognition. The shift from one odd detail to an explanation "
            "that requires another person. "
            "Fear of what the pattern implies, not fear of immediate danger. "
            "The narrator checking things they never thought to check before."
        ),

        "act_3_rules": (
            "Direct confirmation of presence: a sound from where no sound should be, "
            "a figure, a voice, something living in a space believed to be empty. "
            "The encounter must be brief and incomplete — no face, no explanation, no confrontation. "
            "The narrator flees, hides, or freezes. It ends before answers arrive."
        ),
        "act_3_focus": (
            "The moment the narrator stops doubting and starts surviving. "
            "Brief, disorienting, and unresolved. "
            "The presence is confirmed but utterly unexplained. "
            "The narrator has no idea how long this has been happening."
        ),

        "act_4_rules": (
            "Authorities or others investigate the space. Partial answers emerge. "
            "How the presence gained access remains unclear or more unsettling than expected. "
            "Evidence is found suggesting the presence predates the narrator's awareness by far. "
            "The space cannot be trusted again even after the investigation."
        ),
        "act_4_focus": (
            "The gap between what was found and what it means. "
            "Specific evidence of duration — how long before anyone noticed. "
            "The investigation answers 'what' but never 'how long' or 'why.'"
        ),

        "act_5_rules": (
            "Reflect on how the narrator now relates to any space they are supposed to have alone. "
            "End on a specific changed habit — something concrete they now check "
            "that no reasonable person would think to. "
            "Or end on the question about duration that was never answered."
        ),
        "act_5_focus": (
            "The permanent erosion of the assumption of privacy. "
            "Not generalized anxiety — one specific, grounded thing the narrator now does "
            "in hotel rooms, rentals, campsites, or anywhere meant to be theirs alone."
        ),
    },


    # ----------------------------------------------------------------
    # ARC 4: ESCALATING STRANGENESS
    # A person the narrator encounters behaves oddly, then increasingly
    # wrong, until one physical act reveals the full threat.
    # There is no dramatic reveal — just a line that keeps moving.
    # Emotional engine: DISCOMFORT → UNEASE → BREAKING POINT → PARTIAL REMOVAL
    # ----------------------------------------------------------------
    {
        "name": "Escalating Strangeness",
        "theme": "It started as odd. By the end, the narrator had no word for what it was.",

        "act_1_rules": (
            "Introduce a person whose behavior is unusual but not alarming. "
            "The narrator's first reaction is social discomfort or mild confusion, not fear. "
            "The narrator makes a reasonable effort to normalize or accommodate them. "
            "Do NOT frame the person as dangerous in Act 1. They must seem merely eccentric."
        ),
        "act_1_focus": (
            "Quirky, awkward, or socially off — but explainable. "
            "The narrator gives the benefit of the doubt and finds a charitable read. "
            "Establish enough routine contact that later behavior has contrast and context."
        ),

        "act_2_rules": (
            "The person's behavior crosses a line that cannot be explained away. "
            "The narrator attempts to create distance — directly or through avoidance — "
            "and the attempt is ignored or circumvented. "
            "A second incident reveals the first was not coincidence. "
            "The narrator begins to feel studied rather than merely annoyed."
        ),
        "act_2_focus": (
            "The moment discomfort becomes unease. "
            "Something the person knows or does that they should not be able to. "
            "The narrator paying attention differently — noticing patterns they missed before."
        ),

        "act_3_rules": (
            "One physical act so far outside normal behavior that the narrator cannot stay passive. "
            "Showing up somewhere unexpected, making contact outside any normal context, "
            "or doing something that reveals deliberate intent. "
            "The narrator is forced to respond actively — they cannot wait or minimize anymore."
        ),
        "act_3_focus": (
            "The single act that retroactively makes all previous behavior make terrible sense. "
            "The narrator's shift from managing the situation to needing to escape it. "
            "Fast, active response — even if imperfect."
        ),

        "act_4_rules": (
            "The narrator seeks outside help. Response is imperfect and partial. "
            "The person is removed from immediate proximity but not fully accounted for. "
            "Something is discovered about them that makes all earlier behavior retroactively worse. "
            "Their full intent is never confirmed."
        ),
        "act_4_focus": (
            "Partial resolution that does not feel like safety. "
            "The discovered detail that reframes every earlier 'quirk.' "
            "How long the narrator was being watched or studied before they registered anything."
        ),

        "act_5_rules": (
            "The narrator in the present, after enough time has passed. "
            "The person is gone from their life but not from their thinking. "
            "End on a specific behavioral change — what the narrator now does "
            "when someone sets off even a minor alarm. "
            "Leave open whether the threat is fully over."
        ),
        "act_5_focus": (
            "The low-level vigilance that never fully went away. "
            "The permanent shift in the narrator's threshold for 'this person is probably fine.' "
            "Specific and grounded — not generalized anxiety."
        ),
    },


    # ----------------------------------------------------------------
    # ARC 5: ISOLATION TRAP
    # The narrator is alone by choice or circumstance and realizes
    # too late that they are not. Communication and exit are
    # compromised at the same moment the presence is discovered.
    # Emotional engine: SOLITUDE → DOUBT → CONFIRMED THREAT → ESCAPE
    # ----------------------------------------------------------------
    {
        "name": "Isolation Trap",
        "theme": "The moment they realized their aloneness was no longer true",

        "act_1_rules": (
            "Establish the narrator deliberately or circumstantially alone. "
            "They chose this — for work, peace, adventure, or necessity. "
            "The isolation feels manageable, even comfortable or freeing. "
            "Establish exactly what communication and exit look like — "
            "clearly enough that removing both later lands with full force."
        ),
        "act_1_focus": (
            "The narrator alone in a space they understand and feel they control. "
            "Routine established. Rich sensory detail of the environment. "
            "The specific way emptiness feels safe when you are the only person in it."
        ),

        "act_2_rules": (
            "Remove one layer of safety: communication fails, an exit is blocked, "
            "or backup cannot be reached. "
            "Simultaneously — or within minutes — the first sign of another presence appears. "
            "Both losses must arrive close together so they cannot be addressed independently. "
            "The narrator is not yet certain the presence is hostile."
        ),
        "act_2_focus": (
            "The simultaneous loss of safety net and gain of unknown threat. "
            "The narrator still hunting for a non-threatening explanation. "
            "The specific way a controllable space becomes a trap."
        ),

        "act_3_rules": (
            "The presence reacts to the narrator's movements — it follows, avoids, or responds. "
            "This responsiveness is the confirmation that it is aware of them. "
            "The narrator must make a survival decision without full information. "
            "Every option has a cost. They get out — but the threat knows they were there."
        ),
        "act_3_focus": (
            "Cat and mouse in a confined or isolated space. "
            "Decisions made without enough information, under time pressure. "
            "Tension built through movement, sound, and darkness. "
            "The exit is narrow. The narrator is not sure they fully got away."
        ),

        "act_4_rules": (
            "Immediate aftermath: exit, rescue, or return with others. "
            "Physical evidence confirms the presence was real. "
            "Origin or intent remains unclear or more disturbing than expected. "
            "Something about what was found suggests this was not accidental or random."
        ),
        "act_4_focus": (
            "Evidence of real presence alongside unanswered questions about its nature. "
            "The gap between what was found and what it means. "
            "The specific, disturbing implication of what would have happened "
            "if the narrator had not gotten out when they did."
        ),

        "act_5_rules": (
            "The narrator now, living with the permanent change. "
            "They no longer seek or accept isolation in the same way. "
            "End on a specific type of space — named and concrete — "
            "that now produces a physical reaction when encountered. "
            "Memory, not ongoing danger."
        ),
        "act_5_focus": (
            "The end of a specific kind of fearlessness. "
            "The thing the narrator used to do alone without a second thought "
            "that now requires planning, company, or a conscious act of will."
        ),
    },


    # ----------------------------------------------------------------
    # ARC 6: DECEPTIVE INVITATION
    # The situation was constructed before the narrator arrived.
    # They accepted what appeared to be a legitimate opportunity.
    # By the time the deception is clear, extraction is dangerous.
    # Emotional engine: ANTICIPATION → WRONGNESS → REALIZATION → FLIGHT
    # ----------------------------------------------------------------
    {
        "name": "Deceptive Invitation",
        "theme": "The situation was built before the narrator ever arrived",

        "act_1_rules": (
            "Establish the narrator accepting an invitation or opportunity that appears legitimate. "
            "They may have minor reservations but override them for a reasonable cause. "
            "Plant two or three small details that will recontextualize later — "
            "but make each one feel completely ordinary in the moment. "
            "End Act 1 with the narrator en route or just arriving, not yet inside the full situation."
        ),
        "act_1_focus": (
            "Normal anticipation. The narrator is not naive — "
            "they simply had no reason to be suspicious yet. "
            "The invitation must feel plausible and even appealing. "
            "Planted details must read as mundane background noise."
        ),

        "act_2_rules": (
            "The first sign that something does not match the invitation. "
            "One element is wrong: a person who should not be there, "
            "a location detail that does not fit, a request that seems minor but is off. "
            "The narrator explains it away or complies out of politeness or social pressure. "
            "They are now inside the situation and leaving would require a reason."
        ),
        "act_2_focus": (
            "The moment the narrator could have left but did not. "
            "Social pressure, politeness, sunk cost, or genuine uncertainty "
            "about whether they are overreacting. "
            "The trap closes slowly enough that they do not feel it closing."
        ),

        "act_3_rules": (
            "A physical event — not a feeling — forces the narrator to understand "
            "that the invitation was false. "
            "Their attempt to leave is actively or passively resisted. "
            "They get out — but narrowly and not without consequence. "
            "The escape must feel earned and imperfect, never easy."
        ),
        "act_3_focus": (
            "The moment everything recontextualizes at once. "
            "Every planted detail from Acts 1 and 2 suddenly makes terrible sense. "
            "The exit is fast, frightening, and leaves something unresolved."
        ),

        "act_4_rules": (
            "The narrator tries to understand who constructed the situation and why. "
            "Police involvement, private investigation, or discovery of information. "
            "The full scope of what was planned is never confirmed. "
            "The most disturbing discovery: how much was known about the narrator "
            "before they ever arrived — how specifically they were chosen."
        ),
        "act_4_focus": (
            "The depth of the deception. "
            "How long it was planned. How targeted the narrator was. "
            "Evidence of intent that stops short of fully explaining it."
        ),

        "act_5_rules": (
            "Permanent change in how the narrator accepts invitations "
            "or meets strangers or evaluates unfamiliar situations. "
            "Specific and grounded — not generalized paranoia. "
            "End on the one concrete thing they now do before agreeing to anything, "
            "and acknowledge what that caution has cost them."
        ),
        "act_5_focus": (
            "The narrator's new baseline for trust. "
            "The specific check or hesitation that did not exist before. "
            "What that caution has taken from their life — and why they consider it worth it."
        ),
    },

]