"""
Economy & squad management for the auction bot.
Wallets, squads, sold-player tracking, pool filtering by phase, and leaderboards.
"""
import database as db
from config import Config
import players as P


def money(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}{Config.CURRENCY_SYMBOL}{abs(amount):,}"


# --------------------------------------------------------------------------
# Users / wallet
# --------------------------------------------------------------------------
def ensure_user(guild_id: int, user_id: int) -> int:
    with db.cursor() as c:
        row = c.execute(
            "SELECT balance FROM users WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchone()
        if row is None:
            c.execute(
                "INSERT INTO users (guild_id, user_id, balance) VALUES (?, ?, ?)",
                (guild_id, user_id, Config.STARTING_BALANCE),
            )
            return Config.STARTING_BALANCE
        return row["balance"]


def get_balance(guild_id: int, user_id: int) -> int:
    return ensure_user(guild_id, user_id)


def adjust_balance(guild_id: int, user_id: int, delta: int):
    ensure_user(guild_id, user_id)
    with db.cursor() as c:
        c.execute(
            "UPDATE users SET balance = balance + ? WHERE guild_id=? AND user_id=?",
            (delta, guild_id, user_id),
        )


def can_afford(guild_id: int, user_id: int, amount: int) -> bool:
    return get_balance(guild_id, user_id) >= amount


# --------------------------------------------------------------------------
# Squads
# --------------------------------------------------------------------------
def owns(guild_id: int, user_id: int, player_key: str) -> bool:
    with db.cursor() as c:
        return c.execute(
            "SELECT 1 FROM squads WHERE guild_id=? AND user_id=? AND player_key=?",
            (guild_id, user_id, player_key),
        ).fetchone() is not None


def add_player(guild_id: int, user_id: int, player: dict, price: int):
    with db.cursor() as c:
        c.execute(
            "INSERT OR REPLACE INTO squads (guild_id, user_id, player_key, position, acquired_price) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, player["key"], player["position"], price),
        )


def get_squad(guild_id: int, user_id: int) -> list:
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key, position, acquired_price, acquired_at FROM squads "
            "WHERE guild_id=? AND user_id=? ORDER BY acquired_at DESC",
            (guild_id, user_id),
        ).fetchall()
    squad = []
    for r in rows:
        pdata = P.get(r["player_key"])
        if pdata:
            squad.append({**pdata, "acquired_price": r["acquired_price"],
                          "acquired_at": r["acquired_at"]})
    return squad


def squad_value(squad: list) -> int:
    return sum(p["value"] for p in squad)


def squad_count(guild_id: int, user_id: int) -> int:
    with db.cursor() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM squads WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchone()
        return row["n"] if row else 0


# --------------------------------------------------------------------------
# Sold players & the remaining pool
# --------------------------------------------------------------------------
def sold_player_keys(guild_id: int) -> set:
    """All player keys already owned by someone in this guild (never re-auction)."""
    with db.cursor() as c:
        rows = c.execute(
            "SELECT DISTINCT player_key FROM squads WHERE guild_id=?",
            (guild_id,),
        ).fetchall()
    return {r["player_key"] for r in rows}


def is_sold(guild_id: int, player_key: str) -> bool:
    return player_key in sold_player_keys(guild_id)


def remaining_pool(guild_id: int, phase: str = "ALL", exclude: set = None):
    """
    Players not yet sold, optionally filtered to a phase group, sorted OVR desc.
    `exclude` is an extra set of keys to skip (e.g. offered-this-session).
    phase="UNSOLD" returns only players who were offered but got no bids.
    """
    exclude = exclude or set()
    sold = sold_player_keys(guild_id)

    if phase == "UNSOLD":
        unsold = unsold_player_keys(guild_id)
        out = []
        for p in P.all_players():
            if p["key"] in unsold and p["key"] not in sold and p["key"] not in exclude:
                out.append(p)
        out.sort(key=lambda p: p["ovr"], reverse=True)
        return out

    out = []
    for p in P.all_players():
        if p["key"] in sold or p["key"] in exclude:
            continue
        if phase != "ALL" and p["group"] != phase:
            continue
        out.append(p)
    out.sort(key=lambda p: p["ovr"], reverse=True)
    return out


def phase_counts(guild_id: int) -> dict:
    """Remaining (unsold) player counts per phase group + ALL + UNSOLD."""
    sold = sold_player_keys(guild_id)
    counts = {g: 0 for g in P.PHASE_ORDER}
    counts["ALL"] = 0
    for p in P.all_players():
        if p["key"] in sold:
            continue
        counts[p["group"]] += 1
        counts["ALL"] += 1
    counts["UNSOLD"] = len(unsold_player_keys(guild_id))
    return counts


