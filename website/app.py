"""
Flask web app for the FL26 Auction League.

Runs in a background thread inside main.py — same process, same SQLite DB.
For hosting: deploy this file + templates/ + static/ + the bot's data/ folder
to Fly.io, Render, or any Python host.  Set WEB_PORT env var to change port.

Routes:
  /             Dashboard (live overview)
  /standings    League table (sortable)
"""
import os
import threading
import json

# MUST be set before any oauthlib imports — it reads this at module load time.
# Without it, oauthlib blocks all HTTP (non-HTTPS) OAuth flows, including localhost.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from flask import Flask, render_template, send_file, abort, url_for, request, redirect, session, jsonify
from urllib.parse import quote
from requests_oauthlib import OAuth2Session

import database as db
import economy as E
import players as P
import league as L
from config import Config

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
    static_url_path="/static",
)
app.secret_key = Config.FLASK_SECRET_KEY

# Fix: Render terminates HTTPS at proxy. Flask sees http:// internally.
# This makes request.host_url and request.scheme return https:// correctly.
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

OAUTH_AUTH_URL = "https://discord.com/api/oauth2/authorize"
OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
OAUTH_SCOPES = ["identify", "guilds"]
API_BASE = "https://discord.com/api"


# Allow short-term caching for static files (1 min) — speeds up Render
# page loads dramatically since CSS/JS aren't re-downloaded on every click.
# 1 minute is short enough to pick up updates, long enough to help navigation.
@app.after_request
def add_cache_headers(resp):
    if request.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "public, max-age=60"
    return resp


# ===========================================================================
#  AUTH — Discord OAuth2 login
# ===========================================================================

def _oauth_session(state=None, token=None):
    # Build redirect URI dynamically — uses request host, forces HTTPS
    host = request.host_url.rstrip("/")
    # Force HTTPS (Render terminates SSL at proxy, Flask sees http://)
    if host.startswith("http://") and "localhost" not in host:
        host = "https://" + host[7:]
    redirect_uri = host + "/callback"
    return OAuth2Session(
        Config.OAUTH_CLIENT_ID,
        redirect_uri=redirect_uri,
        scope=OAUTH_SCOPES,
        state=state,
        token=token,
    )


@app.route("/login")
def login():
    oauth = _oauth_session()
    auth_url, state = oauth.authorization_url(OAUTH_AUTH_URL)
    session["oauth_state"] = state
    return redirect(auth_url)


@app.route("/callback")
def callback():
    if request.args.get("error"):
        return redirect("/")

    oauth = _oauth_session(state=session.get("oauth_state"))
    token = oauth.fetch_token(
        OAUTH_TOKEN_URL,
        client_secret=Config.OAUTH_CLIENT_SECRET,
        authorization_response=request.url,
    )
    session["oauth_token"] = token

    # fetch user info
    resp = oauth.get(f"{API_BASE}/users/@me")
    if resp.status_code != 200:
        return redirect("/")
    user = resp.json()

    session["user_id"] = str(user["id"])  # Store as STRING — JSON cookie truncates big ints
    session["username"] = user.get("username", "Unknown")
    avatar_id = user.get("avatar")
    if avatar_id:
        session["avatar_url"] = f"https://cdn.discordapp.com/avatars/{user['id']}/{avatar_id}.png?size=64"
    else:
        session["avatar_url"] = ""

    return redirect("/")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


def _current_user():
    """Returns dict with user info if logged in, else None."""
    if "user_id" not in session:
        return None
    return {
        "id": str(session["user_id"]),  # Keep as string — JS truncates big ints
        "username": session.get("username", ""),
        "avatar_url": session.get("avatar_url", ""),
    }


def _is_manager(user_id=None):
    """Check if the given user (or current session user) has a squad."""
    uid = user_id or (session.get("user_id"))
    if not uid:
        return False
    uid = int(uid)  # Convert to int for DB query
    gid = _guild_id()
    return E.squad_count(gid, uid) > 0


@app.context_processor
def inject_user():
    return dict(current_user=_current_user())


# ===========================================================================
#  GUILD RESOLUTION — "which Discord server's data shows on the website?"
#
#  Option A (AUTO): Don't set anything. The site auto-detects the guild
#          with the most squads (i.e. the active league). Works for 99%
#          of setups where you only run one league.
#
#  Option B (PIN): Set WEB_GUILD_ID in your .env file to a specific guild:
#          WEB_GUILD_ID=123456789012345678
#          (right-click your server in Discord > Copy ID, needs Dev Mode)
#
# ===========================================================================
def _guild_id() -> int:
    env = os.getenv("WEB_GUILD_ID")
    if env:
        return int(env)
    with db.cursor() as c:
        # Auto-detect: guild with most REAL squads (exclude test guilds where
        # all user_ids are >= 900000000, those are from /testseason)
        rows = c.execute(
            "SELECT guild_id, COUNT(*) as n, "
            "MIN(user_id) as min_uid "
            "FROM squads GROUP BY guild_id ORDER BY n DESC"
        ).fetchall()
        for row in rows:
            # Skip test guilds (all users have IDs >= 900000000)
            if row["min_uid"] >= 900_000_000:
                continue
            return row["guild_id"]
        # Fallback: any guild
        if rows:
            return rows[0]["guild_id"]
    return 0


