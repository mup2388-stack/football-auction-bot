"""
League engine — fixtures, results, standings, stats for FL26 seasons.

Supports 5 competition formats. All fixture generation, standings math, and
stat aggregation live here. The bot calls these functions; rendering is separate.

FORMATS:
  round_robin    — everyone plays everyone once. One table.
  double_rr      — home & away vs everyone. One table.
  groups_ko      — World Cup style: groups of 4, top 2 advance, knockout bracket.
  league_playoff — full league phase, then top N into playoff bracket.
  knockout       — pure single-elimination bracket (seeds get byes if not power of 2).

A "matchday" is a round of simultaneous fixtures (league). A "stage" is a
knockout round (R32, R16, QF, SF, Final). Standings auto-compute from played
fixtures via recalc().
"""
from __future__ import annotations
import math
from itertools import combinations
from typing import Optional

import database as db


# ──────────────────────────────────────────────────────────────────────────
#  Schema (added to the auto-migration)
# ──────────────────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS seasons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    number      INTEGER NOT NULL DEFAULT 1,
    format      TEXT    NOT NULL,
    group_size  INTEGER NOT NULL DEFAULT 4,
    status      TEXT    NOT NULL DEFAULT 'setup',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS season_teams (
    season_id  INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    team_name  TEXT,
    seed       INTEGER NOT NULL DEFAULT 0,
    group_label TEXT,
    PRIMARY KEY (season_id, user_id)
);

CREATE TABLE IF NOT EXISTS fixtures (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id    INTEGER NOT NULL,
    stage        TEXT,             -- 'league','group','R32','R16','QF','SF','F'
    matchday     INTEGER,          -- 1..N for league; round# for knockout
    group_label  TEXT,             -- 'A','B',... for groups; NULL otherwise
    home_user    INTEGER,
    away_user    INTEGER,
    home_score   INTEGER,
    away_score   INTEGER,
    status       TEXT NOT NULL DEFAULT 'scheduled',  -- scheduled, played
    next_fixture INTEGER,          -- links bracket winners forward
    played_at    TEXT,
    home_pens    INTEGER,
    away_pens    INTEGER
);
"""


FORMATS = {
    "round_robin":    "Single Round-Robin (everyone once, one table)",
    "double_rr":      "Double Round-Robin (home & away, one table)",
    "groups_ko":      "Groups + Knockout (World Cup style)",
    "league_playoff": "League phase + Playoffs (top N into brackets)",
    "knockout":       "Pure Knockout (single-elimination bracket)",
}


def init():
    """Create league tables if missing. Call once at startup."""
    with db.cursor() as c:
        c.executescript(SCHEMA)
        # Migrations for existing databases
        try:
            c.execute("ALTER TABLE fixtures ADD COLUMN home_pens INTEGER")
        except Exception:
            pass  # column already exists
        try:
            c.execute("ALTER TABLE fixtures ADD COLUMN away_pens INTEGER")
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────
#  Season lifecycle
# ──────────────────────────────────────────────────────────────────────────
def create_season(guild_id: int, fmt: str, number: int = 1, group_size: int = 4) -> int:
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format '{fmt}'. Pick one of: {list(FORMATS)}")
    with db.cursor() as c:
        row = c.execute(
            "INSERT INTO seasons (guild_id, number, format, group_size, status) "
            "VALUES (?,?,?,?, 'setup')",
            (guild_id, number, fmt, group_size),
        )
        return row.lastrowid


def get_season(season_id: int) -> Optional[dict]:
    with db.cursor() as c:
        row = c.execute("SELECT * FROM seasons WHERE id=?", (season_id,)).fetchone()
        return dict(row) if row else None


def active_season(guild_id: int) -> Optional[dict]:
    """The most recent season that isn't 'complete'."""
    with db.cursor() as c:
        row = c.execute(
            "SELECT * FROM seasons WHERE guild_id=? AND status != 'complete' "
            "ORDER BY id DESC LIMIT 1",
            (guild_id,),
        ).fetchone()
        return dict(row) if row else None


def set_season_status(season_id: int, status: str):
    with db.cursor() as c:
        c.execute("UPDATE seasons SET status=? WHERE id=?", (status, season_id))


