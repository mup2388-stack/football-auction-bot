"""
Player data: loads the bundled datasets, merges + de-dupes them, computes
market values (calibrated for a draft where everyone must afford a full squad),
ranks players into tiers, maps nationalities to flag emojis, groups positions
into auction phases, and provides accent-insensitive search.
"""
import json
import os
import unicodedata
from functools import lru_cache

from config import Config


# --------------------------------------------------------------------------
# Position groups (the "phases" / auction days)
# --------------------------------------------------------------------------
POSITION_GROUPS = {
    "GK":  {"GK"},
    "DEF": {"CB", "RB", "LB", "RWB", "LWB"},
    "MID": {"CDM", "CM", "CAM", "RM", "LM"},
    "FWD": {"ST", "CF", "LW", "RW"},
}
PHASE_ORDER = ["GK", "DEF", "MID", "FWD"]


def group_of(position: str) -> str:
    for group, positions in POSITION_GROUPS.items():
        if position in positions:
            return group
    return "FWD"   # default fallback


# --------------------------------------------------------------------------
# Load + index
# --------------------------------------------------------------------------
@lru_cache(maxsize=1)
def all_players():
    # Load FL26 real database if it exists, otherwise fall back to hand-curated files
    fl26_path = os.path.join(os.path.dirname(Config.PLAYERS_FILE), "players_fl26.json")
    if os.path.exists(fl26_path):
        with open(fl26_path, "r", encoding="utf-8") as f:
            pool = json.load(f)
    else:
        pool = []
        for fpath in (Config.PLAYERS_FILE, Config.PLAYERS_EXTRA_FILE):
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    pool.extend(json.load(f))

    # Load icons (legends) if present
    icons_path = os.path.join(os.path.dirname(Config.PLAYERS_FILE), "icons_fl26.json")
    print(f"[icons] looking for: {icons_path}")
    print(f"[icons] file exists: {os.path.exists(icons_path)}")
    if os.path.exists(icons_path):
        try:
            with open(icons_path, "r", encoding="utf-8") as f:
                icons_data = json.load(f)
            print(f"[icons] loaded {len(icons_data)} icons from file")
            pool.extend(icons_data)
        except Exception as ex:
            print(f"[icons] ERROR loading file: {ex}")
    else:
        # also try relative to this script's location
        alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "icons_fl26.json")
        print(f"[icons] trying alt path: {alt}  exists={os.path.exists(alt)}")
        if os.path.exists(alt):
            with open(alt, "r", encoding="utf-8") as f:
                pool.extend(json.load(f))
            print(f"[icons] loaded from alt path")

    seen = set()
    players = []
    for p in pool:
        p = dict(p)  # copy
        p["key"] = slug(p["name"])
        # If this key already exists (icon collides with active player),
        # prefix with 'icon-' so BOTH versions exist in the pool.
        is_icon = p.get("club") == "ICON"
        if p["key"] in seen:
            if is_icon:
                p["key"] = "icon-" + p["key"]
            else:
                continue
        if p["key"] in seen:
            continue
        seen.add(p["key"])
        p["value"] = market_value(p["ovr"], is_icon=(p.get("club") == "ICON"))
        p["tier"] = tier(p["ovr"])
        p["group"] = group_of(p["position"])
        players.append(p)
    return players


def get(key: str):
    for p in all_players():
        if p["key"] == key:
            return p
    return None


def search(query: str, limit: int = 25):
    """Accent/case-insensitive partial-name search. Returns best matches."""
    q = slug(query)
    if not q:
        return sorted(all_players(), key=lambda p: p["ovr"], reverse=True)[:limit]
    exact, starts, contains = [], [], []
    for p in all_players():
        k = p["key"]
        if k == q:
            exact.append(p)
        elif k.startswith(q):
            starts.append(p)
        elif q in k:
            contains.append(p)
    results = (exact + starts + contains)[:limit]
    results.sort(key=lambda p: p["ovr"], reverse=True)
    return results