# --------------------------------------------------------------------------
# Leaderboard
# --------------------------------------------------------------------------
def leaderboard(guild_id: int, limit: int = 10):
    entries = []
    with db.cursor() as c:
        rows = c.execute(
            "SELECT user_id, balance FROM users WHERE guild_id=?",
            (guild_id,),
        ).fetchall()
    for r in rows:
        uid = r["user_id"]
        sv = squad_value(get_squad(guild_id, uid))
        entries.append({"user_id": uid, "balance": r["balance"],
                        "squad_value": sv, "net_worth": r["balance"] + sv})
    entries.sort(key=lambda e: e["net_worth"], reverse=True)
    return entries[:limit]


# --------------------------------------------------------------------------
# Auction history
# --------------------------------------------------------------------------
def log_auction(guild_id: int, player: dict, winner_id, final_price: int, status: str = "sold"):
    with db.cursor() as c:
        c.execute(
            "INSERT INTO auction_history (guild_id, player_key, position, winner_id, final_price, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, player["key"], player["position"], winner_id, final_price, status),
        )


def log_unsold(guild_id: int, player: dict):
    """Log a player that was auctioned but got no bids."""
    with db.cursor() as c:
        c.execute(
            "INSERT INTO auction_history (guild_id, player_key, position, winner_id, final_price, status) "
            "VALUES (?, ?, ?, NULL, 0, 'unsold')",
            (guild_id, player["key"], player["position"]),
        )


def unsold_player_keys(guild_id: int) -> set:
    """Players that were offered but got no bids (and haven't been re-sold)."""
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key FROM auction_history "
            "WHERE guild_id=? AND status='unsold' "
            "AND player_key NOT IN (SELECT player_key FROM auction_history WHERE guild_id=? AND status='sold')",
            (guild_id, guild_id),
        ).fetchall()
    return {r["player_key"] for r in rows}


def clear_offered(guild_id: int, player_key: str):
    """Remove a player from the in-memory offered set so they can be re-auctioned."""
    # This is called from auction.py's OFFERED dict, handled there
    pass


