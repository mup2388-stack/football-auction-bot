"""
FL26 Tactics system — all attacking, defensive, and advanced instructions.

Mirrors the exact tactics panel in Football Life 26 (PES 2021 engine).

Data model is a flat dict of string keys → string/int values. Stored as JSON
in the database (one row per manager). Defaults are balanced mid-range.

Usage:
    import tactics as T
    t = T.default_tactics()          # {"attacking_style": "counter_attack", ...}
    label = T.ATTACK_STYLE["counter_attack"]["label"]   # "Counter Attack"
    desc  = T.ATTACK_STYLE["counter_attack"]["desc"]     # "Win the ball..."
"""

# ============================================================================
#  FORMATIONS — FL26 labels mapped to our internal formation keys
#  Each entry: (display_label, internal_key, fl26_variant)
# ============================================================================

FORMATIONS_FL26 = [
    ("4-3-3 (4-2-1-3)",   "4-3-3"),
    ("4-5-1 (4-2-3-1)",   "4-2-3-1"),
    ("4-5-1 (4-1-4-1)",   "4-1-4-1"),
    ("4-5-1 (4-3-2-1)",   "4-3-2-1"),
    ("4-4-2 (4-2-2-2)",   "4-2-2-2"),
    ("4-4-2 (4-3-1-2)",   "4-1-2-1-2"),
    ("4-3-3 (4-1-2-3)",   "4-1-2-3"),
    ("3-6-1 (3-2-4-1)",   "3-6-1"),
    ("3-5-2 (3-2-3-2)",   "3-5-2"),
    ("3-5-2 (3-3-2-2)",   "3-3-2-2"),
    ("3-4-3 (3-2-2-3)",   "3-4-3"),
    ("5-4-1 (5-2-2-1)",   "5-4-1"),
    ("5-3-2 (5-2-1-2)",   "5-2-1-2"),
    ("5-3-2 (5-3-2)",     "5-3-2"),
]

# Formation descriptions for the website/Discord
FORMATION_DESC = {
    "4-3-3":     "A balanced attacking setup with wingers high and wide. The front three stretch the defense while a central midfield trio controls tempo.",
    "4-2-3-1":   "Two holding midfielders shield the back four while an attacking trio supports a lone striker. The modern default for control and structure.",
    "4-1-4-1":   "A single defensive anchor sits behind a flat four-man midfield. Solid defensively with width coming from the wide midfielders.",
    "4-3-2-1":   "The Christmas tree. A narrow midfield with two attacking midfielders tucked behind a lone striker. Excellent central control.",
    "4-2-2-2":   "The Brazilian box midfield. Two holding mids and two attacking mids create a compact diamond in the center. Narrow but fluid.",
    "4-1-2-1-2": "The narrow diamond. A CDM and CAM on the spine with two central midfielders. Extremely compact through the middle.",
    "4-1-2-3":   "A single pivot in front of four defenders feeds a front three. Wide attackers provide the attacking thrust with one striker central.",
    "3-6-1":     "Three centre-backs with a deep midfield quartet supporting a lone striker. Maximizes midfield dominance and possession control.",
    "3-5-2":     "Three at the back with wing-backs providing width. A central midfield three controls the tempo while two strikers lead the line.",
    "3-3-2-2":   "Three defenders, a midfield bank of three with two wing-backs pushing on, and a front two. Balanced wing-back system.",
    "3-4-3":     "Three centre-backs with an attacking midfield four and front three. Aggressive and expansive, committing numbers forward.",
    "5-4-1":     "Five at the back with wing-backs and a midfield four shielding a lone striker. Deep defensive block, hard to break down.",
    "5-2-1-2":   "A back five with wing-backs, two central midfielders, an attacking midfielder, and two strikers. Counter-attacking shape.",
    "5-3-2":     "Five defenders, a flat midfield three, and two strikers. Maximum defensive security with a direct outlet up front.",
}

# Map internal key → display label for lookups
KEY_TO_LABEL = {key: label for label, key in FORMATIONS_FL26}


# ============================================================================
#  TACTIC CHOICE GROUPS
#  Each is a dict: value → {"label", "desc", "emoji"}
#  "off" is always a valid value for advanced instructions.
# ============================================================================

ATTACK_STYLE = {
    "counter_attack": {
        "label": "Counter Attack",
        "desc": "Win the ball back, then rapidly break forward with direct vertical passes to catch the opposition's defense unsettled.",
        "emoji": "",
    },
    "possession_game": {
        "label": "Possession Game",
        "desc": "Build attacks patiently, keeping the ball and probing for openings through sustained passing and intelligent movement.",
        "emoji": "",
    },
}

