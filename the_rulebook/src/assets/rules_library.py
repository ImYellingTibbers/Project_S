from __future__ import annotations

# ============================================================
# RULES LIBRARY
# ============================================================
#
# Each rule has:
#   - id: unique string identifier
#   - name: the framework name
#   - template: the instruction pattern
#   - consequence_tone: what kind of dread it creates
#   - story_moment: what narrative beat it naturally produces
#   - tags: list of place-type tags this rule is compatible with
#
# TAG DEFINITIONS:
#   isolated        - remote, limited access, few people around
#   overnight       - naturally operates or is visited after dark
#   industrial      - has heavy equipment, machinery, physical processes
#   has_equipment   - has specific technical equipment that can be named
#   medical         - involves patients, residents, clinical settings
#   public_facing   - customers, visitors, or guests are present
#   has_staff       - multiple coworkers present during shifts
#   has_records     - archives, logs, files, databases on site
#   has_residents   - people live or stay there (patients, guests, inmates)
#   transit         - people pass through, arrivals and departures
#   government      - official, institutional, bureaucratic setting
#   food_service    - food and drink are prepared or served
#   retail          - goods are sold to the public
#   entertainment   - events, performances, or recreation
#   research        - scientific or academic work is conducted
#   utilities       - manages infrastructure like water, power, gas
#   confined        - enclosed spaces, limited exits, underground
#   wilderness      - outdoor, natural setting, limited shelter
#   has_animals     - animals are present (livestock, wildlife, pets)
#   residential     - people live on the premises long-term
# ============================================================

