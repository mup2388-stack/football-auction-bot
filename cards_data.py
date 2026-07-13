"""
Static card definitions — Management (today's deck) + Finance (unchanged).

Money amounts are full pounds (e.g. 90_000_000 = £90M).
"""

# ---------------------------------------------------------------------------
# MANAGEMENT — 32 unique cards (today)
# Built around the player pool: lots of CBs, STs, a few GKs/wingers,
# and some big icons (Roberto Baggio, Van Nistelrooy, Eusébio, Bergkamp,
# Laudrup, Puyol, Piqué, Gerrard, Seedorf, Schweinsteiger, etc.)
# ---------------------------------------------------------------------------

MANAGEMENT_CARDS = [
    {
        "key": "buy_cb_today",
        "text": "Buy 1 centre-back today.",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position": "CB"},
        "dm_extra": "Win any CB in auction. Plenty dropping today (Van Dijk, Puyol, Piqué, Varane, Bonucci, Stam, etc). Auto-completes.",
    },
    {
        "key": "buy_st_today",
        "text": "Buy 1 striker (ST/CF) today.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "FWD"},
        "dm_extra": "Win any forward. Loads available (Havertz, Osimhen, Lewandowski, Toney, Schick, etc). Auto-completes.",
    },
    {
        "key": "buy_two_players",
        "text": "Buy at least 2 players today.",
        "type": "goal",
        "check": "buy_count",
        "params": {"count": 2},
        "dm_extra": "Win 2 auctions today. Auto-completes when you hit 2.",
    },
    {
        "key": "buy_gk_today",
        "text": "Buy 1 goalkeeper today.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "GK"},
        "dm_extra": "Win a GK. Options today: Robert Sánchez, Matz Sels, Ederson, Brice Samba, ter Stegen, Justin Bijlow, Cássio Ramos. Auto-completes.",
    },
    {
        "key": "buy_icon_today",
        "text": "Buy 1 icon/legend today.",
        "type": "goal",
        "check": "buy_icon",
        "params": {},
        "dm_extra": "Win any ICON player. Big ones today: Baggio (91), Eusébio (92), Bergkamp (93), Van Nistelrooy (90), Laudrup (92), Puyol (87), Piqué (90), Gerrard (88). Auto-completes.",
    },
    {
        "key": "buy_84_plus",
        "text": "Buy a player rated 84 or higher.",
        "type": "goal",
        "check": "buy_ovr_min",
        "params": {"ovr": 84},
        "dm_extra": "Win any 84+ OVR player. Plenty today. Auto-completes.",
    },
    {
        "key": "buy_brazilian",
        "text": "Buy 1 Brazilian player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Brazil"},
        "dm_extra": "Win any Brazilian. Options: Vinícius, Ederson, Casemiro, Cássio Ramos, etc. Auto-completes.",
    },
    {
        "key": "buy_under_50m",
        "text": "Sign 1 player for under £50M (winning bid under £50M).",
        "type": "goal",
        "check": "buy_price_under",
        "params": {"max_price": 50_000_000},
        "dm_extra": "Your winning bid must be under £50M. Grab a bargain. Auto-completes.",
    },
    {
        "key": "buy_lb_or_rb",
        "text": "Buy a full-back (LB or RB).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position_any": ["LB", "RB"]},
        "dm_extra": "Win any LB or RB. Options today: Joakim Mæhle, Pedro Porro, Tino Livramento, Lewis-Skelly, Cucurella, Trippier, Nuno Mendes, Guerreiro. Auto-completes.",
    },
    {
        "key": "buy_cdm_or_cm",
        "text": "Buy a central midfielder (CDM or CM).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position_any": ["CDM", "CM"]},
        "dm_extra": "Win any CDM or CM. Options: Tonali, Kanté, Palacios, Kovačić, Baleba, Stiller, Fabián Ruiz, Schweinsteiger, Gerrard, Seedorf, Thiago. Auto-completes.",
    },
    {
        "key": "buy_cam",
        "text": "Buy an attacking midfielder (CAM).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position": "CAM"},
        "dm_extra": "Win any CAM. Options: Bruno Fernandes, Reus, Szoboszlai, Asensio, Golovin, Iwobi, Matheus Cunha, Laudrup. Auto-completes.",
    },
    {
        "key": "buy_winger",
        "text": "Buy a winger (LW/RW/LWF/RWF).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position_any": ["LW", "RW", "LWF", "RWF", "LM", "RM"]},
        "dm_extra": "Win any winger. Options: Trossard, Doku, Gordon, Vinícius, Sané, Lamine Yamal, Pépé, Semenyo, Dimarco. Auto-completes.",
    },
    {
        "key": "buy_spanish",
        "text": "Buy 1 Spanish player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Spain"},
        "dm_extra": "Win any Spanish player. Options: Lamine Yamal, Pedri (not today), Fabián Ruiz, Asensio, Porro, Griezmann (French), Piqué, Puyol. Auto-completes.",
    },
    {
        "key": "buy_french",
        "text": "Buy 1 French player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "France"},
        "dm_extra": "Win any French player. Options: Varane, Trossard, Kanté (not FR), Thuram, Griezmann, Lucas Hernandez, Saliba, Doku (BE)... check nationality. Auto-completes.",
    },
    {
        "key": "buy_under_25",
        "text": "Buy a player under 25 years old.",
        "type": "goal",
        "check": "buy_age_under",
        "params": {"max_age": 24, "ignore_icons": True},
        "dm_extra": "Age 24 or younger (icons don't count). Options: Lamine Yamal, Lewis-Skelly, Huijsen, Scalvini, Mosquera. Auto-completes.",
    },
    {
        "key": "buy_defender",
        "text": "Buy 1 defender.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "DEF"},
        "dm_extra": "Win any defender (CB/LB/RB). Tons today: Van Dijk, Varane, Puyol, Piqué, Bonucci, Stam, Campbell, Sol, Tah, Araújo, etc. Auto-completes.",
    },
    {
        "key": "no_task_a",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    {
        "key": "no_task_b",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    {
        "key": "no_task_c",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    {
        "key": "no_task_d",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    {
        "key": "no_task_e",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    {
        "key": "max_bid_100m",
        "text": "You can't spend more than £100M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 100_000_000},
        "dm_extra": "Bids over £100M on one player are blocked. Still plenty of options. Ask admin if confused.",
    },
    {
        "key": "spend_cap_300m",
        "text": "You can't spend more than £300M in total today.",
        "type": "restriction",
        "params": {"max_night_spend": 300_000_000},
        "dm_extra": "All your winning bids today add up. Over £300M total is blocked.",
    },
    {
        "key": "no_bid_first_2",
        "text": "You can't bid for the first 2 auctions today.",
        "type": "restriction",
        "params": {"ban_first_n": 2},
        "dm_extra": "Sit out the first 2 finished auctions, then bid normal.",
    },
    {
        "key": "min_ovr_82",
        "text": "You can't buy a player below 82 rated.",
        "type": "restriction",
        "params": {"min_ovr": 82},
        "dm_extra": "You can only bid on players with 82+ OVR. Lower rated = blocked. Most of today's pool qualifies.",
    },
    {
        "key": "buy_laliga_player",
        "text": "Buy a player currently at a La Liga club.",
        "type": "goal",
        "check": "buy_la_liga",
        "params": {},
        "dm_extra": "Win a player whose current club is a La Liga side. Icons don't count as La Liga. Auto-completes when possible.",
    },
    {
        "key": "power_steal_5",
        "text": "You can steal one player from anyone for the price they paid. After using it, you can't bid for the next 5 auctions.",
        "type": "power",
        "params": {"power": "steal", "ban_after_use": 5},
        "dm_extra": "Tell an admin who you want to steal and from whom. You pay the same price they bought him for. Then sit out 5 auctions.",
    },
    {
        "key": "power_swap_half",
        "text": "Swap one of your players (80+ OVR) with someone else's. You pay them half of what they paid + give your player.",
        "type": "power",
        "params": {"power": "swap", "min_give_ovr": 80},
        "dm_extra": "Give an 80+ player + half their purchase price, get their player in return. Contact admin to execute.",
    },
    {
        "key": "buy_italian",
        "text": "Buy 1 Italian player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Italy"},
        "dm_extra": "Win any Italian. Options: Scalvini, Tonali, Retegui, Dimarco, Bonucci. Auto-completes.",
    },
    {
        "key": "buy_dutch",
        "text": "Buy 1 Dutch player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Netherlands"},
        "dm_extra": "Win any Dutch player. Options: Van Dijk, Bergkamp, Seedorf, Stam, Aké, ter Stegen (not NL), Depay (not today). Check nationality. Auto-completes.",
    },
    {
        "key": "buy_portuguese",
        "text": "Buy 1 Portuguese player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Portugal"},
        "dm_extra": "Win any Portuguese player. Options: Samu Aghehowa, Pépé, Fabián Ruiz (not PT), Leão (not today). Check nationality. Auto-completes.",
    },
    {
        "key": "buy_german",
        "text": "Buy 1 German player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Germany"},
        "dm_extra": "Win any German player. Options: Havertz, Sané, ter Stegen, Schweinsteiger, Tah, Hummels, Guerreiro. Auto-completes.",
    },
]

