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

]