BUILD_UP = {
    "short_pass": {
        "label": "Short Pass",
        "desc": "Advance through a series of short ground passes, keeping close control and compact spacing between players.",
        "emoji": "",
    },
    "long_pass": {
        "label": "Long Pass",
        "desc": "Progress up the pitch quickly with longer forward passes, often bypassing the opponent's midfield press.",
        "emoji": "",
    },
}

ATTACK_AREA = {
    "center": {
        "label": "Center",
        "desc": "Concentrate attacks through the central channels of the pitch, targeting the space between full-backs.",
        "emoji": "",
    },
    "wide": {
        "label": "Wide",
        "desc": "Focus attacks down the flanks and wing areas, stretching the opposition and working the ball into the box from wide positions.",
        "emoji": "",
    },
}

POSITIONING = {
    "flexible": {
        "label": "Flexible",
        "desc": "Players drift from their nominal positions to find space, create passing angles, and exploit gaps as the situation demands.",
        "emoji": "",
    },
    "maintain_formation": {
        "label": "Maintain Formation",
        "desc": "Players hold their designated positions and preserve the team's structural shape throughout each phase of play.",
        "emoji": "",
    },
}

DEFENSIVE_STYLE = {
    "frontline_pressure": {
        "label": "Frontline Pressure",
        "desc": "Hunt the ball high up the pitch, aggressively closing down opponents near their own goal to force turnovers in dangerous areas.",
        "emoji": "",
    },
    "all_out_defence": {
        "label": "All-out Defence",
        "desc": "Fall back and defend compactly as a unit near your own goal, prioritizing shape and cover over chasing the ball.",
        "emoji": "",
    },
}

CONTAINMENT_AREA = {
    "wide": {
        "label": "Wide",
        "desc": "Shepherd the ball-carrying opposition toward the flanks, forcing them into less dangerous wide positions.",
        "emoji": "",
    },
    "center": {
        "label": "Center",
        "desc": "Funnel the opposition toward the center of the pitch, crowding the middle to block central progression.",
        "emoji": "",
    },
}

PRESSURING = {
    "conservative": {
        "label": "Conservative",
        "desc": "Players hold their positions and commit to challenges only when the moment is right, avoiding reckless lunges and gaps.",
        "emoji": "",
    },
    "aggressive": {
        "label": "Aggressive",
        "desc": "Players aggressively pursue and tackle the ball carrier, looking to win possession back quickly through sheer intensity.",
        "emoji": "",
    },
}

# Sliders
SLIDERS = {
    "support_range": {
        "label": "Support Range",
        "desc": "How far teammates spread from the ball carrier to offer passing options. Higher values create a more expansive shape with greater distances between players.",
        "default": 5,
        "min": 1, "max": 10,
    },
    "defensive_line": {
        "label": "Defensive Line",
        "desc": "How far up the pitch the defensive line holds. Higher values push the line toward midfield to compress space; lower values sit deeper near the box.",
        "default": 5,
        "min": 1, "max": 10,
    },
    "compactness": {
        "label": "Compactness",
        "desc": "How tightly the team groups together horizontally. Higher values keep players narrow and compact; lower values allow the team to spread wider.",
        "default": 5,
        "min": 1, "max": 10,
    },
}


# ============================================================================
#  ADVANCED INSTRUCTIONS
# ============================================================================

ADV_ATTACK = {
    "off": {
        "label": "Off",
        "desc": "No advanced attacking instruction active.",
        "emoji": "",
    },
    "anchoring": {
        "label": "Anchoring",
        "desc": "The deepest midfielder holds position in front of the defense, anchoring the midfield and shielding the back line rather than joining attacks.",
        "emoji": "",
    },
    "false_winger": {
        "label": "False Winger",
        "desc": "A central player drifts into wide areas to overload the flanks, creating numerical superiority on the wings.",
        "emoji": "",
    },
    "defensive": {
        "label": "Defensive",
        "desc": "Players adopt more conservative positions, prioritizing defensive solidity over attacking ambition.",
        "emoji": "",
    },
    "hug_touchline": {
        "label": "Hug The Touchline",
        "desc": "Players position themselves near the touchlines to stretch the pitch and create space in central areas for teammates to exploit.",
        "emoji": "",
    },
    "attacking_full_backs": {
        "label": "Attacking Full Backs",
        "desc": "Full backs push high up the pitch to join attacks, effectively operating as auxiliary wingers and creating overloads out wide.",
        "emoji": "",
    },
    "wing_rotation": {
        "label": "Wing Rotation",
        "desc": "Wide players and full backs interchange positions to confuse markers and create unpredictable, fluid attacking patterns down the flanks.",
        "emoji": "",
    },
    "tiki_taka": {
        "label": "Tiki Taka",
        "desc": "Players constantly move to offer short passing options, building attacks through rapid one- and two-touch passing and intelligent off-ball movement.",
        "emoji": "",
    },
    "false_9": {
        "label": "False 9",
        "desc": "The central striker drops deep into midfield instead of staying high, dragging centre-backs out of position and creating space in behind for others.",
        "emoji": "",
    },
    "centering_targets": {
        "label": "Centering Targets",
        "desc": "Designated players position themselves in the box as aerial targets for crosses, focusing attacking play on delivery into dangerous areas.",
        "emoji": "",
    },
    "false_fullbacks": {
        "label": "False Fullbacks",
        "desc": "Full backs tuck infield into central positions when in possession, operating as auxiliary midfielders to overload the middle of the pitch.",
        "emoji": "",
    },
}

