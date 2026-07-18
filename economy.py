"""
Economy & squad management for the auction bot.

Wallets, squads, sold-player tracking, pool filtering by phase,
and leaderboards.

Queue helpers are Turso-safe: multi-row inserts + few SQL calls so
bulk / shuffle / consume don't freeze Discord's event loop.
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


def squads_overview(guild_id: int) -> list:
    """Batch fetch ALL managers' squad data in ONE joined query (not N x 5).

    Source of truth: the `squads` table (managers who actually OWN players),
    exactly like the original /squads route. NOT the `users` table — managers
    can have squad players without a users row (draw/bot paths), and sourcing
    from users drops them. We LEFT JOIN users for balance/team identity.

    Returns [{user_id, team_name, team_logo, balance, squad, squad_value,
    power_rating}, ...].
    """
    # ONE joined call: squad memberships + user identity.
    # squad-driven: every manager who owns at least one player is included.
    with db.cursor() as c:
        rows = c.execute(
            "SELECT s.user_id AS uid, s.player_key AS pk, "
            "u.balance AS bal, u.team_name AS tn, u.team_logo AS tl "
            "FROM squads s "
            "LEFT JOIN users u "
            "ON s.guild_id = u.guild_id AND s.user_id = u.user_id "
            "WHERE s.guild_id=?",
            (guild_id,),
        ).fetchall()

    # Group squad players + identity by user (first non-null value wins)
    by_user = {}
    for r in rows:
        uid = r["uid"]
        entry = by_user.setdefault(uid, {
            "user_id": uid,
            "team_name": None,
            "team_logo": None,
            "balance": None,
            "keys": [],
        })
        entry["keys"].append(r["pk"])
        # fill identity from the join (same for all the user's rows)
        if entry["team_name"] is None and r["tn"]:
            entry["team_name"] = r["tn"]
        if entry["team_logo"] is None and r["tl"]:
            entry["team_logo"] = r["tl"]
        if entry["balance"] is None and r["bal"] is not None:
            entry["balance"] = r["bal"]

    out = []
    for uid, entry in by_user.items():
        squad = []
        for k in entry["keys"]:
            pdata = P.get(k)
            if pdata:
                squad.append(pdata)
        sv = squad_value(squad)
        out.append({
            "user_id": uid,
            "team_name": entry["team_name"] or f"Manager {uid}",
            "team_logo": entry["team_logo"],
            "balance": entry["balance"] if entry["balance"] is not None else Config.STARTING_BALANCE,
            "squad": squad,
            "squad_value": sv,
            "power_rating": _power_rating_from_squad(squad),
        })
    return out


def _power_rating_from_squad(squad: list) -> int:
    """Compute power rating from an already-fetched squad list (no DB calls)."""
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


def get_free_lineup(guild_id: int, user_id: int) -> dict:
    """Get custom free-edit positions: {player_key: {x: 0.5, y: 0.3}}"""
    with db.cursor() as c:
        row = c.execute(
            "SELECT free_lineup FROM formations WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchone()
    if row and row["free_lineup"]:
        try:
            import json as _json
            return _json.loads(row["free_lineup"])
        except (ValueError, TypeError):
            pass
    return {}


def set_free_lineup(guild_id: int, user_id: int, positions: dict):
    """Save custom free-edit positions."""
    import json as _json
    ensure_user(guild_id, user_id)
    with db.cursor() as c:
        c.execute(
            "INSERT INTO formations (guild_id, user_id, formation, free_lineup) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET free_lineup=excluded.free_lineup",
            (guild_id, user_id, get_formation(guild_id, user_id),
             _json.dumps(positions)),
        )


def clear_free_lineup(guild_id: int, user_id: int):
    """Clear free-edit positions (revert to formation slots)."""
    with db.cursor() as c:
        c.execute(
            "UPDATE formations SET free_lineup=NULL WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )


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


# --------------------------------------------------------------------------
# Forced substitutes (bench) — never auto-picked into Starting XI
# --------------------------------------------------------------------------

def _ensure_bench_table():
    with db.cursor() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS bench (
                guild_id   INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                player_key TEXT    NOT NULL,
                PRIMARY KEY (guild_id, user_id, player_key)
            )
            """
        )


def get_bench_keys(guild_id: int, user_id: int) -> set:
    """Player keys forced onto the substitutes (excluded from auto XI)."""
    _ensure_bench_table()
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key FROM bench WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        ).fetchall()
    return {r["player_key"] for r in rows}


def is_benched(guild_id: int, user_id: int, player_key: str) -> bool:
    return player_key in get_bench_keys(guild_id, user_id)


