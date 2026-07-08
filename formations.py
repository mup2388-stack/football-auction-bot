"""
Formation definitions — FL26 tactics (14 formations).

Each formation defines rows of slots. Each slot has:
  - pos:  preferred position (LW, ST, CB, GK, etc.)
  - side: L / C / R  (for auto-assignment + staggered layout)
  - x:    horizontal position on pitch (0.0=left, 1.0=right)

These are the EXACT 14 formations available in Football Life 26.
"""


def _slot(pos, side, x):
    return {"pos": pos, "side": side, "x": x}


FORMATIONS = {
    # ── 4-3-3 family ──
    "4-3-3": {
        "name": "4-3-3",
        "desc": "4-2-1-3 — wingers high and wide, central midfield trio",
        "rows": [
            {"y": 0.04, "group": "FWD", "slots": [
                _slot("LW", "L", 0.14), _slot("ST", "C", 0.50), _slot("RW", "R", 0.86)]},
            {"y": 0.36, "group": "MID", "slots": [
                _slot("CM", "L", 0.25), _slot("CM", "C", 0.50), _slot("CM", "R", 0.75)]},
            {"y": 0.67, "group": "DEF", "slots": [
                _slot("LB", "L", 0.12), _slot("CB", "C", 0.36),
                _slot("CB", "C", 0.64), _slot("RB", "R", 0.88)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
    "4-1-2-3": {
        "name": "4-1-2-3",
        "desc": "4-1-2-3 — single pivot feeding a front three",
        "rows": [
            {"y": 0.04, "group": "FWD", "slots": [
                _slot("LW", "L", 0.14), _slot("ST", "C", 0.50), _slot("RW", "R", 0.86)]},
            {"y": 0.36, "group": "MID", "slots": [
                _slot("CM", "L", 0.30), _slot("CM", "R", 0.70)]},
            {"y": 0.52, "group": "MID", "slots": [_slot("CDM", "C", 0.50)]},
            {"y": 0.74, "group": "DEF", "slots": [
                _slot("LB", "L", 0.12), _slot("CB", "C", 0.36),
                _slot("CB", "C", 0.64), _slot("RB", "R", 0.88)]},
            {"y": 0.87, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },

    # ── 4-5-1 family ──
    "4-2-3-1": {
        "name": "4-2-3-1",
        "desc": "4-2-3-1 — two holding mids + attacking trio behind lone striker",
        "rows": [
            {"y": 0.02, "group": "FWD", "slots": [_slot("ST", "C", 0.50)]},
            {"y": 0.20, "group": "MID", "slots": [
                _slot("LW", "L", 0.18), _slot("CAM", "C", 0.50), _slot("RW", "R", 0.82)]},
            {"y": 0.46, "group": "MID", "slots": [
                _slot("CDM", "L", 0.35), _slot("CDM", "R", 0.65)]},
            {"y": 0.72, "group": "DEF", "slots": [
                _slot("LB", "L", 0.12), _slot("CB", "C", 0.36),
                _slot("CB", "C", 0.64), _slot("RB", "R", 0.88)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
    "4-1-4-1": {
        "name": "4-1-4-1",
        "desc": "4-1-4-1 — single CDM shields a flat four-man midfield",
        "rows": [
            {"y": 0.02, "group": "FWD", "slots": [_slot("ST", "C", 0.50)]},
            {"y": 0.28, "group": "MID", "slots": [
                _slot("LM", "L", 0.12), _slot("CM", "C", 0.37),
                _slot("CM", "C", 0.63), _slot("RM", "R", 0.88)]},
            {"y": 0.50, "group": "MID", "slots": [_slot("CDM", "C", 0.50)]},
            {"y": 0.72, "group": "DEF", "slots": [
                _slot("LB", "L", 0.12), _slot("CB", "C", 0.36),
                _slot("CB", "C", 0.64), _slot("RB", "R", 0.88)]},
            {"y": 0.86, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
    "4-3-2-1": {
        "name": "4-3-2-1",
        "desc": "4-3-2-1 — Christmas tree, narrow attack with two AMs",
        "rows": [
            {"y": 0.02, "group": "FWD", "slots": [_slot("ST", "C", 0.50)]},
            {"y": 0.20, "group": "MID", "slots": [
                _slot("CAM", "L", 0.35), _slot("CAM", "R", 0.65)]},
            {"y": 0.42, "group": "MID", "slots": [
                _slot("CM", "L", 0.18), _slot("CM", "C", 0.50), _slot("CM", "R", 0.82)]},
            {"y": 0.72, "group": "DEF", "slots": [
                _slot("LB", "L", 0.12), _slot("CB", "C", 0.36),
                _slot("CB", "C", 0.64), _slot("RB", "R", 0.88)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },

    # ── 4-4-2 family ──
    "4-2-2-2": {
        "name": "4-2-2-2",
        "desc": "4-2-2-2 — Brazilian box, two banks of two in midfield",
        "rows": [
            {"y": 0.04, "group": "FWD", "slots": [
                _slot("ST", "L", 0.35), _slot("ST", "R", 0.65)]},
            {"y": 0.24, "group": "MID", "slots": [
                _slot("CAM", "L", 0.30), _slot("CAM", "R", 0.70)]},
            {"y": 0.44, "group": "MID", "slots": [
                _slot("CDM", "L", 0.30), _slot("CDM", "R", 0.70)]},
            {"y": 0.70, "group": "DEF", "slots": [
                _slot("LB", "L", 0.12), _slot("CB", "C", 0.36),
                _slot("CB", "C", 0.64), _slot("RB", "R", 0.88)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
    "4-1-2-1-2": {
        "name": "4-1-2-1-2",
        "desc": "4-3-1-2 — narrow diamond, CAM + CDM on the spine",
        "rows": [
            {"y": 0.03, "group": "FWD", "slots": [
                _slot("ST", "L", 0.35), _slot("ST", "R", 0.65)]},
            {"y": 0.22, "group": "MID", "slots": [_slot("CAM", "C", 0.50)]},
            {"y": 0.40, "group": "MID", "slots": [
                _slot("CM", "L", 0.30), _slot("CM", "R", 0.70)]},
            {"y": 0.56, "group": "MID", "slots": [_slot("CDM", "C", 0.50)]},
            {"y": 0.74, "group": "DEF", "slots": [
                _slot("LB", "L", 0.12), _slot("CB", "C", 0.38),
                _slot("CB", "C", 0.62), _slot("RB", "R", 0.88)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },

    # ── 3-6-1 ──
    "3-6-1": {
        "name": "3-6-1",
        "desc": "3-2-4-1 — midfield overload, deep quartet behind a striker",
        "rows": [
            {"y": 0.02, "group": "FWD", "slots": [_slot("ST", "C", 0.50)]},
            {"y": 0.22, "group": "MID", "slots": [
                _slot("LM", "L", 0.12), _slot("CAM", "L", 0.35),
                _slot("CAM", "R", 0.65), _slot("RM", "R", 0.88)]},
            {"y": 0.46, "group": "MID", "slots": [
                _slot("CM", "L", 0.32), _slot("CM", "R", 0.68)]},
            {"y": 0.72, "group": "DEF", "slots": [
                _slot("CB", "L", 0.22), _slot("CB", "C", 0.50), _slot("CB", "R", 0.78)]},
            {"y": 0.86, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },

    # ── 3-5-2 family ──
    "3-5-2": {
        "name": "3-5-2",
        "desc": "3-2-3-2 — three at the back, wing-backs provide width",
        "rows": [
            {"y": 0.04, "group": "FWD", "slots": [
                _slot("ST", "L", 0.35), _slot("ST", "R", 0.65)]},
            {"y": 0.34, "group": "MID", "slots": [
                _slot("LM", "L", 0.12), _slot("CM", "C", 0.30),
                _slot("CM", "C", 0.50), _slot("CM", "C", 0.70),
                _slot("RM", "R", 0.88)]},
            {"y": 0.69, "group": "DEF", "slots": [
                _slot("CB", "L", 0.22), _slot("CB", "C", 0.50), _slot("CB", "R", 0.78)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
    "3-3-2-2": {
        "name": "3-3-2-2",
        "desc": "3-3-2-2 - three at the back, two shadow strikers",
        "rows": [
            {"y": 0.04, "group": "FWD", "slots": [
                _slot("ST", "L", 0.35), _slot("ST", "R", 0.65)]},
            {"y": 0.24, "group": "MID", "slots": [
                _slot("CAM", "L", 0.30), _slot("CAM", "R", 0.70)]},
            {"y": 0.44, "group": "MID", "slots": [
                _slot("CM", "L", 0.18), _slot("CM", "C", 0.50), _slot("CM", "R", 0.82)]},
            {"y": 0.74, "group": "DEF", "slots": [
                _slot("CB", "L", 0.22), _slot("CB", "C", 0.50), _slot("CB", "R", 0.78)]},
            {"y": 0.87, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },

    # ── 3-4-3 ──
    "3-4-3": {
        "name": "3-4-3",
        "desc": "3-2-2-3 — three centre-backs, attacking midfield four, front three",
        "rows": [
            {"y": 0.04, "group": "FWD", "slots": [
                _slot("LW", "L", 0.14), _slot("ST", "C", 0.50), _slot("RW", "R", 0.86)]},
            {"y": 0.36, "group": "MID", "slots": [
                _slot("LM", "L", 0.14), _slot("CM", "C", 0.37),
                _slot("CM", "C", 0.63), _slot("RM", "R", 0.86)]},
            {"y": 0.69, "group": "DEF", "slots": [
                _slot("CB", "L", 0.22), _slot("CB", "C", 0.50), _slot("CB", "R", 0.78)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },

    # ── 5-4-1 ──
    "5-4-1": {
        "name": "5-4-1",
        "desc": "5-2-2-1 — five at the back, wing-backs, lone striker",
        "rows": [
            {"y": 0.02, "group": "FWD", "slots": [_slot("ST", "C", 0.50)]},
            {"y": 0.34, "group": "MID", "slots": [
                _slot("LM", "L", 0.12), _slot("CM", "C", 0.38),
                _slot("CM", "C", 0.62), _slot("RM", "R", 0.88)]},
            {"y": 0.68, "group": "DEF", "slots": [
                _slot("LWB", "L", 0.10), _slot("CB", "C", 0.28),
                _slot("CB", "C", 0.50), _slot("CB", "C", 0.72), _slot("RWB", "R", 0.90)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },

    # ── 5-3-2 family ──
    "5-2-1-2": {
        "name": "5-2-1-2",
        "desc": "5-2-1-2 — five back, CAM behind two strikers, counter shape",
        "rows": [
            {"y": 0.04, "group": "FWD", "slots": [
                _slot("ST", "L", 0.35), _slot("ST", "R", 0.65)]},
            {"y": 0.24, "group": "MID", "slots": [_slot("CAM", "C", 0.50)]},
            {"y": 0.42, "group": "MID", "slots": [
                _slot("CM", "L", 0.32), _slot("CM", "R", 0.68)]},
            {"y": 0.70, "group": "DEF", "slots": [
                _slot("LWB", "L", 0.10), _slot("CB", "C", 0.28),
                _slot("CB", "C", 0.50), _slot("CB", "C", 0.72), _slot("RWB", "R", 0.90)]},
            {"y": 0.86, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
    "5-3-2": {
        "name": "5-3-2",
        "desc": "5-3-2 — five defenders, flat midfield three, two strikers",
        "rows": [
            {"y": 0.04, "group": "FWD", "slots": [
                _slot("ST", "L", 0.35), _slot("ST", "R", 0.65)]},
            {"y": 0.36, "group": "MID", "slots": [
                _slot("CM", "L", 0.25), _slot("CM", "C", 0.50), _slot("CM", "R", 0.75)]},
            {"y": 0.68, "group": "DEF", "slots": [
                _slot("LWB", "L", 0.10), _slot("CB", "C", 0.28),
                _slot("CB", "C", 0.50), _slot("CB", "C", 0.72), _slot("RWB", "R", 0.90)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
}

FORMATION_NAMES = sorted(FORMATIONS.keys())
DEFAULT_FORMATION = "4-3-3"

# FL26 display labels for each formation key
FORMATION_LABELS = {
    "4-3-3":     "4-3-3 (4-2-1-3)",
    "4-1-2-3":   "4-3-3 (4-1-2-3)",
    "4-2-3-1":   "4-5-1 (4-2-3-1)",
    "4-1-4-1":   "4-5-1 (4-1-4-1)",
    "4-3-2-1":   "4-5-1 (4-3-2-1)",
    "4-2-2-2":   "4-4-2 (4-2-2-2)",
    "4-1-2-1-2": "4-4-2 (4-3-1-2)",
    "3-6-1":     "3-6-1 (3-2-4-1)",
    "3-5-2":     "3-5-2 (3-2-3-2)",
    "3-3-2-2":   "3-5-2 (3-3-2-2)",
    "3-4-3":     "3-4-3 (3-2-2-3)",
    "5-4-1":     "5-4-1 (5-2-2-1)",
    "5-2-1-2":   "5-3-2 (5-2-1-2)",
    "5-3-2":     "5-3-2 (5-3-2)",
}


def formation_label(key: str) -> str:
    return FORMATION_LABELS.get(key, key.upper())


def get_formation(name):
    return FORMATIONS.get(name, FORMATIONS[DEFAULT_FORMATION])


def all_slots(formation):
    """Flatten all slots in order, each annotated with its row y + slot index."""
    slots = []
    idx = 0
    for row in formation["rows"]:
        for slot in row["slots"]:
            slots.append({
                "index": idx,
                "y": row["y"],
                "group": row["group"],
                "pos": slot["pos"],
                "side": slot["side"],
                "x": slot["x"],
            })
            idx += 1
    return slots


def position_side(pos):
    """Determine L/C/R side from a position string."""
    left = {"LB","LWB","LW","LM","LF","LS","LCB","LCM","LAM","LDM"}
    right = {"RB","RWB","RW","RM","RF","RS","RCB","RCM","RAM","RDM"}
    if pos in left:
        return "L"
    if pos in right:
        return "R"
    return "C"


# Secondary positions: positions that can fill a slot if the primary isn't available.
POS_ALTERNATIVES = {
    # FWD
    "LW": ["LW", "LM", "LF", "RW", "ST", "CF"],
    "RW": ["RW", "RM", "RF", "LW", "ST", "CF"],
    "ST": ["ST", "CF", "LW", "RW", "LS", "RS"],
    "CF": ["CF", "ST", "CAM", "LW", "RW"],
    "LS": ["LS", "ST", "LW", "LF"],
    "RS": ["RS", "ST", "RW", "RF"],
    # MID
    "CAM": ["CAM", "CM", "CF", "LW", "RW"],
    "CM": ["CM", "CAM", "CDM", "LM", "RM"],
    "CDM": ["CDM", "CM", "CB"],
    "LM": ["LM", "LW", "CM", "RM"],
    "RM": ["RM", "RW", "CM", "LM"],
    "LAM": ["LAM", "CAM", "LM", "CM"],
    "RAM": ["RAM", "CAM", "RM", "CM"],
    "LCM": ["LCM", "CM", "CDM", "CAM"],
    "RCM": ["RCM", "CM", "CDM", "CAM"],
    "LDM": ["LDM", "CDM", "CM"],
    "RDM": ["RDM", "CDM", "CM"],
    # DEF
    "LB": ["LB", "LWB", "CB", "LM"],
    "RB": ["RB", "RWB", "CB", "RM"],
    "LWB": ["LWB", "LB", "CB"],
    "RWB": ["RWB", "RB", "CB"],
    "CB": ["CB", "CDM", "LB", "RB"],
    "LCB": ["LCB", "CB", "LB"],
    "RCB": ["RCB", "CB", "RB"],
    # GK
    "GK": ["GK"],
}


def auto_assign_lineup(squad, formation):
    """
    Auto-assign players to formation slots.
    Returns a list of (slot_dict, player_or_None) in slot order.
    """
    slots = all_slots(formation)
    used_keys = set()
    result = []

    squad_sorted = sorted(squad, key=lambda p: p["ovr"], reverse=True)

    by_group = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad_sorted:
        by_group.setdefault(p["group"], []).append(p)

    for slot in slots:
        assigned = None
        preferred = slot["pos"]
        alts = POS_ALTERNATIVES.get(preferred, [preferred])
        group = slot["group"]
        pool = [p for p in by_group.get(group, []) if p["key"] not in used_keys]

        # 1) Exact position match
        for p in pool:
            if p["position"] == preferred:
                assigned = p
                break
        # 2) Alternative positions
        if not assigned:
            for p in pool:
                if p["position"] in alts:
                    assigned = p
                    break
        # 3) Same side
        if not assigned:
            slot_side = slot["side"]
            for p in pool:
                if position_side(p["position"]) == slot_side:
                    assigned = p
                    break
        # 4) Any in group
        if not assigned and pool:
            assigned = pool[0]

        if assigned:
            used_keys.add(assigned["key"])

        result.append((slot, assigned))

    return result
