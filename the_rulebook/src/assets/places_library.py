from __future__ import annotations

# ============================================================
# PLACES LIBRARY
# ============================================================
#
# Each place has:
#   - id: unique string identifier
#   - name: display name used in story generation
#   - role: the narrator's job title at this location
#   - category: broad grouping for reference
#   - tags: the place-type tags this location carries
#   - compatible_rules: list of rule IDs that make physical/
#     operational sense at this location
#
# Compatible rules were assigned by matching the place's tags
# against each rule's tags, then manually reviewed to remove
# any rules that would feel forced or generic at that location.
# ============================================================

PLACES_LIBRARY = [

    # -------------------------
    # RETAIL & COMMERCE
    # -------------------------

    {
        "id": "P01",
        "name": "Walmart",
        "role": "overnight stocker",
        "category": "Retail & Commerce",
        "tags": ["retail", "overnight", "public_facing", "has_staff", "has_records", "confined"],
        "compatible_rules": ["R01", "R03", "R05", "R07", "R08", "R09", "R10", "R11",
                             "R13", "R16", "R17", "R19", "R21", "R22", "R23", "R24",
                             "R32", "R36", "R39", "R40", "R43", "R44", "R45", "R46",
                             "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P02",
        "name": "Target",
        "role": "overnight maintenance worker",
        "category": "Retail & Commerce",
        "tags": ["retail", "overnight", "public_facing", "has_staff", "has_records", "confined"],
        "compatible_rules": ["R01", "R03", "R05", "R07", "R08", "R09", "R10", "R11",
                             "R13", "R16", "R17", "R19", "R21", "R22", "R23", "R24",
                             "R32", "R36", "R39", "R40", "R43", "R44", "R45", "R46",
                             "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P03",
        "name": "a 24-hour Walgreens",
        "role": "overnight cashier",
        "category": "Retail & Commerce",
        "tags": ["retail", "overnight", "public_facing", "has_staff", "has_records"],
        "compatible_rules": ["R01", "R05", "R07", "R08", "R09", "R10", "R11", "R13",
                             "R16", "R17", "R19", "R21", "R22", "R23", "R24", "R32",
                             "R36", "R39", "R40", "R44", "R45", "R46", "R48", "R49", "R50"],
    },

    {
        "id": "P04",
        "name": "a pawn shop that never closes",
        "role": "overnight counter clerk",
        "category": "Retail & Commerce",
        "tags": ["retail", "overnight", "public_facing", "has_records", "confined"],
        "compatible_rules": ["R01", "R05", "R07", "R08", "R09", "R10", "R11", "R13",
                             "R15", "R16", "R17", "R19", "R22", "R23", "R24", "R25",
                             "R29", "R36", "R40", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P05",
        "name": "a self-storage facility",
        "role": "overnight attendant",
        "category": "Retail & Commerce",
        "tags": ["retail", "overnight", "isolated", "confined", "has_records"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R09", "R10", "R13", "R14",
                             "R15", "R16", "R17", "R19", "R22", "R23", "R24", "R25",
                             "R31", "R36", "R37", "R40", "R43", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P06",
        "name": "a coin laundromat with an attached office",
        "role": "overnight attendant",
        "category": "Retail & Commerce",
        "tags": ["retail", "overnight", "public_facing", "confined"],
        "compatible_rules": ["R01", "R04", "R05", "R08", "R10", "R11", "R14", "R15",
                             "R17", "R19", "R22", "R24", "R25", "R36", "R40", "R44",
                             "R48", "R49"],
    },

    {
        "id": "P07",
        "name": "a dollar store in a strip mall",
        "role": "overnight stocker",
        "category": "Retail & Commerce",
        "tags": ["retail", "overnight", "public_facing", "has_staff", "confined"],
        "compatible_rules": ["R01", "R05", "R07", "R08", "R09", "R10", "R11", "R17",
                             "R19", "R21", "R22", "R23", "R24", "R32", "R36", "R39",
                             "R40", "R44", "R46", "R48", "R49", "R50"],
    },

    {
        "id": "P08",
        "name": "a flea market that runs overnight on Fridays",
        "role": "overnight security guard",
        "category": "Retail & Commerce",
        "tags": ["retail", "overnight", "public_facing", "isolated", "has_records"],
        "compatible_rules": ["R01", "R05", "R07", "R08", "R09", "R10", "R11", "R13",
                             "R14", "R15", "R17", "R19", "R22", "R23", "R24", "R25",
                             "R36", "R40", "R44", "R48", "R49"],
    },

    {
        "id": "P09",
        "name": "an Amazon fulfillment warehouse",
        "role": "overnight picker",
        "category": "Retail & Commerce",
        "tags": ["retail", "industrial", "overnight", "has_staff", "has_equipment",
                 "has_records", "confined"],
        "compatible_rules": ["R01", "R03", "R07", "R08", "R09", "R10", "R12", "R13",
                             "R16", "R17", "R21", "R22", "R23", "R26", "R27", "R32",
                             "R33", "R37", "R39", "R40", "R43", "R44", "R45", "R46",
                             "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P10",
        "name": "a military surplus store",
        "role": "overnight inventory clerk",
        "category": "Retail & Commerce",
        "tags": ["retail", "overnight", "has_records", "confined"],
        "compatible_rules": ["R01", "R07", "R08", "R09", "R10", "R13", "R15", "R16",
                             "R17", "R19", "R22", "R23", "R24", "R25", "R36", "R40",
                             "R44", "R45", "R48", "R49"],
    },

    # -------------------------
    # FOOD & HOSPITALITY
    # -------------------------

    {
        "id": "P11",
        "name": "a Denny's on a highway exit",
        "role": "overnight cook",
        "category": "Food & Hospitality",
        "tags": ["food_service", "overnight", "public_facing", "has_staff", "transit"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R17", "R19", "R21",
                             "R22", "R24", "R32", "R36", "R39", "R40", "R44", "R46",
                             "R48", "R49", "R50"],
    },

    {
        "id": "P12",
        "name": "a truck stop diner",
        "role": "overnight waitress",
        "category": "Food & Hospitality",
        "tags": ["food_service", "overnight", "public_facing", "has_staff", "transit"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R14", "R17", "R19",
                             "R21", "R22", "R24", "R25", "R32", "R36", "R39", "R40",
                             "R44", "R46", "R48", "R49", "R50"],
    },

    {
        "id": "P13",
        "name": "a Waffle House",
        "role": "overnight cook",
        "category": "Food & Hospitality",
        "tags": ["food_service", "overnight", "public_facing", "has_staff"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R17", "R19", "R21",
                             "R22", "R24", "R32", "R36", "R39", "R40", "R44", "R46",
                             "R48", "R49", "R50"],
    },

    {
        "id": "P14",
        "name": "a hotel concierge desk",
        "role": "overnight front desk clerk",
        "category": "Food & Hospitality",
        "tags": ["overnight", "public_facing", "has_staff", "has_records", "has_residents",
                 "transit", "confined"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R13", "R15", "R16",
                             "R17", "R19", "R21", "R22", "R23", "R24", "R25", "R29",
                             "R32", "R35", "R36", "R39", "R40", "R44", "R45", "R46",
                             "R48", "R49", "R50"],
    },

    {
        "id": "P15",
        "name": "a roadside motel in a small town",
        "role": "overnight desk clerk",
        "category": "Food & Hospitality",
        "tags": ["overnight", "isolated", "public_facing", "has_residents", "confined"],
        "compatible_rules": ["R01", "R04", "R05", "R08", "R10", "R11", "R13", "R15",
                             "R16", "R17", "R19", "R22", "R23", "R24", "R25", "R29",
                             "R35", "R36", "R38", "R40", "R44", "R48", "R49"],
    },

    {
        "id": "P16",
        "name": "a bed and breakfast in a Victorian house",
        "role": "overnight caretaker",
        "category": "Food & Hospitality",
        "tags": ["overnight", "isolated", "residential", "has_residents", "confined"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R10", "R13", "R15", "R16",
                             "R17", "R18", "R19", "R22", "R24", "R25", "R29", "R34",
                             "R35", "R36", "R37", "R40", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P17",
        "name": "a casino buffet kitchen",
        "role": "overnight prep cook",
        "category": "Food & Hospitality",
        "tags": ["food_service", "overnight", "has_staff", "confined"],
        "compatible_rules": ["R01", "R07", "R08", "R10", "R17", "R19", "R21", "R22",
                             "R23", "R27", "R32", "R36", "R39", "R44", "R46", "R47",
                             "R48", "R49", "R50"],
    },

    {
        "id": "P18",
        "name": "a hospital cafeteria",
        "role": "overnight kitchen worker",
        "category": "Food & Hospitality",
        "tags": ["food_service", "overnight", "medical", "has_staff", "confined"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R17", "R19", "R21",
                             "R22", "R27", "R30", "R32", "R36", "R39", "R44", "R46",
                             "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P19",
        "name": "a cruise ship galley",
        "role": "overnight kitchen hand",
        "category": "Food & Hospitality",
        "tags": ["food_service", "overnight", "has_staff", "confined", "isolated"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R10", "R14", "R17", "R19",
                             "R21", "R22", "R25", "R27", "R32", "R36", "R37", "R39",
                             "R44", "R46", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P20",
        "name": "a catering kitchen in a convention center",
        "role": "overnight cleaning crew member",
        "category": "Food & Hospitality",
        "tags": ["food_service", "overnight", "has_staff", "confined", "has_records"],
        "compatible_rules": ["R01", "R07", "R08", "R10", "R13", "R17", "R19", "R21",
                             "R22", "R23", "R36", "R37", "R39", "R40", "R43", "R44",
                             "R46", "R47", "R48", "R49", "R50"],
    },

    # -------------------------
    # MEDICAL & INSTITUTIONAL
    # -------------------------

    {
        "id": "P21",
        "name": "a psychiatric hospital",
        "role": "overnight orderly",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "has_staff", "has_residents", "has_records",
                 "confined", "government"],
        "compatible_rules": ["R01", "R02", "R04", "R05", "R06", "R08", "R10", "R11",
                             "R13", "R16", "R17", "R19", "R20", "R21", "R22", "R25",
                             "R29", "R32", "R35", "R36", "R39", "R40", "R42", "R43",
                             "R44", "R45", "R46", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P22",
        "name": "a nursing home",
        "role": "overnight aide",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "has_staff", "has_residents", "has_records",
                 "confined", "residential"],
        "compatible_rules": ["R01", "R04", "R05", "R06", "R08", "R10", "R11", "R13",
                             "R16", "R17", "R19", "R21", "R22", "R23", "R25", "R29",
                             "R32", "R35", "R36", "R39", "R40", "R42", "R43", "R44",
                             "R45", "R46", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P23",
        "name": "a county morgue",
        "role": "overnight attendant",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "government", "has_records", "confined", "isolated"],
        "compatible_rules": ["R01", "R04", "R06", "R08", "R10", "R13", "R16", "R17",
                             "R19", "R20", "R22", "R23", "R25", "R26", "R27", "R36",
                             "R40", "R42", "R43", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P24",
        "name": "a blood bank",
        "role": "overnight processing technician",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "has_staff", "has_records", "confined",
                 "has_equipment"],
        "compatible_rules": ["R01", "R03", "R06", "R09", "R10", "R12", "R13", "R16",
                             "R17", "R20", "R21", "R22", "R23", "R26", "R27", "R33",
                             "R36", "R39", "R40", "R43", "R45", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P25",
        "name": "a dialysis center",
        "role": "overnight technician",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "has_staff", "has_residents", "has_equipment",
                 "confined"],
        "compatible_rules": ["R01", "R03", "R05", "R06", "R08", "R10", "R12", "R13",
                             "R17", "R21", "R22", "R26", "R32", "R35", "R36", "R39",
                             "R42", "R43", "R46", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P26",
        "name": "a medical records archive room",
        "role": "overnight file clerk",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "has_records", "confined", "isolated"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R09", "R13", "R14", "R16",
                             "R17", "R19", "R20", "R22", "R23", "R25", "R29", "R36",
                             "R37", "R40", "R43", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P27",
        "name": "a rehabilitation center",
        "role": "overnight staff aide",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "has_staff", "has_residents", "has_records",
                 "confined", "residential"],
        "compatible_rules": ["R01", "R04", "R05", "R06", "R08", "R10", "R11", "R13",
                             "R16", "R17", "R19", "R21", "R22", "R25", "R29", "R32",
                             "R35", "R36", "R39", "R40", "R42", "R43", "R44", "R45",
                             "R46", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P28",
        "name": "a veterans hospital ward",
        "role": "overnight ward aide",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "government", "has_staff", "has_residents",
                 "has_records", "confined"],
        "compatible_rules": ["R01", "R04", "R05", "R06", "R08", "R10", "R11", "R13",
                             "R16", "R17", "R19", "R21", "R22", "R25", "R29", "R32",
                             "R35", "R36", "R39", "R40", "R42", "R43", "R44", "R45",
                             "R46", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P29",
        "name": "an urgent care clinic",
        "role": "overnight receptionist",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "public_facing", "has_staff", "has_records"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R13", "R16", "R17",
                             "R19", "R21", "R22", "R24", "R32", "R36", "R39", "R40",
                             "R42", "R44", "R45", "R46", "R48", "R49", "R50"],
    },

    {
        "id": "P30",
        "name": "a medical examiner's office",
        "role": "overnight assistant",
        "category": "Medical & Institutional",
        "tags": ["medical", "overnight", "government", "has_records", "confined", "isolated"],
        "compatible_rules": ["R01", "R04", "R06", "R08", "R10", "R13", "R16", "R17",
                             "R19", "R20", "R22", "R23", "R25", "R26", "R27", "R36",
                             "R40", "R42", "R43", "R44", "R45", "R48", "R49"],
    },

    # -------------------------
    # INFRASTRUCTURE & UTILITIES
    # -------------------------

    {
        "id": "P31",
        "name": "a water treatment plant",
        "role": "overnight operator",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "industrial", "overnight", "isolated", "has_equipment",
                 "has_records", "confined"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R07", "R08", "R10",
                             "R12", "R13", "R14", "R16", "R17", "R20", "R21", "R22",
                             "R23", "R25", "R26", "R27", "R30", "R33", "R36", "R37",
                             "R43", "R44", "R45", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P32",
        "name": "a nuclear power plant control room",
        "role": "overnight control room operator",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "industrial", "overnight", "isolated", "has_equipment",
                 "has_records", "confined", "government"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R16", "R17", "R20", "R21", "R22", "R23", "R25",
                             "R26", "R27", "R33", "R36", "R37", "R43", "R44", "R45",
                             "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P33",
        "name": "a natural gas pumping station",
        "role": "overnight monitor",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "industrial", "overnight", "isolated", "has_equipment",
                 "has_records"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R16", "R17", "R21", "R22", "R23", "R25",
                             "R26", "R27", "R33", "R36", "R38", "R44", "R45", "R48",
                             "R49", "R50"],
    },

    {
        "id": "P34",
        "name": "an electrical substation",
        "role": "overnight technician",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "industrial", "overnight", "isolated", "has_equipment",
                 "has_records"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R16", "R17", "R22", "R23", "R25", "R26",
                             "R27", "R33", "R36", "R38", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P35",
        "name": "a sewage treatment facility",
        "role": "overnight maintenance worker",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "industrial", "overnight", "isolated", "has_equipment",
                 "confined"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R07", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R22", "R23", "R25", "R26", "R27",
                             "R33", "R36", "R37", "R43", "R44", "R47", "R48", "R49"],
    },

    {
        "id": "P36",
        "name": "a dam operations center",
        "role": "overnight operator",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "industrial", "overnight", "isolated", "has_equipment",
                 "has_records", "government"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R16", "R17", "R20", "R21", "R22", "R23",
                             "R25", "R26", "R27", "R33", "R36", "R38", "R44", "R45",
                             "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P37",
        "name": "a radio tower maintenance post",
        "role": "overnight technician",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "industrial", "overnight", "isolated", "has_equipment",
                 "wilderness"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R15", "R17", "R18", "R22", "R24", "R25",
                             "R26", "R27", "R28", "R31", "R33", "R36", "R38", "R41",
                             "R44", "R48", "R49"],
    },

    {
        "id": "P38",
        "name": "a rural internet relay station",
        "role": "overnight monitor",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "industrial", "overnight", "isolated", "has_equipment",
                 "wilderness"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R15", "R17", "R18", "R22", "R24", "R25",
                             "R26", "R27", "R33", "R36", "R38", "R41", "R44", "R48",
                             "R49"],
    },

    {
        "id": "P39",
        "name": "an oil pipeline monitoring station",
        "role": "overnight operator",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "industrial", "overnight", "isolated", "has_equipment",
                 "has_records", "wilderness"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R20", "R22", "R23", "R25", "R26",
                             "R27", "R33", "R36", "R38", "R41", "R44", "R45", "R48",
                             "R49", "R50"],
    },

    # -------------------------
    # TRANSIT & LOGISTICS
    # -------------------------

    {
        "id": "P40",
        "name": "a Greyhound bus station",
        "role": "overnight station agent",
        "category": "Transit & Logistics",
        "tags": ["transit", "overnight", "public_facing", "has_staff", "has_records"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R13", "R15", "R17",
                             "R19", "R21", "R22", "R24", "R25", "R32", "R36", "R39",
                             "R40", "R44", "R46", "R48", "R49", "R50"],
    },

    {
        "id": "P41",
        "name": "an Amtrak overnight depot",
        "role": "overnight station agent",
        "category": "Transit & Logistics",
        "tags": ["transit", "overnight", "public_facing", "has_staff", "has_records",
                 "confined"],
        "compatible_rules": ["R01", "R05", "R07", "R08", "R10", "R11", "R13", "R15",
                             "R16", "R17", "R19", "R21", "R22", "R24", "R25", "R32",
                             "R36", "R39", "R40", "R43", "R44", "R46", "R48", "R49", "R50"],
    },

    {
        "id": "P42",
        "name": "a long-haul trucking dispatch center",
        "role": "overnight dispatcher",
        "category": "Transit & Logistics",
        "tags": ["transit", "overnight", "has_staff", "has_records", "has_equipment"],
        "compatible_rules": ["R01", "R02", "R08", "R10", "R13", "R16", "R17", "R19",
                             "R21", "R22", "R23", "R25", "R32", "R33", "R36", "R40",
                             "R44", "R45", "R48", "R49", "R50"],
    },

    {
        "id": "P43",
        "name": "a cargo shipping terminal",
        "role": "overnight dock worker",
        "category": "Transit & Logistics",
        "tags": ["transit", "industrial", "overnight", "has_staff", "has_records",
                 "has_equipment", "confined"],
        "compatible_rules": ["R01", "R03", "R07", "R08", "R09", "R10", "R12", "R13",
                             "R16", "R17", "R21", "R22", "R23", "R26", "R27", "R32",
                             "R39", "R40", "R42", "R43", "R44", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P44",
        "name": "a municipal bus garage",
        "role": "overnight maintenance worker",
        "category": "Transit & Logistics",
        "tags": ["transit", "industrial", "overnight", "has_staff", "has_equipment",
                 "confined"],
        "compatible_rules": ["R01", "R03", "R07", "R08", "R10", "R12", "R13", "R14",
                             "R17", "R21", "R22", "R23", "R26", "R27", "R32", "R36",
                             "R37", "R39", "R43", "R44", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P45",
        "name": "an airport overnight ground crew post",
        "role": "overnight ground crew worker",
        "category": "Transit & Logistics",
        "tags": ["transit", "industrial", "overnight", "has_staff", "has_equipment",
                 "has_records", "government"],
        "compatible_rules": ["R01", "R03", "R05", "R08", "R10", "R12", "R13", "R16",
                             "R17", "R21", "R22", "R23", "R26", "R32", "R36", "R39",
                             "R40", "R43", "R44", "R46", "R48", "R49", "R50"],
    },

    {
        "id": "P46",
        "name": "a subway maintenance yard",
        "role": "overnight maintenance worker",
        "category": "Transit & Logistics",
        "tags": ["transit", "industrial", "overnight", "confined", "has_equipment",
                 "has_staff"],
        "compatible_rules": ["R01", "R03", "R04", "R07", "R08", "R10", "R12", "R13",
                             "R14", "R17", "R21", "R22", "R23", "R25", "R26", "R27",
                             "R33", "R36", "R37", "R43", "R44", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P47",
        "name": "a railroad switching station",
        "role": "overnight switch operator",
        "category": "Transit & Logistics",
        "tags": ["transit", "industrial", "overnight", "isolated", "has_equipment",
                 "has_records"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R15", "R17", "R22", "R23", "R25", "R26",
                             "R27", "R33", "R36", "R38", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P48",
        "name": "a ferry terminal",
        "role": "overnight dock attendant",
        "category": "Transit & Logistics",
        "tags": ["transit", "overnight", "public_facing", "isolated", "has_records"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R13", "R14", "R15",
                             "R17", "R19", "R22", "R24", "R25", "R36", "R38", "R40",
                             "R44", "R48", "R49"],
    },

    {
        "id": "P49",
        "name": "a toll booth on an isolated highway",
        "role": "overnight toll collector",
        "category": "Transit & Logistics",
        "tags": ["transit", "overnight", "isolated", "public_facing", "confined"],
        "compatible_rules": ["R02", "R04", "R05", "R08", "R10", "R11", "R14", "R15",
                             "R17", "R19", "R22", "R24", "R25", "R31", "R36", "R38",
                             "R40", "R41", "R44", "R48", "R49"],
    },

    # -------------------------
    # GOVERNMENT & MUNICIPAL
    # -------------------------

    {
        "id": "P50",
        "name": "a county jail",
        "role": "overnight corrections officer",
        "category": "Government & Municipal",
        "tags": ["government", "overnight", "has_staff", "has_residents", "has_records",
                 "confined"],
        "compatible_rules": ["R01", "R04", "R05", "R06", "R08", "R10", "R11", "R13",
                             "R16", "R17", "R19", "R21", "R22", "R23", "R25", "R32",
                             "R35", "R36", "R39", "R40", "R42", "R43", "R44", "R45",
                             "R46", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P51",
        "name": "a city impound lot",
        "role": "overnight attendant",
        "category": "Government & Municipal",
        "tags": ["government", "overnight", "isolated", "has_records"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R09", "R10", "R13", "R14",
                             "R15", "R17", "R19", "R22", "R23", "R24", "R25", "R36",
                             "R40", "R44", "R48", "R49"],
    },

    {
        "id": "P52",
        "name": "a courthouse overnight security post",
        "role": "overnight security guard",
        "category": "Government & Municipal",
        "tags": ["government", "overnight", "has_records", "confined"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R10", "R13", "R15", "R16",
                             "R17", "R19", "R20", "R22", "R23", "R25", "R29", "R36",
                             "R37", "R40", "R43", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P53",
        "name": "a USPS sorting facility",
        "role": "overnight mail sorter",
        "category": "Government & Municipal",
        "tags": ["government", "industrial", "overnight", "has_staff", "has_records",
                 "confined"],
        "compatible_rules": ["R01", "R07", "R08", "R09", "R10", "R13", "R16", "R17",
                             "R20", "R21", "R22", "R23", "R32", "R36", "R39", "R40",
                             "R43", "R44", "R45", "R46", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P54",
        "name": "a state archive building",
        "role": "overnight security guard",
        "category": "Government & Municipal",
        "tags": ["government", "overnight", "has_records", "confined", "isolated"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R09", "R13", "R14", "R16",
                             "R17", "R19", "R20", "R22", "R23", "R25", "R29", "R36",
                             "R37", "R40", "R43", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P55",
        "name": "a fire lookout tower",
        "role": "seasonal fire spotter",
        "category": "Government & Municipal",
        "tags": ["government", "overnight", "isolated", "wilderness", "confined"],
        "compatible_rules": ["R02", "R03", "R04", "R06", "R08", "R10", "R13", "R14",
                             "R15", "R17", "R18", "R19", "R22", "R24", "R25", "R28",
                             "R31", "R36", "R38", "R41", "R44", "R48", "R49"],
    },

    {
        "id": "P56",
        "name": "a national weather service station",
        "role": "overnight meteorological technician",
        "category": "Government & Municipal",
        "tags": ["government", "research", "overnight", "isolated", "has_equipment",
                 "has_records"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R16", "R17", "R20", "R22", "R23", "R25",
                             "R26", "R27", "R33", "R36", "R38", "R41", "R44", "R45",
                             "R48", "R49"],
    },

    {
        "id": "P57",
        "name": "a border checkpoint",
        "role": "overnight inspection officer",
        "category": "Government & Municipal",
        "tags": ["government", "overnight", "public_facing", "has_staff", "has_records",
                 "transit"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R13", "R16", "R17",
                             "R19", "R20", "R21", "R22", "R23", "R25", "R32", "R36",
                             "R39", "R40", "R44", "R45", "R46", "R48", "R49", "R50"],
    },

    # -------------------------
    # EDUCATION & RESEARCH
    # -------------------------

    {
        "id": "P58",
        "name": "a university library",
        "role": "overnight security guard",
        "category": "Education & Research",
        "tags": ["research", "overnight", "has_records", "confined"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R09", "R10", "R13", "R14",
                             "R16", "R17", "R19", "R20", "R22", "R23", "R24", "R25",
                             "R29", "R36", "R37", "R40", "R43", "R44", "R45", "R48",
                             "R49"],
    },

    {
        "id": "P59",
        "name": "a natural history museum",
        "role": "overnight security guard",
        "category": "Education & Research",
        "tags": ["research", "overnight", "has_records", "confined", "public_facing"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R09", "R10", "R13", "R14",
                             "R16", "R17", "R19", "R20", "R22", "R23", "R24", "R25",
                             "R29", "R36", "R37", "R40", "R43", "R44", "R45", "R48",
                             "R49"],
    },

    {
        "id": "P60",
        "name": "a remote scientific research station",
        "role": "overnight station caretaker",
        "category": "Education & Research",
        "tags": ["research", "overnight", "isolated", "wilderness", "has_equipment",
                 "has_records"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R15", "R16", "R17", "R18", "R20", "R22",
                             "R23", "R24", "R25", "R26", "R27", "R28", "R31", "R33",
                             "R36", "R38", "R41", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P61",
        "name": "a university lab building",
        "role": "overnight security guard",
        "category": "Education & Research",
        "tags": ["research", "overnight", "has_equipment", "has_records", "confined"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R09", "R10", "R12", "R13",
                             "R16", "R17", "R19", "R20", "R21", "R22", "R23", "R26",
                             "R27", "R33", "R36", "R37", "R40", "R43", "R44", "R45",
                             "R47", "R48", "R49"],
    },

    {
        "id": "P62",
        "name": "an observatory",
        "role": "overnight telescope operator",
        "category": "Education & Research",
        "tags": ["research", "overnight", "isolated", "has_equipment", "has_records",
                 "wilderness"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R20", "R22", "R24", "R25", "R26",
                             "R27", "R33", "R36", "R38", "R41", "R44", "R48", "R49"],
    },

    {
        "id": "P63",
        "name": "a school overnight custodian post",
        "role": "overnight custodian",
        "category": "Education & Research",
        "tags": ["overnight", "confined", "has_records"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R10", "R13", "R14", "R17",
                             "R19", "R22", "R23", "R24", "R25", "R29", "R36", "R37",
                             "R40", "R43", "R44", "R48", "R49"],
    },

    {
        "id": "P64",
        "name": "an aquarium",
        "role": "overnight maintenance technician",
        "category": "Education & Research",
        "tags": ["overnight", "confined", "has_equipment", "has_animals", "has_records"],
        "compatible_rules": ["R01", "R03", "R06", "R07", "R08", "R10", "R12", "R13",
                             "R14", "R17", "R19", "R22", "R23", "R26", "R27", "R28",
                             "R30", "R33", "R36", "R43", "R44", "R47", "R48", "R49"],
    },

    {
        "id": "P65",
        "name": "a geological survey outpost",
        "role": "overnight survey technician",
        "category": "Education & Research",
        "tags": ["research", "overnight", "isolated", "wilderness", "has_equipment",
                 "has_records"],
        "compatible_rules": ["R02", "R03", "R04", "R06", "R08", "R10", "R12", "R13",
                             "R14", "R15", "R17", "R18", "R20", "R22", "R24", "R25",
                             "R26", "R27", "R28", "R31", "R33", "R36", "R38", "R41",
                             "R44", "R48", "R49"],
    },

    {
        "id": "P66",
        "name": "a field research station in a national park",
        "role": "overnight research assistant",
        "category": "Education & Research",
        "tags": ["research", "overnight", "isolated", "wilderness", "has_animals",
                 "has_records"],
        "compatible_rules": ["R02", "R03", "R04", "R06", "R08", "R10", "R13", "R14",
                             "R15", "R17", "R18", "R20", "R22", "R24", "R25", "R26",
                             "R27", "R28", "R31", "R36", "R38", "R41", "R44", "R48",
                             "R49"],
    },

    # -------------------------
    # INDUSTRIAL & COMMERCIAL
    # -------------------------

    {
        "id": "P67",
        "name": "a meatpacking plant",
        "role": "overnight line worker",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "has_staff", "has_equipment", "confined"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R07", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R21", "R22", "R23", "R26", "R27",
                             "R32", "R36", "R39", "R42", "R43", "R44", "R46", "R47",
                             "R48", "R49", "R50"],
    },

    {
        "id": "P68",
        "name": "a paper mill",
        "role": "overnight machine operator",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "has_staff", "has_equipment", "confined",
                 "isolated"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R07", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R21", "R22", "R23", "R26", "R27",
                             "R33", "R36", "R37", "R39", "R43", "R44", "R47", "R48",
                             "R49", "R50"],
    },

    {
        "id": "P69",
        "name": "a textile factory",
        "role": "overnight floor supervisor",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "has_staff", "has_equipment", "confined"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R07", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R21", "R22", "R23", "R26", "R27",
                             "R32", "R36", "R37", "R39", "R43", "R44", "R47", "R48",
                             "R49", "R50"],
    },

    {
        "id": "P70",
        "name": "a grain elevator",
        "role": "overnight attendant",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "isolated", "has_equipment", "confined"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R08", "R10", "R12", "R13",
                             "R14", "R15", "R17", "R22", "R23", "R25", "R26", "R27",
                             "R33", "R36", "R37", "R38", "R44", "R47", "R48", "R49"],
    },

    {
        "id": "P71",
        "name": "a cold storage warehouse",
        "role": "overnight inventory worker",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "isolated", "has_equipment", "confined",
                 "has_records"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R07", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R22", "R23", "R25", "R26", "R27",
                             "R36", "R37", "R42", "R43", "R44", "R47", "R48", "R49"],
    },

    {
        "id": "P72",
        "name": "a salvage yard",
        "role": "overnight security guard",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "isolated", "has_animals"],
        "compatible_rules": ["R04", "R06", "R07", "R08", "R10", "R14", "R15", "R17",
                             "R19", "R22", "R24", "R25", "R28", "R31", "R36", "R38",
                             "R41", "R44", "R48", "R49"],
    },

    {
        "id": "P73",
        "name": "a printing press facility",
        "role": "overnight press operator",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "has_staff", "has_equipment", "confined"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R08", "R10", "R12", "R13",
                             "R14", "R17", "R21", "R22", "R23", "R26", "R27", "R33",
                             "R36", "R37", "R39", "R43", "R44", "R47", "R48", "R49",
                             "R50"],
    },

    {
        "id": "P74",
        "name": "a glass manufacturing plant",
        "role": "overnight furnace monitor",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "has_staff", "has_equipment", "confined"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R08", "R10", "R12", "R13",
                             "R14", "R17", "R21", "R22", "R23", "R26", "R27", "R33",
                             "R36", "R39", "R43", "R44", "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P75",
        "name": "a coal processing facility",
        "role": "overnight plant operator",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "has_staff", "has_equipment", "confined",
                 "isolated"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R07", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R21", "R22", "R23", "R26", "R27",
                             "R33", "R36", "R37", "R43", "R44", "R47", "R48", "R49",
                             "R50"],
    },

    # -------------------------
    # ENTERTAINMENT & MEDIA
    # -------------------------

    {
        "id": "P76",
        "name": "a radio station",
        "role": "overnight board operator",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "isolated", "has_equipment", "has_records",
                 "confined"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R09", "R10",
                             "R12", "R13", "R14", "R15", "R16", "R17", "R19", "R20",
                             "R22", "R25", "R26", "R27", "R33", "R36", "R44", "R45",
                             "R48", "R49"],
    },

    {
        "id": "P77",
        "name": "a television broadcast tower",
        "role": "overnight transmission engineer",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "isolated", "has_equipment", "utilities"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R15", "R17", "R19", "R20", "R22", "R25",
                             "R26", "R27", "R33", "R36", "R38", "R41", "R44", "R48",
                             "R49"],
    },

    {
        "id": "P78",
        "name": "a movie theater",
        "role": "overnight cleaning crew member",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "confined", "has_staff", "has_records"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R09", "R10", "R13", "R14",
                             "R17", "R19", "R21", "R22", "R23", "R24", "R25", "R36",
                             "R37", "R40", "R43", "R44", "R46", "R47", "R48", "R49",
                             "R50"],
    },

    {
        "id": "P79",
        "name": "a bowling alley after hours",
        "role": "overnight maintenance worker",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "confined", "has_staff"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R10", "R12", "R13", "R14",
                             "R17", "R19", "R21", "R22", "R24", "R25", "R36", "R37",
                             "R43", "R44", "R46", "R48", "R49", "R50"],
    },

    {
        "id": "P80",
        "name": "an arcade that stays open until 4 a.m.",
        "role": "overnight attendant",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "public_facing", "has_equipment", "confined"],
        "compatible_rules": ["R01", "R04", "R05", "R08", "R09", "R10", "R11", "R12",
                             "R14", "R17", "R19", "R21", "R22", "R24", "R25", "R33",
                             "R36", "R40", "R44", "R46", "R48", "R49"],
    },

    {
        "id": "P81",
        "name": "a drive-in movie theater",
        "role": "overnight projectionist",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "isolated", "has_equipment"],
        "compatible_rules": ["R02", "R04", "R05", "R08", "R09", "R10", "R11", "R14",
                             "R15", "R17", "R19", "R22", "R24", "R25", "R28", "R33",
                             "R36", "R38", "R41", "R44", "R48", "R49"],
    },

    {
        "id": "P82",
        "name": "a recording studio",
        "role": "overnight engineer",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "has_equipment", "has_records", "confined"],
        "compatible_rules": ["R01", "R02", "R04", "R08", "R09", "R10", "R12", "R13",
                             "R14", "R15", "R16", "R17", "R19", "R20", "R22", "R25",
                             "R26", "R27", "R33", "R36", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P83",
        "name": "a theme park",
        "role": "overnight maintenance technician",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "has_staff", "has_equipment", "confined",
                 "has_records"],
        "compatible_rules": ["R01", "R03", "R07", "R08", "R10", "R12", "R13", "R14",
                             "R17", "R19", "R21", "R22", "R23", "R26", "R27", "R32",
                             "R36", "R37", "R39", "R40", "R43", "R44", "R47", "R48",
                             "R49", "R50"],
    },

    {
        "id": "P84",
        "name": "a county fairground during off-season",
        "role": "winter caretaker",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "isolated", "has_animals", "has_records"],
        "compatible_rules": ["R04", "R06", "R07", "R08", "R10", "R13", "R14", "R15",
                             "R17", "R18", "R19", "R22", "R24", "R25", "R28", "R31",
                             "R36", "R38", "R41", "R44", "R48", "R49"],
    },

    {
        "id": "P85",
        "name": "a casino floor",
        "role": "overnight pit supervisor",
        "category": "Entertainment & Media",
        "tags": ["entertainment", "overnight", "public_facing", "has_staff", "has_records",
                 "has_equipment", "confined"],
        "compatible_rules": ["R01", "R05", "R08", "R10", "R11", "R13", "R16", "R17",
                             "R19", "R21", "R22", "R23", "R25", "R32", "R36", "R39",
                             "R40", "R44", "R45", "R46", "R48", "R49", "R50"],
    },

    # -------------------------
    # ISOLATED & UNCONVENTIONAL
    # -------------------------

    {
        "id": "P86",
        "name": "a lighthouse",
        "role": "temporary keeper",
        "category": "Isolated & Unconventional",
        "tags": ["overnight", "isolated", "wilderness", "has_equipment", "confined"],
        "compatible_rules": ["R02", "R03", "R04", "R06", "R08", "R10", "R12", "R13",
                             "R14", "R15", "R17", "R18", "R19", "R22", "R24", "R25",
                             "R26", "R27", "R28", "R31", "R33", "R36", "R38", "R41",
                             "R44", "R48", "R49"],
    },

    {
        "id": "P87",
        "name": "a fire lookout cabin",
        "role": "seasonal fire spotter",
        "category": "Isolated & Unconventional",
        "tags": ["overnight", "isolated", "wilderness", "confined", "government"],
        "compatible_rules": ["R02", "R03", "R04", "R06", "R08", "R10", "R13", "R14",
                             "R15", "R17", "R18", "R19", "R22", "R24", "R25", "R26",
                             "R27", "R28", "R31", "R36", "R38", "R41", "R44", "R48",
                             "R49"],
    },

    {
        "id": "P88",
        "name": "a remote national park ranger station",
        "role": "seasonal ranger aide",
        "category": "Isolated & Unconventional",
        "tags": ["overnight", "isolated", "wilderness", "has_animals", "government",
                 "has_records"],
        "compatible_rules": ["R02", "R03", "R04", "R06", "R08", "R10", "R13", "R14",
                             "R15", "R17", "R18", "R20", "R22", "R24", "R25", "R26",
                             "R27", "R28", "R31", "R36", "R38", "R41", "R44", "R48",
                             "R49"],
    },

    {
        "id": "P89",
        "name": "a mountain weather monitoring station",
        "role": "overnight instrument technician",
        "category": "Isolated & Unconventional",
        "tags": ["overnight", "isolated", "wilderness", "has_equipment", "has_records",
                 "research"],
        "compatible_rules": ["R02", "R03", "R04", "R06", "R08", "R10", "R12", "R13",
                             "R14", "R15", "R17", "R18", "R20", "R22", "R24", "R25",
                             "R26", "R27", "R28", "R31", "R33", "R36", "R38", "R41",
                             "R44", "R48", "R49"],
    },

    {
        "id": "P90",
        "name": "an offshore oil rig",
        "role": "overnight floor hand",
        "category": "Isolated & Unconventional",
        "tags": ["industrial", "overnight", "isolated", "has_equipment", "has_staff",
                 "confined"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R21", "R22", "R23", "R25", "R26",
                             "R27", "R32", "R33", "R36", "R37", "R39", "R43", "R44",
                             "R47", "R48", "R49", "R50"],
    },

    {
        "id": "P91",
        "name": "a wilderness camp for troubled youth",
        "role": "overnight counselor",
        "category": "Isolated & Unconventional",
        "tags": ["overnight", "isolated", "wilderness", "has_residents", "has_staff",
                 "has_animals"],
        "compatible_rules": ["R04", "R06", "R08", "R10", "R13", "R14", "R15", "R17",
                             "R18", "R19", "R22", "R24", "R25", "R28", "R31", "R35",
                             "R36", "R38", "R41", "R42", "R44", "R46", "R48", "R49",
                             "R50"],
    },

    {
        "id": "P92",
        "name": "a remote roadside rest stop",
        "role": "overnight maintenance attendant",
        "category": "Isolated & Unconventional",
        "tags": ["overnight", "isolated", "public_facing", "transit", "confined"],
        "compatible_rules": ["R04", "R05", "R08", "R10", "R11", "R14", "R15", "R17",
                             "R19", "R22", "R24", "R25", "R31", "R36", "R38", "R40",
                             "R41", "R44", "R48", "R49"],
    },

    {
        "id": "P93",
        "name": "a mine shaft monitoring station",
        "role": "overnight safety monitor",
        "category": "Isolated & Unconventional",
        "tags": ["industrial", "overnight", "isolated", "confined", "has_equipment",
                 "has_records"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R06", "R08", "R10", "R12",
                             "R13", "R14", "R17", "R22", "R23", "R25", "R26", "R27",
                             "R33", "R36", "R37", "R43", "R44", "R47", "R48", "R49"],
    },

    {
        "id": "P94",
        "name": "a ghost town with one operational building",
        "role": "caretaker / property manager",
        "category": "Isolated & Unconventional",
        "tags": ["overnight", "isolated", "wilderness", "confined", "has_records"],
        "compatible_rules": ["R04", "R06", "R07", "R08", "R10", "R13", "R14", "R15",
                             "R16", "R17", "R18", "R19", "R22", "R24", "R25", "R29",
                             "R31", "R36", "R38", "R41", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P95",
        "name": "a decommissioned military base being converted to civilian use",
        "role": "overnight security contractor",
        "category": "Isolated & Unconventional",
        "tags": ["government", "overnight", "isolated", "has_records", "has_equipment",
                 "confined", "industrial"],
        "compatible_rules": ["R01", "R02", "R04", "R06", "R07", "R08", "R09", "R10",
                             "R13", "R14", "R15", "R16", "R17", "R19", "R20", "R22",
                             "R23", "R24", "R25", "R26", "R27", "R31", "R36", "R37",
                             "R38", "R40", "R43", "R44", "R45", "R47", "R48", "R49"],
    },

    {
        "id": "P96",
        "name": "a planetarium",
        "role": "overnight technician",
        "category": "Isolated & Unconventional",
        "tags": ["entertainment", "research", "overnight", "confined", "has_equipment",
                 "isolated"],
        "compatible_rules": ["R01", "R02", "R03", "R04", "R08", "R09", "R10", "R12",
                             "R13", "R14", "R17", "R19", "R20", "R22", "R25", "R26",
                             "R27", "R33", "R36", "R44", "R48", "R49"],
    },

    {
        "id": "P97",
        "name": "a DMV records storage room",
        "role": "overnight clerk",
        "category": "Government & Municipal",
        "tags": ["government", "overnight", "has_records", "confined", "isolated"],
        "compatible_rules": ["R01", "R04", "R07", "R08", "R09", "R13", "R14", "R16",
                             "R17", "R19", "R20", "R22", "R23", "R25", "R29", "R36",
                             "R37", "R43", "R44", "R45", "R48", "R49"],
    },

    {
        "id": "P98",
        "name": "a municipal water tower maintenance post",
        "role": "overnight maintenance worker",
        "category": "Government & Municipal",
        "tags": ["utilities", "government", "overnight", "isolated", "has_equipment",
                 "confined"],
        "compatible_rules": ["R02", "R03", "R04", "R06", "R08", "R10", "R12", "R13",
                             "R14", "R15", "R17", "R22", "R24", "R25", "R26", "R27",
                             "R30", "R33", "R36", "R38", "R41", "R44", "R48", "R49"],
    },

    {
        "id": "P99",
        "name": "a cell tower service station",
        "role": "overnight monitor",
        "category": "Infrastructure & Utilities",
        "tags": ["utilities", "overnight", "isolated", "has_equipment", "wilderness"],
        "compatible_rules": ["R02", "R03", "R04", "R06", "R08", "R10", "R12", "R13",
                             "R14", "R15", "R17", "R22", "R24", "R25", "R26", "R27",
                             "R33", "R36", "R38", "R41", "R44", "R48", "R49"],
    },

    {
        "id": "P100",
        "name": "a concrete batching plant",
        "role": "overnight plant operator",
        "category": "Industrial & Commercial",
        "tags": ["industrial", "overnight", "isolated", "has_equipment", "confined"],
        "compatible_rules": ["R01", "R03", "R04", "R06", "R08", "R10", "R12", "R13",
                             "R14", "R17", "R22", "R23", "R25", "R26", "R27", "R33",
                             "R36", "R37", "R43", "R44", "R47", "R48", "R49"],
    },

]