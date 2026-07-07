"""
Emoji registry — the ONE place to wire your custom server emojis.

HOW IT WORKS
------------
1. Upload the generated emoji PNGs (emojis/discord_ready/*.png) to your Discord
   server:  Server Settings -> Emoji -> Upload.
2. For each one, type \\:emojiname: in Discord (e.g. \\:greencheck:). — it will
   expand to something like <:greencheck:123456789012345678>. Copy that.
3. Paste it into CUSTOM below. Done — the whole bot uses it everywhere.

Leave a slot as None and the bot falls back to the default unicode emoji.
"""

import os

# ---------------------------------------------------------------------------
# Paste your custom emoji strings here once you've uploaded them.
# Example:  "check": "<:greencheck:123456789012345678>",
# ---------------------------------------------------------------------------
CUSTOM = {
    # --- UI / navigation ---
    "check":      "<:greentick:1522684972811419920>",   # ✅ green tick
    "x":          "<:redcross:1522684978427859055>",     # ❌ red cross
    "warning":    None,   # replaces ⚠️
    "stop":       None,   # replaces 🛑
    "no_entry":   None,   # replaces ⛔
    "diamond":    None,   # replaces 🔹
    "arrow_left": None,   # replaces ◀
    "arrow_right":None,   # replaces ▶
    "gear":       None,   # replaces ⚙️
    "broom":      None,   # replaces 🧹
    "hourglass":  None,   # replaces ⏳
    "stopwatch":  None,   # replaces ⏱
    "manager":    "<:silhouette:1522683662368243753>",  # manager silhouette (titles)

    # --- Auction drama ---
    "money":      "<:coin:1522683657251459262>",   # 💰 coin
    "fire":       None,   # 🔥
    "sold":       None,   # 🎉
    "bolt":       None,   # ⚡
    "up_arrow":   None,   # ⬆
    "pen":        None,   # ✍️
    "alarm":      None,   # ⏰
    "medal":      None,   # 🏅
    "money_wings":None,   # 💸
    "smile":      None,   # 🙂

    # --- Positions / team ---
    "stadium":    None,   # 🏟️
    "gloves":     None,   # 🧤
    "shield":     None,   # 🛡️
    "target":     None,   # 🎯
    "chair":      None,   # 🪑
    "chart":      None,   # 📊

    # --- Commands ---
    "clipboard":  None,   # 📋
    "globe":      None,   # 🌍
    "trophy":     "<:championtrophy:1522684262929793144>",   # 🏆 champion trophy
    "scroll":     None,   # 📜
    "inbox":      None,   # 📥
    "outbox":     None,   # 📤
    "recycle":    None,   # ♻️
    "ball":       None,   # ⚽

    # --- Leaderboard medals ---
    "gold":       "<:gold_medal:1522683660531138671>",   # 🥇
    "silver":     "<:silver_medal:1522683664998338761>", # 🥈
    "bronze":     "<:bronze_medal:1522683811610099903>", # 🥉

    # --- Match stats (YOUR uploaded emojis) ---
    "stat_goals":       "<:stat_goals:1522622093253021726>",
    "stat_assists":     "<:stat_assists:1522622075049607308>",
    "stat_tackles":     "<:stat_tackles:1522622104753803274>",
    "stat_saves":       "<:stat_saves:1522622102593732662>",
    "stat_appearances": "<:stat_appearances:1522622055059685426>",
    "stat_yellow":      "<:stat_yellow:1522622109103296584>",
    "stat_red":         "<:stat_red:1522622100622545086>",
    "stat_motm":        "<:stat_motm:1522622098487509032>",
    "stat_clean":       "<:stat_clean_sheet:1522622087846428822>",
    "stat_win":         "<:stat_win:1522622107018596459>",
    "stat_draw":        "<:stat_draw:1522622090111488022>",
    "stat_loss":        "<:stat_loss:1522622095899492372>",
}

