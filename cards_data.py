"""
Static card definitions — Management (today's deck) + Finance (unchanged).

Money amounts are full pounds (e.g. 90_000_000 = £90M).
"""

# ---------------------------------------------------------------------------
# MANAGEMENT — 32 unique cards (today)
# types: free | goal | goal_manual | restriction | power
# dm_extra: longer explanation sent in DM after pick
# ---------------------------------------------------------------------------

MANAGEMENT_CARDS = [
    {
        "key": "power_steal_7",
        "text": "You can steal one player from anyone for the price they paid. After you use it, you can't bid for the next 7 auctions.",
        "type": "power",
        "params": {"power": "steal", "ban_after_use": 7},
        "dm_extra": (
            "How it works: tell an admin who you want to steal from and which player. "
            "You pay the same price they bought him for. Then you sit out 7 auctions. "
            "Confused? Ping an admin."
        ),
    },
    {
        "key": "power_swap_half",
        "text": (
            "You can swap one of your players (80+ OVR) with someone else's player. "
            "You pay them half of what they paid for that player + give them your player."
        ),
        "type": "power",
        "params": {"power": "swap", "min_give_ovr": 80},
        "dm_extra": (
            "Example: you give Vini (must be 80+ OVR) and want their Mbappé (bought for £150M). "
            "You pay them £75M + Vini, they get Vini + £75M, you get Mbappé. "
            "Confused? Contact an admin."
        ),
    },
    {
        "key": "buy_three_players",
        "text": "Buy at least 3 players tonight.",
        "type": "goal",
        "check": "buy_count",
        "params": {"count": 3},
        "dm_extra": "Win 3 auctions tonight. Auto-completes when you hit 3. Stuck? Ask an admin.",
    },
    {
        "key": "max_per_player_90m",
        "text": "You can't spend more than £90M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 90_000_000},
        "dm_extra": "Any bid over £90M on one player is blocked. Confused? Contact an admin.",
    },
    {
        "key": "buy_ucl_winner",
        "text": "Buy 1 UCL winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": (
            "Win an auction for a player who has won the UEFA Champions League (player, not club only). "
            "Unsure if a player counts? Ask an admin."
        ),
    },
    {
        "key": "buy_wc_winner",
        "text": "Buy 1 World Cup winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": (
            "Buy a player who has won the FIFA World Cup. "
            "Not sure? Contact an admin."
        ),
    },
    {
        "key": "buy_multi_league_titles",
        "text": "Buy a player who has won multiple league titles.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": (
            "The player must have won 2+ top-flight league titles in their career. "
            "Admin marks complete. Edge cases → ask an admin."
        ),
    },
    {
        "key": "spend_cap_250m_night",
        "text": "You can't spend more than £250M in total tonight.",
        "type": "restriction",
        "params": {"max_night_spend": 250_000_000},
        "dm_extra": "All your winning bids tonight add up. Over £250M total is blocked. Questions? Admin.",
    },
    {
        "key": "buy_brazilian",
        "text": "Buy 1 Brazilian player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Brazil"},
        "dm_extra": "Win any Brazilian nationality player. Auto-completes on purchase. Unsure? Admin.",
    },
    {
        "key": "buy_icon",
        "text": "Buy 1 icon.",
        "type": "goal",
        "check": "buy_icon",
        "params": {},
        "dm_extra": "Win an ICON / legend card. Auto-completes. Confused? Contact an admin.",
    },
    {
        "key": "buy_german",
        "text": "Buy 1 German player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Germany"},
        "dm_extra": "Win a player with nationality Germany. Auto-completes. Ask admin if unsure.",
    },
    {
        "key": "no_task_a",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine for this card. Just play.",
    },
    {
        "key": "no_task_b",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine for this card. Just play.",
    },
    {
        "key": "no_task_c",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine for this card. Just play.",
    },
    {
        "key": "no_task_d",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine for this card. Just play.",
    },
    {
        "key": "no_task_e",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine for this card. Just play.",
    },
    {
        "key": "no_bid_first_3_a",
        "text": "You can't bid for the first 3 rounds tonight.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
        "dm_extra": (
            "Rounds = finished auctions after management cards started (sold/skip/unsold). "
            "You can bid from the 4th auction onward. Questions? Admin."
        ),
    },
    {
        "key": "buy_5m_ig",
        "text": "Buy a player with more than 5M Instagram followers.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": (
            "The player's real IG must be over 5M followers at the time of purchase. "
            "Not sure? Contact an admin."
        ),
    },
    {
        "key": "buy_golden_boot",
        "text": "Buy a player who has won the Golden Boot for any league.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": (
            "Top scorer award in a recognized top league (PL, La Liga, Serie A, etc.) counts. "
            "Admin marks complete. Grey area? Ask an admin."
        ),
    },
    {
        "key": "buy_laliga",
        "text": "Buy a player from La Liga.",
        "type": "goal",
        "check": "buy_la_liga",
        "params": {},
        "dm_extra": (
            "Win a player whose club is a La Liga side (Real Madrid, Barcelona, Atlético, etc.). "
            "Icons don't count as La Liga. Auto-completes when possible. Unsure? Admin."
        ),
    },
    {
        "key": "buy_current_player",
        "text": "Buy 1 current player (not an icon).",
        "type": "goal",
        "check": "buy_active",
        "params": {},
        "dm_extra": "Win any non-ICON player. Auto-completes. Icons do not count. Ask admin if confused.",
    },
    {
        "key": "no_bid_first_3_b",
        "text": "You can't bid for the first 3 rounds tonight.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
        "dm_extra": (
            "Sit out the first 3 finished auctions, then bid normal. "
            "Contact an admin if something feels wrong."
        ),
    },
    {
        "key": "buy_copa_america",
        "text": "Buy 1 Copa América winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": (
            "Player must have won the Copa América."
            "Not sure? Contact an admin."
        ),
    },
    {
        "key": "buy_wc_semis_now",
        "text": "Buy a player who is currently in the World Cup semis.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": (
            "Based on the real-world World Cup right now (semi-finalists' squads). "
            "Admin decides who counts. If unsure, message an admin before you bid."
        ),
    },
    {
        "key": "buy_100_goals",
        "text": "Sign a player who has more than 100 career goals.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": (
            "100+ senior career goals (club + country accepted). "
            "Admin marks complete. Edge cases → contact an admin."
        ),
    },
    {
        "key": "buy_midfielder",
        "text": "Sign 1 midfielder.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "MID"},
        "dm_extra": "Win a MID-group player (CM/CDM/CAM/LM/RM). Auto-completes. Ask admin if confused.",
    },
    {
        "key": "buy_under_50m",
        "text": "Sign 1 player for under £50M (winning bid under £50M).",
        "type": "goal",
        "check": "buy_price_under",
        "params": {"max_price": 50_000_000},
        "dm_extra": (
            "Your winning bid must be under £50M. Auto-completes on a cheap win. "
            "Questions? Contact an admin."
        ),
    },
    {
        "key": "no_task_f",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine for this card. Just play.",
    },
    {
        "key": "buy_under_25",
        "text": "Buy a player under 25 years old (icons ignored for age).",
        "type": "goal",
        "check": "buy_age_under",
        "params": {"max_age": 24, "ignore_icons": True},
        "dm_extra": (
            "Age under 25 (24 or younger). Icons don't count for this goal. "
            "Auto-completes when age data matches. Unsure? Admin."
        ),
    },
    {
        "key": "buy_86_plus",
        "text": "Buy a 86+ rated player.",
        "type": "goal",
        "check": "buy_ovr_min",
        "params": {"ovr": 86},
        "dm_extra": "Win any player with 86 OVR or higher. Auto-completes. Ask admin if confused.",
    },
    {
        "key": "max_per_player_110m",
        "text": "The max you can spend on a player is £110M.",
        "type": "restriction",
        "params": {"max_bid": 110_000_000},
        "dm_extra": "Bids over £110M on one player are blocked. Contact an admin if stuck.",
    },
    {
        "key": "min_ovr_84",
        "text": "You can't buy a player below 84 rated.",
        "type": "restriction",
        "params": {"min_ovr": 84},
        "dm_extra": (
            "You can only bid on players with 84+ OVR. Lower rated = blocked. "
            "Confused? Contact an admin."
        ),
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