# ===========================================================================
#  HELPERS
# ===========================================================================
def _team_logo_url(team_name: str) -> str:
    """Return URL to the club logo endpoint. Always returns a URL —
    the /logo/ route serves the real PNG if found, or generates a badge."""
    if not team_name:
        return ""
    return f"/logo/{quote(team_name)}"


def _face_url(player_key: str) -> str:
    """Return face image URL — ALWAYS routed through Flask (/face/{key}).
    The browser can't load SoFIFA CDN directly (hotlink protection),
    so we proxy through the /face/ route which downloads + caches."""
    if not player_key:
        return ""
    return f"/face/{quote(player_key)}"


def _money(amount: int) -> str:
    return E.money(amount)


# ===========================================================================
#  HEALTH CHECK — for UptimeRobot / Render to keep the site warm 24/7
# ===========================================================================
@app.route("/health")
def health():
    """Lightweight endpoint for UptimeRobot pings. Returns 200 + minimal JSON.
    Does NOT hit the database so it responds instantly even on slow connections."""
    return jsonify({"status": "ok"}), 200


# ===========================================================================
#  ROUTES
# ===========================================================================
@app.route("/")
def dashboard():
    gid = _guild_id()
    season = L.active_season(gid)

    # season stats
    season_stat = {"teams": 0, "played": 0, "total": 0}
    if season:
        fxs = L.fixtures(season["id"])
        season_stat = {
            "teams": len(L.teams(season["id"])),
            "played": len([f for f in fxs if f["status"] == "played"]),
            "total": len(fxs),
        }

    # top scorers (per active season)
    sid_for_stats = season["id"] if season else None
    scorers = []
    for s in E.get_top_scorers(gid, 5, season_id=sid_for_stats):
        p = P.get(s["player_key"])
        if not p:
            continue
        owner = E.get_player_owner(gid, s["player_key"])
        club = owner[1] if owner and owner[1] else p.get("club", "")
        scorers.append({
            "name": p["name"],
            "club": club,
            "goals": s["goals"],
            "face_url": _face_url(s["player_key"]),
        })

    # upcoming fixtures
    fixtures = []
    if season:
        all_fxs = L.fixtures(season["id"])
        upcoming = [f for f in all_fxs if f["status"] == "scheduled"
                    and f["home_user"] and f["away_user"]][:5]
        for f in upcoming:
            hn = L.team_name_of(season["id"], f["home_user"]) or "TBD"
            an = L.team_name_of(season["id"], f["away_user"]) or "TBD"
            fixtures.append({
                "home_name": hn, "away_name": an,
                "home_logo": _team_logo_url(hn),
                "away_logo": _team_logo_url(an),
            })

    # recent results
    results = []
    if season:
        all_fxs = L.fixtures(season["id"])
        played = [f for f in all_fxs if f["status"] == "played"][-5:]
        for f in reversed(played):
            hn = L.team_name_of(season["id"], f["home_user"]) or "?"
            an = L.team_name_of(season["id"], f["away_user"]) or "?"
            results.append({
                "home_name": hn, "away_name": an,
                "home_score": f["home_score"], "away_score": f["away_score"],
                "home_logo": _team_logo_url(hn),
                "away_logo": _team_logo_url(an),
            })

    # top signings (by price) for the rotating carousel
    top_signings = []
    with db.cursor() as c:
        rows = c.execute(
            "SELECT player_key, winner_id, final_price FROM auction_history "
            "WHERE guild_id=? AND winner_id IS NOT NULL "
            "ORDER BY final_price DESC LIMIT 8",
            (gid,),
        ).fetchall()
    for r in rows:
        pdata = P.get(r["player_key"])
        if not pdata:
            continue
        tn = E.get_team_name(gid, r["winner_id"]) or "Unknown"
        top_signings.append({
            "name": pdata["name"],
            "team": tn,
            "position": pdata.get("position", ""),
            "price": _money(r["final_price"]),
            "face_url": _face_url(r["player_key"]),
            "logo_url": _team_logo_url(tn),
        })

    # recent 5 sales for the list
    recent_sales_list = []
    for s in E.recent_sales(gid, 5):
        tn = E.get_team_name(gid, s["winner_id"]) or "Unknown"
        recent_sales_list.append({
            "name": s["name"],
            "team": tn,
            "position": s.get("position", ""),
            "price": _money(s["price"]),
            "face_url": _face_url(s.get("key", "")),
        })

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        season=season,
        season_stat=season_stat,
        scorers=scorers,
        fixtures=fixtures,
        results=results,
        top_signings=top_signings,
        recent_sales_list=recent_sales_list,
    )


