"""
Management + Finance card system for the auction draft.

Lifecycle (management):
  admin: start → managers pick (unique cards) → admin lock → auction
  late arrivals: auto-assigned leftover card on first bid
  admin: end day → incomplete goals get £50M penalty

Lifecycle (finance):
  admin: start → pick → balance applied instantly → admin reveal/lock

Auction rules:
  - only managers with a drawn team in the active season can bid
  - must hold a management card for the open day (or get auto leftover on bid)
  - restrictions hard-block invalid bids
"""

from __future__ import annotations

import json
import random
import threading
from datetime import datetime, timezone
from typing import Optional

import database as db
import economy as E
import players as P
import league as L
import emojis as EM
from cards_data import (
    MANAGEMENT_CARDS,
    FINANCE_CARDS,
    MANAGEMENT_BY_KEY,
    FINANCE_BY_KEY,
    MANAGEMENT_PENALTY,
    EUROPE_COUNTRIES,
    PREMIER_LEAGUE_CLUBS,
)

# Serialize draws so two simultaneous clicks never get the same card
_draw_lock = threading.Lock()

# In-memory auction round counter per guild (incremented when an auction finalizes)
_auction_rounds: dict[int, int] = {}
# Temporary bid bans: guild_id -> {user_id: remaining auctions they must skip}
_temp_bid_bans: dict[int, dict[int, int]] = {}
# Peek power: ban starts AFTER the revealed player's auction ends
# (so they can still bid on the player they peeked)
# guild_id -> {user_id: {"player_key": str, "ban_n": int}}
_pending_after_player_ban: dict[int, dict[int, dict]] = {}