def next_season_number(guild_id: int) -> int:
    with db.cursor() as c:
        row = c.execute(
            "SELECT MAX(number) AS m FROM seasons WHERE guild_id=?", (guild_id,)
        ).fetchone()
        return (row["m"] or 0) + 1 if row else 1


# ──────────────────────────────────────────────────────────────────────────
#  Teams
# ──────────────────────────────────────────────────────────────────────────
def add_team(season_id: int, user_id: int, team_name: str = None, seed: int = 0):
    with db.cursor() as c:
        c.execute(
            "INSERT OR IGNORE INTO season_teams "
            "(season_id, user_id, team_name, seed) VALUES (?,?,?,?)",
            (season_id, user_id, team_name, seed),
        )


def add_team_auto_seed(season_id: int, user_id: int, team_name: str = None) -> int:
    """Add a team and auto-assign the next seed number."""
    with db.cursor() as c:
        row = c.execute(
            "SELECT MAX(seed) AS m FROM season_teams WHERE season_id=?", (season_id,)
        ).fetchone()
        seed = ((row["m"] or 0) + 1) if row else 1
        c.execute(
            "INSERT OR IGNORE INTO season_teams "
            "(season_id, user_id, team_name, seed) VALUES (?,?,?,?)",
            (season_id, user_id, team_name, seed),
        )
        return seed


def remove_team(season_id: int, user_id: int):
    with db.cursor() as c:
        c.execute(
            "DELETE FROM season_teams WHERE season_id=? AND user_id=?",
            (season_id, user_id),
        )


