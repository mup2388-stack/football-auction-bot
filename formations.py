"""
Formation definitions for the squad card renderer.

Each formation defines rows of slots. Each slot has:
  - pos:  preferred position (LW, ST, CB, GK, etc.)
  - side: L / C / R  (for auto-assignment + staggered layout)
  - x:    horizontal position on pitch (0.0=left, 1.0=right)

X positions are deliberately staggered so wingers sit WIDER than midfielders,
but pulled in from the edges so cards stay ON the pitch.
"""


def _slot(pos, side, x):
    return {"pos": pos, "side": side, "x": x}


FORMATIONS = {
    "4-3-3": {
        "name": "4-3-3",
        "desc": "Attacking — wingers high and wide",
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
    "4-4-2": {
        "name": "4-4-2",
        "desc": "Classic — two strikers, flat midfield",
        "rows": [
            {"y": 0.04, "group": "FWD", "slots": [
                _slot("ST", "L", 0.35), _slot("ST", "R", 0.65)]},
            {"y": 0.36, "group": "MID", "slots": [
                _slot("LM", "L", 0.14), _slot("CM", "C", 0.37),
                _slot("CM", "C", 0.63), _slot("RM", "R", 0.86)]},
            {"y": 0.67, "group": "DEF", "slots": [
                _slot("LB", "L", 0.12), _slot("CB", "C", 0.36),
                _slot("CB", "C", 0.64), _slot("RB", "R", 0.88)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
    "3-5-2": {
        "name": "3-5-2",
        "desc": "Wing-backs provide width",
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
    "4-2-3-1": {
        "name": "4-2-3-1",
        "desc": "Modern — holding mids + attacking trio",
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
    "3-4-3": {
        "name": "3-4-3",
        "desc": "Aggressive — three at the back, front three",
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
    "5-3-2": {
        "name": "5-3-2",
        "desc": "Defensive — five at the back",
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
    "4-5-1": {
        "name": "4-5-1",
        "desc": "Midfield-heavy — five across the middle",
        "rows": [
            {"y": 0.02, "group": "FWD", "slots": [_slot("ST", "C", 0.50)]},
            {"y": 0.34, "group": "MID", "slots": [
                _slot("LM", "L", 0.10), _slot("CM", "C", 0.27),
                _slot("CM", "C", 0.50), _slot("CM", "C", 0.73),
                _slot("RM", "R", 0.90)]},
            {"y": 0.68, "group": "DEF", "slots": [
                _slot("LB", "L", 0.12), _slot("CB", "C", 0.36),
                _slot("CB", "C", 0.64), _slot("RB", "R", 0.88)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
    "5-4-1": {
        "name": "5-4-1",
        "desc": "Very defensive — five back, lone striker",
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
    "4-1-2-1-2": {
        "name": "4-1-2-1-2",
        "desc": "Narrow diamond — CAM + CDM",
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
    "4-3-2-1": {
        "name": "4-3-2-1",
        "desc": "Christmas tree — narrow attack",
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
    "3-4-2-1": {
        "name": "3-4-2-1",
        "desc": "Conte style — three back, two shadow strikers",
        "rows": [
            {"y": 0.02, "group": "FWD", "slots": [_slot("ST", "C", 0.50)]},
            {"y": 0.20, "group": "MID", "slots": [
                _slot("CAM", "L", 0.30), _slot("CAM", "R", 0.70)]},
            {"y": 0.42, "group": "MID", "slots": [
                _slot("LM", "L", 0.14), _slot("CM", "C", 0.38),
                _slot("CM", "C", 0.62), _slot("RM", "R", 0.86)]},
            {"y": 0.72, "group": "DEF", "slots": [
                _slot("CB", "L", 0.22), _slot("CB", "C", 0.50), _slot("CB", "R", 0.78)]},
            {"y": 0.83, "group": "GK", "slots": [_slot("GK", "C", 0.50)]},
        ],
    },
    "4-2-2-2": {
        "name": "4-2-2-2",
        "desc": "Brazilian box — two banks of two",
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
}

FORMATION_NAMES = sorted(FORMATIONS.keys())
DEFAULT_FORMATION = "4-3-3"


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
# Maps each slot-preferred position to a list of acceptable alternatives (same group).
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
    Prefers exact position, then alternatives (with secondary positions),
    then any player in the group.
    """
    slots = all_slots(formation)
    used_keys = set()
    result = []

    # Sort squad by OVR descending so best players get priority
    squad_sorted = sorted(squad, key=lambda p: p["ovr"], reverse=True)

    # Group players by their position group
    by_group = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad_sorted:
        by_group.setdefault(p["group"], []).append(p)

    for slot in slots:
        assigned = None
        preferred = slot["pos"]
        alts = POS_ALTERNATIVES.get(preferred, [preferred])
        group = slot["group"]
        pool = [p for p in by_group.get(group, []) if p["key"] not in used_keys]

        # 1) Try exact position match
        for p in pool:
            if p["position"] == preferred:
                assigned = p
                break

        # 2) Try alternative positions
        if not assigned:
            for p in pool:
                if p["position"] in alts:
                    assigned = p
                    break

        # 3) Try same side in the group
        if not assigned:
            slot_side = slot["side"]
            for p in pool:
                if position_side(p["position"]) == slot_side:
                    assigned = p
                    break

        # 4) Any player in the group
        if not assigned and pool:
            assigned = pool[0]

        if assigned:
            used_keys.add(assigned["key"])

        result.append((slot, assigned))

    return result