def ensure_schema():
    """Create card tables if missing. Safe to call often."""
    with db.cursor() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS card_days (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id      INTEGER NOT NULL,
                kind          TEXT    NOT NULL,  -- management | finance
                status        TEXT    NOT NULL DEFAULT 'open',  -- open|locked|ended
                channel_id    INTEGER,
                message_id    INTEGER,
                season_id     INTEGER,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                locked_at     TEXT,
                ended_at      TEXT
            );
            CREATE TABLE IF NOT EXISTS card_assignments (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                day_id        INTEGER NOT NULL,
                guild_id      INTEGER NOT NULL,
                user_id       INTEGER NOT NULL,
                card_key      TEXT    NOT NULL,
                card_text     TEXT    NOT NULL,
                status        TEXT    NOT NULL DEFAULT 'active',
                -- management: active|completed|failed|penalized
                -- finance: applied
                completed_at  TEXT,
                meta_json     TEXT    NOT NULL DEFAULT '{}',
                UNIQUE(day_id, user_id),
                UNIQUE(day_id, card_key)
            );
            CREATE TABLE IF NOT EXISTS card_day_events (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                day_id        INTEGER NOT NULL,
                guild_id      INTEGER NOT NULL,
                user_id       INTEGER,
                event         TEXT    NOT NULL,
                detail        TEXT,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            """
        )


# --------------------------------------------------------------------------
# Season managers (drawn teams only)
# --------------------------------------------------------------------------

def season_manager_ids(guild_id: int) -> list[int]:
    """Managers in the active season who already have a drawn team name."""
    s = L.active_season(guild_id)
    if not s:
        return []
    tms = L.teams(s["id"])
    out = []
    for t in tms:
        name = t.get("team_name")
        if name:  # drawn
            out.append(int(t["user_id"]))
    return out


def is_season_manager(guild_id: int, user_id: int) -> bool:
    return int(user_id) in set(season_manager_ids(guild_id))


def team_label(guild_id: int, user_id: int) -> str:
    """Club emoji + team name only (no Discord mention)."""
    name = E.get_team_name(guild_id, user_id) or f"Manager {user_id}"
    return EM.club_tag(name)


def manager_line(guild_id: int, user_id: int) -> str:
    """
    Public reveal format:  <:club:> Real Madrid (<@user>)
    Falls back to mention-only if no team name yet.
    """
    name = E.get_team_name(guild_id, user_id)
    mention = f"<@{int(user_id)}>"
    if name:
        return f"{EM.club_tag(name)} ({mention})"
    return mention


# --------------------------------------------------------------------------
# Auction round tracking
# --------------------------------------------------------------------------

def get_auction_round(guild_id: int) -> int:
    return _auction_rounds.get(guild_id, 0)


def on_auction_finished(guild_id: int, player_key: str = None):
    """
    Call when an auction ends (sold / void / skip).

    player_key: the player that was just on the block (used to activate
    delayed peek bans so the peeker can bid on the revealed player).
    """
    _auction_rounds[guild_id] = _auction_rounds.get(guild_id, 0) + 1

    # Tick down active bans (auctions they must sit out)
    bans = _temp_bid_bans.get(guild_id, {})
    for uid in list(bans.keys()):
        bans[uid] -= 1
        if bans[uid] <= 0:
            bans.pop(uid, None)
    if bans:
        _temp_bid_bans[guild_id] = bans
    else:
        _temp_bid_bans.pop(guild_id, None)

    # Activate delayed peek bans after the revealed player's auction ends
    pending = _pending_after_player_ban.get(guild_id, {})
    for uid in list(pending.keys()):
        info = pending[uid]
        if player_key is None or info.get("player_key") == player_key:
            ban_n = int(info.get("ban_n") or 5)
            set_temp_bid_ban(guild_id, uid, ban_n)
            pending.pop(uid, None)
    if pending:
        _pending_after_player_ban[guild_id] = pending
    else:
        _pending_after_player_ban.pop(guild_id, None)


def set_temp_bid_ban(guild_id: int, user_id: int, n_auctions: int):
    """Ban user from bidding for the next n completed auctions (active now)."""
    _temp_bid_bans.setdefault(guild_id, {})[int(user_id)] = int(n_auctions)


def schedule_ban_after_player(
    guild_id: int, user_id: int, player_key: str, n_auctions: int
):
    """
    After the auction for player_key finishes, ban user for n_auctions.
    Until then they can still bid (including on that player).
    """
    _pending_after_player_ban.setdefault(guild_id, {})[int(user_id)] = {
        "player_key": player_key,
        "ban_n": int(n_auctions),
    }


def temp_ban_remaining(guild_id: int, user_id: int) -> int:
    return _temp_bid_bans.get(guild_id, {}).get(int(user_id), 0)


def pending_peek_info(guild_id: int, user_id: int) -> Optional[dict]:
    """If user used peek and ban hasn't started yet."""
    return _pending_after_player_ban.get(guild_id, {}).get(int(user_id))


# --------------------------------------------------------------------------
# Day helpers
# --------------------------------------------------------------------------

def _row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        return {k: row[k] for k in row.keys()}


def get_open_day(guild_id: int, kind: str) -> Optional[dict]:
    ensure_schema()
    with db.cursor() as c:
        row = c.execute(
            "SELECT * FROM card_days WHERE guild_id=? AND kind=? "
            "AND status IN ('open','locked') ORDER BY id DESC LIMIT 1",
            (guild_id, kind),
        ).fetchone()
    return _row_to_dict(row)


def get_day(day_id: int) -> Optional[dict]:
    ensure_schema()
    with db.cursor() as c:
        row = c.execute("SELECT * FROM card_days WHERE id=?", (day_id,)).fetchone()
    return _row_to_dict(row)


def start_day(guild_id: int, kind: str, channel_id: int = None) -> dict:
    """
    Start a new card day. Fails if one is already open/locked for that kind.
    kind: 'management' | 'finance'
    """
    ensure_schema()
    existing = get_open_day(guild_id, kind)
    if existing:
        raise RuntimeError(
            f"A {kind} day is already {existing['status']} (id={existing['id']}). "
            f"End or lock it first."
        )
    s = L.active_season(guild_id)
    sid = s["id"] if s else None
    with db.cursor() as c:
        c.execute(
            "INSERT INTO card_days (guild_id, kind, status, channel_id, season_id) "
            "VALUES (?, ?, 'open', ?, ?)",
            (guild_id, kind, channel_id, sid),
        )
        day_id = c.lastrowid
    day = get_day(day_id)
    if not day:
        # Turso lastrowid fallback
        with db.cursor() as c:
            row = c.execute(
                "SELECT * FROM card_days WHERE guild_id=? AND kind=? "
                "ORDER BY id DESC LIMIT 1",
                (guild_id, kind),
            ).fetchone()
        day = _row_to_dict(row)
    # reset auction round counter for management days so ban_first_n works
    if kind == "management":
        _auction_rounds[guild_id] = 0
    return day


def set_day_message(day_id: int, channel_id: int, message_id: int):
    with db.cursor() as c:
        c.execute(
            "UPDATE card_days SET channel_id=?, message_id=? WHERE id=?",
            (channel_id, message_id, day_id),
        )


def lock_day(day_id: int) -> dict:
    with db.cursor() as c:
        c.execute(
            "UPDATE card_days SET status='locked', locked_at=datetime('now') WHERE id=?",
            (day_id,),
        )
    return get_day(day_id)


def end_management_day(guild_id: int, day_id: int) -> list[dict]:
    """
    End management day: incomplete goals → £50M penalty.
    free / restriction / power (unused) → completed if still active.
    Returns list of penalty results.
    """
    day = get_day(day_id)
    if not day or day["guild_id"] != guild_id:
        raise RuntimeError("Day not found.")
    if day["kind"] != "management":
        raise RuntimeError("Not a management day.")

    assigns = list_assignments(day_id)
    penalties = []
    for a in assigns:
        card = MANAGEMENT_BY_KEY.get(a["card_key"], {})
        ctype = card.get("type", "free")
        if a["status"] == "completed":
            continue
        if ctype == "free":
            _set_assignment_status(a["id"], "completed")
            continue
        if ctype in ("restriction", "power"):
            # no breach tracking for restriction failure yet → complete
            _set_assignment_status(a["id"], "completed")
            continue
        # goal / goal_manual incomplete
        E.adjust_balance(guild_id, a["user_id"], -MANAGEMENT_PENALTY)
        _set_assignment_status(a["id"], "penalized")
        penalties.append({
            "user_id": a["user_id"],
            "card_text": a["card_text"],
            "penalty": MANAGEMENT_PENALTY,
            "balance": E.get_balance(guild_id, a["user_id"]),
        })

    with db.cursor() as c:
        c.execute(
            "UPDATE card_days SET status='ended', ended_at=datetime('now') WHERE id=?",
            (day_id,),
        )
    return penalties


def list_assignments(day_id: int) -> list[dict]:
    with db.cursor() as c:
        rows = c.execute(
            "SELECT * FROM card_assignments WHERE day_id=? ORDER BY id",
            (day_id,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_assignment(day_id: int, user_id: int) -> Optional[dict]:
    with db.cursor() as c:
        row = c.execute(
            "SELECT * FROM card_assignments WHERE day_id=? AND user_id=?",
            (day_id, user_id),
        ).fetchone()
    return _row_to_dict(row)


def get_user_management(guild_id: int, user_id: int) -> Optional[dict]:
    """Active/locked management assignment for profile display."""
    day = get_open_day(guild_id, "management")
    if not day:
        return None
    a = get_assignment(day["id"], user_id)
    if not a:
        return None
    card = MANAGEMENT_BY_KEY.get(a["card_key"], {})
    return {**a, "card": card, "day": day}


def remaining_keys(day_id: int, kind: str) -> list[str]:
    pool = MANAGEMENT_CARDS if kind == "management" else FINANCE_CARDS
    all_keys = [c["key"] for c in pool]
    with db.cursor() as c:
        rows = c.execute(
            "SELECT card_key FROM card_assignments WHERE day_id=?",
            (day_id,),
        ).fetchall()
    taken = {r["card_key"] for r in rows}
    return [k for k in all_keys if k not in taken]


def _set_assignment_status(assignment_id: int, status: str):
    with db.cursor() as c:
        if status == "completed":
            c.execute(
                "UPDATE card_assignments SET status=?, completed_at=datetime('now') WHERE id=?",
                (status, assignment_id),
            )
        else:
            c.execute(
                "UPDATE card_assignments SET status=? WHERE id=?",
                (status, assignment_id),
            )


def admin_complete(guild_id: int, user_id: int) -> Optional[dict]:
    """Mark current management goal as completed (manual cards)."""
    day = get_open_day(guild_id, "management")
    if not day:
        return None
    a = get_assignment(day["id"], user_id)
    if not a:
        return None
    if a["status"] == "completed":
        return a
    _set_assignment_status(a["id"], "completed")
    return get_assignment(day["id"], user_id)


# --------------------------------------------------------------------------
# Draw (unique, race-safe)
# --------------------------------------------------------------------------

def draw_card(guild_id: int, user_id: int, kind: str, auto: bool = False) -> dict:
    """
    Assign a unique random card. Thread-locked so concurrent clicks never
    share a card_key (UNIQUE constraint is the final backstop).
    """
    ensure_schema()
    user_id = int(user_id)
    with _draw_lock:
        day = get_open_day(guild_id, kind)
        if not day:
            raise RuntimeError(f"No open {kind} card day. Admin must start one.")
        if day["status"] != "open" and not auto:
            raise RuntimeError(f"{kind.title()} picks are locked.")

        existing = get_assignment(day["id"], user_id)
        if existing:
            raise RuntimeError("You already have a card for this day.")

        if not is_season_manager(guild_id, user_id):
            raise RuntimeError("Only managers with a drawn team can pick cards.")

        left = remaining_keys(day["id"], kind)
        if not left:
            raise RuntimeError("No cards left in the deck.")

        key = random.choice(left)
        if kind == "management":
            card = MANAGEMENT_BY_KEY[key]
            text = card["text"]
            status = "completed" if card["type"] == "free" else "active"
            meta = {
                "type": card["type"],
                "params": card.get("params", {}),
                "check": card.get("check"),
                "auto": auto,
                "icons_bought": 0,
                "night_spend": 0,
                "buys": 0,
            }
        else:
            card = FINANCE_BY_KEY[key]
            text = card["text"]
            status = "applied"
            meta = {"delta": card["delta"], "auto": auto}

        try:
            with db.cursor() as c:
                c.execute(
                    "INSERT INTO card_assignments "
                    "(day_id, guild_id, user_id, card_key, card_text, status, meta_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        day["id"], guild_id, user_id, key, text, status,
                        json.dumps(meta),
                    ),
                )
        except Exception as e:
            # unique collision — retry once with another key
            left2 = [k for k in remaining_keys(day["id"], kind) if k != key]
            if not left2:
                raise RuntimeError("No cards left (race).") from e
            key = random.choice(left2)
            if kind == "management":
                card = MANAGEMENT_BY_KEY[key]
                text = card["text"]
                status = "completed" if card["type"] == "free" else "active"
                meta = {
                    "type": card["type"],
                    "params": card.get("params", {}),
                    "check": card.get("check"),
                    "auto": auto,
                    "icons_bought": 0,
                    "night_spend": 0,
                    "buys": 0,
                }
            else:
                card = FINANCE_BY_KEY[key]
                text = card["text"]
                status = "applied"
                meta = {"delta": card["delta"], "auto": auto}
            with db.cursor() as c:
                c.execute(
                    "INSERT INTO card_assignments "
                    "(day_id, guild_id, user_id, card_key, card_text, status, meta_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        day["id"], guild_id, user_id, key, text, status,
                        json.dumps(meta),
                    ),
                )

        # Apply finance immediately
        if kind == "finance":
            delta = int(card["delta"])
            if delta != 0:
                E.ensure_user(guild_id, user_id)
                E.adjust_balance(guild_id, user_id, delta)

        return get_assignment(day["id"], user_id)


def ensure_management_for_bid(guild_id: int, user_id: int) -> Optional[dict]:
    """
    If management day is open/locked and user has no card, auto-assign leftover.
    Returns assignment or None if no management day.
    """
    day = get_open_day(guild_id, "management")
    if not day:
        return None
    a = get_assignment(day["id"], user_id)
    if a:
        return a
    # auto from leftovers (allowed even when locked)
    return draw_card(guild_id, user_id, "management", auto=True)


# --------------------------------------------------------------------------
# Bid validation
# --------------------------------------------------------------------------

def _meta(a: dict) -> dict:
    try:
        return json.loads(a.get("meta_json") or "{}")
    except Exception:
        return {}


def _save_meta(assignment_id: int, meta: dict):
    with db.cursor() as c:
        c.execute(
            "UPDATE card_assignments SET meta_json=? WHERE id=?",
            (json.dumps(meta), assignment_id),
        )


def _is_icon(player: dict) -> bool:
    return player.get("club") == "ICON" or P.is_icon(player)


def _is_premier_league(player: dict) -> bool:
    club = (player.get("club") or "").strip()
    if not club or club == "ICON":
        return False
    cl = club.lower()
    for pl in PREMIER_LEAGUE_CLUBS:
        pll = pl.lower()
        if pll in cl or cl in pll:
            return True
    return False


def can_bid(guild_id: int, user_id: int, player: dict, amount: int) -> tuple[bool, str]:
    """
    Gate all auction bids.
    Returns (ok, error_message).
    """
    user_id = int(user_id)

    # 1) must be in season with drawn team
    if not is_season_manager(guild_id, user_id):
        return False, "Only managers in the season (with a drawn team) can bid."

    # 2) temp ban from power use
    rem = temp_ban_remaining(guild_id, user_id)
    if rem > 0:
        return False, f"You're banned from bidding for {rem} more auction(s)."

    # 3) management card required if a day is open/locked
    day = get_open_day(guild_id, "management")
    if day:
        try:
            a = ensure_management_for_bid(guild_id, user_id)
        except Exception as e:
            return False, f"Couldn't assign a management card: {e}"
        if not a:
            return False, "You need a management card to bid."

        card = MANAGEMENT_BY_KEY.get(a["card_key"], {})
        params = card.get("params") or _meta(a).get("params") or {}
        ctype = card.get("type")
        rnd = get_auction_round(guild_id)

        # ban first N rounds (0-indexed completed auctions before this one)
        ban_first = int(params.get("ban_first_n") or 0)
        if ban_first and rnd < ban_first:
            return False, (
                f"Your card bans you for the first {ban_first} rounds "
                f"(this is round {rnd + 1})."
            )

        # max bid per player
        max_bid = params.get("max_bid")
        if max_bid is not None and amount > int(max_bid):
            return False, f"Your card caps single bids at {E.money(int(max_bid))}."

        # night spend cap (include this bid)
        max_night = params.get("max_night_spend")
        if max_night is not None:
            meta = _meta(a)
            spent = int(meta.get("night_spend") or 0)
            if spent + amount > int(max_night):
                return False, (
                    f"Your card caps total spend tonight at {E.money(int(max_night))} "
                    f"(spent {E.money(spent)} so far)."
                )

        # group bans
        ban_groups = params.get("ban_groups") or []
        if ban_groups and player.get("group") in ban_groups:
            return False, f"Your card bans bidding on {player.get('group')} players."

        # age bans (icons ignored when ignore_icons)
        ignore_icons = bool(params.get("ignore_icons"))
        is_ic = _is_icon(player)
        age = player.get("age")
        try:
            age = int(age) if age is not None else None
        except (TypeError, ValueError):
            age = None

        if age is not None and not (ignore_icons and is_ic):
            if params.get("max_age") is not None and age > int(params["max_age"]):
                return False, f"Your card bans players over {params['max_age']}."
            if params.get("min_age") is not None and age < int(params["min_age"]):
                return False, f"Your card bans players under {params['min_age']}."

        # max icons
        max_icons = params.get("max_icons")
        if max_icons is not None and is_ic:
            meta = _meta(a)
            bought = int(meta.get("icons_bought") or 0)
            if bought >= int(max_icons):
                return False, f"Your card allows at most {max_icons} icon(s) tonight."

    return True, ""


# --------------------------------------------------------------------------
# Sale hooks — progress goals + completion
# --------------------------------------------------------------------------

def on_player_bought(guild_id: int, user_id: int, player: dict, price: int) -> Optional[dict]:
    """
    Call after a successful sale. Updates meta + auto-completes goals.
    Returns dict if a goal was just completed: {user_id, card_text, ...}
    """
    day = get_open_day(guild_id, "management")
    if not day:
        return None
    a = get_assignment(day["id"], user_id)
    if not a or a["status"] not in ("active", "completed"):
        return None

    card = MANAGEMENT_BY_KEY.get(a["card_key"], {})
    meta = _meta(a)
    meta["buys"] = int(meta.get("buys") or 0) + 1
    meta["night_spend"] = int(meta.get("night_spend") or 0) + int(price)
    if _is_icon(player):
        meta["icons_bought"] = int(meta.get("icons_bought") or 0) + 1
    _save_meta(a["id"], meta)

    if a["status"] == "completed":
        return None
    if card.get("type") not in ("goal",):
        return None

    check = card.get("check")
    params = card.get("params") or {}
    ok = False

    if check == "buy_ovr_min":
        ok = int(player.get("ovr") or 0) >= int(params.get("ovr", 99))
    elif check == "buy_premier_league":
        ok = _is_premier_league(player)
    elif check == "buy_non_europe":
        country = player.get("country") or ""
        ok = country not in EUROPE_COUNTRIES
    elif check == "buy_group":
        ok = player.get("group") == params.get("group")
    elif check == "buy_country":
        ok = (player.get("country") or "") == params.get("country")
    elif check == "buy_country_active":
        ok = (
            (player.get("country") or "") == params.get("country")
            and not _is_icon(player)
        )
    elif check == "buy_icon":
        ok = _is_icon(player)
    elif check == "buy_count":
        ok = int(meta.get("buys") or 0) >= int(params.get("count") or 1)

    if ok:
        _set_assignment_status(a["id"], "completed")
        return {
            "user_id": user_id,
            "card_text": a["card_text"],
            "player": player,
            "price": price,
        }
    return None


# --------------------------------------------------------------------------
# Powers (admin-triggered)
# --------------------------------------------------------------------------

def use_power_steal(guild_id: int, thief_id: int, victim_id: int, player_key: str) -> dict:
    """
    Steal player for same acquired price. Applies 5-round bid ban to thief.
    """
    day = get_open_day(guild_id, "management")
    if not day:
        raise RuntimeError("No management day open.")
    a = get_assignment(day["id"], thief_id)
    if not a:
        raise RuntimeError("Thief has no management card.")
    card = MANAGEMENT_BY_KEY.get(a["card_key"], {})
    if card.get("params", {}).get("power") != "steal":
        raise RuntimeError("This manager's card is not the steal power.")

    if not E.owns(guild_id, victim_id, player_key):
        raise RuntimeError("Victim does not own that player.")

    p = P.get(player_key)
    if not p:
        raise RuntimeError("Player not found.")

    with db.cursor() as c:
        row = c.execute(
            "SELECT acquired_price FROM squads WHERE guild_id=? AND user_id=? AND player_key=?",
            (guild_id, victim_id, player_key),
        ).fetchone()
    price = int(row["acquired_price"]) if row else int(p.get("value") or 0)

    if not E.can_afford(guild_id, thief_id, price):
        raise RuntimeError(f"Thief can't afford the steal price ({E.money(price)}).")

    # money + ownership
    E.adjust_balance(guild_id, thief_id, -price)
    E.adjust_balance(guild_id, victim_id, price)
    with db.cursor() as c:
        c.execute(
            "DELETE FROM squads WHERE guild_id=? AND user_id=? AND player_key=?",
            (guild_id, victim_id, player_key),
        )
        c.execute(
            "INSERT OR REPLACE INTO squads "
            "(guild_id, user_id, player_key, position, acquired_price) "
            "VALUES (?, ?, ?, ?, ?)",
            (guild_id, thief_id, player_key, p.get("position", ""), price),
        )

    ban_n = int(card.get("params", {}).get("ban_after_use") or 5)
    set_temp_bid_ban(guild_id, thief_id, ban_n)
    _set_assignment_status(a["id"], "completed")

    return {
        "player": p,
        "price": price,
        "thief_id": thief_id,
        "victim_id": victim_id,
        "ban": ban_n,
    }


def use_power_peek(guild_id: int, user_id: int, power: str = "peek_player") -> dict:
    """
    Reveal next queue player.

    Ban does NOT start immediately — they may bid on the revealed player.
    After that player's auction ends, they are banned for ban_after_use rounds.
    """
    day = get_open_day(guild_id, "management")
    if not day:
        raise RuntimeError("No management day open.")
    a = get_assignment(day["id"], user_id)
    if not a:
        raise RuntimeError("Manager has no card.")
    card = MANAGEMENT_BY_KEY.get(a["card_key"], {})
    if card.get("params", {}).get("power") not in ("peek_player", "peek_card", power):
        if card.get("params", {}).get("power") not in ("peek_player", "peek_card"):
            raise RuntimeError("This manager's card is not a peek power.")

    qkey, qcount = E.queue_next(guild_id)
    if not qkey:
        raise RuntimeError("Queue is empty.")
    p = P.get(qkey)
    if not p:
        raise RuntimeError("Next queue key not found in player DB.")

    ban_n = int(card.get("params", {}).get("ban_after_use") or 5)
    # Delayed ban: can bid on THIS player; ban starts when their auction ends
    schedule_ban_after_player(guild_id, user_id, p["key"], ban_n)
    _set_assignment_status(a["id"], "completed")

    return {
        "player": p,
        "remaining_queue": qcount,
        "ban": ban_n,
        "player_key": p["key"],
    }


# --------------------------------------------------------------------------
# Profile snippet
# --------------------------------------------------------------------------

def profile_lines(guild_id: int, user_id: int) -> list[str]:
    """Lines for /profile embed — full task text (no truncation)."""
    info = get_user_management(guild_id, user_id)
    if not info:
        return []
    status = info["status"]
    if status == "completed":
        mark = EM.e("check")
    elif status in ("failed", "penalized"):
        mark = EM.e("x")
    else:
        mark = EM.e("x")  # not done yet
    text = (info.get("card_text") or "").strip()
    # Discord field value max is 1024; keep full task, hard-cap only as safety
    body = f"**Management card**\n{mark} {text}"
    if len(body) > 1024:
        body = body[:1020] + "…"
    return [body]
