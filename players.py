"""
Player data: loads the bundled datasets, merges + de-dupes them,
computes market values (calibrated for a draft where everyone must
afford a full squad), ranks players into tiers, maps nationalities
to flag emojis, groups positions into auction phases, and provides
accent-insensitive search.
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
    """Accent/case-insensitive partial-name search. Returns best matches.

    Sort by OVR *before* applying the limit so a low-rated exact slug
    (e.g. GK 'Ronaldo') doesn't beat a higher-rated related card
    (e.g. ICON 'icon-ronaldo' / R9) when limit=1.
    """
    q = slug(query)
    if not q:
        return sorted(all_players(), key=lambda p: p["ovr"], reverse=True)[:limit]

    # Aliases people type that aren't in the player name string itself
    ALIASES = {
        "r9": "icon-ronaldo",
        "fenomeno": "icon-ronaldo",
        "il-fenomeno": "icon-ronaldo",
        "ronaldo-nazario": "icon-ronaldo",
        "nazario": "icon-ronaldo",
    }
    if q in ALIASES:
        target = ALIASES[q]
        for p in all_players():
            if p["key"] == target:
                return [p]

    exact, starts, contains = [], [], []
    for p in all_players():
        k = p["key"]
        if k == q:
            exact.append(p)
        elif k.startswith(q) or k.startswith("icon-" + q) or k == "icon-" + q:
            starts.append(p)
        elif q in k:
            contains.append(p)

    # Rank:
    #   0 = exact key match that is an ICON (or only match)
    #   1 = icon-* sibling of the query (icon-ronaldo for "ronaldo")
    #   2 = other exact key match (active player with same slug)
    #   3 = starts-with
    #   4 = contains
    # then higher OVR wins inside a tier.
    def rank(p):
        k = p["key"]
        is_ic = p.get("club") == "ICON" or k.startswith("icon-")
        if k == "icon-" + q:
            tier = 0
        elif k == q and is_ic:
            tier = 0
        elif k == q:
            tier = 2
        elif k.startswith("icon-" + q) or (is_ic and q in k):
            tier = 1
        elif k.startswith(q):
            tier = 3
        else:
            tier = 4
        return (tier, -int(p.get("ovr") or 0))

    results = exact + starts + contains
    results.sort(key=rank)
    return results[:limit]


# --------------------------------------------------------------------------
# Derived economics
# --------------------------------------------------------------------------

# Opening-bid floors (your "base price"):
#   OVR < 75  → £15M
#   OVR ≥ 75  → £25M
BASE_PRICE_LOW = 15_000_000
BASE_PRICE_HIGH = 25_000_000
BASE_PRICE_OVR_CUTOFF = 75


def base_price(ovr: int) -> int:
    """Minimum opening bid for this OVR band."""
    return BASE_PRICE_LOW if ovr < BASE_PRICE_OVR_CUTOFF else BASE_PRICE_HIGH


def market_value(ovr: int, is_icon: bool = False) -> int:
    """
    Map an overall rating to a market value in pounds.
    All values are rounded to whole millions for clean auction math.

    Tuned for a 32-manager draft with £1B each and base floors of
    £15M (OVR < 75) / £25M (OVR ≥ 75). Curve is gentler than the old
    exponential so stars sit around £100–140M instead of £160–200M+.

    ACTIVE PLAYERS:
        OVR < 75 → £15M          (filler floor)
        OVR 75   → £25M          (base for gold)
        OVR 80   → £42M
        OVR 85   → £71M
        OVR 88   → £97M
        OVR 90   → £120M
        OVR 91   → £133M

    ICONS — flat-tier pricing so GOAT legends don't blow up the curve:
        OVR 95+  → £150M
        OVR 92–94 → £120M
        OVR 89–91 → £90M
        OVR 86–88 → £65M
        OVR 80–85 → £40M
        OVR <80   → £20M
    """
    if is_icon:
        if ovr >= 95:
            return 150_000_000
        if ovr >= 92:
            return 120_000_000
        if ovr >= 89:
            return 90_000_000
        if ovr >= 86:
            return 65_000_000
        if ovr >= 80:
            return 40_000_000
        return 20_000_000

    if ovr < BASE_PRICE_OVR_CUTOFF:
        return BASE_PRICE_LOW

    # Soft exponential from £25M at OVR 75.
    # Factor 1.11 → OVR 90 ≈ £120M, OVR 91 ≈ £133M (softer than old curve).
    millions = round(25 * (1.11 ** (ovr - BASE_PRICE_OVR_CUTOFF)))
    return max(25, millions) * 1_000_000


def start_price(ovr: int, is_icon: bool = False) -> int:
    """
    Opening bid is FLAT by OVR band — no star premium on the open.

      OVR < 75  → £15M
      OVR ≥ 75  → £25M  (including icons / superstars)

    Market value still scales with OVR for squad value, cards, and
    the SOLD steal/overpay verdict. Bidding is what pushes prices up.
    """
    return base_price(ovr)


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
    "Northern Ireland": "🇬🇧",
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