def teams(season_id: int) -> list[dict]:
    with db.cursor() as c:
        rows = c.execute(
            "SELECT * FROM season_teams WHERE season_id=? ORDER BY seed",
            (season_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def team_name_of(season_id: int, user_id: int) -> str:
    with db.cursor() as c:
        row = c.execute(
            "SELECT team_name FROM season_teams WHERE season_id=? AND user_id=?",
            (season_id, user_id),
        ).fetchone()
        return row["team_name"] if row and row["team_name"] else None


# ──────────────────────────────────────────────────────────────────────────
#  Fixture generation
# ──────────────────────────────────────────────────────────────────────────
def generate_fixtures(season_id: int, playoff_count: int = 8):
    """Clear existing fixtures and build fresh ones based on the season format.
    playoff_count: for league_playoff, how many top teams advance to playoffs."""
    season = get_season(season_id)
    if not season:
        raise ValueError("Season not found")
    fmt = season["format"]
    t = teams(season_id)
    if len(t) < 2:
        raise ValueError("Need at least 2 teams to generate fixtures")
    gsize = season["group_size"]

    with db.cursor() as c:
        c.execute("DELETE FROM fixtures WHERE season_id=?", (season_id,))

    if fmt in ("round_robin", "double_rr"):
        rounds = _circle_method(t, double=(fmt == "double_rr"))
        _insert_rounds(c, season_id, rounds, stage="league")

    elif fmt == "knockout":
        _insert_knockout(c, season_id, _seed_bracket(t))

    elif fmt == "league_playoff":
        rounds = _circle_method(t, double=False)
        _insert_rounds(c, season_id, rounds, stage="league")
        _insert_knockout_placeholder(c, season_id, t, playoff_count, prefix="PO")

    elif fmt == "groups_ko":
        groups = _split_groups(t, gsize)
        for label, members in groups.items():
            c.execute(
                "UPDATE season_teams SET group_label=? "
                "WHERE season_id=? AND user_id IN (%s)"
                % ",".join("?" * len(members)),
                (label, season_id, *[m["user_id"] for m in members]),
            )
            rounds = _circle_method(members, double=False)
            _insert_rounds(c, season_id, rounds, stage="group", group_label=label)
        # knockout placeholders — filled after group stage resolves
        _insert_knockout_placeholder(c, season_id, t, _ko_advancers(len(t), gsize),
                                     prefix="KO")

    set_season_status(season_id, "active")


def _circle_method(teams: list[dict], double: bool) -> list[list[tuple]]:
    """Standard round-robin circle method. Returns list of matchdays,
    each a list of (home_user, away_user) tuples. Byes handled if odd count."""
    arr = [t["user_id"] for t in teams]
    if len(arr) % 2 == 1:
        arr.append(None)  # bye
    n = len(arr)
    half = n // 2
    rotation = arr[:]
    rounds = []
    n_rounds = n - 1
    for r in range(n_rounds):
        md = []
        for i in range(half):
            a = rotation[i]
            b = rotation[n - 1 - i]
            if a is not None and b is not None:
                # alternate home/away across rounds for balance
                if r % 2 == 0:
                    md.append((a, b))
                else:
                    md.append((b, a))
        rounds.append(md)
        # rotate: fix first, shift the rest
        rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]
    if double:
        second = [[(b, a) for (a, b) in md] for md in rounds]
        rounds = rounds + second
    return rounds


def _split_groups(teams: list[dict], group_size: int) -> dict[str, list[dict]]:
    """Snake-distribute seeded teams across lettered groups (A, B, C...)."""
    n_groups = math.ceil(len(teams) / group_size)
    labels = [chr(ord("A") + i) for i in range(n_groups)]
    groups = {l: [] for l in labels}
    for i, t in enumerate(teams):
        g = i % n_groups
        groups[labels[g]].append(t)
    return groups


def _ko_advancers(total_teams: int, group_size: int) -> int:
    """How many teams advance from groups to a clean knockout bracket."""
    n_groups = math.ceil(total_teams / group_size)
    # top 2 per group, then round down to nearest power of 2
    adv = n_groups * 2
    p = 1
    while p * 2 <= adv:
        p *= 2
    return p


def _seed_bracket(teams: list[dict]) -> list[int]:
    """Standard single-elimination seeding (1vN, 2v(N-1)...).
    Pads with byes (0) to next power of 2. Returns a flat slot list where
    pairs are adjacent: [seed1, seedN, seed2, seedN-1, ...]."""
    seeded = [t["user_id"] for t in sorted(teams, key=lambda x: x["seed"])]
    n = len(seeded)
    # next power of 2
    size = 1
    while size < n:
        size *= 2
    # build standard bracket order via recursive seed positions
    order = _bracket_seed_positions(size)
    bracket = []
    for pos in order:
        bracket.append(seeded[pos - 1] if pos <= n else 0)  # 0 = bye
    return bracket


def _bracket_seed_positions(size: int) -> list[int]:
    """Return seed positions for a standard bracket of given size.
    e.g. size 8 -> [1,8,5,4,3,6,7,2] so top half meets bottom half."""
    if size == 1:
        return [1]
    half = size // 2
    sub = _bracket_seed_positions(half)
    result = []
    for s in sub:
        result.append(s)
        result.append(size + 1 - s)
    return result


def _knockout_rounds(bracket: list[int]) -> list[tuple[str, int]]:
    """Given a flat bracket, return list of (stage_label, teams_in_round)."""
    n = len(bracket)
    rounds = []
    while n > 1:
        label = _ko_label(n)
        rounds.append((label, n))
        n //= 2
    return rounds


def _ko_label(teams_in_round: int) -> str:
    labels = {2: "Final", 4: "Semi-Final", 8: "Quarter-Final",
              16: "Round of 16", 32: "Round of 32", 64: "Round of 64"}
    return labels.get(teams_in_round, f"Round of {teams_in_round}")


def _insert_rounds(c, season_id, rounds, stage="league", group_label=None):
    for md_idx, matches in enumerate(rounds):
        for home, away in matches:
            c.execute(
                "INSERT INTO fixtures (season_id, stage, matchday, group_label, "
                "home_user, away_user, status) VALUES (?,?,?,?,?,?,'scheduled')",
                (season_id, stage, md_idx + 1, group_label, home, away),
            )


def _insert_knockout(c, season_id, bracket: list[int]):
    """Insert a full knockout bracket with linked next_fixture pointers."""
    # round 1 matches
    label = _ko_label(len(bracket))
    match_ids = []
    for i in range(0, len(bracket), 2):
        h = bracket[i]
        a = bracket[i + 1]
        mid = _add_fixture(c, season_id, stage=label, matchday=1,
                           home=h, away=a)
        match_ids.append(mid)
    # link: winners advance to next round (placeholders, resolved on result entry)
    _link_bracket(c, season_id, match_ids, round_num=1)


def _insert_knockout_placeholder(c, season_id, all_teams, advancers: int, prefix="KO"):
    """Insert an empty knockout bracket of given size, to be seeded later
    (after league/group phase resolves). Fixtures have NULL home/away."""
    size = 1
    while size < advancers:
        size *= 2
    label = f"{prefix} " + _ko_label(size)
    match_ids = []
    for i in range(size // 2):
        mid = _add_fixture(c, season_id, stage=label, matchday=1,
                           home=None, away=None)
        match_ids.append(mid)
    _link_bracket(c, season_id, match_ids, round_num=1)


def _add_fixture(c, season_id, stage, matchday, home, away) -> int:
    cur = c.execute(
        "INSERT INTO fixtures (season_id, stage, matchday, home_user, away_user, "
        "status) VALUES (?,?,?,?,?,'scheduled') "
        "RETURNING id",
        (season_id, stage, matchday, home, away),
    )
    row = cur.fetchone()
    return row["id"] if row else c.lastrowid


def _link_bracket(c, season_id, match_ids: list[int], round_num: int):
    """Recursively create and link subsequent knockout rounds.
    Each pair of matches feeds into one next-round match."""
    if len(match_ids) <= 1:
        return
    # next round has as many teams as winners from this round = len(match_ids)
    next_teams = len(match_ids)
    label = _ko_label(next_teams)
    next_ids = []
    for i in range(0, len(match_ids), 2):
        nid = _add_fixture(c, season_id, stage=label, matchday=round_num + 1,
                           home=None, away=None)
        # link both feeder matches to this one
        c.execute("UPDATE fixtures SET next_fixture=? WHERE id=?",
                  (nid, match_ids[i]))
        if i + 1 < len(match_ids):
            c.execute("UPDATE fixtures SET next_fixture=? WHERE id=?",
                      (nid, match_ids[i + 1]))
        next_ids.append(nid)
    _link_bracket(c, season_id, next_ids, round_num + 1)


# ──────────────────────────────────────────────────────────────────────────
#  Results
# ──────────────────────────────────────────────────────────────────────────
def enter_result(fixture_id: int, home_score: int, away_score: int):
    """Record a result. If it's a knockout match, advance the winner forward."""
    with db.cursor() as c:
        fx = c.execute("SELECT * FROM fixtures WHERE id=?", (fixture_id,)).fetchone()
        if not fx:
            raise ValueError("Fixture not found")
        fx = dict(fx)
        c.execute(
            "UPDATE fixtures SET home_score=?, away_score=?, status='played', "
            "played_at=datetime('now') WHERE id=?",
            (home_score, away_score, fixture_id),
        )
        # advance winner to next_fixture in bracket
        if fx["next_fixture"]:
            winner = _match_winner(fx, home_score, away_score)
            if winner:
                _advance_winner(c, fx, winner)


def _match_winner(fx: dict, hs: int, as_: int) -> Optional[int]:
    if hs > as_:
        return fx["home_user"]
    if as_ > hs:
        return fx["away_user"]
    return None  # draw — needs admin to resolve (penalties)


def _advance_winner(c, fx: dict, winner: int):
    """Place the winner into the linked next_fixture's home or away slot."""
    nxt = c.execute("SELECT * FROM fixtures WHERE id=?", (fx["next_fixture"],)).fetchone()
    if not nxt:
        return
    nxt = dict(nxt)
    # first empty slot (home first, then away)
    if nxt["home_user"] is None:
        c.execute("UPDATE fixtures SET home_user=? WHERE id=?",
                  (winner, fx["next_fixture"]))
    elif nxt["away_user"] is None:
        c.execute("UPDATE fixtures SET away_user=? WHERE id=?",
                  (winner, fx["next_fixture"]))


def set_knockout_winner(fixture_id: int, winner_user: int):
    """Manually set a bracket winner (e.g. after penalties / draws)."""
    with db.cursor() as c:
        fx = c.execute("SELECT * FROM fixtures WHERE id=?", (fixture_id,)).fetchone()
        if not fx:
            raise ValueError("Fixture not found")
        fx = dict(fx)
        # ensure it's marked played
        c.execute("UPDATE fixtures SET status='played', played_at=datetime('now') "
                  "WHERE id=?", (fixture_id,))
        if fx["next_fixture"]:
            _advance_winner(c, fx, winner_user)


# ──────────────────────────────────────────────────────────────────────────
#  Queries
# ──────────────────────────────────────────────────────────────────────────
def fixtures(season_id: int, stage: str = None, group: str = None,
             played_only: bool = False) -> list[dict]:
    q = "SELECT * FROM fixtures WHERE season_id=?"
    params = [season_id]
    if stage:
        q += " AND stage=?"
        params.append(stage)
    if group:
        q += " AND group_label=?"
        params.append(group)
    if played_only:
        q += " AND status='played'"
    q += " ORDER BY matchday, id"
    with db.cursor() as c:
        rows = c.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def fixture_by_id(fixture_id: int) -> Optional[dict]:
    with db.cursor() as c:
        row = c.execute("SELECT * FROM fixtures WHERE id=?", (fixture_id,)).fetchone()
        return dict(row) if row else None


def upcoming_fixtures(season_id: int, limit: int = 10) -> list[dict]:
    with db.cursor() as c:
        rows = c.execute(
            "SELECT * FROM fixtures WHERE season_id=? AND status='scheduled' "
            "AND home_user IS NOT NULL AND away_user IS NOT NULL "
            "ORDER BY matchday, id LIMIT ?",
            (season_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def matchdays_played(season_id: int, stage: str = None) -> int:
    q = ("SELECT COUNT(DISTINCT matchday) AS m FROM fixtures "
         "WHERE season_id=? AND status='played'")
    params = [season_id]
    if stage:
        q += " AND stage=?"
        params.append(stage)
    with db.cursor() as c:
        row = c.execute(q, params).fetchone()
        return row["m"] if row else 0


def total_matchdays(season_id: int, stage: str = None) -> int:
    q = ("SELECT MAX(matchday) AS m FROM fixtures WHERE season_id=?")
    params = [season_id]
    if stage:
        q += " AND stage=?"
        params.append(stage)
    with db.cursor() as c:
        row = c.execute(q, params).fetchone()
        return row["m"] if row else 0


# ──────────────────────────────────────────────────────────────────────────
#  Standings (auto-computed from played fixtures)
# ──────────────────────────────────────────────────────────────────────────
def standings(season_id: int, group: str = None, stage: str = "league") -> list[dict]:
    """Compute standings from played fixtures in a league/group stage.
    Returns sorted list of dicts: team, P, W, D, L, GF, GA, GD, Pts."""
    all_teams = teams(season_id)
    if group:
        team_ids = {t["user_id"]: t for t in all_teams if t.get("group_label") == group}
    else:
        team_ids = {t["user_id"]: t for t in all_teams}
    fxs = fixtures(season_id, stage=stage, group=group, played_only=True)
    table = {}
    for uid in team_ids:
        table[uid] = {
            "user_id": uid,
            "team_name": team_ids[uid]["team_name"],
            "P": 0, "W": 0, "D": 0, "L": 0,
            "GF": 0, "GA": 0, "GD": 0, "Pts": 0,
        }
    for fx in fxs:
        h, a = fx["home_user"], fx["away_user"]
        hs, as_ = fx["home_score"], fx["away_score"]
        if h is None or a is None or hs is None or as_ is None:
            continue
        if h in table:
            _apply_result(table[h], hs, as_)
        if a in table:
            _apply_result(table[a], as_, hs)
    rows = list(table.values())
    for r in rows:
        r["GD"] = r["GF"] - r["GA"]
    rows.sort(key=lambda x: (-x["Pts"], -x["GD"], -x["GF"], x["team_name"] or ""))
    return rows


def _apply_result(row: dict, gf: int, ga: int):
    row["P"] += 1
    row["GF"] += gf
    row["GA"] += ga
    if gf > ga:
        row["W"] += 1
        row["Pts"] += 3
    elif gf == ga:
        row["D"] += 1
        row["Pts"] += 1
    else:
        row["L"] += 1


def groups(season_id: int) -> dict[str, list[dict]]:
    """Return {group_label: [standings rows]} for group-stage seasons."""
    with db.cursor() as c:
        rows = c.execute(
            "SELECT DISTINCT group_label FROM season_teams "
            "WHERE season_id=? AND group_label IS NOT NULL ORDER BY group_label",
            (season_id,),
        ).fetchall()
    return {r["group_label"]: standings(season_id, group=r["group_label"], stage="group")
            for r in rows}


# ──────────────────────────────────────────────────────────────────────────
#  Knockout bracket view
# ──────────────────────────────────────────────────────────────────────────
def bracket(season_id: int) -> list[list[dict]]:
    """Return the knockout bracket as rounds of fixture dicts.
    Only includes fixtures whose stage isn't 'league' or 'group'."""
    with db.cursor() as c:
        rows = c.execute(
            "SELECT * FROM fixtures WHERE season_id=? "
            "AND stage NOT IN ('league','group') ORDER BY matchday, id",
            (season_id,),
        ).fetchall()
        fxs = [dict(r) for r in rows]
    # group by matchday
    if not fxs:
        return []
    max_md = max(f["matchday"] for f in fxs)
    rounds = []
    for md in range(1, max_md + 1):
        rnd = [f for f in fxs if f["matchday"] == md]
        if rnd:
            rounds.append(rnd)
    return rounds


def champion(season_id: int) -> Optional[int]:
    """The winner of the final (last knockout match with a result)."""
    with db.cursor() as c:
        rows = c.execute(
            "SELECT * FROM fixtures WHERE season_id=? "
            "AND stage LIKE '%Final%' AND status='played' "
            "ORDER BY id DESC LIMIT 1",
            (season_id,),
        ).fetchall()
        if not rows:
            return None
        fx = dict(rows[0])
        if fx["home_score"] is not None and fx["away_score"] is not None:
            return _match_winner(fx, fx["home_score"], fx["away_score"])
    return None


def league_winner(season_id: int) -> Optional[int]:
    """Top of the league standings (for round_robin / double_rr)."""
    tbl = standings(season_id, stage="league")
    if tbl and tbl[0]["P"] > 0:
        return tbl[0]["user_id"]
    return None


def recent_form(season_id: int, user_id: int, limit: int = 5,
                stage: str = None, group: str = None) -> list[str]:
    """A team's last N results as 'W'/'D'/'L' (most recent first).
    Pulls from played fixtures where this team was home or away."""
    fxs = fixtures(season_id, stage=stage, group=group, played_only=True)
    results = []
    for fx in fxs:
        if fx["home_user"] != user_id and fx["away_user"] != user_id:
            continue
        hs, as_ = fx["home_score"], fx["away_score"]
        if hs is None or as_ is None:
            continue
        is_home = fx["home_user"] == user_id
        gf = hs if is_home else as_
        ga = as_ if is_home else hs
        if gf > ga:
            results.append("W")
        elif gf == ga:
            results.append("D")
        else:
            results.append("L")
    # most recent first
    results.reverse()
    return results[:limit]


def enter_result_with_penalties(fixture_id: int, home_score: int, away_score: int,
                                home_pens: int = None, away_pens: int = None):
    """Update a played fixture with penalty shootout results and advance the winner.
    The fixture must already be marked as 'played' with the score entered.
    """
    with db.cursor() as c:
        fx = c.execute("SELECT * FROM fixtures WHERE id=?", (fixture_id,)).fetchone()
        if not fx:
            raise ValueError("Fixture not found")
        fx = dict(fx)
        # Just update the penalty columns (result already entered)
        c.execute(
            "UPDATE fixtures SET home_pens=?, away_pens=? WHERE id=?",
            (home_pens, away_pens, fixture_id),
        )
        # Determine winner
        if home_pens is not None and away_pens is not None:
            winner = fx["home_user"] if home_pens > away_pens else fx["away_user"]
        else:
            winner = None

        if fx["next_fixture"] and winner:
            nxt = c.execute("SELECT * FROM fixtures WHERE id=?", (fx["next_fixture"],)).fetchone()
            if nxt:
                nxt = dict(nxt)
                if nxt["home_user"] is None:
                    c.execute("UPDATE fixtures SET home_user=? WHERE id=?", (winner, fx["next_fixture"]))
                elif nxt["away_user"] is None:
                    c.execute("UPDATE fixtures SET away_user=? WHERE id=?", (winner, fx["next_fixture"]))