assert len(MANAGEMENT_CARDS) == 32, len(MANAGEMENT_CARDS)
assert len({c["key"] for c in MANAGEMENT_CARDS}) == 32

# La Liga clubs (fuzzy match on club name)
LA_LIGA_CLUBS = {
    "Real Madrid", "Barcelona", "Atletico Madrid", "Atlético Madrid",
    "Sevilla", "Real Sociedad", "Villarreal", "Athletic Bilbao", "Athletic Club",
    "Real Betis", "Osasuna", "Celta", "Celta de Vigo", "Mallorca", "Girona",
    "Getafe", "Valencia", "Alaves", "Alavés", "Las Palmas", "Rayo Vallecano",
    "Espanyol", "Leganes", "Leganés", "Valladolid", "Cadiz", "Cádiz",
}

# Europe countries for non-europe goals (kept for compatibility)
EUROPE_COUNTRIES = {
    "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium",
    "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "England", "Estonia", "Finland", "France", "Georgia", "Germany",
    "Greece", "Hungary", "Iceland", "Ireland", "Italy", "Kazakhstan", "Kosovo",
    "Latvia", "Lithuania", "Luxembourg", "Malta", "Moldova", "Montenegro",
    "Netherlands", "North Macedonia", "Northern Ireland", "Norway", "Poland",
    "Portugal", "Romania", "Russia", "Scotland", "Serbia", "Slovakia", "Slovenia",
    "Spain", "Sweden", "Switzerland", "Turkey", "Ukraine", "Wales",
}