def recent_sales(guild_id: int, limit: int = 10):
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key, winner_id, final_price, finished_at FROM auction_history "
            "WHERE guild_id=? AND winner_id IS NOT NULL "
            "ORDER BY finished_at DESC LIMIT ?",
            (guild_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        pdata = P.get(r["player_key"])
        if pdata:
            out.append({**pdata, "winner_id": r["winner_id"],
                        "price": r["final_price"], "when": r["finished_at"]})
    return out


# --------------------------------------------------------------------------
# Formations & lineup overrides
# --------------------------------------------------------------------------
import formations as FM


def get_formation(guild_id: int, user_id: int) -> str:
    with db.cursor() as c:
        row = c.execute(
            "SELECT formation FROM formations WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchone()
    return row["formation"] if row else FM.DEFAULT_FORMATION


def set_formation(guild_id: int, user_id: int, formation: str):
    with db.cursor() as c:
        c.execute(
            "INSERT INTO formations (guild_id, user_id, formation) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET formation=excluded.formation",
            (guild_id, user_id, formation),
        )


# ── Tactics (attacking/defensive/advanced instructions) ──

def get_tactics(guild_id: int, user_id: int) -> dict:
    """Get a manager's full tactic settings (normalized with defaults)."""
    import tactics as T
    import json as _json
    with db.cursor() as c:
        row = c.execute(
            "SELECT data FROM tactics WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchone()
    if row and row["data"]:
        try:
            raw = _json.loads(row["data"])
        except (ValueError, TypeError):
            raw = {}
        return T.normalize(raw)
    return T.default_tactics()


def save_tactics(guild_id: int, user_id: int, data: dict):
    """Save tactic settings (normalized before storage)."""
    import tactics as T
    import json as _json
    ensure_user(guild_id, user_id)
    normalized = T.normalize(data)
    with db.cursor() as c:
        c.execute(
            "INSERT INTO tactics (guild_id, user_id, data) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET data=excluded.data",
            (guild_id, user_id, _json.dumps(normalized)),
        )


def get_lineup_overrides(guild_id: int, user_id: int) -> dict:
    """Returns {slot_index: player_key} for manually assigned slots."""
    with db.cursor() as c:
        rows = c.execute(
            "SELECT slot_index, player_key FROM lineup_overrides "
            "WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchall()
    return {r["slot_index"]: r["player_key"] for r in rows}


def set_lineup_slot(guild_id: int, user_id: int, slot_index: int, player_key: str):
    with db.cursor() as c:
        c.execute(
            "INSERT INTO lineup_overrides (guild_id, user_id, slot_index, player_key) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id, slot_index) "
            "DO UPDATE SET player_key=excluded.player_key",
            (guild_id, user_id, slot_index, player_key),
        )


def clear_lineup_slot(guild_id: int, user_id: int, slot_index: int):
    with db.cursor() as c:
        c.execute(
            "DELETE FROM lineup_overrides "
            "WHERE guild_id=? AND user_id=? AND slot_index=?",
            (guild_id, user_id, slot_index),
        )


def clear_all_overrides(guild_id: int, user_id: int):
    with db.cursor() as c:
        c.execute(
            "DELETE FROM lineup_overrides WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )


def get_lineup(guild_id: int, user_id: int):
    """
    Get the full lineup: formation + assigned players per slot.
    Apply manual overrides FIRST, then auto-fill remaining slots.
    """
    formation_name = get_formation(guild_id, user_id)
    formation = FM.get_formation(formation_name)
    squad = get_squad(guild_id, user_id)
    overrides = get_lineup_overrides(guild_id, user_id)
    slots = FM.all_slots(formation)

    result = [None] * len(slots)
    used_keys = set()

    # PASS 1: Apply manual overrides first (they take priority)
    for slot in slots:
        idx = slot["index"]
        if idx in overrides:
            override_key = overrides[idx]
            override_player = next((p for p in squad if p["key"] == override_key), None)
            if override_player and override_key not in used_keys:
                result[idx] = (slot, override_player)
                used_keys.add(override_key)
            else:
                result[idx] = (slot, None)

    # PASS 2: Auto-assign remaining slots
    squad_sorted = sorted(squad, key=lambda p: p["ovr"], reverse=True)
    by_group = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad_sorted:
        if p["key"] not in used_keys:
            by_group.setdefault(p["group"], []).append(p)

    for slot in slots:
        idx = slot["index"]
        if result[idx] is not None:
            continue

        assigned = None
        preferred = slot["pos"]
        alts = FM.POS_ALTERNATIVES.get(preferred, [preferred])
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
                if p["position"] in alts and p["position"] != preferred:
                    assigned = p
                    break
        # 3) Same side
        if not assigned:
            slot_side = slot["side"]
            for p in pool:
                if FM.position_side(p["position"]) == slot_side:
                    assigned = p
                    break
        # 4) Any in group
        if not assigned and pool:
            assigned = pool[0]

        if assigned:
            used_keys.add(assigned["key"])
            result[idx] = (slot, assigned)
        else:
            result[idx] = (slot, None)

    return result, formation_name


# --------------------------------------------------------------------------
# Scripted draft queue
# --------------------------------------------------------------------------
def queue_list(guild_id: int):
    """Return the ordered list of queued player keys for a guild."""
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key FROM draft_queue WHERE guild_id=? ORDER BY position",
            (guild_id,),
        ).fetchall()
    return [r["player_key"] for r in rows]


def queue_add(guild_id: int, player_key: str) -> int:
    """Append a player to the end of the queue. Returns the new position (1-based)."""
    with db.cursor() as c:
        row = c.execute(
            "SELECT MAX(position) AS m FROM draft_queue WHERE guild_id=?", (guild_id,)
        ).fetchone()
        pos = (row["m"] or 0) + 1
        c.execute(
            "INSERT OR REPLACE INTO draft_queue (guild_id, position, player_key) VALUES (?, ?, ?)",
            (guild_id, pos, player_key),
        )
    return pos


def queue_add_many(guild_id: int, player_keys: list) -> int:
    """Append many player keys. Returns count added (skips already-queued)."""
    existing = set(queue_list(guild_id))
    added = 0
    for key in player_keys:
        if key in existing:
            continue
        queue_add(guild_id, key)
        existing.add(key)
        added += 1
    return added


def queue_clear(guild_id: int):
    with db.cursor() as c:
        c.execute("DELETE FROM draft_queue WHERE guild_id=?", (guild_id,))


def queue_next(guild_id: int):
    """Return (player_key, remaining_count) of the front of the queue, or (None, 0)."""
    q = queue_list(guild_id)
    if not q:
        return None, 0
    return q[0], len(q)


def queue_consume(guild_id: int, player_key: str):
    """Remove the first occurrence of a player from the queue, then re-number."""
    with db.cursor() as c:
        remaining = [r["player_key"] for r in c.execute(
            "SELECT player_key FROM draft_queue WHERE guild_id=? ORDER BY position",
            (guild_id,)).fetchall()]
        for i, key in enumerate(remaining):
            if key == player_key:
                del remaining[i]
                break
        c.execute("DELETE FROM draft_queue WHERE guild_id=?", (guild_id,))
        for i, key in enumerate(remaining, 1):
            c.execute(
                "INSERT INTO draft_queue (guild_id, position, player_key) VALUES (?, ?, ?)",
                (guild_id, i, key),
            )


# --------------------------------------------------------------------------
# Player faces (SoFIFA URLs)
# --------------------------------------------------------------------------
_FACE_URL_MAP = None

def _load_face_map():
    """Load pre-built face URL mapping (83% coverage from SoFiFA CSV)."""
    global _FACE_URL_MAP
    _FACE_URL_MAP = {}
    try:
        import os, json as _json
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "face_urls.json")
        if os.path.exists(path):
            with open(path) as f:
                _FACE_URL_MAP = _json.load(f)
            print(f"[i] Face URLs loaded: {len(_FACE_URL_MAP)} players")
    except Exception as e:
        print(f"[!] face_urls.json load failed: {e}")


def get_face_url(player_key: str):
    """Get SoFiFA face URL. Checks DB first (manual overrides via /setface),
    then falls back to the pre-built face_urls.json mapping."""
    with db.cursor() as c:
        row = c.execute(
            "SELECT face_url FROM player_faces WHERE player_key=?", (player_key,)
        ).fetchone()
    if row and row["face_url"]:
        return row["face_url"]
    global _FACE_URL_MAP
    if _FACE_URL_MAP is None:
        _load_face_map()
    return _FACE_URL_MAP.get(player_key)




def set_face_url(player_key: str, url: str):
    with db.cursor() as c:
        c.execute(
            "INSERT INTO player_faces (player_key, face_url) VALUES (?, ?) "
            "ON CONFLICT(player_key) DO UPDATE SET face_url=excluded.face_url",
            (player_key, url),
        )


# --------------------------------------------------------------------------
# Team name & logo
# --------------------------------------------------------------------------
def get_team_name(guild_id: int, user_id: int):
    ensure_user(guild_id, user_id)
    with db.cursor() as c:
        row = c.execute(
            "SELECT team_name FROM users WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchone()
    return row["team_name"] if row and row["team_name"] else None


def set_team_name(guild_id: int, user_id: int, name: str):
    ensure_user(guild_id, user_id)
    with db.cursor() as c:
        c.execute(
            "UPDATE users SET team_name=? WHERE guild_id=? AND user_id=?",
            (name[:50], guild_id, user_id),  # cap at 50 chars
        )


def get_team_logo(guild_id: int, user_id: int):
    ensure_user(guild_id, user_id)
    with db.cursor() as c:
        row = c.execute(
            "SELECT team_logo FROM users WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchone()
    return row["team_logo"] if row and row["team_logo"] else None


def set_team_logo(guild_id: int, user_id: int, url: str):
    ensure_user(guild_id, user_id)
    with db.cursor() as c:
        c.execute(
            "UPDATE users SET team_logo=? WHERE guild_id=? AND user_id=?",
            (url, guild_id, user_id),
        )


def get_player_owner(guild_id: int, player_key: str):
    """Returns (user_id, team_name, team_logo) of whoever owns this player, or None."""
    with db.cursor() as c:
        row = c.execute(
            "SELECT user_id FROM squads WHERE guild_id=? AND player_key=?",
            (guild_id, player_key),
        ).fetchone()
    if not row:
        return None
    uid = row["user_id"]
    return (uid, get_team_name(guild_id, uid), get_team_logo(guild_id, uid))


# --------------------------------------------------------------------------
# Budget tracking / needs analysis
# --------------------------------------------------------------------------

# Minimum squad requirements
REQUIREMENTS = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
MIN_SQUAD_SIZE = sum(REQUIREMENTS.values())  # 15

# Cheapest player value (for calculating minimum fill cost)
CHEAPEST_PLAYER_VALUE = 250_000  # £250k


def get_needs(guild_id: int, user_id: int):
    """
    Analyze what a manager still needs.
    Returns dict with:
      - counts: {GK: have, DEF: have, ...}
      - needed: {GK: remaining_needed, ...}
      - budget: current balance
      - min_cost: minimum cost to fill remaining slots
      - max_bid: max they can spend on next player
      - complete: bool
    """
    squad = get_squad(guild_id, user_id)
    budget = get_balance(guild_id, user_id)

    counts = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
    for p in squad:
        counts[p["group"]] += 1

    needed = {}
    total_needed = 0
    for g, req in REQUIREMENTS.items():
        remaining = max(0, req - counts[g])
        needed[g] = remaining
        total_needed += remaining

    # Min cost = cheapest player value × remaining slots needed
    min_cost = total_needed * CHEAPEST_PLAYER_VALUE

    # Max bid = budget - min_cost (what they can spend on the NEXT player)
    max_bid = budget - min_cost

    complete = total_needed == 0

    return {
        "counts": counts,
        "needed": needed,
        "total_needed": total_needed,
        "budget": budget,
        "min_cost": min_cost,
        "max_bid": max_bid,
        "complete": complete,
        "squad_size": len(squad),
    }


# --------------------------------------------------------------------------
# Trade system
# --------------------------------------------------------------------------

def create_trade(guild_id: int, from_user: int, to_user: int,
                 offering_keys: list, requesting_keys: list) -> int:
    """Create a trade offer. Returns trade ID."""
    with db.cursor() as c:
        c.execute(
            "INSERT INTO trades (guild_id, from_user, to_user, offering, requesting, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'))",
            (guild_id, from_user, to_user,
             ",".join(offering_keys), ",".join(requesting_keys)),
        )
        return c.lastrowid


def get_trade(guild_id: int, trade_id: int):
    with db.cursor() as c:
        row = c.execute(
            "SELECT * FROM trades WHERE guild_id=? AND id=?",
            (guild_id, trade_id),
        ).fetchone()
    return dict(row) if row else None


def get_pending_trades(guild_id: int, user_id: int):
    with db.cursor() as c:
        rows = c.execute(
            "SELECT * FROM trades WHERE guild_id=? AND to_user=? AND status='pending' "
            "ORDER BY created_at DESC",
            (guild_id, user_id),
        ).fetchall()
    return [dict(r) for r in rows]


def update_trade_status(guild_id: int, trade_id: int, status: str):
    with db.cursor() as c:
        c.execute(
            "UPDATE trades SET status=?, resolved_at=datetime('now') WHERE guild_id=? AND id=?",
            (status, guild_id, trade_id),
        )


def execute_trade(guild_id: int, trade_id: int):
    """Swap player ownership between two managers."""
    trade = get_trade(guild_id, trade_id)
    if not trade or trade["status"] != "pending":
        return False

    from_user = trade["from_user"]
    to_user = trade["to_user"]
    offering = [k for k in trade["offering"].split(",") if k]
    requesting = [k for k in trade["requesting"].split(",") if k]

    with db.cursor() as c:
        # Move offered players from → to
        for key in offering:
            # Get the acquired price first
            row = c.execute(
                "SELECT acquired_price FROM squads WHERE guild_id=? AND user_id=? AND player_key=?",
                (guild_id, from_user, key),
            ).fetchone()
            price = row["acquired_price"] if row else 0
            c.execute(
                "DELETE FROM squads WHERE guild_id=? AND user_id=? AND player_key=?",
                (guild_id, from_user, key),
            )
            c.execute(
                "INSERT OR REPLACE INTO squads (guild_id, user_id, player_key, position, acquired_price) "
                "VALUES (?, ?, ?, ?, ?)",
                (guild_id, to_user, key, "", price),
            )

        # Move requested players to → from
        for key in requesting:
            row = c.execute(
                "SELECT acquired_price FROM squads WHERE guild_id=? AND user_id=? AND player_key=?",
                (guild_id, to_user, key),
            ).fetchone()
            price = row["acquired_price"] if row else 0
            c.execute(
                "DELETE FROM squads WHERE guild_id=? AND user_id=? AND player_key=?",
                (guild_id, to_user, key),
            )
            c.execute(
                "INSERT OR REPLACE INTO squads (guild_id, user_id, player_key, position, acquired_price) "
                "VALUES (?, ?, ?, ?, ?)",
                (guild_id, from_user, key, "", price),
            )

        c.execute(
            "UPDATE trades SET status='accepted', resolved_at=datetime('now') "
            "WHERE guild_id=? AND id=?",
            (guild_id, trade_id),
        )
    return True


# --------------------------------------------------------------------------
# CSV export (for Football Life / external tools)
# --------------------------------------------------------------------------
def export_csv(guild_id: int) -> str:
    """Build a CSV of every manager's squad. Returns the CSV text."""
    import csv as _csv
    import io
    buf = io.StringIO()
    w = _csv.writer(buf)
    w.writerow(["manager_id", "player", "position", "group", "club", "country",
                "ovr", "acquired_price", "market_value"])
    with db.cursor() as c:
        rows = c.execute(
            "SELECT user_id, player_key, acquired_price FROM squads "
            "WHERE guild_id=? ORDER BY user_id, player_key",
            (guild_id,),
        ).fetchall()
    for r in rows:
        p = P.get(r["player_key"])
        if not p:
            continue
        w.writerow([r["user_id"], p["name"], p["position"], p["group"], p.get("club",""),
                    p["country"], p["ovr"], r["acquired_price"], p["value"]])
    return buf.getvalue()


def export_fl26_guide(guild_id: int) -> str:
    """
    Generate a comprehensive FL26 setup guide.
    FL26 uses PES 2021's database — teams are created in Edit Mode
    and player assignments are done manually or via ejogc PES Editor.

    This generates a guide the admin can follow step by step.
    """
    import csv as _csv
    import io

    # Get all managers with squads
    with db.cursor() as c:
        user_rows = c.execute(
            "SELECT DISTINCT user_id FROM squads WHERE guild_id=? ORDER BY user_id",
            (guild_id,),
        ).fetchall()

    buf = io.StringIO()
    w = _csv.writer(buf)

    # Header
    w.writerow(["=== FOOTBALL LIFE 26 SETUP GUIDE ==="])
    w.writerow(["Generated by Football Auction Bot"])
    w.writerow([])
    w.writerow(["STEP 1: Create Custom Teams"])
    w.writerow(["In FL26: Edit Mode > Data Management > Create New Team"])
    w.writerow(["Use the custom team slots (there are 3 available)"])
    w.writerow(["Set each team name, kit colors, stadium, etc."])
    w.writerow([])
    w.writerow(["Team Slot", "Discord User ID", "Team Name", "Formation"])

    managers_data = []
    for i, ur in enumerate(user_rows):
        uid = ur["user_id"]
        team_name = get_team_name(guild_id, uid) or f"Team {uid}"
        formation_name = get_formation(guild_id, uid)
        squad = get_squad(guild_id, uid)
        managers_data.append((uid, team_name, formation_name, squad))
        # FL26 has limited custom team slots (3)
        slot = i + 1
        w.writerow([f"Slot {slot}", uid, team_name, formation_name])

    w.writerow([])
    w.writerow(["STEP 2: Assign Players to Teams"])
    w.writerow(["In FL26: Edit Mode > Transfers > move players to your custom teams"])
    w.writerow(["OR use ejogc PES Editor > Player Assignments > CSV import"])
    w.writerow([])
    w.writerow(["PES_ID", "Player Name", "Position", "OVR", "From_Club",
                "Assign_To_Team", "Team_Slot", "Team_Name"])

    for slot_idx, (uid, team_name, formation_name, squad) in enumerate(managers_data):
        slot = slot_idx + 1
        for p in squad:
            pes_id = p.get("pes_id", "")
            w.writerow([
                pes_id, p["name"], p["position"], p["ovr"],
                p.get("club", ""), "Custom", f"Slot {slot}", team_name
            ])

    w.writerow([])
    w.writerow(["STEP 3: Set Formations"])
    w.writerow(["In FL26: Select each custom team > Tactics > set formation"])
    w.writerow([])
    w.writerow(["Team_Slot", "Team_Name", "Formation"])

    for slot_idx, (uid, team_name, formation_name, squad) in enumerate(managers_data):
        slot = slot_idx + 1
        w.writerow([f"Slot {slot}", team_name, formation_name])

    w.writerow([])
    w.writerow(["STEP 4: Set Starting Lineups"])
    w.writerow(["Use the formation slot assignments below"])
    w.writerow([])

    for slot_idx, (uid, team_name, formation_name, squad) in enumerate(managers_data):
        slot = slot_idx + 1
        lineup, fmt = get_lineup(guild_id, uid)
        w.writerow([f"--- Team Slot {slot}: {team_name} ({fmt}) ---"])
        w.writerow(["Slot", "Position", "PES_ID", "Player_Name", "OVR"])
        for slot_info, player in lineup:
            if player:
                w.writerow([
                    slot_info["index"], slot_info["pos"],
                    player.get("pes_id", ""), player["name"], player["ovr"]
                ])
        w.writerow([])

    w.writerow(["=== END OF GUIDE ==="])
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────
#  PLAYER MATCH STATS
# ──────────────────────────────────────────────────────────────────────────
def get_player_stats(guild_id: int, player_key: str, season_id: int = None) -> dict:
    """Get match stats for a player (optionally filtered to a season)."""
    with db.cursor() as c:
        if season_id is not None:
            row = c.execute(
                "SELECT * FROM player_match_stats "
                "WHERE guild_id=? AND player_key=? AND season_id=?",
                (guild_id, player_key, season_id),
            ).fetchone()
        else:
            row = c.execute(
                "SELECT * FROM player_match_stats "
                "WHERE guild_id=? AND player_key=? "
                "ORDER BY season_id DESC LIMIT 1",
                (guild_id, player_key),
            ).fetchone()
    if row:
        return dict(row)
    return {
        "matches": 0, "goals": 0, "assists": 0, "tackles": 0,
        "saves": 0, "motm": 0, "yellow_cards": 0, "red_cards": 0,
    }


def add_player_stats(guild_id: int, player_key: str, goals=0, assists=0,
                     tackles=0, saves=0, motm=0, yellow=0, red=0,
                     season_id: int = None):
    """Add match stats to a player for a specific season."""
    with db.cursor() as c:
        c.execute(
            "INSERT INTO player_match_stats (guild_id, season_id, player_key, "
            "matches, goals, assists, tackles, saves, motm, yellow_cards, red_cards) "
            "VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(guild_id, season_id, player_key) DO UPDATE SET "
            "matches=matches+1, goals=goals+?, assists=assists+?, "
            "tackles=tackles+?, saves=saves+?, motm=motm+?, "
            "yellow_cards=yellow_cards+?, red_cards=red_cards+?",
            (guild_id, season_id, player_key,
             goals, assists, tackles, saves, motm, yellow, red,
             goals, assists, tackles, saves, motm, yellow, red),
        )


def get_squad_match_stats(guild_id: int, user_id: int, season_id: int = None) -> dict:
    """Aggregate match stats for an entire squad (optionally per season)."""
    squad = get_squad(guild_id, user_id)
    if not squad:
        return {"matches": 0, "goals": 0, "assists": 0, "tackles": 0,
                "saves": 0, "motm": 0, "yellow_cards": 0, "red_cards": 0}
    agg = {"matches": 0, "goals": 0, "assists": 0, "tackles": 0,
           "saves": 0, "motm": 0, "yellow_cards": 0, "red_cards": 0}
    for p in squad:
        stats = get_player_stats(guild_id, p["key"])
        for k in agg:
            agg[k] += stats.get(k, 0)
    return agg


def reset_all_stats(guild_id: int, season_id: int = None):
    """Clear player match stats (for a new season, or all if no season_id)."""
    with db.cursor() as c:
        if season_id is not None:
            c.execute(
                "DELETE FROM player_match_stats WHERE guild_id=? AND season_id=?",
                (guild_id, season_id),
            )
        else:
            c.execute("DELETE FROM player_match_stats WHERE guild_id=?", (guild_id,))


def get_top_scorers(guild_id: int, limit: int = 10, season_id: int = None) -> list[dict]:
    """Top scorers for the league (filtered to a season if given)."""
    with db.cursor() as c:
        if season_id is not None:
            rows = c.execute(
                "SELECT s.player_key, s.goals, s.assists, s.motm, s.matches "
                "FROM player_match_stats s "
                "WHERE s.guild_id=? AND s.season_id=? AND s.goals > 0 "
                "ORDER BY s.goals DESC, s.assists DESC LIMIT ?",
                (guild_id, season_id, limit),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT s.player_key, s.goals, s.assists, s.motm, s.matches "
                "FROM player_match_stats s "
                "WHERE s.guild_id=? AND s.goals > 0 "
                "ORDER BY s.goals DESC, s.assists DESC LIMIT ?",
                (guild_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────
#  QUEUE SHUFFLE
# ──────────────────────────────────────────────────────────────────────────
def queue_shuffle(guild_id: int):
    """Randomize the order of the draft queue."""
    import random
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key FROM draft_queue WHERE guild_id=? ORDER BY position",
            (guild_id,),
        ).fetchall()
        keys = [r["player_key"] for r in rows]
        if len(keys) < 2:
            return 0
        random.shuffle(keys)
        c.execute("DELETE FROM draft_queue WHERE guild_id=?", (guild_id,))
        for i, key in enumerate(keys):
            c.execute(
                "INSERT INTO draft_queue (guild_id, position, player_key) VALUES (?, ?, ?)",
                (guild_id, i, key),
            )
        return len(keys)



# ──────────────────────────────────────────────────────────────────────────
#  WATCHLIST
# ──────────────────────────────────────────────────────────────────────────
def watch_add(guild_id, user_id, player_key):
    with db.cursor() as c:
        c.execute(
            "INSERT OR IGNORE INTO watchlist (guild_id, user_id, player_key) VALUES (?, ?, ?)",
            (guild_id, user_id, player_key),
        )


def watch_remove(guild_id, user_id, player_key):
    with db.cursor() as c:
        c.execute(
            "DELETE FROM watchlist WHERE guild_id=? AND user_id=? AND player_key=?",
            (guild_id, user_id, player_key),
        )


def watch_list(guild_id, user_id):
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key FROM watchlist WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchall()
    return [r["player_key"] for r in rows]


def watch_watchers(guild_id, player_key):
    with db.cursor() as c:
        rows = c.execute(
            "SELECT user_id FROM watchlist WHERE guild_id=? AND player_key=?",
            (guild_id, player_key),
        ).fetchall()
    return [r["user_id"] for r in rows]


# ──────────────────────────────────────────────────────────────────────────
#  AUCTION HISTORY SEARCH + DRAFT RECAP
# ──────────────────────────────────────────────────────────────────────────
def search_sales(guild_id, player_key=None, user_id=None, limit=20):
    q = "SELECT * FROM auction_history WHERE guild_id=? AND status='sold'"
    params = [guild_id]
    if player_key:
        q += " AND player_key=?"
        params.append(player_key)
    if user_id:
        q += " AND winner_id=?"
        params.append(user_id)
    q += " ORDER BY finished_at DESC LIMIT ?"
    params.append(limit)
    with db.cursor() as c:
        rows = c.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def draft_recap(guild_id):
    with db.cursor() as c:
        rows = c.execute(
            "SELECT * FROM auction_history WHERE guild_id=? AND status='sold' ORDER BY final_price DESC",
            (guild_id,),
        ).fetchall()
    sales = [dict(r) for r in rows]
    if not sales:
        return None
    top_buys = sales[:10]
    steals = []
    overpays = []
    for s in sales:
        p = P.get(s["player_key"])
        if not p:
            continue
        if p["value"] > 0:
            ratio = s["final_price"] / p["value"]
            if ratio < 0.5 and p["ovr"] >= 80:
                steals.append((s, p, ratio))
            if ratio > 2.0:
                overpays.append((s, p, ratio))
    steals.sort(key=lambda x: x[2])
    overpays.sort(key=lambda x: -x[2])
    spending = {}
    for s in sales:
        uid = s["winner_id"]
        spending[uid] = spending.get(uid, 0) + s["final_price"]
    return {
        "total_sales": len(sales),
        "total_spent": sum(s["final_price"] for s in sales),
        "top_buys": top_buys, "steals": steals[:5], "overpays": overpays[:5],
        "spending": spending,
    }


# ──────────────────────────────────────────────────────────────────────────
#  POWER RATING + H2H
# ──────────────────────────────────────────────────────────────────────────
def power_rating(guild_id, user_id):
    squad = get_squad(guild_id, user_id)
    if not squad:
        return 0
    sorted_squad = sorted(squad, key=lambda p: p["ovr"], reverse=True)
    best_xi = sorted_squad[:11]
    xi_avg = sum(p["ovr"] for p in best_xi) / len(best_xi) if best_xi else 0
    depth = sum(1 for p in squad if p["ovr"] >= 80)
    sv = squad_value(squad)
    value_score = min(sv / 1_000_000_000 * 20, 20)
    xi_score = max(0, min(60, (xi_avg - 60) * 60 / 40))
    depth_score = min(depth * 2, 20)
    return round(xi_score + depth_score + value_score)


def head_to_head(guild_id, user_a, user_b, season_id=None):
    q = ("SELECT f.* FROM fixtures f "
         "JOIN seasons s ON f.season_id=s.id "
         "WHERE s.guild_id=? AND f.status='played' "
         "AND ((f.home_user=? AND f.away_user=?) OR (f.home_user=? AND f.away_user=?))")
    params = [guild_id, user_a, user_b, user_b, user_a]
    if season_id:
        q += " AND season_id=?"
        params.append(season_id)
    q += " ORDER BY played_at DESC"
    with db.cursor() as c:
        rows = c.execute(q, params).fetchall()
    fixtures = [dict(r) for r in rows]
    a_wins = b_wins = draws = 0
    for f in fixtures:
        hs, as_ = f["home_score"], f["away_score"]
        h_is_a = f["home_user"] == user_a
        a_score = hs if h_is_a else as_
        b_score = as_ if h_is_a else hs
        if a_score > b_score: a_wins += 1
        elif b_score > a_score: b_wins += 1
        else: draws += 1
    return {"fixtures": fixtures, "a_wins": a_wins, "b_wins": b_wins, "draws": draws}