def set_bench(guild_id: int, user_id: int, player_key: str) -> dict:
    """
    Force a player onto substitutes: they will not be auto-picked into the XI.
    Also clears any lineup slot override that currently holds them.
    """
    _ensure_bench_table()
    p = P.get(player_key)
    if not p:
        results = P.search(str(player_key), limit=1)
        p = results[0] if results else None
    if not p:
        raise RuntimeError("Player not found.")
    key = p["key"]
    if not owns(guild_id, user_id, key):
        raise RuntimeError("You don't own that player.")

    with db.cursor() as c:
        c.execute(
            "INSERT OR IGNORE INTO bench (guild_id, user_id, player_key) VALUES (?, ?, ?)",
            (guild_id, user_id, key),
        )
        # Kick them out of any starting slot override
        c.execute(
            "DELETE FROM lineup_overrides "
            "WHERE guild_id=? AND user_id=? AND player_key=?",
            (guild_id, user_id, key),
        )
    return {"player": p, "benched": True}


def clear_bench(guild_id: int, user_id: int, player_key: str) -> dict:
    """Allow a player back into auto Starting XI selection."""
    _ensure_bench_table()
    p = P.get(player_key)
    if not p:
        results = P.search(str(player_key), limit=1)
        p = results[0] if results else None
    if not p:
        raise RuntimeError("Player not found.")
    key = p["key"]
    with db.cursor() as c:
        c.execute(
            "DELETE FROM bench WHERE guild_id=? AND user_id=? AND player_key=?",
            (guild_id, user_id, key),
        )
    return {"player": p, "benched": False}


def clear_all_bench(guild_id: int, user_id: int):
    _ensure_bench_table()
    with db.cursor() as c:
        c.execute(
            "DELETE FROM bench WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )


def get_lineup(guild_id: int, user_id: int):
    """
    Get the full lineup: formation + assigned players per slot.
    Apply manual overrides FIRST, then auto-fill remaining slots.
    Players on the forced bench list are never auto-picked into the XI.
    """
    formation_name = get_formation(guild_id, user_id)
    formation = FM.get_formation(formation_name)
    squad = get_squad(guild_id, user_id)
    overrides = get_lineup_overrides(guild_id, user_id)
    benched = get_bench_keys(guild_id, user_id)
    slots = FM.all_slots(formation)
    result = [None] * len(slots)
    used_keys = set()

    # Forced bench never starts — treat as already "used" for auto-fill
    used_keys |= benched

    # PASS 1: Apply manual overrides first (they take priority)
    # If someone was benched, their slot override was cleared in set_bench.
    for slot in slots:
        idx = slot["index"]
        if idx in overrides:
            override_key = overrides[idx]
            if override_key in benched:
                result[idx] = (slot, None)
                continue
            override_player = next((p for p in squad if p["key"] == override_key), None)
            if override_player and override_key not in used_keys:
                result[idx] = (slot, override_player)
                used_keys.add(override_key)
            else:
                result[idx] = (slot, None)

    # PASS 2: Auto-assign remaining slots (skip benched)
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

        for p in pool:
            if p["position"] == preferred:
                assigned = p
                break
        if not assigned:
            for p in pool:
                if p["position"] in alts and p["position"] != preferred:
                    assigned = p
                    break
        if not assigned:
            slot_side = slot["side"]
            for p in pool:
                if FM.position_side(p["position"]) == slot_side:
                    assigned = p
                    break
        if not assigned and pool:
            assigned = pool[0]

        if assigned:
            used_keys.add(assigned["key"])
            result[idx] = (slot, assigned)
        else:
            result[idx] = (slot, None)

    return result, formation_name


# --------------------------------------------------------------------------
# Scripted draft queue  (Turso-safe / batched)
# --------------------------------------------------------------------------

# How many rows per multi-value INSERT (keeps SQL size reasonable)
_QUEUE_INSERT_CHUNK = 80


def _queue_insert_rows(c, guild_id: int, ordered_keys: list):
    """
    Insert (guild_id, position, player_key) for ordered_keys.
    position is 1-based in order of the list.
    Uses multi-row INSERT — ~1 HTTP call per 80 players on Turso.
    """
    if not ordered_keys:
        return
    for start in range(0, len(ordered_keys), _QUEUE_INSERT_CHUNK):
        chunk = ordered_keys[start:start + _QUEUE_INSERT_CHUNK]
        placeholders = ",".join(["(?,?,?)"] * len(chunk))
        params = []
        for i, key in enumerate(chunk):
            params.extend([guild_id, start + i + 1, key])
        c.execute(
            f"INSERT INTO draft_queue (guild_id, position, player_key) "
            f"VALUES {placeholders}",
            tuple(params),
        )


def queue_list(guild_id: int):
    """Return the ordered list of queued player keys for a guild."""
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key FROM draft_queue WHERE guild_id=? ORDER BY position",
            (guild_id,),
        ).fetchall()
    return [r["player_key"] for r in rows]