PREMIER_LEAGUE_CLUBS = {
    "Arsenal", "Aston Villa", "AFC Bournemouth", "Bournemouth", "Brentford",
    "Brighton", "Brighton & Hove Albion", "Burnley", "Chelsea", "Crystal Palace",
    "Everton", "Fulham", "Ipswich", "Leicester", "Liverpool", "Manchester City",
    "Manchester United", "Newcastle", "Newcastle United", "Nottingham Forest",
    "Southampton", "Tottenham", "Tottenham Hotspur", "West Ham", "West Ham United",
    "Wolves", "Wolverhampton Wanderers", "Leeds United", "Leeds", "Sunderland",
}

# ---------------------------------------------------------------------------
# FINANCE — unchanged 32 cards
# ---------------------------------------------------------------------------

FINANCE_CARDS = [
    {"key": "f_p50_a", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_m50", "text": "-£50M", "delta": -50_000_000},
    {"key": "f_p100", "text": "+£100M", "delta": 100_000_000},
    {"key": "f_m25_a", "text": "-£25M", "delta": -25_000_000},
    {"key": "f_p10", "text": "+£10M", "delta": 10_000_000},
    {"key": "f_p25", "text": "+£25M", "delta": 25_000_000},
    {"key": "f_p30_a", "text": "+£30M", "delta": 30_000_000},
    {"key": "f_m30_a", "text": "-£30M", "delta": -30_000_000},
    {"key": "f_p75", "text": "+£75M", "delta": 75_000_000},
    {"key": "f_m10", "text": "-£10M", "delta": -10_000_000},
    {"key": "f_m15", "text": "-£15M", "delta": -15_000_000},
    {"key": "f_p15_a", "text": "+£15M", "delta": 15_000_000},
    {"key": "f_p50_b", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_m20", "text": "-£20M", "delta": -20_000_000},
    {"key": "f_p30_b", "text": "+£30M", "delta": 30_000_000},
    {"key": "f_p40_a", "text": "+£40M", "delta": 40_000_000},
    {"key": "f_m25_b", "text": "-£25M", "delta": -25_000_000},
    {"key": "f_zero", "text": "£0 — nothing happens. Pure vibes.", "delta": 0},
    {"key": "f_p40_b", "text": "+£40M", "delta": 40_000_000},
    {"key": "f_p50_c", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_m30_b", "text": "-£30M", "delta": -30_000_000},
    {"key": "f_m35_a", "text": "-£35M", "delta": -35_000_000},
    {"key": "f_p20", "text": "+£20M", "delta": 20_000_000},
    {"key": "f_p15_b", "text": "+£15M", "delta": 15_000_000},
    {"key": "f_p60", "text": "+£60M", "delta": 60_000_000},
    {"key": "f_m40_a", "text": "-£40M", "delta": -40_000_000},
    {"key": "f_p70", "text": "+£70M", "delta": 70_000_000},
    {"key": "f_m35_b", "text": "-£35M", "delta": -35_000_000},
    {"key": "f_m30_c", "text": "-£30M", "delta": -30_000_000},
    {"key": "f_p50_d", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_m40_b", "text": "-£40M", "delta": -40_000_000},
    {"key": "f_p40_c", "text": "+£40M", "delta": 40_000_000},
]

assert len(FINANCE_CARDS) == 32, len(FINANCE_CARDS)
assert len({c["key"] for c in FINANCE_CARDS}) == 32

MANAGEMENT_BY_KEY = {c["key"]: c for c in MANAGEMENT_CARDS}
FINANCE_BY_KEY = {c["key"]: c for c in FINANCE_CARDS}

MANAGEMENT_PENALTY = 50_000_000  # £50M incomplete goals at day end