# --------------------------------------------------------------------------
# Derived economics
# --------------------------------------------------------------------------
def market_value(ovr: int, is_icon: bool = False) -> int:
    """
    Map an overall rating to a market value in pounds.
    All values are rounded to whole millions for clean auction math.

    ACTIVE PLAYERS — tuned for a 32-manager draft with £800M each:
        OVR 75  -> £3M        (cheap filler)
        OVR 80  -> £11M
        OVR 83  -> £22M
        OVR 85  -> £37M
        OVR 86  -> £47M       (superstar threshold)
        OVR 88  -> £78M
        OVR 89  -> £100M      (Mbappe — opening bid £50M)
        OVR 90  -> £129M
        OVR 91  -> £166M

    ICONS — flat-tier pricing so GOAT-tier legends don't blow up the curve:
        OVR 95+  -> £200M     (Maradona, Zidane, Garrincha)
        OVR 92-94 -> £150M    (Beckenbauer, Ronaldo, Cruyff)
        OVR 89-91 -> £110M    (Henry, Ronaldinho, Kahn)
        OVR 86-88 -> £80M     (Gerrard, Pirlo, Pique)
        OVR 80-85 -> £45M     (solid legends)
        OVR <80  -> £20M      (role-player legends)
    """
    if is_icon:
        if ovr >= 95:
            return 200_000_000
        if ovr >= 92:
            return 150_000_000
        if ovr >= 89:
            return 110_000_000
        if ovr >= 86:
            return 80_000_000
        if ovr >= 80:
            return 45_000_000
        return 20_000_000

    millions = round(3 * (1.285 ** (ovr - 75)))
    return max(1, millions) * 1_000_000