# Unicode fallbacks — used when a CUSTOM slot is None
_DEFAULTS = {
    "check": "✅", "x": "❌", "warning": "⚠️", "stop": "🛑", "no_entry": "⛔",
    "diamond": "🔹", "arrow_left": "◀", "arrow_right": "▶", "gear": "⚙️",
    "broom": "🧹", "hourglass": "⏳", "stopwatch": "⏱️",
    "money": "💰", "fire": "🔥", "sold": "🎉", "bolt": "⚡", "up_arrow": "⬆️",
    "pen": "✍️", "alarm": "⏰", "medal": "🏅", "money_wings": "💸", "smile": "🙂",
    "stadium": "🏟️", "gloves": "🧤", "shield": "🛡️", "target": "🎯",
    "chair": "🪑", "chart": "📊", "clipboard": "📋", "globe": "🌍",
    "trophy": "🏆", "scroll": "📜", "inbox": "📥", "outbox": "📤",
    "recycle": "♻️", "ball": "⚽", "gold": "🥇", "silver": "🥈", "bronze": "🥉",
    "manager": "👤",
    "stat_goals": "⚽", "stat_assists": "🅰️", "stat_tackles": "🛡️",
    "stat_saves": "🧤", "stat_appearances": "🎽", "stat_yellow": "🟨",
    "stat_red": "🟥", "stat_motm": "⭐", "stat_clean": "🧱",
    "stat_win": "🟢", "stat_draw": "⚪", "stat_loss": "🔴",
}


def e(key: str) -> str:
    """Return the custom emoji for a slot, or its unicode fallback."""
    return CUSTOM.get(key) or _DEFAULTS.get(key, "")


# ===========================================================================
#  CLUB EMOJIS  — paste your club emoji IDs here
#
#  Key   = club name (any spelling — fuzzy matched at runtime)
#  Value = Discord emoji string  e.g.  "<:realmadrid:123456789>"
#
#  Fuzzy matching strips FC/CF/AC suffixes and accents, so "Real Madrid CF"
#  in the data will match a "Real Madrid" key here.  Leave blank/empty to
#  skip (no emoji shown for that club).
# ===========================================================================
CLUB_EMOJIS = {
    # --- Premier League ---
    "Arsenal":           "",
    "Chelsea":           "",
    "Liverpool":         "",
    "Manchester City":   "",
    "Manchester United": "",
    "Tottenham":         "",

    # --- La Liga ---
    "Real Madrid":       "<:realmadridcf:1522669663513870436>",
    "Barcelona":         "<:barcelona:1522669626310524958>",
    "Atletico Madrid":   "",

    # --- Bundesliga ---
    "Bayern Munich":     "",
    "Dortmund":          "",

    # --- Serie A ---
    "Juventus":          "",
    "AC Milan":          "",
    "Inter Milan":       "",
    "Napoli":            "",

    # --- Ligue 1 ---
    "PSG":               "",
}

# ── fuzzy matching (mirrors club_logos._core_slug logic) ──────────────────
import unicodedata as _ud

_STRIP_SUFFIXES = [
    "fc", "cf", "ac", "sc", "afc", "sl", "ssc", "ss", "bc", "rc",
    "cd", "sv", "vfl", "vfb", "tsg", "rb", "as", "usc",
]
_CLUB_ALIASES = {
    "munchen": "munich",
    "koln": "cologne",
    "monchengladbach": "gladbach",
    "mainz-05": "mainz",
}

_club_cache = {}


def _club_slug(name):
    nfkd = _ud.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    out = "".join(ch if ch.isalnum() else "-" for ch in ascii_only.lower())
    slug = "-".join(p for p in out.split("-") if p)
    for native, eng in _CLUB_ALIASES.items():
        if native in slug:
            slug = slug.replace(native, eng)
    parts = slug.split("-")
    while parts and parts[-1] in _STRIP_SUFFIXES:
        parts.pop()
    while parts and parts[0] in _STRIP_SUFFIXES:
        parts.pop(0)
    return "-".join(parts)


def _build_club_index():
    """Pre-compute a core-slug → emoji map once."""
    idx = {}
    for name, emoji in CLUB_EMOJIS.items():
        if not emoji:
            continue
        core = _club_slug(name)
        idx[core] = emoji
    return idx


def club(team_name: str) -> str:
    """Return the club emoji for a team name, or '' if none configured.

    Uses fuzzy matching so 'Real Madrid CF' finds a 'Real Madrid' key.
    Returns just the emoji — call club_tag() if you want 'emoji Name'.
    """
    if not team_name or not CLUB_EMOJIS:
        return ""
    if not _club_cache:
        _club_cache.update(_build_club_index())
    if not _club_cache:
        return ""
    core = _club_slug(team_name)
    if core in _club_cache:
        return _club_cache[core]
    # fuzzy: partial match
    for key, emoji in _club_cache.items():
        if len(core) >= 4 and (core in key or key in core):
            return emoji
    return ""


def club_tag(team_name: str) -> str:
    """Return '{emoji} {team_name}' or just '{team_name}' if no emoji."""
    emoji = club(team_name)
    return f"{emoji} {team_name}" if emoji else team_name
