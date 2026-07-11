"""
Static card definitions for Management + Finance drafts.

All money amounts are in £ (millions already expanded, e.g. 50_000_000).
"""

# ---------------------------------------------------------------------------
# MANAGEMENT — 32 unique cards per day
# types:
#   free          — no task, auto-completed, can bid freely
#   goal          — must complete something; bot auto-checks when possible
#   goal_manual   — needs /cards complete @user (trophies, insta, etc.)
#   restriction   — hard blocks on bids; auto-completes at day end if no breach
#   power         — special ability used via admin commands
# ---------------------------------------------------------------------------

MANAGEMENT_CARDS = [
    {
        "key": "buy_88_plus",
        "text": "You need to buy at least 1 player rated 88+ tonight.",
        "type": "goal",
        "check": "buy_ovr_min",
        "params": {"ovr": 88},
    },
    {
        "key": "no_bid_first_3_a",
        "text": "You can't bid for the first 3 rounds tonight.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
    },
    {
        "key": "spend_cap_100m_night",
        "text": "You cannot spend more than £100M in total tonight.",
        "type": "restriction",
        "params": {"max_night_spend": 100_000_000},
    },
    {
        "key": "buy_pl",
        "text": "Buy one player from the Premier League.",
        "type": "goal",
        "check": "buy_premier_league",
        "params": {},
    },
    {
        "key": "no_over_45",
        "text": "You can't bid for players who are above 45 years old (icons ignored).",
        "type": "restriction",
        "params": {"max_age": 45, "ignore_icons": True},
    },
    {
        "key": "max_per_player_90m",
        "text": "The maximum you can spend on a single player tonight is £90M.",
        "type": "restriction",
        "params": {"max_bid": 90_000_000},
    },
    {
        "key": "no_task_ggs",
        "text": "No task — ggs. Bid freely.",
        "type": "free",
        "params": {},
    },
    {
        "key": "buy_non_europe",
        "text": "Buy 1 player who is not from Europe.",
        "type": "goal",
        "check": "buy_non_europe",
        "params": {},
    },
    {
        "key": "buy_wc_winner",
        "text": "Buy 1 World Cup winner.",
        "type": "goal_manual",
        "params": {},
    },
    {
        "key": "no_defenders",
        "text": "Can't bid for any defenders tonight.",
        "type": "restriction",
        "params": {"ban_groups": ["DEF"]},
    },
    {
        "key": "no_task_b",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
    },
    {
        "key": "buy_attacker",
        "text": "Buy 1 attacker (FWD group).",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "FWD"},
    },
    {
        "key": "min_age_27",
        "text": "You can't buy players below 27 years old tonight (icons ignored).",
        "type": "restriction",
        "params": {"min_age": 27, "ignore_icons": True},
    },
    {
        "key": "buy_brazilian",
        "text": "Buy 1 Brazilian player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Brazil"},
    },
    {
        "key": "buy_spanish_active",
        "text": "Buy 1 Spanish player (not an icon / not retired).",
        "type": "goal",
        "check": "buy_country_active",
        "params": {"country": "Spain"},
    },
    {
        "key": "buy_icon",
        "text": "Buy 1 icon.",
        "type": "goal",
        "check": "buy_icon",
        "params": {},
    },
    {
        "key": "max_per_player_70m",
        "text": "Can't spend more than £70M on a single player tonight.",
        "type": "restriction",
        "params": {"max_bid": 70_000_000},
    },
    {
        "key": "no_task_c",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
    },
    {
        "key": "no_task_d",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
    },
    {
        "key": "no_task_e",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
    },
    {
        "key": "power_steal",
        "text": (
            "You can steal one player from someone for the same price they paid. "
            "If you use it, you can't bid for the next 5 rounds. Tell an admin."
        ),
        "type": "power",
        "params": {"power": "steal", "ban_after_use": 5},
    },
    {
        "key": "power_peek_player",
        "text": (
            "You can see the next player in the queue from admin. "
            "You may bid on that revealed player; after their auction ends, "
            "you can't bid for the next 5 auctions. Tell an admin."
        ),
        "type": "power",
        "params": {"power": "peek_player", "ban_after_use": 5},
    },
    {
        "key": "max_one_icon",
        "text": "You cannot buy more than one icon tonight.",
        "type": "restriction",
        "params": {"max_icons": 1},
    },
    {
        "key": "buy_two_players",
        "text": "Buy at least 2 players tonight.",
        "type": "goal",
        "check": "buy_count",
        "params": {"count": 2},
    },
    {
        "key": "no_task_f",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
    },
    {
        "key": "power_peek_card",
        "text": (
            "Power to see the next player in the queue via admin. "
            "You may bid on that revealed player; after their auction ends, "
            "you can't bid for the next 5 auctions."
        ),
        "type": "power",
        "params": {"power": "peek_card", "ban_after_use": 5},
    },
    {
        "key": "buy_midfielder",
        "text": "Buy 1 midfielder.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "MID"},
    },
    {
        "key": "buy_3m_ig",
        "text": "Buy a player with more than 3M followers on Instagram.",
        "type": "goal_manual",
        "params": {},
    },
    {
        "key": "buy_ucl_winner",
        "text": "Buy a player who has won the UCL.",
        "type": "goal_manual",
        "params": {},
    },
    {
        "key": "buy_2_league_titles",
        "text": "Buy a player who has won 2 or more league titles.",
        "type": "goal_manual",
        "params": {},
    },
    {
        "key": "no_bid_first_3_b",
        "text": "You can't bid for the first 3 rounds tonight.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
    },
    {
        "key": "no_task_g",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
    },
]

assert len(MANAGEMENT_CARDS) == 32, len(MANAGEMENT_CARDS)
assert len({c["key"] for c in MANAGEMENT_CARDS}) == 32

# Europe countries for "not from Europe" (nationality)
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

# Premier League clubs (fuzzy — matched via core club name)
PREMIER_LEAGUE_CLUBS = {
    "Arsenal", "Aston Villa", "AFC Bournemouth", "Bournemouth", "Brentford",
    "Brighton", "Brighton & Hove Albion", "Burnley", "Chelsea", "Crystal Palace",
    "Everton", "Fulham", "Ipswich", "Leicester", "Liverpool", "Manchester City",
    "Manchester United", "Newcastle", "Newcastle United", "Nottingham Forest",
    "Southampton", "Tottenham", "Tottenham Hotspur", "West Ham", "West Ham United",
    "Wolves", "Wolverhampton Wanderers", "Leeds United", "Leeds", "Sunderland",
}

# ---------------------------------------------------------------------------
# FINANCE — 32 unique cards (£ millions)
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

MANAGEMENT_PENALTY = 50_000_000  # £50M for incomplete goals at day end