RULES_LIBRARY = [

    {
        "id": "R01",
        "name": "THE FORBIDDEN ZONE",
        "template": "Do not enter [specific room/area/floor] for any reason.",
        "consequence_tone": "Vague but severe — people have gone in and not come back, or things get significantly worse.",
        "story_moment": "The narrator inevitably enters and discovers the reason the rule exists.",
        "tags": ["isolated", "overnight", "industrial", "medical", "has_equipment", "confined",
                 "government", "research", "utilities", "residential", "has_records"],
    },

    {
        "id": "R02",
        "name": "THE IGNORED SUMMONS",
        "template": "If [name/sound/voice] calls for you over [intercom/radio/phone], do not respond.",
        "consequence_tone": "Answering acknowledges something and creates a connection that can be used against the narrator.",
        "story_moment": "The narrator hears something familiar — a loved one's voice, their own name — and has to fight every instinct not to respond.",
        "tags": ["overnight", "has_equipment", "industrial", "utilities", "isolated",
                 "government", "research", "medical", "confined"],
    },

    {
        "id": "R03",
        "name": "THE COUNTDOWN RITUAL",
        "template": "At exactly [specific time], perform [specific action] for exactly [specific duration]. Do not skip it.",
        "consequence_tone": "Something goes wrong in the building or surroundings if the ritual is skipped.",
        "story_moment": "The narrator almost misses it, or watches closely during the ritual and discovers what it actually does.",
        "tags": ["overnight", "has_equipment", "industrial", "utilities", "isolated",
                 "research", "government", "confined", "wilderness"],
    },

    {
        "id": "R04",
        "name": "THE PROTECTED HOURS",
        "template": "Between [time] and [time], do not [specific action — move, speak, use lights].",
        "consequence_tone": "Things are more active during this window — stillness and silence are the only protection.",
        "story_moment": "The narrator has to remain perfectly still or silent during a dangerous period while something moves nearby.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "wilderness", "residential"],
    },

    {
        "id": "R05",
        "name": "THE KNOWN STRANGER",
        "template": "If you see [specific description of person], do not make eye contact / do not speak to them / direct them to [specific location].",
        "consequence_tone": "Interaction escalates something or invites direct attention from a dangerous presence.",
        "story_moment": "The narrator encounters someone who matches the description exactly and has to act normal.",
        "tags": ["public_facing", "retail", "medical", "transit", "overnight", "has_residents",
                 "government", "entertainment", "food_service", "residential"],
    },

    {
        "id": "R06",
        "name": "THE SAFE OBJECT",
        "template": "Always carry / wear [specific item] while on the premises. If you lose it, leave immediately.",
        "consequence_tone": "The item provides protection the narrator only understands after something almost happens without it.",
        "story_moment": "The narrator loses the item or discovers what it actually does when something gets too close.",
        "tags": ["overnight", "isolated", "industrial", "medical", "confined", "utilities",
                 "research", "wilderness", "government", "has_staff"],
    },

    {
        "id": "R07",
        "name": "THE CIRCLE PROTOCOL",
        "template": "If you find [objects] arranged in a [specific pattern], do not disturb it. Report using [specific code].",
        "consequence_tone": "The arrangement is a threshold or trap — disturbing it releases or invites something.",
        "story_moment": "The narrator finds one and has to resist the urge to fix or clean it up.",
        "tags": ["retail", "overnight", "industrial", "isolated", "research",
                 "utilities", "government", "confined", "wilderness"],
    },

    {
        "id": "R08",
        "name": "THE UNACKNOWLEDGED PRESENCE",
        "template": "If you see [specific type of figure or person], do not acknowledge them. Continue working normally.",
        "consequence_tone": "Acknowledgment creates a connection or gives the presence permission to escalate its behavior.",
        "story_moment": "The narrator sees something unmistakably wrong and has to pretend they didn't.",
        "tags": ["overnight", "isolated", "medical", "retail", "industrial", "has_residents",
                 "transit", "government", "research", "entertainment", "confined"],
    },

    {
        "id": "R09",
        "name": "THE MARKED ITEM",
        "template": "Do not use / play / open any [specific category of item] that has [specific marking — no label, red tag, upside down].",
        "consequence_tone": "The item contains or transmits something dangerous.",
        "story_moment": "The narrator encounters a marked item and has to decide whether to investigate.",
        "tags": ["retail", "industrial", "has_equipment", "research", "medical",
                 "has_records", "overnight", "government", "utilities"],
    },

    {
        "id": "R10",
        "name": "THE EMERGENCY EXIT RULE",
        "template": "If [specific warning sign] occurs, go immediately to [specific location] and stay until [specific condition is met].",
        "consequence_tone": "The designated location is either a safe zone or a convergence point — the ambiguity is the horror.",
        "story_moment": "The warning sign occurs and the narrator has to trust the rule completely without understanding it.",
        "tags": ["overnight", "industrial", "confined", "utilities", "government",
                 "research", "medical", "isolated", "has_staff"],
    },

    {
        "id": "R11",
        "name": "THE CUSTOMER EXCEPTION",
        "template": "If a customer / visitor / guest [specific description], do not assist them. Do not touch them. Direct them to [specific location].",
        "consequence_tone": "These individuals are either partially lost or not what they appear — interaction transfers something.",
        "story_moment": "The narrator has to turn away someone who seems to genuinely need help.",
        "tags": ["public_facing", "retail", "medical", "transit", "food_service",
                 "entertainment", "has_residents", "government", "overnight"],
    },

    {
        "id": "R12",
        "name": "THE MAINTENANCE RITUAL",
        "template": "[Specific piece of equipment] must be [started / stopped / reset] at [specific time] regardless of conditions.",
        "consequence_tone": "The equipment is containing or suppressing something — skipping the ritual lets it grow.",
        "story_moment": "The narrator discovers the equipment is connected to something they can't explain mechanically.",
        "tags": ["industrial", "has_equipment", "utilities", "overnight", "isolated",
                 "research", "government", "confined", "medical"],
    },

    {
        "id": "R13",
        "name": "THE LOGGING REQUIREMENT",
        "template": "Every [time interval], record [specific readings] in the physical log. Do not estimate. Do not skip entries.",
        "consequence_tone": "The logs are a record that something monitors — gaps in the record invite direct attention.",
        "story_moment": "The narrator discovers old logs with entries that describe things that shouldn't have been witnessed.",
        "tags": ["has_records", "industrial", "utilities", "overnight", "government",
                 "research", "medical", "isolated", "has_equipment"],
    },

    {
        "id": "R14",
        "name": "THE SOUND RULE",
        "template": "If you hear [specific sound — digging, singing, children laughing, something dragging], do not investigate. Leave the area immediately.",
        "consequence_tone": "The sound is a lure — it gets louder and more specific the closer you get.",
        "story_moment": "The narrator hears something that sounds exactly like a person in distress and has to walk away.",
        "tags": ["overnight", "isolated", "confined", "industrial", "wilderness",
                 "utilities", "research", "medical", "government"],
    },

    {
        "id": "R15",
        "name": "THE SECOND KNOCK",
        "template": "If someone knocks [specific number of times], do not answer. If they knock [different number], check the peephole first.",
        "consequence_tone": "The number of knocks signals intent — two knocks means something that knows you're there.",
        "story_moment": "The narrator hears the wrong number of knocks at the wrong time of night.",
        "tags": ["overnight", "isolated", "residential", "confined", "industrial",
                 "utilities", "government", "research", "wilderness"],
    },

    {
        "id": "R16",
        "name": "THE LOCKED RECORD",
        "template": "Do not access [specific file / archive / log / database] without authorization from [specific person or role].",
        "consequence_tone": "The record contains something that fundamentally changes the narrator's understanding of the place.",
        "story_moment": "The narrator accesses it and discovers the history of what happened to people who worked there before.",
        "tags": ["has_records", "government", "medical", "research", "industrial",
                 "overnight", "utilities", "confined", "has_staff"],
    },

    {
        "id": "R17",
        "name": "THE SHIFT BOUNDARY",
        "template": "Do not leave the building / premises during your shift for any reason.",
        "consequence_tone": "Leaving breaks a boundary that was protecting the narrator — whatever is inside stays inside only as long as they do.",
        "story_moment": "The narrator is forced to consider leaving during an emergency and has to weigh the risk of staying against the risk of going.",
        "tags": ["overnight", "isolated", "confined", "industrial", "utilities",
                 "government", "research", "medical", "has_staff"],
    },

    {
        "id": "R18",
        "name": "THE FEEDING RULE",
        "template": "Leave [specific offering — food, water, salt, iron filings] at [specific location] at [specific time]. Do not skip it.",
        "consequence_tone": "The offering appeases something that would otherwise turn its attention toward the people inside.",
        "story_moment": "The narrator skips it once and something in the building changes immediately and noticeably.",
        "tags": ["isolated", "overnight", "wilderness", "confined", "industrial",
                 "utilities", "research", "government", "residential"],
    },

    {
        "id": "R19",
        "name": "THE MIRROR RULE",
        "template": "Cover / avoid / do not look at [mirrors / windows / reflective surfaces] after [specific time or triggering condition].",
        "consequence_tone": "Reflections show the narrator something they aren't ready to see — or show the narrator to something else.",
        "story_moment": "The narrator catches a glimpse in a reflection anyway and can't determine if something has changed.",
        "tags": ["overnight", "isolated", "residential", "medical", "confined",
                 "industrial", "research", "government", "has_residents"],
    },

    {
        "id": "R20",
        "name": "THE DOCUMENTATION RULE",
        "template": "Do not photograph, record, or write down [specific things]. Some things should not be documented.",
        "consequence_tone": "Documentation creates a persistent connection — the thing follows the record out of the building.",
        "story_moment": "The narrator has already documented something before they learn the rule exists.",
        "tags": ["research", "medical", "government", "has_records", "industrial",
                 "overnight", "isolated", "utilities", "confined"],
    },

    {
        "id": "R21",
        "name": "THE CO-WORKER RULE",
        "template": "If a colleague begins [specific behavior — humming the same note, staring at one spot, repeating a phrase], do not engage. Report immediately.",
        "consequence_tone": "The behavior signals that a co-worker has been compromised or is being used as a conduit.",
        "story_moment": "The narrator notices the behavior in someone they trust and has to decide if they're overreacting.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R22",
        "name": "THE POWER RULE",
        "template": "If the lights go out, stay exactly where you are. Do not use a flashlight or your phone light. Wait for them to come back on.",
        "consequence_tone": "Movement in the dark draws attention — artificial light signals the narrator's exact location.",
        "story_moment": "The narrator is caught in complete darkness and every instinct tells them to turn on their phone.",
        "tags": ["overnight", "confined", "industrial", "isolated", "utilities",
                 "research", "government", "medical", "has_equipment"],
    },

    {
        "id": "R23",
        "name": "THE INVENTORY RULE",
        "template": "Count [specific items] at the start and end of every shift. If the numbers don't match, report immediately.",
        "consequence_tone": "Something is taking or adding items — the count is the only reliable way to know if something has changed.",
        "story_moment": "The numbers don't match and the narrator has to figure out what changed and why.",
        "tags": ["retail", "industrial", "medical", "government", "research",
                 "has_records", "overnight", "utilities", "confined"],
    },

    {
        "id": "R24",
        "name": "THE WINDOW RULE",
        "template": "Close all blinds and curtains before [specific time]. Do not look outside after dark.",
        "consequence_tone": "The outside can see in before the narrator can see out — looking out is an invitation.",
        "story_moment": "The narrator looks anyway and sees something on the other side looking back.",
        "tags": ["overnight", "isolated", "residential", "confined", "industrial",
                 "wilderness", "research", "government", "utilities"],
    },

    {
        "id": "R25",
        "name": "THE NAME RULE",
        "template": "Do not tell anyone your real name. Do not use anyone else's name aloud. Do not answer if your name is called.",
        "consequence_tone": "Names create ownership — saying or hearing your name gives something a direct claim on the narrator.",
        "story_moment": "The narrator hears their name said perfectly in a familiar voice from somewhere it couldn't possibly be coming from.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R26",
        "name": "THE TEMPERATURE RULE",
        "template": "If the temperature in [specific area] drops or rises unexpectedly by [specific amount], evacuate that section immediately.",
        "consequence_tone": "Temperature shifts signal proximity — the cold or heat is a symptom of presence, not a cause.",
        "story_moment": "The narrator notices the shift mid-task and has to leave before they see what's causing it.",
        "tags": ["industrial", "confined", "medical", "utilities", "overnight",
                 "research", "isolated", "government", "has_equipment"],
    },

    {
        "id": "R27",
        "name": "THE SMELL RULE",
        "template": "If you detect [specific smell — copper, sulfur, fresh earth, burnt hair, something sweet] anywhere on the premises, move upwind immediately. Do not try to identify the source.",
        "consequence_tone": "The smell is either a byproduct of something dangerous nearby or a lure designed to disorient.",
        "story_moment": "The narrator smells it and has to fight the instinct to find where it's coming from.",
        "tags": ["industrial", "confined", "utilities", "overnight", "isolated",
                 "research", "medical", "wilderness", "government"],
    },

    {
        "id": "R28",
        "name": "THE ANIMAL RULE",
        "template": "If the [specific animals — dogs, birds, rats] on the property go silent all at once, stop what you are doing and do not move until they resume.",
        "consequence_tone": "The animals sense something the narrator can't — their collective silence means it's very close.",
        "story_moment": "The narrator is mid-task in a vulnerable position when everything goes completely silent.",
        "tags": ["has_animals", "isolated", "wilderness", "overnight", "industrial",
                 "residential", "research", "government", "utilities"],
    },

    {
        "id": "R29",
        "name": "THE PHOTOGRAPH RULE",
        "template": "Do not look directly at any photographs or portraits of [specific subject] displayed on the premises.",
        "consequence_tone": "The subject in the image is aware of being looked at and responds to sustained attention.",
        "story_moment": "The narrator glances at one and cannot tell if something in the image has shifted position.",
        "tags": ["residential", "medical", "overnight", "government", "has_records",
                 "research", "isolated", "has_residents", "confined"],
    },

    {
        "id": "R30",
        "name": "THE WATER RULE",
        "template": "Do not drink water from [specific source — certain tap, certain floor, certain fixture]. Use only [specific approved source].",
        "consequence_tone": "Water from the forbidden source causes gradual confusion, compliance, or something worse.",
        "story_moment": "The narrator drinks from the wrong source by accident and starts noticing their thinking change.",
        "tags": ["industrial", "confined", "utilities", "medical", "isolated",
                 "research", "government", "overnight", "wilderness"],
    },

    {
        "id": "R31",
        "name": "THE SHADOW RULE",
        "template": "If your shadow behaves differently from your movement — lagging, leading, or moving independently — go directly to [specific location] and wait.",
        "consequence_tone": "The shadow is the first sign of being noticed by something that tracks through light and movement.",
        "story_moment": "The narrator catches it in peripheral vision and cannot confirm whether what they saw was real.",
        "tags": ["overnight", "isolated", "confined", "industrial", "utilities",
                 "research", "wilderness", "government", "medical"],
    },

    {
        "id": "R32",
        "name": "THE DOUBLE RULE",
        "template": "If you encounter someone who looks exactly like a coworker who is not scheduled today, do not speak to them. Call [specific number] immediately.",
        "consequence_tone": "The double is either a replacement or a lure — engaging with it accelerates something irreversible.",
        "story_moment": "The narrator sees the double performing the job perfectly and almost convinces themselves it's fine.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R33",
        "name": "THE FREQUENCY RULE",
        "template": "Do not adjust [specific dial / frequency / channel / setting] on [specific equipment]. If it changes on its own, log the new setting but do not correct it.",
        "consequence_tone": "The frequency is a boundary marker — tuning it disrupts a signal keeping something at a fixed distance.",
        "story_moment": "The narrator finds the setting has drifted on its own and has to decide whether to log it or fix it.",
        "tags": ["has_equipment", "utilities", "research", "industrial", "overnight",
                 "government", "isolated", "confined", "medical"],
    },

    {
        "id": "R34",
        "name": "THE THRESHOLD RULE",
        "template": "Always step over the threshold of [specific doorway] with your right foot first. Never back out of the room.",
        "consequence_tone": "The threshold has a specific orientation — crossing it wrong creates an opening that wasn't there before.",
        "story_moment": "The narrator backs out in a hurry during a tense moment and immediately feels something change.",
        "tags": ["overnight", "confined", "industrial", "isolated", "medical",
                 "utilities", "research", "government", "residential"],
    },

    {
        "id": "R35",
        "name": "THE PATIENT RULE",
        "template": "If a resident / patient / guest asks you what day it is, always tell them it is [specific day, always the same]. Never give the real date.",
        "consequence_tone": "The person asking is caught in a loop — confirming reality either accelerates their deterioration or releases them from it.",
        "story_moment": "The narrator slips and gives the real date and watches the person's expression change completely.",
        "tags": ["medical", "has_residents", "residential", "overnight", "government",
                 "confined", "isolated"],
    },

    {
        "id": "R36",
        "name": "THE CLOCK RULE",
        "template": "If any clock on the premises stops at [specific time], do not restart it. Cover it and report it.",
        "consequence_tone": "The stopped time marks when something happened — restarting the clock resumes whatever was interrupted.",
        "story_moment": "The narrator finds a stopped clock and almost winds it back out of habit.",
        "tags": ["overnight", "isolated", "residential", "industrial", "confined",
                 "medical", "research", "government", "utilities"],
    },

    {
        "id": "R37",
        "name": "THE STAIRWELL RULE",
        "template": "Always count the stairs when using [specific stairwell]. If the count differs from the last time, do not proceed. Return the way you came.",
        "consequence_tone": "Extra or missing stairs mean the space has shifted — proceeding puts the narrator somewhere they cannot return from.",
        "story_moment": "The narrator counts wrong mid-descent and has to figure out if they miscounted or if something changed.",
        "tags": ["confined", "overnight", "industrial", "government", "medical",
                 "research", "utilities", "isolated", "has_records"],
    },

    {
        "id": "R38",
        "name": "THE WEATHER RULE",
        "template": "If [specific weather condition — fog, dead calm, unseasonable warmth] occurs outside, do not open any exterior door or window until it passes.",
        "consequence_tone": "The weather condition signals something moving outside — opening a door during it is an invitation inside.",
        "story_moment": "The narrator needs to go outside for a legitimate urgent reason while the condition is active.",
        "tags": ["isolated", "wilderness", "overnight", "industrial", "utilities",
                 "research", "government", "residential", "confined"],
    },

    {
        "id": "R39",
        "name": "THE UNIFORM RULE",
        "template": "Never remove [specific item of uniform — badge, lanyard, vest] while on the premises, even on break.",
        "consequence_tone": "The item identifies the narrator as staff — without it they become indistinguishable from other categories of presence.",
        "story_moment": "The narrator removes it without thinking and immediately notices something looking at them differently.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "retail",
                 "utilities", "government", "transit", "confined"],
    },

    {
        "id": "R40",
        "name": "THE GUEST LOG RULE",
        "template": "Every visitor must sign the log at the front. If someone is already inside who did not sign in, do not confront them. Call [specific code].",
        "consequence_tone": "Unsigned presences are threats or things that slipped through — direct confrontation acknowledges them.",
        "story_moment": "The narrator counts people and realizes there is one more inside than there are signatures in the log.",
        "tags": ["public_facing", "government", "medical", "research", "overnight",
                 "has_records", "industrial", "confined", "transit"],
    },

    {
        "id": "R41",
        "name": "THE PHRASE RULE",
        "template": "If you feel [specific sensation — watched, followed, like you forgot something important], recite [specific phrase] quietly before proceeding.",
        "consequence_tone": "The phrase is a reset — it interrupts whatever is beginning to focus its attention on the narrator.",
        "story_moment": "The narrator forgets the phrase under pressure and feels the sensation intensify rapidly.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R42",
        "name": "THE BODY RULE",
        "template": "If you find anyone lying down anywhere on the premises who is not a patient / resident, do not touch them. Do not speak to them. Leave the area and report.",
        "consequence_tone": "The person is either a trap or a lure — interacting with them transfers something to the narrator.",
        "story_moment": "The narrator finds someone who appears injured and has to fight the instinct to help.",
        "tags": ["overnight", "medical", "industrial", "confined", "isolated",
                 "utilities", "government", "research", "has_staff"],
    },

    {
        "id": "R43",
        "name": "THE DOOR COUNT RULE",
        "template": "At the start of every shift, count all interior doors in [specific wing / floor / section]. If the number has changed, do not open any door you cannot account for.",
        "consequence_tone": "New doors are thresholds that weren't there before — opening them crosses into something that wasn't accessible.",
        "story_moment": "The narrator finds an extra door and has to determine whether they miscounted or something is genuinely wrong.",
        "tags": ["confined", "overnight", "industrial", "medical", "government",
                 "research", "utilities", "isolated", "has_records"],
    },

    {
        "id": "R44",
        "name": "THE SILENCE RULE",
        "template": "Do not whistle, hum, or sing anywhere on the premises. If you hear anyone doing so, leave the area immediately.",
        "consequence_tone": "Tonal sound at certain frequencies resonates with something in the structure — it functions as a call.",
        "story_moment": "The narrator catches themselves humming without realizing it and stops mid-note, suddenly aware.",
        "tags": ["overnight", "confined", "isolated", "industrial", "utilities",
                 "research", "medical", "government", "wilderness"],
    },

    {
        "id": "R45",
        "name": "THE HANDWRITING RULE",
        "template": "All log entries must be in your own handwriting. Do not type, print, or allow anyone else to fill in your entries.",
        "consequence_tone": "Handwriting carries identity — a forged entry creates an opening under the narrator's name.",
        "story_moment": "The narrator discovers an entry in their section they didn't write, in handwriting close but not quite like their own.",
        "tags": ["has_records", "government", "medical", "research", "industrial",
                 "overnight", "utilities", "confined", "isolated"],
    },

    {
        "id": "R46",
        "name": "THE FOOD RULE",
        "template": "Do not eat anything brought onto the premises by anyone other than yourself. Do not accept food or drink from coworkers, vendors, or visitors.",
        "consequence_tone": "Food from the wrong source creates compliance or connection — the narrator becomes easier to steer.",
        "story_moment": "The narrator accepts something small — a piece of candy, a cup of coffee — from a coworker without thinking.",
        "tags": ["has_staff", "food_service", "medical", "industrial", "overnight",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R47",
        "name": "THE PAIR RULE",
        "template": "[Specific floor / section / wing] is accessible but must only be visited in pairs. Never go there alone.",
        "consequence_tone": "The space amplifies whatever you bring into it — including fear, suspicion, and attention.",
        "story_moment": "The narrator ends up there alone due to circumstances and feels the amplification begin.",
        "tags": ["confined", "industrial", "medical", "government", "overnight",
                 "utilities", "research", "isolated", "has_staff"],
    },

    {
        "id": "R48",
        "name": "THE BREATHING RULE",
        "template": "If you hear breathing that is not your own in an empty room, do not hold your breath. Breathe normally and leave at a normal pace.",
        "consequence_tone": "Holding your breath signals awareness — it tells whatever is there that the narrator has noticed it.",
        "story_moment": "The narrator hears it clearly in a silent room and has to consciously control their own breathing while walking out.",
        "tags": ["overnight", "confined", "isolated", "medical", "industrial",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R49",
        "name": "THE LAST SHIFT RULE",
        "template": "When your employment here ends, do not return to the premises for any reason. Do not drive past. Do not contact former coworkers for at least [specific time period].",
        "consequence_tone": "Leaving severs the connection — returning or maintaining contact reopens it completely.",
        "story_moment": "The narrator, after surviving everything, is tempted to go back for a reason that seems legitimate and urgent.",
        "tags": ["overnight", "isolated", "industrial", "medical", "utilities",
                 "government", "research", "confined", "has_staff"],
    },

    {
        "id": "R50",
        "name": "THE REPLACEMENT RULE",
        "template": "When training a new employee, do not tell them why the rules exist. Answer only what they ask directly. Do not volunteer information.",
        "consequence_tone": "Full knowledge passed on too early overwhelms the ability to follow rules calmly — panic breaks the protocols.",
        "story_moment": "The narrator realizes they are now the experienced one training someone new and has to decide how much to say.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    # ================================================================
    # R51 – R150: EXPANDED RULES
    # ================================================================

    # --- Directional & Positional ---

    {
        "id": "R51",
        "name": "THE FACING RULE",
        "template": "After [specific hour], never face [specific direction — the north wall / the back corridor / the loading side] while stationary. If you need to look, turn your whole body, do not hold the position.",
        "consequence_tone": "Facing that direction for too long creates visibility — you become findable from something that navigates by attention.",
        "story_moment": "The narrator catches themselves standing still, staring at the north wall, and realizes they don't remember turning to face it.",
        "tags": ["overnight", "isolated", "confined", "industrial", "utilities",
                 "research", "medical", "government", "wilderness"],
    },

    {
        "id": "R52",
        "name": "THE BACK RULE",
        "template": "When stationary, always position yourself so your back is against a wall or solid surface. Never stand with your back exposed to open space.",
        "consequence_tone": "Open space behind you is where attention enters — things locate the narrator by what is unguarded.",
        "story_moment": "The narrator realizes mid-task that they have been standing in the center of a room for several minutes with nothing at their back.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R53",
        "name": "THE OVERHEAD RULE",
        "template": "Do not look up in [specific area — the atrium / the stairwell / the storage loft] unless there is a specific work reason to do so. If you do look up, complete the task and look away.",
        "consequence_tone": "Looking up creates a line of connection — whatever is above registers it as attention directed upward.",
        "story_moment": "The narrator hears something above them and has to resist looking up while completing the task at hand.",
        "tags": ["industrial", "confined", "overnight", "isolated", "utilities",
                 "research", "government", "entertainment"],
    },

    {
        "id": "R54",
        "name": "THE CORNER ANNOUNCEMENT RULE",
        "template": "Before turning any corner in [specific wing / hallway / section], knock twice on the wall and wait three seconds before proceeding.",
        "consequence_tone": "Corners are where things wait — the knock signals you are coming and allows whatever is there to clear before you arrive.",
        "story_moment": "The narrator is in a hurry and rounds a corner without knocking. They find something that should not be there and back away without making eye contact.",
        "tags": ["confined", "overnight", "medical", "industrial", "government",
                 "utilities", "research", "isolated"],
    },

    {
        "id": "R55",
        "name": "THE CENTER ROOM RULE",
        "template": "Do not stop moving in the center of [specific large room — the main floor / the warehouse bay / the atrium]. Pass through; do not linger.",
        "consequence_tone": "The center of large rooms is the point of maximum visibility from all directions — stopping there broadcasts position.",
        "story_moment": "The narrator's radio cuts out in the center of the room. They stop to check it and realize they have been standing still, completely exposed, for longer than they intended.",
        "tags": ["industrial", "retail", "overnight", "confined", "government",
                 "entertainment", "transit", "utilities"],
    },

    {
        "id": "R56",
        "name": "THE ELEVATOR RULE",
        "template": "After [specific hour], ride the elevator facing away from the doors. Do not turn around until the doors open at your floor.",
        "consequence_tone": "Watching the doors as they open means witnessing what might have entered between floors — not watching means you don't confirm it.",
        "story_moment": "The narrator hears the elevator doors open behind them at an unscheduled floor and has to decide whether to turn around.",
        "tags": ["overnight", "confined", "medical", "government", "retail",
                 "industrial", "transit", "has_residents", "research"],
    },

    {
        "id": "R57",
        "name": "THE DOORWAY RULE",
        "template": "Never stand in any doorway on the premises. Pass through completely or stay on one side. A person standing in a doorway belongs to neither space.",
        "consequence_tone": "Doorways are thresholds — lingering in them makes the narrator unclaimed, which is an invitation.",
        "story_moment": "The narrator stops in a doorway mid-conversation without thinking about it and notices the room temperature change around them.",
        "tags": ["overnight", "confined", "isolated", "industrial", "medical",
                 "government", "utilities", "research", "residential"],
    },

    {
        "id": "R58",
        "name": "THE DESIGNATED SEAT RULE",
        "template": "During breaks, use only the designated break area chair assigned to your shift. Do not sit in chairs assigned to other shifts. If your chair is occupied, stand.",
        "consequence_tone": "Sitting in another shift's place creates a residue — you inherit whatever was left in that position.",
        "story_moment": "The narrator's chair is occupied by something that doesn't immediately register as wrong, and they sit in a different chair without thinking.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "food_service", "confined"],
    },

    # --- Movement & Gait ---

    {
        "id": "R59",
        "name": "THE PACE RULE",
        "template": "Do not run on the premises for any reason. If you feel the urge to run, walk faster. Running signals panic, and panic is a signal that draws attention.",
        "consequence_tone": "Running broadcasts fear as a frequency — it marks the narrator as prey in a space that pays attention to those signals.",
        "story_moment": "Something happens that makes every instinct tell the narrator to run, and they have to force themselves to walk out.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R60",
        "name": "THE CORRIDOR PAUSE RULE",
        "template": "Do not stop moving in [specific hallway / corridor / passage]. If you need to review something, step into a room first.",
        "consequence_tone": "That corridor channels movement — stopping in it breaks the pattern the space expects and marks the narrator as stationary prey.",
        "story_moment": "The narrator's phone buzzes in the corridor and they stop to check it. The lights at the far end go out one by one.",
        "tags": ["confined", "overnight", "industrial", "medical", "government",
                 "utilities", "research", "isolated"],
    },

    {
        "id": "R61",
        "name": "THE RE-ENTRY PAUSE RULE",
        "template": "If you step outside for any reason, wait at least [specific duration — two minutes / five minutes / until the exterior light changes] before coming back in.",
        "consequence_tone": "Re-entering too quickly brings in whatever was waiting just outside — the pause allows the threshold to reset.",
        "story_moment": "The narrator steps out briefly and comes back before the window is up. They notice they are being followed room to room for the rest of the shift.",
        "tags": ["overnight", "isolated", "industrial", "confined", "utilities",
                 "research", "government", "wilderness", "medical"],
    },

    {
        "id": "R62",
        "name": "THE ESTABLISHED PATH RULE",
        "template": "Use only the established routes between [specific areas]. Do not take shortcuts through unmarked or rarely-used spaces.",
        "consequence_tone": "Unmarked routes haven't been walked enough to be claimed — using them for the first time makes the narrator the first person it has ever noticed there.",
        "story_moment": "The narrator takes a shortcut through a rarely-used section to save time and realizes partway through that no one has walked this particular path in a very long time.",
        "tags": ["industrial", "overnight", "confined", "isolated", "utilities",
                 "government", "research", "medical", "wilderness"],
    },

    {
        "id": "R63",
        "name": "THE LAST OUT RITUAL",
        "template": "Whoever leaves last must perform the following before exiting: [specific sequence — check every light switch / say each room aloud / walk the perimeter once]. Do not leave without completing it.",
        "consequence_tone": "The ritual is a closing of the space — skipping it leaves something inside that has no reason to stop waiting.",
        "story_moment": "The narrator is last out, rushed, skips a step in the ritual, and is halfway home before they realize what they forgot.",
        "tags": ["overnight", "isolated", "confined", "industrial", "utilities",
                 "government", "research", "medical", "retail"],
    },

    # --- Communication & Language ---

    {
        "id": "R64",
        "name": "THE DEPARTURE PHRASE RULE",
        "template": "Do not say goodbye, see you later, or any farewell when leaving the premises. The departure phrase is [specific phrase]. Use only that.",
        "consequence_tone": "Casual farewells create an expectation of return — something uses that expectation as a claim.",
        "story_moment": "A coworker says a casual goodbye to the narrator as they leave. The narrator doesn't correct them in time and drives home with a feeling they can't explain.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R65",
        "name": "THE APOLOGY RULE",
        "template": "Do not say sorry, I'm sorry, or any apology while on the premises. If you make an error, correct it without comment.",
        "consequence_tone": "Apologies create obligation — they acknowledge fault in a space that can hold that acknowledgment against you.",
        "story_moment": "The narrator bumps into something and reflexively says sorry before they remember the rule. The temperature drops noticeably.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R66",
        "name": "THE HISTORY QUESTION RULE",
        "template": "Do not ask what happened in [specific room / to a specific previous employee / before you were hired]. If a coworker brings it up, change the subject.",
        "consequence_tone": "Asking creates a ritual of telling — and whatever happened here registers when the story is repeated on the premises.",
        "story_moment": "A coworker starts to tell the narrator what happened to the last person in this position. The narrator stops them. The coworker looks relieved.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated", "has_records"],
    },

    {
        "id": "R67",
        "name": "THE SURNAME RULE",
        "template": "If asked your name while on the premises, give only your first name. Do not give your surname, your employee number, or any identifier that extends beyond the site.",
        "consequence_tone": "A full name establishes a claim that travels beyond the site — a first name is enough to do the job without being claimable.",
        "story_moment": "A visitor asks for the narrator's full name for a form. The narrator instinctively gives it and realizes immediately.",
        "tags": ["public_facing", "retail", "medical", "transit", "government",
                 "food_service", "entertainment", "has_residents", "overnight"],
    },

    {
        "id": "R68",
        "name": "THE PROMISE RULE",
        "template": "Do not make promises while on the premises — not to coworkers, not to customers, not aloud to yourself. Use will instead of promise.",
        "consequence_tone": "A promise made here creates a binding that the premises can hold you to — it doesn't matter what the promise was about.",
        "story_moment": "The narrator tells a distressed customer 'I promise we'll get this sorted.' The words land wrong and they feel something shift in the room.",
        "tags": ["public_facing", "retail", "medical", "food_service", "government",
                 "has_residents", "transit", "overnight", "has_staff"],
    },

    {
        "id": "R69",
        "name": "THE AFTER-HOURS PHONE RULE",
        "template": "If a phone rings on the premises after [specific hour], do not answer it. Let it ring. If it stops and immediately starts again, leave the area.",
        "consequence_tone": "Calls after hours are not from outside — they originate from something that learned how to use the system.",
        "story_moment": "The phone rings four times. Stops. Rings again before the silence finishes. The narrator is already moving.",
        "tags": ["overnight", "isolated", "confined", "has_equipment", "government",
                 "medical", "utilities", "research", "industrial"],
    },

    {
        "id": "R70",
        "name": "THE SILENT COUNT RULE",
        "template": "Never count aloud on the premises. All counting — inventory, rooms, people — must be done silently. Written tallies are acceptable.",
        "consequence_tone": "Counting aloud assigns numbers to things in the space — including things the narrator didn't intend to count.",
        "story_moment": "The narrator counts items aloud without thinking. When they finish, the number is wrong. They don't know when it changed.",
        "tags": ["retail", "industrial", "medical", "overnight", "government",
                 "utilities", "research", "confined", "has_records"],
    },

    {
        "id": "R71",
        "name": "THE SHIFT START PHRASE RULE",
        "template": "On arriving at the start of every shift, say the following phrase aloud before doing anything else: [specific phrase]. You do not need to understand it.",
        "consequence_tone": "The phrase is a marker — it tells whatever occupies the space that a worker with authorization has arrived.",
        "story_moment": "The narrator forgets the phrase on a rushed morning and realizes partway through the shift that the space feels different — like it hasn't registered them yet.",
        "tags": ["overnight", "isolated", "industrial", "confined", "utilities",
                 "research", "government", "medical", "wilderness"],
    },

    {
        "id": "R72",
        "name": "THE DENIAL RULE",
        "template": "If asked directly whether you have seen or heard anything unusual, say no. Do not qualify, hedge, or describe what you saw. Just no.",
        "consequence_tone": "Describing an anomaly to an unauthorized person gives it more definition than it currently has — it becomes more real each time it is described.",
        "story_moment": "A coworker asks the narrator if they've noticed anything strange lately. The narrator says no and feels the weight of the silence afterward.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    # --- Personal & Body ---

    {
        "id": "R73",
        "name": "THE SCENT RULE",
        "template": "Do not wear any fragrance — perfume, cologne, scented lotion — on the premises. Wear only unscented products.",
        "consequence_tone": "Scent marks a trail — fragrance left in a space lingers far longer than the person who wore it and something uses that residue as a map.",
        "story_moment": "The narrator realizes partway through the shift they forgot and wore scented product. They become aware of being followed room to room for the rest of the night.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R74",
        "name": "THE BLEEDING RULE",
        "template": "If you bleed anywhere on the premises — even a small cut — clean it immediately with the kit provided and leave for the remainder of your shift. No exceptions.",
        "consequence_tone": "Blood in the space is a marker of presence far more specific than a name — leaving before the shift ends prevents it from being used as a claim.",
        "story_moment": "The narrator cuts a finger on packaging material. They remember the rule and look at the clock. They have four hours left.",
        "tags": ["industrial", "overnight", "isolated", "confined", "medical",
                 "utilities", "research", "food_service", "wilderness"],
    },

    {
        "id": "R75",
        "name": "THE SLEEP RULE",
        "template": "Do not fall asleep anywhere on the premises except the designated rest area. If you wake up anywhere else, do not move until you have spoken your name aloud.",
        "consequence_tone": "Sleep in an undesignated area breaks the boundary between worker and space — waking without anchoring yourself leaves part of you behind.",
        "story_moment": "The narrator dozes off in a break chair outside the designated area and wakes up in the dark, disoriented. They say their name before they move.",
        "tags": ["overnight", "isolated", "industrial", "confined", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R76",
        "name": "THE LAUGH RULE",
        "template": "Do not laugh out loud when alone anywhere on the premises. Smiling is fine. Laughter alone in an empty space is an invitation.",
        "consequence_tone": "Spontaneous laughter in an empty space sounds like a response — it signals to whatever is listening that a connection was made.",
        "story_moment": "The narrator reads something funny on their phone during a solo round and laughs before they catch themselves. The lights at the end of the hall flicker once.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R77",
        "name": "THE REFLECTIVE SURFACE RULE",
        "template": "Do not touch the glass of any window, mirror, or reflective surface after [specific hour]. If a surface has a handprint already on it that you didn't make, cover it.",
        "consequence_tone": "Touch on a reflective surface from the outside and touch from the inside create the same mark — contact becomes mutual.",
        "story_moment": "The narrator finds a handprint on the inside of a window that faces an area no one should have accessed. They cover it with paper and don't look at it again.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "residential"],
    },

    # --- Objects & Materials ---

    {
        "id": "R78",
        "name": "THE COLOR RESTRICTION RULE",
        "template": "Do not bring any items that are [specific color — red / white / yellow] onto the premises. This includes clothing, accessories, food packaging, or personal items.",
        "consequence_tone": "That color is a signal in this space — it marks the person carrying it as either a target or an offering.",
        "story_moment": "The narrator realizes their coffee cup is the restricted color. They put it in their bag, out of sight. The shift proceeds differently from that point.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R79",
        "name": "THE ORGANIC MATERIAL RULE",
        "template": "Do not bring cut flowers, potted plants, or fresh produce into [specific area]. Sealed packaged food is acceptable.",
        "consequence_tone": "Living organic material in that space feeds something — its presence shortens the cycle between visits.",
        "story_moment": "A coworker brings flowers for the break room. The narrator moves them outside without explaining why. The coworker asks questions the narrator cannot answer.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R80",
        "name": "THE ODD NUMBER RULE",
        "template": "When storing or arranging items in [specific area], always leave them in odd numbers. Never leave exactly two of anything together.",
        "consequence_tone": "Two identical things create a pair — pairs attract attention and invite a third.",
        "story_moment": "The narrator counts the items they've staged and finds an even number. They separate one and carry it to another area, unable to explain why this matters so much to them.",
        "tags": ["retail", "industrial", "overnight", "confined", "utilities",
                 "research", "government", "medical", "has_records"],
    },

    {
        "id": "R81",
        "name": "THE UNATTENDED BELONGINGS RULE",
        "template": "Do not leave your personal bag, coat, or belongings unattended anywhere on the premises. Keep them with you or locked in your designated locker.",
        "consequence_tone": "Unattended belongings are an open invitation — whatever picks them up or examines them gains access to their owner.",
        "story_moment": "The narrator leaves their bag in the break room while handling something urgent and returns to find it exactly as they left it, except for one small displaced item.",
        "tags": ["overnight", "industrial", "retail", "medical", "confined",
                 "government", "transit", "food_service", "has_staff"],
    },

    {
        "id": "R82",
        "name": "THE CLOCK DISCREPANCY RULE",
        "template": "If you find a clock on the premises showing a different time than the others, do not correct it. Note the time it shows and keep that note on your person for the remainder of the shift.",
        "consequence_tone": "A stopped or wrong clock is showing the time something happened — carrying that knowledge keeps the narrator adjacent to the event rather than inside it.",
        "story_moment": "The narrator finds a clock showing 3:17am in a place that should have been empty at that hour. They write it down and spend the rest of the shift trying not to wonder what happened then.",
        "tags": ["overnight", "confined", "isolated", "industrial", "medical",
                 "utilities", "research", "government", "residential"],
    },

    {
        "id": "R83",
        "name": "THE PERSONAL PHOTOGRAPH RULE",
        "template": "Do not bring photographs of family, friends, or any person you recognize into the premises. Photographs of landscapes or objects are acceptable.",
        "consequence_tone": "A photograph of a known person in this space creates a connection from the site to that person — the site now knows they exist.",
        "story_moment": "The narrator realizes their phone wallpaper is a photo of someone they love. They change it to a solid color for the duration of every shift.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "wilderness"],
    },

    {
        "id": "R84",
        "name": "THE FOUND OBJECT RULE",
        "template": "If you find any object left in a specific location for you — a note, a gift, a tool, food — do not touch it. Photograph it, place a marker near it, and report it. Do not read the note.",
        "consequence_tone": "Objects left specifically for you carry an invitation embedded in their placement — touching them accepts the terms.",
        "story_moment": "The narrator finds a small object placed precisely in front of their locker. It is something only they would recognize. They photograph it without touching it and feel sick.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R85",
        "name": "THE KEY DUPLICATION RULE",
        "template": "Your access key must not be duplicated. One copy exists. If it is lost, report immediately and do not return to work until a replacement is issued through the formal process.",
        "consequence_tone": "A duplicate key creates a second path into the space under your name — anything can use that path.",
        "story_moment": "The narrator loses their key, finds it again in a place they're certain they didn't leave it, and has to decide whether to report it.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "has_staff"],
    },

    # --- Environmental & Sensory ---

    {
        "id": "R86",
        "name": "THE RAIN PROTOCOL RULE",
        "template": "During [specific weather event — heavy rain / electrical storm / fog above a certain density], all exterior-facing doors must be locked and remain locked until the event passes. Deliveries and arrivals wait outside.",
        "consequence_tone": "Weather events create cover for movement — things that are normally visible during clear conditions become undetectable and use that cover.",
        "story_moment": "A storm comes in fast and the narrator realizes they've left a loading door propped open. They go back and find it closed from the inside.",
        "tags": ["industrial", "overnight", "isolated", "confined", "utilities",
                 "wilderness", "government", "research", "medical"],
    },

    {
        "id": "R87",
        "name": "THE WATER LEVEL RULE",
        "template": "Monitor the water level marker at [specific location]. If the water rises above [specific mark], do not proceed to the lower level for the rest of the shift.",
        "consequence_tone": "Rising water brings things from below that the structure normally keeps separate — the marker exists because someone learned where the boundary is.",
        "story_moment": "The narrator checks the marker and finds it at exactly the threshold. They watch it for a long moment, trying to determine if it is still rising.",
        "tags": ["industrial", "utilities", "overnight", "isolated", "confined",
                 "wilderness", "research", "government"],
    },

    {
        "id": "R88",
        "name": "THE NEW DISCOLORATION RULE",
        "template": "If you notice new staining, discoloration, or markings on the walls, floor, or ceiling that were not there in the previous shift, photograph and report them. Do not approach within arm's reach.",
        "consequence_tone": "New marks indicate something that left a residue — proximity to a fresh mark is proximity to whatever made it.",
        "story_moment": "The narrator finds a dark stain on the wall in a place they walked past two hours ago. It was not there before. It is shaped in a way that is hard to look at directly.",
        "tags": ["overnight", "industrial", "confined", "isolated", "medical",
                 "utilities", "research", "government", "residential"],
    },

    {
        "id": "R89",
        "name": "THE COLD SPOT RULE",
        "template": "If a room feels noticeably colder than the adjacent rooms — not drafty, just cold — do not enter alone. Return with another person or leave it for the next shift.",
        "consequence_tone": "Isolated cold is a displacement — something is occupying that space and the temperature reflects what it takes out of the air.",
        "story_moment": "The narrator opens a door and feels the cold hit them immediately. The room beyond looks completely normal. They stand in the doorway and realize they cannot see their breath.",
        "tags": ["overnight", "confined", "isolated", "industrial", "medical",
                 "utilities", "research", "government", "residential"],
    },

    {
        "id": "R90",
        "name": "THE FOOTPRINT RULE",
        "template": "If you find footprints in dust or debris in an area that should have had no traffic, do not follow them. Note direction and report.",
        "consequence_tone": "Following a trail in this space is not the same as following a trail outside — moving in the same direction as the prints puts you on the same path as what made them.",
        "story_moment": "The narrator finds clear prints in the dust heading into a corridor that dead-ends. They note them down and do not look to see if anything is standing at the end.",
        "tags": ["industrial", "overnight", "isolated", "confined", "utilities",
                 "research", "government", "wilderness", "has_records"],
    },

    {
        "id": "R91",
        "name": "THE VIBRATION RULE",
        "template": "If you feel vibrations in the floor with no identifiable equipment source, stop what you are doing and move to the designated holding area. Wait until it stops.",
        "consequence_tone": "Unaccounted vibration means something is moving in the structure in a way that isn't supposed to be possible — the holding area has been verified to be outside that range.",
        "story_moment": "The narrator feels the vibration start under their feet and realizes they are not near any machinery. They walk to the holding area and count the seconds until it stops.",
        "tags": ["industrial", "overnight", "confined", "isolated", "utilities",
                 "research", "government", "underground"],
    },

    {
        "id": "R92",
        "name": "THE WRONG LIGHT RULE",
        "template": "If the natural light entering the building looks wrong — wrong color, wrong angle for the time of day, wrong intensity — check all exterior entry points immediately and report.",
        "consequence_tone": "Anomalous natural light indicates the exterior is not presenting correctly — something is altering what the building receives from outside.",
        "story_moment": "The narrator notices the sunlight coming through a window is amber at midday. They check the sky directly and it looks normal. The light through the glass does not.",
        "tags": ["overnight", "isolated", "confined", "industrial", "utilities",
                 "research", "government", "medical", "wilderness"],
    },

    {
        "id": "R93",
        "name": "THE STATIC RULE",
        "template": "If you receive static discharge in the same area more than twice in one shift, leave that area and do not return during that shift.",
        "consequence_tone": "Repeated static in a fixed location is a sign of concentrated attention — something in that spot is registering the narrator's presence very precisely.",
        "story_moment": "The narrator gets a second shock from the same filing cabinet. They step back and notice the hair on their arms is still standing.",
        "tags": ["industrial", "overnight", "confined", "has_equipment", "utilities",
                 "research", "government", "medical", "isolated"],
    },

    # --- Staff & Institutional ---

    {
        "id": "R94",
        "name": "THE OUTGOING SHIFT RULE",
        "template": "Do not ask the outgoing shift why they look the way they look. Take the keys. Say the departure phrase. Begin your shift.",
        "consequence_tone": "The question creates a story — and a story told on-site while the incident is still fresh can reopen it.",
        "story_moment": "The narrator takes the keys from someone who is visibly shaking. They say the departure phrase and watch the person leave without making eye contact.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R95",
        "name": "THE NO-CALL ABSENCE RULE",
        "template": "If a coworker doesn't appear for their shift and doesn't call, do not cover their station. Leave it empty and log the absence. Do not attempt to contact them.",
        "consequence_tone": "A station left empty is a statement that someone is missing — covering it erases that statement and allows the absence to go unnoticed.",
        "story_moment": "The narrator is told to just cover the missing coworker's station for tonight. They remember the rule and refuse without being able to explain why.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R96",
        "name": "THE LEFT BELONGINGS RULE",
        "template": "If a former employee left personal items — a coat, a mug, a photo, anything — do not touch, move, or discard them. Log their location and leave them.",
        "consequence_tone": "Personal items left behind hold a claim on the space — moving them on behalf of someone who may not have intended to leave can transfer what they were carrying.",
        "story_moment": "The narrator finds a personal item they recognize from weeks ago when the last person in this position disappeared. It is sitting in exactly the spot they described.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated", "has_records"],
    },

    {
        "id": "R97",
        "name": "THE SHIFT SWAP RULE",
        "template": "If a coworker asks to swap shifts with you for a specific date, ask why before agreeing. If they cannot or will not explain, do not swap.",
        "consequence_tone": "A shift swap request for a specific date means the person asking knows what happens that night — their reason for wanting out is the reason the narrator should know.",
        "story_moment": "A coworker asks to swap for a date three weeks out. When the narrator asks why, the coworker says they just have a feeling. The narrator agrees anyway.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R98",
        "name": "THE WRITTEN RULE RULE",
        "template": "If your supervisor gives you a verbal instruction that contradicts the written guidelines, follow the written guidelines. Do not confront; simply comply with what is written.",
        "consequence_tone": "Verbal instructions can be given under duress or under influence — the written rules exist precisely because they were set when the situation was clear.",
        "story_moment": "The narrator's supervisor tells them to ignore a specific rule tonight. Just this once. The narrator nods, then follows the rule anyway. The supervisor doesn't mention it.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R99",
        "name": "THE VISITOR COUNT RULE",
        "template": "Every visitor receives a badge at entry. At the end of each shift, count the returned badges. The number returned must equal the number issued. If it does not, do not leave.",
        "consequence_tone": "A badge not returned means someone is still on the premises — or something is using that unaccounted presence as cover.",
        "story_moment": "The narrator counts the badges at the end of the shift. One is missing. They check the visitor log. The name on the last entry is a person who was signed in six months ago.",
        "tags": ["public_facing", "government", "medical", "industrial", "research",
                 "overnight", "has_records", "transit", "confined"],
    },

    {
        "id": "R100",
        "name": "THE CAMERA DOWN RULE",
        "template": "If a security camera goes offline, note it in the log but do not attempt to diagnose or repair it yourself. Work as if it is still recording.",
        "consequence_tone": "A camera going offline in a specific location at a specific time is not random — things that need cameras down know how to take them down.",
        "story_moment": "The narrator notices camera three has been offline since the start of the shift. Camera three covers the corridor they've been walking past every hour.",
        "tags": ["overnight", "confined", "industrial", "medical", "government",
                 "utilities", "research", "has_equipment", "has_records"],
    },

    # --- Documentation & Records ---

    {
        "id": "R101",
        "name": "THE ERASURE RULE",
        "template": "If you find an erased or overwritten entry in the log, note its location in your own entry. Do not attempt to read the original. Do not ask who wrote it.",
        "consequence_tone": "Something was removed from the record for a reason — trying to recover it reopens the same question that got it removed.",
        "story_moment": "The narrator holds the log page up to the light and can almost make out what was written underneath the correction. They put it down before they can read it.",
        "tags": ["has_records", "overnight", "industrial", "medical", "government",
                 "utilities", "research", "confined", "isolated"],
    },

    {
        "id": "R102",
        "name": "THE OLD INCIDENT RULE",
        "template": "Any incident report filed more than [specific period — six months / two years] ago is sealed. Do not request, reference, or search for it.",
        "consequence_tone": "Old incidents were sealed because reading them on-site reactivates what they described — the file is a precise account of something that can happen again.",
        "story_moment": "The narrator finds a reference to an old incident report in a current file. The date is [specific]. They close the file before finding the report number.",
        "tags": ["has_records", "government", "medical", "industrial", "research",
                 "overnight", "utilities", "confined", "isolated"],
    },

    {
        "id": "R103",
        "name": "THE BACKDATING RULE",
        "template": "Never backdate a log entry. If you missed a recording window, leave it blank and note the gap. Do not fill it in retroactively, even with accurate information.",
        "consequence_tone": "A backdated entry creates a false record of where you were — the space uses records as maps, and a false record puts you in a place you weren't.",
        "story_moment": "The narrator misses an entry during a chaotic hour and is tempted to fill it in from memory. They leave the gap blank and write the real time alongside it.",
        "tags": ["has_records", "government", "medical", "industrial", "research",
                 "overnight", "utilities", "confined", "isolated"],
    },

    {
        "id": "R104",
        "name": "THE COPY RULE",
        "template": "Do not make personal copies of any on-site documentation — not photographs, not handwritten transcriptions, not digital scans. Information belongs to the premises.",
        "consequence_tone": "A copy taken off-site carries a fragment of the space with it — it becomes a door that can be opened from either direction.",
        "story_moment": "The narrator wants to remember one specific rule and starts to photograph the posted sheet. They stop halfway through and close their phone.",
        "tags": ["has_records", "government", "medical", "industrial", "research",
                 "overnight", "utilities", "confined", "isolated"],
    },

    {
        "id": "R105",
        "name": "THE SOLO INCIDENT RULE",
        "template": "Any unusual event requiring a report must be witnessed by at least one other person. A report filed by a lone witness goes into the secondary log, not the primary.",
        "consequence_tone": "A solo account of something that cannot be verified is an invitation — an unconfirmed incident has room to grow in the gap between what happened and what can be proven.",
        "story_moment": "The narrator experiences something undeniable and finds no one else saw it. They file in the secondary log and feel the inadequacy of it.",
        "tags": ["has_staff", "has_records", "overnight", "industrial", "medical",
                 "utilities", "government", "research", "confined"],
    },

    # --- Threshold & Exit ---

    {
        "id": "R106",
        "name": "THE PROPPED DOOR RULE",
        "template": "Never prop a door open on the premises. If you need both hands free, set the item down on one side and retrieve it after crossing.",
        "consequence_tone": "A propped door is an unclosed threshold — it holds the boundary open indefinitely, and something that cannot cross a closed door has no such restriction here.",
        "story_moment": "The narrator props a door with their foot while carrying supplies and feels an immediate wrongness — they let the door close and carry the items in two trips.",
        "tags": ["overnight", "isolated", "confined", "industrial", "medical",
                 "utilities", "research", "government", "residential"],
    },

    {
        "id": "R107",
        "name": "THE BASEMENT ENTRY RULE",
        "template": "If the basement door is found unlocked at shift start, lock it without opening it to check inside. Log that it was found unlocked. Do not investigate why.",
        "consequence_tone": "The basement door being unlocked means something got out, not that someone got in — opening it to check confirms that the space is now empty.",
        "story_moment": "The narrator locks the door, makes the note, and spends the rest of the shift listening for the sound of something that shouldn't be upstairs.",
        "tags": ["confined", "overnight", "industrial", "isolated", "medical",
                 "utilities", "research", "government", "residential"],
    },

    {
        "id": "R108",
        "name": "THE ROOF CHECK RULE",
        "template": "At [specific time — 11:00pm / 2:00am], check the roof access door. If it is unlocked, lock it. Do not look up before securing it. Do not check what may be on the roof.",
        "consequence_tone": "The roof is where things wait between arrival and entry — looking up before locking the door shows them you know they're there.",
        "story_moment": "The narrator locks the roof door and feels something shift its weight on the other side. They complete the motion and walk away without looking up.",
        "tags": ["overnight", "isolated", "confined", "industrial", "utilities",
                 "research", "government", "medical"],
    },

    {
        "id": "R109",
        "name": "THE LOADING DOCK RULE",
        "template": "Secure the loading dock before dark. If you arrive and it is already secured, do not open it to verify the interior. Log that it was pre-secured and move on.",
        "consequence_tone": "A pre-secured loading dock means something was inside that needed to be contained — opening it to check releases the containment.",
        "story_moment": "The narrator arrives at the loading dock and finds the roll door down and padlocked from the outside. They remember the rule and write the time in the log.",
        "tags": ["industrial", "retail", "overnight", "confined", "utilities",
                 "government", "food_service", "transit"],
    },

    {
        "id": "R110",
        "name": "THE INTERIOR WINDOW RULE",
        "template": "Internal observation windows between rooms may not be used after [specific hour]. Cover them from your side before that time.",
        "consequence_tone": "Interior windows work both directions — after a certain hour, using them to look in means being looked out at from a room that should be empty.",
        "story_moment": "The narrator forgets to cover the observation window and glances through it late in the shift. The room on the other side is dark. They cover the glass without looking longer.",
        "tags": ["medical", "confined", "overnight", "government", "research",
                 "industrial", "utilities", "has_residents", "isolated"],
    },

    {
        "id": "R111",
        "name": "THE SERVICE ENTRANCE RULE",
        "template": "Do not use the service entrance alone. If no one is available to accompany you, use the main entrance regardless of inconvenience.",
        "consequence_tone": "The service entrance is less monitored and less traveled — the lack of witnesses is exactly why something prefers to operate there.",
        "story_moment": "The narrator is running late and considers using the service entrance to save time. They go around to the main entrance and arrive two minutes later than they would have.",
        "tags": ["industrial", "retail", "overnight", "confined", "government",
                 "food_service", "transit", "medical", "utilities"],
    },

    # --- Anomaly & Exception ---

    {
        "id": "R112",
        "name": "THE REPEAT VISITOR RULE",
        "template": "If the same visitor comes two days in a row asking for the same person or service that is unavailable, notify management. On the third day, do not engage with them.",
        "consequence_tone": "A visitor who returns under the same false premise twice is not confused — they are testing whether the obstruction has changed, and on the third attempt they may not need it to have.",
        "story_moment": "The narrator sees the same person at the desk for the third day and remembers the rule. They ask a coworker to handle it without explaining. The visitor leaves without being spoken to.",
        "tags": ["public_facing", "retail", "medical", "government", "transit",
                 "overnight", "has_records", "food_service", "entertainment"],
    },

    {
        "id": "R113",
        "name": "THE MOVED FURNITURE RULE",
        "template": "If furniture or equipment has been moved overnight from its established position, log it but do not move it back. Work around it.",
        "consequence_tone": "Something moved it for a reason that made sense in the context of what the space is — moving it back undoes a change the space made intentionally.",
        "story_moment": "The narrator arrives to find a heavy industrial shelf moved six inches from the wall, facing a different direction. There are no wheel marks. They work around it.",
        "tags": ["industrial", "overnight", "confined", "isolated", "medical",
                 "utilities", "research", "government", "retail"],
    },

    {
        "id": "R114",
        "name": "THE LOCKED FROM INSIDE RULE",
        "template": "If a room that should be empty is locked from the inside, do not attempt to open it. Mark the door and note the time. Come back at the end of the shift; if still locked, report and do not investigate.",
        "consequence_tone": "A room locked from the inside by something that should not be there is a negotiated barrier — forcing it open breaks the negotiation.",
        "story_moment": "The narrator marks the door at 11pm and returns at 6am. The room is unlocked. Whatever was inside is gone. Nothing inside has been touched.",
        "tags": ["confined", "overnight", "isolated", "industrial", "medical",
                 "utilities", "research", "government", "residential"],
    },

    {
        "id": "R115",
        "name": "THE HANDWRITTEN NOTES RULE",
        "template": "If you find handwritten notes anywhere on the premises that are not part of the official log, do not read them. Place them in the sealed collection envelope at the front desk.",
        "consequence_tone": "Notes left outside the official record are messages — reading them on-site completes the delivery and establishes the narrator as the recipient.",
        "story_moment": "The narrator finds a note tucked under a keyboard. The first word is their name. They fold it without reading further and walk it to the envelope.",
        "tags": ["has_records", "overnight", "confined", "isolated", "industrial",
                 "medical", "government", "utilities", "research"],
    },

    {
        "id": "R116",
        "name": "THE RECORDING DISCREPANCY RULE",
        "template": "If a security recording shows you in a location during a time you were not there, report it immediately. Do not try to account for it or explain it to the responding officer.",
        "consequence_tone": "A recording of someone in a place they weren't is not a technical error — it is documentation that something was using their appearance.",
        "story_moment": "The narrator reviews footage after a reported incident and sees themselves walking a corridor at 2am. They were at home at 2am. They call it in without watching further.",
        "tags": ["has_records", "overnight", "has_equipment", "government", "medical",
                 "industrial", "research", "confined", "utilities"],
    },

    {
        "id": "R117",
        "name": "THE ECHO RULE",
        "template": "If your footsteps echo in an area where they normally don't, stop walking and stand still for thirty seconds before continuing.",
        "consequence_tone": "An echo in a space that never echoed means the acoustic geometry has changed — something has altered the space or is occupying it in a way that changes how sound moves.",
        "story_moment": "The narrator hears their own footsteps reflecting back from an empty concrete floor that has never echoed in months of working there. They stop. Wait. The echoes don't stop when they do.",
        "tags": ["overnight", "confined", "isolated", "industrial", "utilities",
                 "research", "government", "medical", "wilderness"],
    },

    {
        "id": "R118",
        "name": "THE OCCUPANCY COUNTER RULE",
        "template": "If the occupancy counter shows more people in the building than are signed in, do not take a headcount yourself. Note the discrepancy and contact the supervisor.",
        "consequence_tone": "The counter counts presence, not personnel — a discrepancy means something is present that did not enter through a monitored access point.",
        "story_moment": "The narrator checks the counter: 4 in the building. They count the people they can account for: 3. They call the supervisor and wait for instructions.",
        "tags": ["government", "medical", "industrial", "confined", "has_equipment",
                 "overnight", "research", "utilities", "has_records"],
    },

    {
        "id": "R119",
        "name": "THE MISSED APPOINTMENT RULE",
        "template": "If someone scheduled for pickup, delivery, or appointment doesn't arrive within [specific window], log the no-show and move on. Do not call to follow up.",
        "consequence_tone": "Following up on a missed appointment creates contact with whatever intercepted that person — the question of where they are may get an answer.",
        "story_moment": "The narrator waits the full window, logs the missed appointment, and spends the rest of the shift not checking whether a message came in.",
        "tags": ["public_facing", "government", "medical", "transit", "retail",
                 "food_service", "overnight", "has_records", "industrial"],
    },

    {
        "id": "R120",
        "name": "THE FAMILIAR STRANGER RULE",
        "template": "If someone addresses you as if they know you but you do not recognize them, do not confirm or deny how you know them. Treat the interaction as a case of mistaken identity and disengage politely.",
        "consequence_tone": "Confirming a false familiarity grants it validity — whatever is using that false recognition to approach the narrator has less purchase if it is never acknowledged.",
        "story_moment": "Someone at the entrance calls the narrator by name and acts like they've met before. The narrator doesn't recognize them. They respond with generic pleasantries and end the interaction without confirming anything.",
        "tags": ["public_facing", "retail", "medical", "transit", "government",
                 "food_service", "entertainment", "overnight", "has_residents"],
    },

    {
        "id": "R121",
        "name": "THE EQUIPMENT FAILURE MODE RULE",
        "template": "If equipment fails in a way you have never seen before — not a known error, not something the manual covers — do not attempt to fix it. Power it down using the emergency procedure and wait.",
        "consequence_tone": "An unprecedented failure mode is not a mechanical problem — it is the equipment registering something the manufacturer never accounted for.",
        "story_moment": "A machine produces an output that is physically impossible given its inputs. The narrator hits the emergency shutoff and writes the description down while they still have words for it.",
        "tags": ["industrial", "has_equipment", "overnight", "utilities", "research",
                 "medical", "government", "confined", "isolated"],
    },

    {
        "id": "R122",
        "name": "THE FULL SIGNATURE RULE",
        "template": "Do not sign your full legal name on any document that will remain on the premises overnight. Use initials or a work designation.",
        "consequence_tone": "A full legal name in a document left in this space overnight gives the space access to something more complete than a first name alone provides.",
        "story_moment": "The narrator signs a form and realizes too late it was their full name. They cross it out and initial it, hoping that's sufficient.",
        "tags": ["government", "has_records", "medical", "industrial", "research",
                 "overnight", "utilities", "confined", "isolated"],
    },

    {
        "id": "R123",
        "name": "THE WAITING AREA RULE",
        "template": "If someone is in the public waiting area after closing time, do not approach them alone. Alert a coworker first. If no coworker is available, do not approach.",
        "consequence_tone": "Someone present after hours who has not left is either waiting for a specific thing to happen or has no way to leave — neither situation benefits from approach.",
        "story_moment": "The narrator is alone and sees a figure seated in the waiting area after everyone else has gone. They do not approach. They complete closing from the other side of the desk.",
        "tags": ["public_facing", "retail", "medical", "government", "transit",
                 "overnight", "has_residents", "entertainment", "food_service"],
    },

    {
        "id": "R124",
        "name": "THE DRAIN INSPECTION RULE",
        "template": "At shift start, check all floor drains in [specific area]. If any drain is covered with anything that was not placed there by maintenance, uncover it using the provided tool — not your hands — and report.",
        "consequence_tone": "Something covering a drain from below is using it as a seal — approaching the coverage with your hands crosses the threshold of the drain.",
        "story_moment": "The narrator finds a drain covered with a flat piece of material that has no obvious source. They use the hook to lift it and find it was held down from underneath.",
        "tags": ["industrial", "medical", "utilities", "overnight", "confined",
                 "food_service", "government", "research", "isolated"],
    },

    {
        "id": "R125",
        "name": "THE REPEATED COMPLAINT RULE",
        "template": "If a resident or patient makes the same specific complaint three shifts in a row — not a variation, the exact same complaint — escalate to the supervisor rather than addressing it yourself.",
        "consequence_tone": "A repeated identical complaint is not a symptom — it is a message that the person has been coached to deliver, and whoever is coaching them is listening to the responses.",
        "story_moment": "A resident says the same specific phrase for the third night. The narrator does not respond to it, writes it down word for word, and calls the supervisor.",
        "tags": ["medical", "has_residents", "overnight", "government", "residential",
                 "has_staff", "confined", "isolated"],
    },

    {
        "id": "R126",
        "name": "THE CLOSING SCRIPT RULE",
        "template": "When making the closing announcement, use only the exact written script. Do not improvise, do not add personal phrasing, do not vary the wording.",
        "consequence_tone": "The closing script is calibrated — it tells whoever is in the building that it is time to leave. Improvised language does not carry the same instruction.",
        "story_moment": "The narrator is tired and skips a line of the closing script. They finish the announcement and hear, from somewhere in the building, a door open.",
        "tags": ["retail", "public_facing", "overnight", "entertainment", "transit",
                 "government", "medical", "has_residents", "food_service"],
    },

    {
        "id": "R127",
        "name": "THE MAINTENANCE LOG AWARENESS RULE",
        "template": "At the start of each week, read the previous week's maintenance log before beginning your shift. If any entry is marked with [specific symbol — an asterisk / a bracket / a circle], know the location of that entry before going anywhere.",
        "consequence_tone": "Marked entries are warnings about locations that had something happen — working near them without awareness is working near something that was documented and not resolved.",
        "story_moment": "The narrator sees a circled entry in the maintenance log for the east corridor. They go to the east corridor last and find the work order was never completed.",
        "tags": ["industrial", "has_records", "overnight", "utilities", "confined",
                 "medical", "government", "research", "isolated"],
    },

    {
        "id": "R128",
        "name": "THE OVERTIME DATE RULE",
        "template": "Do not volunteer for overtime on [specific dates — the last Friday of the month / any shift spanning midnight on the 15th]. If assigned, follow the extended protocol.",
        "consequence_tone": "Those dates are when the cycle is closest to the surface — extended presence on those nights increases exposure in proportion to time spent.",
        "story_moment": "The narrator takes overtime on the wrong date because they need the money. By 1am they understand why the rule exists.",
        "tags": ["overnight", "has_staff", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R129",
        "name": "THE NEW EMPLOYEE HOURS RULE",
        "template": "In your first two weeks, do not arrive early or stay late. Work only your assigned hours. Come in, do the job, leave on time.",
        "consequence_tone": "The space has not yet fully registered the new person — unusual hours in the early period create a window of ambiguity that is dangerous.",
        "story_moment": "The narrator stays late on their second week to finish something important. They realize as they leave that they are the only person who knows they stayed.",
        "tags": ["has_staff", "overnight", "industrial", "medical", "utilities",
                 "government", "research", "confined", "isolated"],
    },

    {
        "id": "R130",
        "name": "THE GLASS DISPOSAL RULE",
        "template": "If glass breaks anywhere on the premises during your shift, clean it up yourself before the shift ends. Do not leave it for the incoming crew.",
        "consequence_tone": "Broken glass left overnight is a record of a fracture in the space — the next person who encounters it is the one who has to account for it.",
        "story_moment": "A jar breaks late in the shift and the narrator considers leaving it for the morning crew. They clean it up instead and find a shard that is somehow on the wrong side of the room.",
        "tags": ["industrial", "retail", "food_service", "overnight", "medical",
                 "utilities", "research", "government", "confined"],
    },

    {
        "id": "R131",
        "name": "THE RADIO INTERFERENCE RULE",
        "template": "If your radio or communication device experiences interference in a specific location — static, cutting out, wrong voices — log the location and time. Do not try to boost the signal.",
        "consequence_tone": "Radio interference in a fixed location is not a coverage problem — it is the location actively resisting communication with the outside.",
        "story_moment": "The narrator's radio cuts to static in the same corridor it always does, but this time the static briefly resolves into something that sounds like it is trying to speak.",
        "tags": ["industrial", "has_equipment", "overnight", "isolated", "utilities",
                 "government", "research", "medical", "confined", "wilderness"],
    },

    {
        "id": "R132",
        "name": "THE WINDOW SHADE RULE",
        "template": "All window shades in [specific area] must be drawn before 8pm. If you arrive after that time and any are open, close them. Do not look outside before closing them.",
        "consequence_tone": "An open window at night is two-directional — the rule exists because the view outside has been noted to differ from what should be there.",
        "story_moment": "The narrator arrives late and finds three shades up. They close them quickly, face-in. Through the last one, before it closes, they see the parking lot contains one more car than it should.",
        "tags": ["overnight", "confined", "isolated", "industrial", "medical",
                 "utilities", "research", "government", "residential"],
    },

    {
        "id": "R133",
        "name": "THE ANALOG BACKUP RULE",
        "template": "Keep a handwritten copy of the daily schedule and emergency contacts on your person at all times. Do not rely solely on your phone or the building's system.",
        "consequence_tone": "Digital systems in this building have been known to display incorrect information during certain conditions — handwritten records cannot be altered by the building.",
        "story_moment": "The narrator checks their phone and finds all their contacts show the same number. They pull out the paper copy and verify by calling each one.",
        "tags": ["overnight", "isolated", "has_equipment", "utilities", "government",
                 "medical", "industrial", "research", "confined", "wilderness"],
    },

    {
        "id": "R134",
        "name": "THE UNSOLICITED ADVICE RULE",
        "template": "If a visitor or resident tells you something about the building — its history, what happened here, what to watch out for — listen without confirming. Do not add to the account.",
        "consequence_tone": "Confirming an account of the building's history validates it on-site — the space registers when its past is being acknowledged and responds to attention.",
        "story_moment": "A visitor leans in and begins describing in specific detail something that happened in this building. The narrator listens without nodding and ends the conversation carefully.",
        "tags": ["public_facing", "has_residents", "medical", "government", "retail",
                 "overnight", "entertainment", "transit", "food_service"],
    },

    {
        "id": "R135",
        "name": "THE INCOMPLETE ROUND RULE",
        "template": "If you begin a standard walkthrough round, complete it fully before doing anything else. Do not interrupt a round to answer a call, assist someone, or investigate a sound.",
        "consequence_tone": "An incomplete round leaves a gap in the pattern — the unvisited area becomes the one place the narrator has not verified is clear.",
        "story_moment": "The narrator gets a radio call mid-round and responds. When they return to complete the round, the last section they visited shows signs that something came through after they passed.",
        "tags": ["overnight", "industrial", "confined", "isolated", "medical",
                 "utilities", "government", "research", "has_staff"],
    },

]