@app.route("/standings")
def standings():
    gid = _guild_id()
    season = L.active_season(gid)

    rows = []
    if season:
        tms = L.teams(season["id"])
        has_groups = any(t.get("group_label") for t in tms)
        if has_groups:
            raw_rows = L.standings(season["id"], stage="group")
        else:
            raw_rows = L.standings(season["id"], stage="league")

        for r in raw_rows:
            team_name = r.get("team_name") or ""
            form = L.recent_form(season["id"], r["user_id"], limit=5) if r["P"] > 0 else []
            rows.append({
                **r,
                "logo_url": _team_logo_url(team_name),
                "form": form,
            })

    return render_template(
        "standings.html",
        active_page="standings",
        season=season,
        rows=rows,
    )


@app.route("/squads")
def squads():
    """List all managers who have players. Logged-in managers get a My Squad pin."""
    gid = _guild_id()
    with db.cursor() as c:
        rows = c.execute(
            "SELECT DISTINCT user_id FROM squads WHERE guild_id=?",
            (gid,),
        ).fetchall()

    managers = []
    for r in rows:
        uid = r["user_id"]
        team_name = E.get_team_name(gid, uid) or f"Manager {uid}"
        squad = E.get_squad(gid, uid)
        sv = E.squad_value(squad)
        bal = E.get_balance(gid, uid)
        pr = E.power_rating(gid, uid)
        managers.append({
            "user_id": uid,
            "team_name": team_name,
            "logo_url": _team_logo_url(team_name),
            "squad_size": len(squad),
            "squad_value": _money(sv),
            "budget": _money(bal),
            "net_worth": _money(sv + bal),
            "power_rating": pr,
            "_net_raw": sv + bal,
        })

    managers.sort(key=lambda m: m["_net_raw"], reverse=True)
    for m in managers:
        m.pop("_net_raw", None)

    # My Squad: only if Discord-logged-in AND they own players in this guild
    my_squad = None
    cu = _current_user()
    if cu:
        try:
            my_uid = int(cu["id"])
        except (TypeError, ValueError):
            my_uid = None
        if my_uid is not None:
            for m in managers:
                if int(m["user_id"]) == my_uid:
                    my_squad = m
                    break

    return render_template(
        "squads.html",
        active_page="squads",
        managers=managers,
        my_squad=my_squad,
    )