def start_price(ovr: int, is_icon: bool = False) -> int:
    """Opening bid = 50% of market value, floored at £1M."""
    return max(1_000_000, market_value(ovr, is_icon) // 2)


def tier(ovr: int) -> str:
    """
    FIFA-style tiers.
    ICON = legend players (club="ICON"), shown distinct from active players.
    Within active players: GoldRare (86+), Gold (75-85), Silver, Bronze.
    """
    if ovr >= 86:
        return "GoldRare"
    if ovr >= 75:
        return "Gold"
    if ovr >= 65:
        return "Silver"
    return "Bronze"


def is_icon(player: dict) -> bool:
    return player.get("club") == "ICON"


TIER_COLOUR = {
    "GoldRare": 0xF1C40F,   # bright shiny gold
    "Gold":     0xC9971B,   # slightly less bright gold
    "Silver":   0xBDC3C7,   # silver
    "Bronze":   0xCD7F32,   # bronze
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def slug(text: str) -> str:
    """Normalise to ascii lowercase kebab-case for stable keys & search."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    out = ""
    for ch in ascii_only.lower():
        out += ch if ch.isalnum() else "-"
    return "-".join(part for part in out.split("-") if part)


_FLAGS = {
    "Albania": "🇦🇱",
    "Algeria": "🇩🇿",
    "Andorra": "🇦🇩",
    "Angola": "🇦🇴",
    "Argentina": "🇦🇷",
    "Armenia": "🇦🇲",
    "Australia": "🇦🇺",
    "Austria": "🇦🇹",
    "Azerbaijan": "🇦🇿",
    "Bangladesh": "🇧🇩",
    "Belarus": "🇧🇾",
    "Belgium": "🇧🇪",
    "Benin": "🇧🇯",
    "Bolivia": "🇧🇴",
    "Bosnia and Herzegovina": "🇧🇦",
    "Brazil": "🇧🇷",
    "Bulgaria": "🇧🇬",
    "Burkina Faso": "🇧🇫",
    "Burundi": "🇧🇮",
    "Cabo Verde": "🇨🇻",
    "Cameroon": "🇨🇲",
    "Canada": "🇨🇦",
    "Cape Verde": "🇨🇻",
    "Central African Republic": "🇨🇫",
    "Chad": "🇹🇩",
    "Chile": "🇨🇱",
    "China": "🇨🇳",
    "China PR": "🇨🇳",
    "Colombia": "🇨🇴",
    "Comoros": "🇰🇲",
    "Congo": "🇨🇬",
    "Congo DR": "🇨🇩",
    "Costa Rica": "🇨🇷",
    "Croatia": "🇭🇷",
    "Cuba": "🇨🇺",
    "Curacao": "🇨🇼",
    "Curaçao": "🇨🇼",
    "Cyprus": "🇨🇾",
    "Czech Republic": "🇨🇿",
    "Côte D'Ivoire": "🇨🇮",
    "DR Congo": "🇨🇩",
    "Denmark": "🇩🇰",
    "Dominican Republic": "🇩🇴",
    "Ecuador": "🇪🇨",
    "Egypt": "🇪🇬",
    "El Salvador": "🇸🇻",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Estonia": "🇪🇪",
    "Finland": "🇫🇮",
    "France": "🇫🇷",
    "Gabon": "🇬🇦",
    "Georgia": "🇬🇪",
    "Germany": "🇩🇪",
    "Ghana": "🇬🇭",
    "Greece": "🇬🇷",
    "Grenada": "🇬🇩",
    "Guatemala": "🇬🇹",
    "Guinea": "🇬🇳",
    "Guinea-Bissau": "🇬🇼",
    "Haiti": "🇭🇹",
    "Honduras": "🇭🇳",
    "Hong Kong": "🇭🇰",
    "Hungary": "🇭🇺",
    "Iceland": "🇮🇸",
    "Indonesia": "🇮🇩",
    "Iran": "🇮🇷",
    "Iraq": "🇮🇶",
    "Ireland": "🇮🇪",
    "Israel": "🇮🇱",
    "Italy": "🇮🇹",
    "Ivory Coast": "🇨🇮",
    "Jamaica": "🇯🇲",
    "Japan": "🇯🇵",
    "Jordan": "🇯🇴",
    "Kazakhstan": "🇰🇿",
    "Kenya": "🇰🇪",
    "Kosovo": "🇽🇰",
    "Latvia": "🇱🇻",
    "Liberia": "🇱🇷",
    "Libya": "🇱🇾",
    "Lithuania": "🇱🇹",
    "Luxembourg": "🇱🇺",
    "Macao": "🇲🇴",
    "Madagascar": "🇲🇬",
    "Malaysia": "🇲🇾",
    "Mali": "🇲🇱",
    "Malta": "🇲🇹",
    "Mauritania": "🇲🇷",
    "Mexico": "🇲🇽",
    "Moldova": "🇲🇩",
    "Montenegro": "🇲🇪",
    "Morocco": "🇲🇦",
    "Netherlands": "🇳🇱",
    "New Zealand": "🇳🇿",
    "Niger": "🇳🇪",
    "Nigeria": "🇳🇬",
    "North Macedonia": "🇲🇰",
    "Northern Ireland": "🏴󠁧󠁢󠁮󠁩󠁲󠁿",
    "Norway": "🇳🇴",
    "Palestine": "🇵🇸",
    "Panama": "🇵🇦",
    "Paraguay": "🇵🇾",
    "Peru": "🇵🇪",
    "Philippines": "🇵🇭",
    "Poland": "🇵🇱",
    "Portugal": "🇵🇹",
    "Puerto Rico": "🇵🇷",
    "Qatar": "🇶🇦",
    "Romania": "🇷🇴",
    "Russia": "🇷🇺",
    "Saudi Arabia": "🇸🇦",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Senegal": "🇸🇳",
    "Serbia": "🇷🇸",
    "Sierra Leone": "🇸🇱",
    "Slovakia": "🇸🇰",
    "Slovenia": "🇸🇮",
    "South Africa": "🇿🇦",
    "South Korea": "🇰🇷",
    "South Sudan": "🇸🇸",
    "Spain": "🇪🇸",
    "Sudan": "🇸🇩",
    "Suriname": "🇸🇷",
    "Sweden": "🇸🇪",
    "Switzerland": "🇨🇭",
    "Syria": "🇸🇾",
    "Tajikistan": "🇹🇯",
    "Tanzania": "🇹🇿",
    "Togo": "🇹🇬",
    "Trinidad and Tobago": "🇹🇹",
    "Tunisia": "🇹🇳",
    "Turkey": "🇹🇷",
    "UAE": "🇦🇪",
    "USA": "🇺🇸",
    "Ukraine": "🇺🇦",
    "United Arab Emirates": "🇦🇪",
    "United States": "🇺🇸",
    "Uruguay": "🇺🇾",
    "Uzbekistan": "🇺🇿",
    "Venezuela": "🇻🇪",
    "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    "Zambia": "🇿🇲",
    "Zimbabwe": "🇿🇼",
}


def flag(country: str) -> str:
    return _FLAGS.get(country, "🏳️")


def stat_bars(stats: dict, is_gk: bool) -> str:
    """Render the six stats as compact bars."""
    if is_gk:
        labels = [("DIV", "div"), ("HAN", "han"), ("KIC", "kic"),
                  ("REF", "ref"), ("SPD", "spd"), ("POS", "pos")]
    else:
        labels = [("PAC", "pac"), ("SHO", "sho"), ("PAS", "pas"),
                  ("DRI", "dri"), ("DEF", "def"), ("PHY", "phy")]

    def bar(v):
        filled = round(v / 100 * 10)
        return "█" * filled + "░" * (10 - filled)

    lines = []
    for label, key in labels:
        v = stats.get(key, 0)
        lines.append(f"`{label}` {bar(v)} **{v}**")
    return "\n".join(lines)