def queued_pool(guild_id: int):
    """Return the list of queued players (full dicts) not yet sold."""
    sold = sold_player_keys(guild_id)
    keys = queue_list(guild_id)
    players = []
    for k in keys:
        if k in sold:
            continue
        p = P.get(k)
        if p:
            players.append(p)
    return players


def has_queue(guild_id: int) -> bool:
    """True if this guild has any players in the queue."""
    with db.cursor() as c:
        row = c.execute(
            "SELECT 1 FROM draft_queue WHERE guild_id=? LIMIT 1",
            (guild_id,),
        ).fetchone()
    return row is not None


def queue_add(guild_id: int, player_key: str) -> int:
    """Append a player to the end of the queue. Returns the new position (1-based)."""
    with db.cursor() as c:
        row = c.execute(
            "SELECT MAX(position) AS m FROM draft_queue WHERE guild_id=?",
            (guild_id,),
        ).fetchone()
        pos = (row["m"] or 0) + 1
        c.execute(
            "INSERT INTO draft_queue (guild_id, position, player_key) VALUES (?, ?, ?)",
            (guild_id, pos, player_key),
        )
    return pos


def queue_add_many(guild_id: int, player_keys: list) -> int:
    """
    Append many player keys. Returns count added (skips already-queued).
    ONE select + few multi-row inserts — NOT N separate queue_add calls.
    """
    if not player_keys:
        return 0

    with db.cursor() as c:
        rows = c.execute(
            "SELECT position, player_key FROM draft_queue WHERE guild_id=? ORDER BY position",
            (guild_id,),
        ).fetchall()
        existing = {r["player_key"] for r in rows}
        next_pos = (rows[-1]["position"] if rows else 0) + 1

        to_add = []
        for key in player_keys:
            if key in existing:
                continue
            to_add.append(key)
            existing.add(key)

        if not to_add:
            return 0

        for start in range(0, len(to_add), _QUEUE_INSERT_CHUNK):
            chunk = to_add[start:start + _QUEUE_INSERT_CHUNK]
            placeholders = ",".join(["(?,?,?)"] * len(chunk))
            params = []
            for i, key in enumerate(chunk):
                params.extend([guild_id, next_pos + start + i, key])
            c.execute(
                f"INSERT INTO draft_queue (guild_id, position, player_key) "
                f"VALUES {placeholders}",
                tuple(params),
            )
        return len(to_add)


def queue_clear(guild_id: int):
    with db.cursor() as c:
        c.execute("DELETE FROM draft_queue WHERE guild_id=?", (guild_id,))


def queue_next(guild_id: int):
    """Return (player_key, remaining_count) of the front of the queue, or (None, 0)."""
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key FROM draft_queue WHERE guild_id=? ORDER BY position",
            (guild_id,),
        ).fetchall()
    if not rows:
        return None, 0
    return rows[0]["player_key"], len(rows)


def queue_consume(guild_id: int, player_key: str):
    """
    Remove ALL occurrences of a player from the queue, then re-number.
    Uses a few SQL statements + multi-row insert — NOT N single inserts.
    """
    with db.cursor() as c:
        c.execute(
            "DELETE FROM draft_queue WHERE guild_id=? AND player_key=?",
            (guild_id, player_key),
        )
        remaining = c.execute(
            "SELECT player_key FROM draft_queue WHERE guild_id=? ORDER BY position",
            (guild_id,),
        ).fetchall()
        keys = [r["player_key"] for r in remaining]
        c.execute("DELETE FROM draft_queue WHERE guild_id=?", (guild_id,))
        _queue_insert_rows(c, guild_id, keys)


def queue_remove_many(guild_id: int, player_keys: list):
    """Remove multiple players from the queue at once, then renumber."""
    if not player_keys:
        return 0

    remove_set = set(player_keys)
    with db.cursor() as c:
        remaining_rows = c.execute(
            "SELECT player_key FROM draft_queue WHERE guild_id=? ORDER BY position",
            (guild_id,),
        ).fetchall()
        before = len(remaining_rows)
        keys = [r["player_key"] for r in remaining_rows if r["player_key"] not in remove_set]
        removed = before - len(keys)

        if removed == 0:
            return 0

        c.execute("DELETE FROM draft_queue WHERE guild_id=?", (guild_id,))
        _queue_insert_rows(c, guild_id, keys)
        return removed