@app.route("/players")
def players_page():
    """Browse draft players: queue + sold in this guild (not the entire FL26 DB)."""
    gid = _guild_id()

    # Queue (still available) + anyone currently owned in this guild (sold)
    queued_keys = set(E.queue_list(gid))
    sold_keys = E.sold_player_keys(gid)

    # Full draft pool for this server = queue ∪ sold
    draft_keys = queued_keys | sold_keys

    if draft_keys:
        all_players = [p for p in P.all_players() if p["key"] in draft_keys]
    else:
        # Fallback if nothing queued/sold yet: empty list (or optional full DB)
        all_players = []

    sold = sold_keys  # set of keys

    # Watchlist (optional — keep if you wired watchlist)
    cu = _current_user()
    watched = set()
    if cu:
        try:
            watched = set(E.watch_list(gid, int(cu["id"])))
        except Exception:
            watched = set()

    # filters from query params
    q = (request.args.get("q") or "").strip()
    pos = (request.args.get("pos") or "").strip()
    status = (request.args.get("status") or "").strip()
    min_ovr = request.args.get("min_ovr", type=int)
    club_filter = (request.args.get("club") or "").strip()
    nation = (request.args.get("nation") or "").strip()
    max_age = request.args.get("max_age", type=int)

    results = []
    for p in all_players:
        # search filter
        if q:
            if (
                q.lower() not in p["name"].lower()
                and q.lower() not in p.get("club", "").lower()
            ):
                continue
        # position filter
        if pos and pos != "ALL":
            if p.get("group", "") != pos:
                continue
        # status filter — THIS is what restores sold visibility
        is_sold = p["key"] in sold
        if status == "sold" and not is_sold:
            continue
        if status == "unsold" and is_sold:
            continue
        # rating filter
        if min_ovr and p["ovr"] < min_ovr:
            continue
        # club filter
        if club_filter and club_filter.lower() not in p.get("club", "").lower():
            continue
        # nation filter
        if nation and p.get("country", "") != nation:
            continue
        # age filter
        if max_age:
            try:
                if int(p.get("age", 99)) > max_age:
                    continue
            except (ValueError, TypeError):
                continue

        owner_team = None
        if is_sold:
            owner = E.get_player_owner(gid, p["key"])
            if owner:
                owner_team = owner[1]

        try:
            value_str = _money(
                P.market_value(p["ovr"], is_icon=P.is_icon(p))
            )
        except Exception:
            value_str = _money(p.get("value") or 0)

        results.append({
            "key": p["key"],
            "name": p["name"],
            "ovr": p["ovr"],
            "position": p.get("position", ""),
            "group": p.get("group", ""),
            "club": p.get("club", ""),
            "country": p.get("country", ""),
            "face_url": _face_url(p["key"]),
            "value": value_str,
            "is_sold": is_sold,
            "owner_team": owner_team,
            "watching": p["key"] in watched,
        })

    # sort: unsold first? or OVR desc — keep classic OVR desc
    filtered_count = len(results)
    results.sort(key=lambda x: x["ovr"], reverse=True)

    # pagination
    per_page = 30
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1
    total_pages = max(1, (filtered_count + per_page - 1) // per_page)
    start = (page - 1) * per_page
    page_results = results[start:start + per_page]

    from urllib.parse import urlencode
    filter_params = {}
    for k in ("q", "pos", "status", "min_ovr", "club", "nation", "max_age"):
        v = request.args.get(k)
        if v and str(v) != "0" and str(v) != "ALL":
            filter_params[k] = v
    filter_qs = urlencode(filter_params)

    nations = sorted(
        set(p.get("country", "") for p in all_players if p.get("country"))
    )

    return render_template(
        "players.html",
        active_page="players",
        players=page_results,
        q=q,
        pos=pos,
        status=status,
        min_ovr=min_ovr or 0,
        club=club_filter,
        nation=nation,
        max_age=max_age or 0,
        nations=nations,
        total_count=len(all_players),
        filtered_count=filtered_count,
        shown_count=min(len(page_results), per_page),
        page=page,
        total_pages=total_pages,
        filter_qs=filter_qs,
        is_logged_in=bool(cu),
        watch_count=len(watched),
        watched_keys=list(watched),
    )

@app.route("/squad/<int:user_id>")
def squad_detail(user_id):
    """View a specific manager's squad."""
    gid = _guild_id()
    team_name = E.get_team_name(gid, user_id) or f"Manager {user_id}"
    squad = E.get_squad(gid, user_id)
    bal = E.get_balance(gid, user_id)
    sv = E.squad_value(squad)
    pr = E.power_rating(gid, user_id)

    _s = L.active_season(gid)
    _sid = _s["id"] if _s else None

    # starting XI formation + bench
    import formations as FM
    # allow formation preview via query param (doesn't save until "Save")
    preview_formation = request.args.get("formation")
    formation_name = preview_formation or E.get_formation(gid, user_id)
    if formation_name not in FM.FORMATIONS:
        formation_name = FM.DEFAULT_FORMATION
    formation = FM.get_formation(formation_name)
    lineup, _ = E.get_lineup(gid, user_id)
    all_slots = FM.all_slots(formation)

    # Build a lookup: slot_index -> player
    lineup_map = {}
    used_keys = set()
    for slot_data, player in lineup:
        if slot_data and player:
            lineup_map[slot_data["index"]] = player
            used_keys.add(player["key"])

    # Build pitch rows from formation, attaching players by slot index
    slot_counter = 0
    pitch_rows = []
    for row in formation["rows"]:
        pr_data = {"y": row["y"], "players": []}
        for slot in row["slots"]:
            idx = slot_counter
            slot_counter += 1
            player = lineup_map.get(idx)
            if player:
                pr_data["players"].append({
                    "pos": slot["pos"],
                    "x": slot["x"],
                    "name": player["name"],
                    "ovr": player["ovr"],
                    "face_url": _face_url(player["key"]),
                    "key": player["key"],
                    "slot": idx,
                })
            else:
                pr_data["players"].append({"pos": slot["pos"], "x": slot["x"], "name": None, "slot": idx})
        pitch_rows.append(pr_data)

    # Build player roster for JS (all squad players with their info)
    roster = {}
    for p in squad:
        roster[p["key"]] = {
            "name": p["name"],
            "ovr": p["ovr"],
            "pos": p.get("position", ""),
            "group": p.get("group", ""),
            "face_url": _face_url(p["key"]),
        }

    # Build formation data for JS
    import formations as FM
    formations_data = {}
    for fname in FM.FORMATION_NAMES:
        f = FM.get_formation(fname)
        slots = []
        for row in f["rows"]:
            for s in row["slots"]:
                slots.append({"pos": s["pos"], "x": s["x"], "y": row["y"]})
        formations_data[fname] = slots

    # Build initial lineup state: {slot_index: player_key}
    lineup_state = {}
    for slot_data, player in lineup:
        if slot_data and player:
            lineup_state[slot_data["index"]] = player["key"]

    # Bench = squad minus starting XI
    used_keys = set(lineup_state.values())
    bench_keys = [p["key"] for p in squad if p["key"] not in used_keys]

    groups = {"GK": [], "DEF": [], "MID": [], "FWD": []}
    for p in squad:
        groups.setdefault(p.get("group", "MID"), []).append(p)
    for g in groups:
        groups[g].sort(key=lambda p: p["ovr"], reverse=True)

    import json as _json
    import tactics as T

    # Tactics data for the tactics editor
    tactics_data = E.get_tactics(gid, user_id)

    # Build choice lists for the JS editor
    def _choices(group):
        return [{"value": k, "label": v["label"], "desc": v["desc"]} for k, v in group.items()]

    tactics_config = {
        "attack_style": _choices(T.ATTACK_STYLE),
        "build_up": _choices(T.BUILD_UP),
        "attack_area": _choices(T.ATTACK_AREA),
        "positioning": _choices(T.POSITIONING),
        "defensive_style": _choices(T.DEFENSIVE_STYLE),
        "containment_area": _choices(T.CONTAINMENT_AREA),
        "pressuring": _choices(T.PRESSURING),
        "sliders": {k: {"label": v["label"], "desc": v["desc"],
                         "min": v["min"], "max": v["max"]} for k, v in T.SLIDERS.items()},
        "adv_attack": _choices(T.ADV_ATTACK),
        "adv_defence": _choices(T.ADV_DEFENCE),
    }

    return render_template(
        "squad_detail.html",
        active_page="squads",
        team_name=team_name,
        logo_url=_team_logo_url(team_name),
        user_id=user_id,
        squad_size=len(squad),
        squad_value=_money(sv),
        budget=_money(bal),
        power_rating=pr,
        formation_name=formation_name,
        formations_list=FM.FORMATION_NAMES,
        formations_json=_json.dumps(formations_data),
        roster_json=_json.dumps(roster),
        lineup_json=_json.dumps(lineup_state),
        bench_json=_json.dumps(bench_keys),
        groups=groups,
        face_url=_face_url,
        is_owner=_current_user() and str(_current_user()["id"]) == str(user_id),
        tactics_json=_json.dumps(tactics_data),
        tactics_config_json=_json.dumps(tactics_config),
    )


@app.route("/player/<path:player_key>")
def player_detail(player_key):
    """View a player's full detail card."""
    gid = _guild_id()
    p = P.get(player_key)
    if not p:
        abort(404)

    owner = E.get_player_owner(gid, player_key)
    owner_team = owner[1] if owner and owner[1] else None

    _s = L.active_season(gid)
    _sid = _s["id"] if _s else None
    stats = E.get_player_stats(gid, player_key, season_id=_sid)

    all_stats = p.get("all_stats", {})
    is_gk = p.get("position") == "GK"

    if is_gk:
        categories = [
            ("Goalkeeping", [("GK Awareness", "GKAwareness"), ("GK Catching", "GKCatching"),
                             ("GK Clearing", "GKClearing"), ("GK Reflexes", "GKReflexes"),
                             ("GK Reach", "GKReach")]),
            ("Physical", [("Speed", "Speed"), ("Acceleration", "Acceleration"),
                          ("Physical Contact", "PhysicalContact"), ("Stamina", "Stamina"),
                          ("Balance", "Balance"), ("Jump", "Jump")]),
            ("Distribution", [("Low Pass", "LowPass"), ("Lofted Pass", "LoftedPass"),
                              ("Kicking Power", "KickingPower"), ("Curl", "Curl")]),
        ]
    else:
        categories = [
            ("Pace", [("Speed", "Speed"), ("Acceleration", "Acceleration")]),
            ("Shooting", [("Finishing", "Finishing"), ("Heading", "Heading"),
                          ("Place Kicking", "PlaceKicking"), ("Kicking Power", "KickingPower")]),
            ("Passing", [("Low Pass", "LowPass"), ("Lofted Pass", "LoftedPass"), ("Curl", "Curl")]),
            ("Dribbling", [("Dribbling", "Dribbling"), ("Ball Control", "BallControl"),
                           ("Tight Possession", "TightPossession"), ("Balance", "Balance")]),
            ("Defending", [("Defensive Awareness", "DefensiveAwareness"),
                           ("Ball Winning", "BallWinning"), ("Aggression", "Aggression")]),
            ("Physical", [("Physical Contact", "PhysicalContact"), ("Stamina", "Stamina"),
                          ("Jump", "Jump")]),
        ]

    return render_template(
        "player_detail.html",
        active_page="",
        player=p,
        owner_team=owner_team,
        stats=stats,
        all_stats=all_stats,
        categories=categories,
        face_url=_face_url(player_key),
        logo_url=_team_logo_url,
    )


@app.route("/fixtures")
def fixtures_page():
    """Match schedule with matchday navigation."""
    gid = _guild_id()
    season = L.active_season(gid)

    matchdays = []
    selected_md = None

    if season:
        all_fxs = L.fixtures(season["id"])
        # build matchday groups
        md_map = {}
        for f in all_fxs:
            if f["home_user"] is not None or f["away_user"] is not None:
                md_map.setdefault(f["matchday"], []).append(f)

        if not md_map:
            # No fixtures yet — render empty state
            return render_template(
                "fixtures.html",
                active_page="fixtures",
                season=season,
                matchdays=[],
                selected_md=None,
            )

        # get selected matchday from query, or default to next unplayed
        selected_md = request.args.get("md", type=int)
        if not selected_md:
            unplayed = sorted(md for md, fxs in md_map.items()
                              if any(f["status"] == "scheduled" for f in fxs))
            selected_md = unplayed[0] if unplayed else sorted(md_map.keys())[-1]

        for md in sorted(md_map.keys()):
            fxs_data = []
            for f in md_map[md]:
                hn = L.team_name_of(season["id"], f["home_user"]) if f["home_user"] else "TBD"
                an = L.team_name_of(season["id"], f["away_user"]) if f["away_user"] else "TBD"
                grp = f.get("group_label")
                fxs_data.append({
                    "id": f["id"],
                    "home_name": hn,
                    "away_name": an,
                    "home_score": f["home_score"],
                    "away_score": f["away_score"],
                    "status": f["status"],
                    "stage": f.get("stage", ""),
                    "group": grp,
                    "home_logo": _team_logo_url(hn) if hn != "TBD" else "",
                    "away_logo": _team_logo_url(an) if an != "TBD" else "",
                    "home_pens": f.get("home_pens"),
                    "away_pens": f.get("away_pens"),
                })
            played = sum(1 for f in md_map[md] if f["status"] == "played")
            total = len(md_map[md])
            matchdays.append({
                "md": md,
                "played": played,
                "total": total,
                "fixtures": fxs_data,
                "is_selected": md == selected_md,
            })

    return render_template(
        "fixtures.html",
        active_page="fixtures",
        season=season,
        matchdays=matchdays,
        selected_md=selected_md,
    )


@app.route("/bracket")
def bracket_page():
    """Knockout bracket — HTML convergence layout with connector lines."""
    gid = _guild_id()
    season = L.active_season(gid)

    left_cols = []
    right_cols = []
    final_match = None
    champion = None

    if season:
        raw = L.bracket(season["id"])
        if raw:
            pre = raw
            if len(raw[-1]) == 1:
                final_match = raw[-1][0]
                pre = raw[:-1]

            # split each round into left/right halves
            left_raw = []
            right_raw = []
            for rnd in pre:
                half = len(rnd) // 2
                left_raw.append(list(rnd[:half]))
                right_raw.append(list(rnd[half:]))

            def _md(f):
                hn = L.team_name_of(season["id"], f["home_user"]) if f["home_user"] else None
                an = L.team_name_of(season["id"], f["away_user"]) if f["away_user"] else None
                hs = f["home_score"]
                as_ = f["away_score"]
                played = f["status"] == "played"
                hw = played and hs is not None and as_ is not None and hs > as_
                aw = played and hs is not None and as_ is not None and as_ > hs
                hp = f.get("home_pens")
                ap = f.get("away_pens")
                if played and hs == as_ and hp is not None and ap is not None:
                    hw, aw = hp > ap, ap > hp
                return {
                    "home_name": hn or "TBD", "away_name": an or "TBD",
                    "home_score": hs, "away_score": as_,
                    "played": played, "home_winner": hw, "away_winner": aw,
                    "home_pens": hp, "away_pens": ap,
                    "home_logo": _team_logo_url(hn) if hn else "",
                    "away_logo": _team_logo_url(an) if an else "",
                }

            def _build_cols(raw_cols):
                cols = []
                for rnd in raw_cols:
                    matches = [_md(f) for f in rnd]
                    cols.append({
                        "name": rnd[0].get("stage", "") if rnd else "",
                        "matches": matches,
                    })
                return cols

            left_cols = _build_cols(left_raw)
            right_cols = _build_cols(list(reversed(right_raw)))

            if final_match:
                final_match = _md(final_match)

            champ_uid = L.champion(season["id"])
            if champ_uid:
                champion = L.team_name_of(season["id"], champ_uid)

    return render_template(
        "bracket.html",
        active_page="bracket",
        season=season,
        left_cols=left_cols,
        right_cols=right_cols,
        final_match=final_match,
        champion=champion,
    )


# ===========================================================================
#  LINEUP API — drag & drop save, formation switch, webhook
# ===========================================================================
@app.route("/api/lineup/<int:target_uid>", methods=["POST"])
def save_lineup(target_uid):
    """Save lineup overrides + formation + tactics for a manager.
    Only the logged-in owner of the squad can save."""
    try:
        user = _current_user()
        if not user:
            return jsonify({"error": "Not logged in. Click Login first."}), 401
        if str(user["id"]) != str(target_uid):
            return jsonify({"error": "Not authorized."}), 403

        data = request.json
        if not data:
            return jsonify({"error": "No data"}), 400

        gid = _guild_id()

        # change formation if requested
        new_formation = data.get("formation")
        if new_formation:
            import formations as FM
            if new_formation in FM.FORMATIONS:
                E.set_formation(gid, target_uid, new_formation)

        # clear existing overrides then apply new ones
        E.clear_all_overrides(gid, target_uid)

        overrides = data.get("overrides", {})
        for slot_idx_str, player_key in overrides.items():
            try:
                slot_idx = int(slot_idx_str)
                if player_key and player_key != "empty":
                    E.set_lineup_slot(gid, target_uid, slot_idx, player_key)
            except (ValueError, Exception):
                pass

        # save tactics if sent in the same request
        tactics_data = data.get("tactics")
        if tactics_data:
            E.save_tactics(gid, target_uid, tactics_data)

        # build webhook with lineup + tactics
        team_name = E.get_team_name(gid, target_uid) or "Unknown"
        import formations as FM
        formation_name_saved = new_formation or E.get_formation(gid, target_uid)
        formation = FM.get_formation(formation_name_saved)
        all_slots = FM.all_slots(formation)

        changes_detailed = []
        for slot_idx_str, player_key in overrides.items():
            try:
                slot_idx = int(slot_idx_str)
                if player_key and player_key != "empty":
                    p = P.get(player_key)
                    if p:
                        pos_code = all_slots[slot_idx]["pos"] if slot_idx < len(all_slots) else f"Slot {slot_idx+1}"
                        changes_detailed.append(f"{pos_code}: {p['name']}")
            except (ValueError, Exception):
                pass

        # build tactics summary for webhook
        import tactics as T
        tac = E.get_tactics(gid, target_uid)
        tac_lines = []
        tac_lines.append(f"Formation: **{FM.formation_label(formation_name_saved)}**")
        tac_lines.append(f"Style: **{T.label(T.ATTACK_STYLE, tac['attacking_style'])}** / **{T.label(T.DEFENSIVE_STYLE, tac['defensive_style'])}**")
        tac_lines.append(f"Build-up: **{T.label(T.BUILD_UP, tac['build_up'])}** / Press: **{T.label(T.PRESSURING, tac['pressuring'])}**")
        for label_txt, slot_key, group in [
            ("Atk 1", "adv_attack_1", T.ADV_ATTACK),
            ("Atk 2", "adv_attack_2", T.ADV_ATTACK),
            ("Def 1", "adv_defence_1", T.ADV_DEFENCE),
            ("Def 2", "adv_defence_2", T.ADV_DEFENCE),
        ]:
            val = tac[slot_key]
            if val != "off":
                tac_lines.append(f"{label_txt}: **{T.label(group, val)}**")

        webhook_desc = "\n".join(changes_detailed[:11])
        if tac_lines:
            webhook_desc += "\n\n**Tactics:**\n" + "\n".join(tac_lines)

        _send_webhook(f"**{team_name}** - Squad Updated", webhook_desc)

        return jsonify({"ok": True, "changes": len(changes_detailed)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/formations")
def formations_list():
    """Return all available formations."""
    import formations as FM
    return jsonify({
        "formations": FM.FORMATION_NAMES,
        "default": FM.DEFAULT_FORMATION,
    })


@app.route("/api/tactics/<int:target_uid>", methods=["GET", "POST"])
def tactics_api(target_uid):
    """Get or save a manager's FL26 tactics."""
    try:
        if request.method == "GET":
            return jsonify(E.get_tactics(_guild_id(), target_uid))

        user = _current_user()
        if not user:
            return jsonify({"error": "Not logged in."}), 401
        if str(user["id"]) != str(target_uid):
            return jsonify({"error": "Not authorized."}), 403
        data = request.json
        if not data:
            return jsonify({"error": "No data"}), 400
        E.save_tactics(_guild_id(), target_uid, data)
        return jsonify({"ok": True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/watchlist/<path:player_key>", methods=["POST", "DELETE"])
def watchlist_api(player_key):
    user = _current_user()
    if not user:
        return jsonify({"error": "Not logged in."}), 401
    gid = _guild_id()
    uid = int(user["id"])
    if request.method == "POST":
        E.watch_add(gid, uid, player_key)
        return jsonify({"ok": True, "watching": True})
    else:
        E.watch_remove(gid, uid, player_key)
        return jsonify({"ok": True, "watching": False})


@app.route("/watchlist")
def watchlist_page():
    user = _current_user()
    gid = _guild_id()
    if not user:
        return redirect("/login")
    keys = E.watch_list(gid, int(user["id"]))
    players = []
    sold = E.sold_player_keys(gid)
    for k in keys:
        p = P.get(k)
        if not p:
            continue
        is_sold = k in sold
        owner_team = None
        if is_sold:
            owner = E.get_player_owner(gid, k)
            if owner:
                owner_team = owner[1]
        try:
            value_str = _money(P.market_value(p["ovr"], is_icon=P.is_icon(p)))
        except Exception:
            value_str = _money(p.get("value") or 0)
        players.append({
            "key": p["key"], "name": p["name"], "ovr": p["ovr"],
            "position": p.get("position", ""), "club": p.get("club", ""),
            "country": p.get("country", ""), "face_url": _face_url(p["key"]),
            "value": value_str, "is_sold": is_sold, "owner_team": owner_team,
        })
    return render_template("watchlist.html", active_page="watchlist", players=players)


def _send_webhook(title, description):
    """POST a message to the configured Discord webhook."""
    url = Config.WEBHOOK_URL
    if not url:
        return
    try:
        import requests
        payload = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": 0xFFBA46,
            }]
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[!] Webhook failed: {e}")


@app.route("/scorers")
def scorers():
    """Full golden boot race page."""
    gid = _guild_id()
    season = L.active_season(gid)
    sid = season["id"] if season else None

    raw_scorers = E.get_top_scorers(gid, 15, season_id=sid)
    scorers = []
    for s in raw_scorers:
        p = P.get(s["player_key"])
        if not p:
            continue
        owner = E.get_player_owner(gid, s["player_key"])
        club = owner[1] if owner and owner[1] else p.get("club", "")
        scorers.append({
            "name": p["name"],
            "club": club,
            "club_logo": _team_logo_url(club),
            "country": p.get("country", ""),
            "goals": s["goals"],
            "assists": s["assists"],
            "motm": s["motm"],
            "matches": s["matches"],
            "face_url": _face_url(s["player_key"]),
        })

    sub = f"Season {season['number']}" if season else "All Time"
    return render_template(
        "scorers.html",
        active_page="scorers",
        season=season,
        subtitle=sub,
        scorers=scorers,
    )


@app.route("/logo/<path:team_name>")
def logo(team_name):
    """Serve a club logo PNG from assets/logos/ (fuzzy matched).
    Falls back to generating a badge PNG if no real logo file exists."""
    import club_logos as CL
    from io import BytesIO
    path = CL._find_logo_file(team_name)
    if path:
        # MUST use absolute path — Flask resolves relative paths against the
        # app root (website/), not the CWD. This was the image bug.
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return send_file(abs_path, mimetype="image/png")
    # Fallback: generate a badge on the fly and serve it
    badge = CL.get_club_logo(team_name, 64)
    buf = BytesIO()
    badge.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/face/<path:player_key>")
def face(player_key):
    """Serve a player's face image. Downloads from SoFIFA CDN server-side
    (browsers can't hotlink sofifa.net), caches locally. Falls back to
    generated silhouette if no face URL exists."""
    from io import BytesIO
    from PIL import Image, ImageDraw

    url = E.get_face_url(player_key)
    if url:
        # Use the bot's existing face-fetch+cache (data/faces/)
        from squad_card import fetch_face
        img = fetch_face(url)
        if img:
            buf = BytesIO()
            img.convert("RGBA").save(buf, "PNG")
            buf.seek(0)
            return send_file(buf, mimetype="image/png")

    # No face URL or download failed — generate silhouette placeholder
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = 32
    d.ellipse([cx - 12, 8, cx + 12, 32], fill=(40, 40, 50, 255))
    d.ellipse([cx - 22, 30, cx + 22, 70], fill=(40, 40, 50, 255))
    buf = BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ===========================================================================
#  LAUNCH (called from main.py)
# ===========================================================================
def run_in_thread(port=5000):
    """Start Flask in a daemon thread so it doesn't block the bot."""
    # Ensure schema exists — when the website runs standalone (e.g. on Render
    # without the bot), nothing else calls init_db(). Idempotent, safe to call
    # even when the bot already did it.
    try:
        db.init_db()
    except Exception as e:
        print(f"[!] init_db failed in website: {e}")
    def _run():
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    print(f"[✓] Website running at http://localhost:{port}")
    return t