ADV_DEFENCE = {
    "off": {
        "label": "Off",
        "desc": "No advanced defensive instruction active.",
        "emoji": "",
    },
    "wing_back": {
        "label": "Wing Back",
        "desc": "Wing-backs prioritize their defensive duties, staying deep and providing cover for the flanks rather than pushing forward.",
        "emoji": "",
    },
    "tight_marking": {
        "label": "Tight Marking",
        "desc": "Players stay goal-side and closely mark their direct opponent, denying them time and space on the ball.",
        "emoji": "",
    },
    "deep_defensive_line": {
        "label": "Deep Defensive Line",
        "desc": "The defensive line drops even deeper than the standard setting, sitting close to the penalty area to compress space for the opposition.",
        "emoji": "",
    },
    "swarm_the_box": {
        "label": "Swarm The Box",
        "desc": "When the opposition attacks, additional players flood back to crowd the penalty area and block shooting angles.",
        "emoji": "",
    },
    "counter_target": {
        "label": "Counter Target",
        "desc": "The team focuses on winning the ball from a designated opponent, marking them intensively to trigger rapid counter-attacks.",
        "emoji": "",
    },
    "gegenpress": {
        "label": "Gegenpress",
        "desc": "Immediately after losing possession, players aggressively swarm the ball carrier to win it back within seconds, exploiting the opposition's vulnerable transition.",
        "emoji": "",
    },
}


# ============================================================================
#  DEFAULT TACTICS  —  balanced mid-range setup
# ============================================================================

def default_tactics() -> dict:
    return {
        "attacking_style": "counter_attack",
        "build_up": "short_pass",
        "attacking_area": "center",
        "positioning": "flexible",
        "support_range": 5,
        "defensive_style": "frontline_pressure",
        "containment_area": "center",
        "pressuring": "conservative",
        "defensive_line": 5,
        "compactness": 5,
        "adv_attack_1": "off",
        "adv_attack_2": "off",
        "adv_defence_1": "off",
        "adv_defence_2": "off",
    }


# Validate that a tactics dict has all keys, filling defaults for missing ones.
def normalize(raw: dict) -> dict:
    t = default_tactics()
    if raw:
        for k, v in raw.items():
            if k in t:
                t[k] = v
    # clamp sliders
    for sk, conf in SLIDERS.items():
        try:
            t[sk] = max(conf["min"], min(conf["max"], int(t[sk])))
        except (ValueError, TypeError):
            t[sk] = conf["default"]
    # validate choices
    validators = [
        ("attacking_style", ATTACK_STYLE),
        ("build_up", BUILD_UP),
        ("attacking_area", ATTACK_AREA),
        ("positioning", POSITIONING),
        ("defensive_style", DEFENSIVE_STYLE),
        ("containment_area", CONTAINMENT_AREA),
        ("pressuring", PRESSURING),
        ("adv_attack_1", ADV_ATTACK),
        ("adv_attack_2", ADV_ATTACK),
        ("adv_defence_1", ADV_DEFENCE),
        ("adv_defence_2", ADV_DEFENCE),
    ]
    for key, group in validators:
        if t[key] not in group:
            t[key] = default_tactics()[key]
    return t


# ============================================================================
#  LOOKUP HELPERS
# ============================================================================

def label(group: dict, value: str) -> str:
    """Get the human label for a tactic value, or the raw value if unknown."""
    entry = group.get(value)
    return entry["label"] if entry else value

def desc(group: dict, value: str) -> str:
    """Get the description for a tactic value."""
    entry = group.get(value)
    return entry["desc"] if entry else ""

def slider_label(key: str) -> str:
    return SLIDERS.get(key, {}).get("label", key)

def slider_desc(key: str) -> str:
    return SLIDERS.get(key, {}).get("desc", "")