def queue_shuffle(guild_id: int):
    """
    Randomize the order of the draft queue.
    1 SELECT + 1 DELETE + few multi-row INSERTs. Not N HTTP inserts.
    """
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
        _queue_insert_rows(c, guild_id, keys)
        return len(keys)


# --------------------------------------------------------------------------
# Player faces (SoFIFA URLs)
# --------------------------------------------------------------------------

_FACE_URL_MAP = None
_FACE_URL_CACHE = {}   # in-process cache to avoid a DB round-trip per face image


def _load_face_map():
    """Load pre-built face URL mapping (83% coverage from SoFiFA CSV)."""
    global _FACE_URL_MAP
    _FACE_URL_MAP = {}
    try:
        import os
        import json as _json
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
    then falls back to the pre-built face_urls.json mapping.

    Caches per key after first lookup so the /players grid (30+ face images)
    does not make 30 separate DB round-trips on Turso.
    """
    global _FACE_URL_MAP
    cache = _FACE_URL_CACHE
    if player_key in cache:
        return cache[player_key]
    with db.cursor() as c:
        row = c.execute(
            "SELECT face_url FROM player_faces WHERE player_key=?", (player_key,)
        ).fetchone()
    if row and row["face_url"]:
        cache[player_key] = row["face_url"]
        return row["face_url"]
    if _FACE_URL_MAP is None:
        _load_face_map()
    val = _FACE_URL_MAP.get(player_key)
    cache[player_key] = val
    return val


def set_face_url(player_key: str, url: str):
    with db.cursor() as c:
        c.execute(
            "INSERT INTO player_faces (player_key, face_url) VALUES (?, ?) "
            "ON CONFLICT(player_key) DO UPDATE SET face_url=excluded.face_url",
            (player_key, url),
        )
    _FACE_URL_CACHE[player_key] = url


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
            (name[:50], guild_id, user_id),
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


def owners_map(guild_id: int, keys: "set | list | None" = None) -> dict:
    """Batch owner lookup. Returns {player_key: (user_id, team_name, team_logo)}.

    ONE database round-trip instead of N x 5 calls to get_player_owner().
    This is the critical optimization for the /players, /compare, /watchlist
    pages on Turso, where every query is an HTTP request and the old per-player
    loop made a sold-player page take 1-2 minutes.
    """
    with db.cursor() as c:
        if keys:
            # limit to the requested set (keeps the result small)
            params = [guild_id] + list(keys)
            placeholders = ",".join("?" * len(keys))
            rows = c.execute(
                "SELECT s.player_key AS pk, s.user_id AS uid, "
                "u.team_name AS tn, u.team_logo AS tl "
                "FROM squads s LEFT JOIN users u "
                "ON s.guild_id = u.guild_id AND s.user_id = u.user_id "
                f"WHERE s.guild_id=? AND s.player_key IN ({placeholders})",
                tuple(params),
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT s.player_key AS pk, s.user_id AS uid, "
                "u.team_name AS tn, u.team_logo AS tl "
                "FROM squads s LEFT JOIN users u "
                "ON s.guild_id = u.guild_id AND s.user_id = u.user_id "
                "WHERE s.guild_id=?",
                (guild_id,),
            ).fetchall()
    return {r["pk"]: (r["uid"], r["tn"], r["tl"]) for r in rows}


# --------------------------------------------------------------------------
# Budget tracking / needs analysis
# --------------------------------------------------------------------------

# Full squad (ideal): 2 GK, 5 DEF, 5 MID, 3 FWD = 15
REQUIREMENTS = {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
MIN_SQUAD_SIZE = sum(REQUIREMENTS.values())  # 15

# Minimum viable squad (yellow zone): 2 GK, 4 DEF, 4 MID, 3 FWD = 13
# Once a manager hits these minimums, they can bid freely (no slot reservation)
MIN_VIABLE = {"GK": 1, "DEF": 4, "MID": 4, "FWD": 3}

# Matches OVR < 75 floor in players.base_price
CHEAPEST_PLAYER_VALUE = 15_000_000  # £15M


def get_needs(guild_id: int, user_id: int):
    """
    Analyze what a manager still needs.
    Returns dict with counts, needed, budget, min_cost, max_bid, complete, squad_size.

    Uses a two-tier system:
      - Yellow zone: manager hasn't hit MIN_VIABLE yet (2 GK, 4 DEF, 4 MID, 3 FWD)
        -> reserve budget for cheapest fills so they can complete a viable squad
      - Free zone: manager HAS hit MIN_VIABLE (13+ players with minimums met)
        -> max_bid = full remaining budget, bid freely
    """
    squad = get_squad(guild_id, user_id)
    budget = get_balance(guild_id, user_id)
    counts = {"GK": 0, "DEF": 0, "MID": 0, "FWD": 0}
    for p in squad:
        counts[p["group"]] += 1

    # Full requirements (for display)
    needed = {}
    total_needed = 0
    for g, req in REQUIREMENTS.items():
        remaining = max(0, req - counts[g])
        needed[g] = remaining
        total_needed += remaining

    # Minimum viable check: have they hit the yellow-zone floor?
    min_viable_met = all(counts[g] >= MIN_VIABLE[g] for g in MIN_VIABLE)

    if min_viable_met:
        # Free zone - they can bid their full remaining budget
        slots_needed = 0
        for g, req in MIN_VIABLE.items():
            slots_needed += max(0, req - counts[g])
        min_cost = slots_needed * CHEAPEST_PLAYER_VALUE
        max_bid = budget  # full budget, no reservation
    else:
        # Yellow zone - reserve for minimum viable slots only (not full 15)
        slots_needed = 0
        for g, req in MIN_VIABLE.items():
            slots_needed += max(0, req - counts[g])
        min_cost = slots_needed * CHEAPEST_PLAYER_VALUE
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
        "min_viable_met": min_viable_met,
    }


# Soft buffer on top of /needs max_bid during live auctions
AUCTION_MAX_BID_BUFFER = 10_000_000  # +£10M
# Extra penalty when bidding on a position you already have enough of
NON_ESSENTIAL_PENALTY = 20_000_000  # -£20M from cap when buying unneeded positions


def auction_max_bid(guild_id: int, user_id: int, player_group: str = None) -> dict:
    """
    Position-aware bid cap for live auctions.

    Two cases:
      1. Bidding for a NEEDED position (below MIN_VIABLE for that group):
         - Light restriction: reserve for OTHER missing slots, not this one
         - cap = (budget - other_slots_cost) + £10M buffer
      2. Bidding for a position already at/above minimum (or no group specified):
         - Heavy restriction: reserve for ALL missing slots
         - cap = (budget - all_slots_cost) - £20M penalty + £10M buffer

    Still subject to can_afford (never above balance).
    """
    needs = get_needs(guild_id, user_id)
    counts = needs["counts"]
    budget = needs["budget"]

    # Calculate missing slots per group
    missing = {}
    total_missing = 0
    for g, req in MIN_VIABLE.items():
        missing[g] = max(0, req - counts[g])
        total_missing += missing[g]

    if player_group and player_group in MIN_VIABLE:
        is_needed = missing[player_group] > 0
        if is_needed:
            # Bidding for a needed position - only reserve OTHER slots
            other_slots = total_missing - 1  # minus the one they're bidding on
            other_cost = other_slots * CHEAPEST_PLAYER_VALUE
            floor = budget - other_cost
            cap = floor + AUCTION_MAX_BID_BUFFER
            return {
                "floor": floor,
                "cap": cap,
                "buffer": AUCTION_MAX_BID_BUFFER,
                "budget": budget,
                "min_cost": other_cost,
                "total_needed": total_missing,
                "complete": total_missing == 0,
                "position_needed": True,
            }
        else:
            # Bidding for unneeded position - reserve ALL + penalty
            all_cost = total_missing * CHEAPEST_PLAYER_VALUE
            floor = budget - all_cost - NON_ESSENTIAL_PENALTY
            cap = floor + AUCTION_MAX_BID_BUFFER
            return {
                "floor": floor,
                "cap": cap,
                "buffer": AUCTION_MAX_BID_BUFFER,
                "budget": budget,
                "min_cost": all_cost,
                "total_needed": total_missing,
                "complete": total_missing == 0,
                "position_needed": False,
            }

    # Default (no group specified) - standard reservation
    floor = int(needs["max_bid"])
    cap = floor + AUCTION_MAX_BID_BUFFER
    return {
        "floor": floor,
        "cap": cap,
        "buffer": AUCTION_MAX_BID_BUFFER,
        "budget": budget,
        "min_cost": needs["min_cost"],
        "total_needed": total_missing,
        "complete": total_missing == 0,
    }


# --------------------------------------------------------------------------
# Trade system
# --------------------------------------------------------------------------

def create_trade(guild_id: int, from_user: int, to_user: int,
                 offering_keys: list, requesting_keys: list, cash: int = 0) -> int:
    """Create a trade offer. Returns trade ID.

    cash = amount the TO user pays to FROM user (for player-for-money trades).
    0 = player-for-player or free gift.
    """
    with db.cursor() as c:
        c.execute(
            "INSERT INTO trades (guild_id, from_user, to_user, offering, requesting, cash, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending', datetime('now'))",
            (guild_id, from_user, to_user,
             ",".join(offering_keys), ",".join(requesting_keys), cash),
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
    """Execute a trade: swap players + handle cash transfer.

    cash column = amount TO user pays to FROM user.
    """
    trade = get_trade(guild_id, trade_id)
    if not trade or trade["status"] != "pending":
        return False
    from_user = trade["from_user"]
    to_user = trade["to_user"]
    offering = [k for k in trade["offering"].split(",") if k]
    requesting = [k for k in trade["requesting"].split(",") if k]
    cash = int(trade.get("cash") or 0)

    # Check cash affordability (TO user pays FROM user)
    if cash > 0:
        if not can_afford(guild_id, to_user, cash):
            return False

    with db.cursor() as c:
        # Move offered players from -> to
        for key in offering:
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
        # Move requested players to -> from
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
        # Cash transfer: TO pays FROM
        if cash > 0:
            adjust_balance(guild_id, to_user, -cash)
            adjust_balance(guild_id, from_user, cash)
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
        w.writerow([r["user_id"], p["name"], p["position"], p["group"], p.get("club", ""),
                    p["country"], p["ovr"], r["acquired_price"], p["value"]])
    return buf.getvalue()


def export_fl26_guide(guild_id: int) -> str:
    """Generate a comprehensive FL26 setup guide."""
    import csv as _csv
    import io
    with db.cursor() as c:
        user_rows = c.execute(
            "SELECT DISTINCT user_id FROM squads WHERE guild_id=? ORDER BY user_id",
            (guild_id,),
        ).fetchall()
    buf = io.StringIO()
    w = _csv.writer(buf)
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


# --------------------------------------------------------------------------
# PLAYER MATCH STATS
# --------------------------------------------------------------------------

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
        stats = get_player_stats(guild_id, p["key"], season_id=season_id)
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


def get_top_scorers(guild_id: int, limit: int = 10, season_id: int = None) -> list:
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


# --------------------------------------------------------------------------
# WATCHLIST
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# AUCTION HISTORY SEARCH + DRAFT RECAP
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# POWER RATING + H2H
# --------------------------------------------------------------------------

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
        if a_score > b_score:
            a_wins += 1
        elif b_score > a_score:
            b_wins += 1
        else:
            draws += 1
    return {"fixtures": fixtures, "a_wins": a_wins, "b_wins": b_wins, "draws": draws}


# --------------------------------------------------------------------------
# Manager replace (same team, new Discord user)
# --------------------------------------------------------------------------

def replace_manager(guild_id: int, old_user_id: int, new_user_id: int) -> dict:
    """
    Transfer everything from old_user_id → new_user_id in this guild.

    Same team name, logo, balance, squad, formation, lineup, tactics,
    watchlist, card assignment, season slot, fixtures, trades, auction history.

    IMPORTANT: Does NOT UPDATE the users primary key in-place (breaks on Turso).
    Instead: copy users row → move child tables → delete old users row →
    force-write team_name/logo onto the new user.
    """
    old_user_id = int(old_user_id)
    new_user_id = int(new_user_id)
    if old_user_id == new_user_id:
        raise RuntimeError("Old and new user are the same person.")

    if squad_count(guild_id, new_user_id) > 0:
        raise RuntimeError(
            "New user already has a squad in this server. "
            "Run `/reset @new` first, or pick someone with no team."
        )

    try:
        import league as L
        s = L.active_season(guild_id)
        if s:
            tms = L.teams(s["id"])
            if any(int(t["user_id"]) == new_user_id for t in tms):
                raise RuntimeError(
                    "New user is already registered in the active season."
                )
    except RuntimeError:
        raise
    except Exception:
        s = None
        L = None

    with db.cursor() as c:
        old_row = c.execute(
            "SELECT * FROM users WHERE guild_id=? AND user_id=?",
            (guild_id, old_user_id),
        ).fetchone()

    # Also try season team name if users.team_name missing
    season_team_name = None
    try:
        import league as L2
        s2 = L2.active_season(guild_id)
        if s2:
            for t in L2.teams(s2["id"]):
                if int(t["user_id"]) == old_user_id and t.get("team_name"):
                    season_team_name = t["team_name"]
                    break
    except Exception:
        pass

    if old_row is None and squad_count(guild_id, old_user_id) == 0 and not season_team_name:
        raise RuntimeError("Old user has no account/squad/season seat in this server.")

    # Snapshot old profile
    if old_row is not None:
        try:
            old = dict(old_row)
        except Exception:
            old = {k: old_row[k] for k in old_row.keys()}
        bal = int(old.get("balance") or Config.STARTING_BALANCE)
        team_name = old.get("team_name") or season_team_name
        team_logo = old.get("team_logo")
    else:
        bal = Config.STARTING_BALANCE
        team_name = season_team_name
        team_logo = None

    n_players = squad_count(guild_id, old_user_id)

    with db.cursor() as c:
        # 1) Clear any empty shell for the new user
        c.execute(
            "DELETE FROM users WHERE guild_id=? AND user_id=?",
            (guild_id, new_user_id),
        )
        c.execute(
            "DELETE FROM formations WHERE guild_id=? AND user_id=?",
            (guild_id, new_user_id),
        )
        c.execute(
            "DELETE FROM lineup_overrides WHERE guild_id=? AND user_id=?",
            (guild_id, new_user_id),
        )
        c.execute(
            "DELETE FROM tactics WHERE guild_id=? AND user_id=?",
            (guild_id, new_user_id),
        )
        c.execute(
            "DELETE FROM watchlist WHERE guild_id=? AND user_id=?",
            (guild_id, new_user_id),
        )

        # 2) INSERT new users row (never UPDATE PK — Turso/SQLite-safe)
        c.execute(
            "INSERT INTO users (guild_id, user_id, balance, team_name, team_logo) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, new_user_id, bal, team_name, team_logo),
        )

        # 3) Move child tables (these use user_id as part of PK / column, not users PK rewrite)
        def _move(table: str, col: str = "user_id"):
            c.execute(
                f"UPDATE {table} SET {col}=? WHERE guild_id=? AND {col}=?",
                (new_user_id, guild_id, old_user_id),
            )

        _move("squads")
        _move("formations")
        _move("lineup_overrides")
        _move("tactics")
        _move("watchlist")
        try:
            _ensure_bench_table()
            _move("bench")
        except Exception:
            pass

        c.execute(
            "UPDATE auction_history SET winner_id=? "
            "WHERE guild_id=? AND winner_id=?",
            (new_user_id, guild_id, old_user_id),
        )
        c.execute(
            "UPDATE trades SET from_user=? WHERE guild_id=? AND from_user=?",
            (new_user_id, guild_id, old_user_id),
        )
        c.execute(
            "UPDATE trades SET to_user=? WHERE guild_id=? AND to_user=?",
            (new_user_id, guild_id, old_user_id),
        )

        try:
            c.execute(
                "UPDATE card_assignments SET user_id=? "
                "WHERE guild_id=? AND user_id=?",
                (new_user_id, guild_id, old_user_id),
            )
        except Exception:
            pass

        # 4) Season seat + fixtures (fetch season ids first — more Turso-friendly)
        try:
            season_rows = c.execute(
                "SELECT id FROM seasons WHERE guild_id=?",
                (guild_id,),
            ).fetchall()
            season_ids = [int(r["id"]) for r in season_rows]
            for sid in season_ids:
                c.execute(
                    "UPDATE season_teams SET user_id=? WHERE season_id=? AND user_id=?",
                    (new_user_id, sid, old_user_id),
                )
                # Keep team_name on season_teams if it was only stored there
                if team_name:
                    c.execute(
                        "UPDATE season_teams SET team_name=? "
                        "WHERE season_id=? AND user_id=?",
                        (team_name, sid, new_user_id),
                    )
                c.execute(
                    "UPDATE fixtures SET home_user=? WHERE season_id=? AND home_user=?",
                    (new_user_id, sid, old_user_id),
                )
                c.execute(
                    "UPDATE fixtures SET away_user=? WHERE season_id=? AND away_user=?",
                    (new_user_id, sid, old_user_id),
                )
        except Exception as ex:
            print(f"[!] replace_manager season/fixture update: {ex}")

        # 5) Delete old users shell (after children moved)
        c.execute(
            "DELETE FROM users WHERE guild_id=? AND user_id=?",
            (guild_id, old_user_id),
        )

    # 6) Force-write team identity again (belt + suspenders)
    if team_name:
        set_team_name(guild_id, new_user_id, team_name)
    if team_logo:
        try:
            set_team_logo(guild_id, new_user_id, team_logo)
        except Exception:
            pass

    # Verify
    final_name = get_team_name(guild_id, new_user_id)
    if team_name and not final_name:
        # Last resort direct write
        with db.cursor() as c:
            c.execute(
                "UPDATE users SET team_name=? WHERE guild_id=? AND user_id=?",
                (team_name[:50], guild_id, new_user_id),
            )
        final_name = get_team_name(guild_id, new_user_id)

    # In-memory card bans / peek state
    try:
        import cards as Cards
        bans = Cards._temp_bid_bans.get(guild_id, {})
        if old_user_id in bans:
            bans[new_user_id] = bans.pop(old_user_id)
        pending = Cards._pending_after_player_ban.get(guild_id, {})
        if old_user_id in pending:
            pending[new_user_id] = pending.pop(old_user_id)
    except Exception:
        pass

    return {
        "old_user_id": old_user_id,
        "new_user_id": new_user_id,
        "team_name": final_name or team_name,
        "balance": get_balance(guild_id, new_user_id),
        "squad_size": squad_count(guild_id, new_user_id),
    }


# Fine charged to the manager when a player is dumped (always a debit)
DUMP_FEE = 70_000_000  # −£70M from the manager


def dump_player(guild_id: int, user_id: int, player_key: str, fee: int = None) -> dict:
    """
    Admin dump:
      - remove player from manager's squad
      - FINE them fee (default −£70M)
      - log as UNSOLD so they can re-enter the auction pool

    fee is always applied as a charge (negative balance change).
    """
    guild_id = int(guild_id)
    user_id = int(user_id)
    # ALWAYS fine the manager
    fee = abs(DUMP_FEE if fee is None else int(fee))

    p = P.get(player_key)
    if not p:
        results = P.search(str(player_key), limit=1)
        p = results[0] if results else None
    if not p:
        raise RuntimeError("Player not found.")

    key = p["key"]
    if not owns(guild_id, user_id, key):
        raise RuntimeError("That manager does not own this player.")

    bal_before = get_balance(guild_id, user_id)

    # Remove from squad
    with db.cursor() as c:
        c.execute(
            "DELETE FROM squads WHERE guild_id=? AND user_id=? AND player_key=?",
            (guild_id, user_id, key),
        )
        try:
            c.execute(
                "DELETE FROM lineup_overrides "
                "WHERE guild_id=? AND user_id=? AND player_key=?",
                (guild_id, user_id, key),
            )
        except Exception:
            pass

    # FINE the manager (−fee)
    ensure_user(guild_id, user_id)
    adjust_balance(guild_id, user_id, -fee)

    bal_after = get_balance(guild_id, user_id)

    try:
        log_unsold(guild_id, p)
    except Exception as ex:
        print(f"[!] dump log_unsold: {ex}")

    try:
        import auction as A
        offered = A.OFFERED.get(guild_id, set())
        offered.discard(key)
    except Exception:
        pass

    return {
        "player": p,
        "user_id": user_id,
        "fee": fee,  # amount fined (positive number meaning £ taken)
        "balance_before": bal_before,
        "balance": bal_after,
        "team_name": get_team_name(guild_id, user_id),
        "squad_size": squad_count(guild_id, user_id),
    }


def take_money(guild_id: int, user_id: int, amount: int) -> dict:
    """
    Admin: remove money from a manager.
    amount is the positive £ to take (e.g. 70_000_000).
    """
    guild_id = int(guild_id)
    user_id = int(user_id)
    amount = abs(int(amount))
    if amount <= 0:
        raise RuntimeError("Amount must be > 0.")

    ensure_user(guild_id, user_id)
    before = get_balance(guild_id, user_id)
    adjust_balance(guild_id, user_id, -amount)
    after = get_balance(guild_id, user_id)
    return {
        "user_id": user_id,
        "taken": amount,
        "balance_before": before,
        "balance": after,
        "team_name": get_team_name(guild_id, user_id),
    }


def force_set_team(guild_id: int, user_id: int, team_name: str, logo_url: str = None) -> dict:
    """
    Admin: force club name (+ optional logo) onto a manager.
    Writes BOTH users.team_name and active season_teams.team_name.
    """
    user_id = int(user_id)
    name = (team_name or "").strip()
    if not name:
        raise RuntimeError("Team name is empty.")

    ensure_user(guild_id, user_id)
    set_team_name(guild_id, user_id, name)
    if logo_url:
        set_team_logo(guild_id, user_id, logo_url)

    # Mirror onto active season seat if any
    try:
        import league as L
        s = L.active_season(guild_id)
        if s:
            # ensure they're a season team
            tms = L.teams(s["id"])
            if not any(int(t["user_id"]) == user_id for t in tms):
                try:
                    L.add_team_auto_seed(s["id"], user_id, team_name=name)
                except Exception:
                    pass
            try:
                L.set_team_name(s["id"], user_id, name)
            except Exception:
                with db.cursor() as c:
                    c.execute(
                        "UPDATE season_teams SET team_name=? "
                        "WHERE season_id=? AND user_id=?",
                        (name, s["id"], user_id),
                    )
    except Exception as ex:
        print(f"[!] force_set_team season mirror: {ex}")

    return {
        "user_id": user_id,
        "team_name": get_team_name(guild_id, user_id),
        "logo": get_team_logo(guild_id, user_id),
    }
