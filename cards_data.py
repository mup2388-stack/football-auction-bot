"""
Static card definitions — Management (TONIGHT'S deck) + Finance.

TONIGHT'S POOL: 60 players. See organizer's task list for details.

For career-achievement tasks (WC goals, UCL wins, IG followers, career goals,
transfers): dm_extra says "Ask admin" — never list specific players unless 100% sure.
"""

# ---------------------------------------------------------------------------
# MANAGEMENT — 32 unique cards (TONIGHT'S TASKS)
# ---------------------------------------------------------------------------

MANAGEMENT_CARDS = [
    # 1
    {
        "key": "buy_under_25",
        "text": "Buy at least one player aged 25 or under.",
        "type": "goal",
        "check": "buy_age_under",
        "params": {"max_age": 25, "ignore_icons": True},
        "dm_extra": (
            "Win at least ONE player aged 25 or under. Options:\n"
            "Pau Cubarsí (18), Désiré Doué (20), Lewis Hall (21), Adam Wharton (21), "
            "Gavi (21), Harvey Elliott (22), Marc Casadó (22), Šeško (22), Xavi Simons (22), "
            "Calafiori (23), Udogie (23), Barcola (23), Branthwaite (23), Cole Palmer (23), "
            "Gravenberch (23), Vlahović (25), Bellanova (25), De Cuyper (25), Gibbs-White (25)."
        ),
    },
    # 2
    {
        "key": "no_attackers",
        "text": "You can't buy any attackers tonight.",
        "type": "restriction",
        "params": {"ban_groups": ["FWD"]},
        "dm_extra": "No ST, CF, LW, RW or LF/RF. Midfielders, defenders and GK are fine.",
    },
    # 3
    {
        "key": "buy_three",
        "text": "Buy at least 3 players today.",
        "type": "goal",
        "check": "buy_count",
        "params": {"count": 3},
        "dm_extra": "Win 3 auctions today. Auto-completes when you hit 3.",
    },
    # 4
    {
        "key": "max_bid_90m",
        "text": "You can't spend more than £90M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 90_000_000},
        "dm_extra": "Single bids over £90M are blocked.",
    },
    # 5
    {
        "key": "buy_2x_ucl",
        "text": "Buy a player who has won the Champions League more than once.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    # 6
    {
        "key": "buy_wc_winner",
        "text": "Buy 1 World Cup winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    # 7
    {
        "key": "buy_multi_titles",
        "text": "Buy a player who has won multiple league titles.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    # 8
    {
        "key": "spend_cap_250m",
        "text": "You can't spend more than £250M in total tonight.",
        "type": "restriction",
        "params": {"max_night_spend": 250_000_000},
        "dm_extra": "All your winning bids add up. Over £250M total is blocked.",
    },
    # 9
    {
        "key": "buy_brazilian",
        "text": "Buy 1 Brazilian player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Brazil"},
        "dm_extra": "Win any Brazilian. Options: Kaka (88), Roberto Carlos (88), Richarlison (82), Marcelo (80), Douglas Luiz (80).",
    },
    # 10
    {
        "key": "buy_icon",
        "text": "Buy 1 icon.",
        "type": "goal",
        "check": "buy_icon",
        "params": {},
        "dm_extra": (
            "Win any ICON. Options: Maradona (97), Rijkaard (92), Dalglish (91), Kaka (88), "
            "Roberto Carlos (88), Desailly (87), Zanetti (87), Brehme (86), Pirès (86), "
            "Verón (85), Okocha (85), Lamela (85), Hamšík (85), Agger (85), Lev Yashin (84), "
            "Abidal (84), Jorge Campos (84), Insúa (84)."
        ),
    },
    # 11
    {
        "key": "max_ovr_86",
        "text": "You can't buy players above 86 rating.",
        "type": "restriction",
        "params": {"max_ovr": 86},
        "dm_extra": "Players rated 87+ are blocked. Bargain hunting time.",
    },
    # 12
    {
        "key": "no_task_a",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    # 13
    {
        "key": "max_bid_170m_a",
        "text": "You can't spend more than £170M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 170_000_000},
        "dm_extra": "Single bids over £170M are blocked.",
    },
    # 14
    {
        "key": "no_task_b",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    # 15
    {
        "key": "no_task_c",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    # 16
    {
        "key": "no_task_d",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    # 17
    {
        "key": "ban_first_3_a",
        "text": "You can't bid for the first 3 auctions today.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
        "dm_extra": "Sit out the first 3 finished auctions, then bid normal.",
    },
    # 18
    {
        "key": "buy_5m_insta",
        "text": "Buy a player with more than 5M Instagram followers.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    # 19
    {
        "key": "buy_golden_boot",
        "text": "Buy a player who has won the Golden Boot for any league.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    # 20
    {
        "key": "max_bid_170m_b",
        "text": "You can't spend more than £170M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 170_000_000},
        "dm_extra": "Single bids over £170M are blocked.",
    },
    # 21
    {
        "key": "buy_current",
        "text": "Buy 1 current player (not an icon).",
        "type": "goal",
        "check": "buy_active",
        "params": {},
        "dm_extra": "Win any non-ICON player. Auto-completes.",
    },
    # 22
    {
        "key": "ban_first_3_b",
        "text": "You can't bid for the first 3 auctions today.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
        "dm_extra": "Sit out the first 3 finished auctions, then bid normal.",
    },
    # 23
    {
        "key": "buy_copa_america",
        "text": "Buy 1 Copa América winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    # 24
    {
        "key": "max_bid_pct_40",
        "text": "You can't spend more than 40% of your budget on a single player.",
        "type": "restriction",
        "params": {"max_bid_pct": 0.40},
        "dm_extra": "If you have £800M left, max bid is £320M. If £200M left, max is £80M. Scales with balance.",
    },
    # 25
    {
        "key": "buy_150_goals",
        "text": "Sign a player who has more than 150 career goals.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    # 26
    {
        "key": "buy_midfielder",
        "text": "Sign 1 midfielder.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "MID"},
        "dm_extra": (
            "Win any MID (CM/CDM/CAM/LM/RM). Options: Rijkaard (92), Kaka (88), Pirès (86 LM), "
            "Cole Palmer (86), Verón (85), KDB (85), Okocha (85), Lamela (85), Hamšík (85), "
            "Zubimendi (84), Gravenberch (84), Brozović (83), Aleix García (83), Xavi Simons (83), "
            "Isco (83), Gibbs-White (83), Verón (85), Parejo (82), Locatelli (82), Gavi (82), "
            "Arrascaeta (82), Ward-Prowse (80), Elliott (80), Douglas Luiz (80)."
        ),
    },
    # 27
    {
        "key": "buy_under_50m",
        "text": "Sign 1 player for under £50M (winning bid under £50M).",
        "type": "goal",
        "check": "buy_price_under",
        "params": {"max_price": 50_000_000},
        "dm_extra": "Your winning bid must be under £50M. Auto-completes.",
    },
    # 28
    {
        "key": "no_task_e",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine. Just play.",
    },
    # 29
    {
        "key": "buy_under_26",
        "text": "Buy a player under 26 years old.",
        "type": "goal",
        "check": "buy_age_under",
        "params": {"max_age": 25, "ignore_icons": True},
        "dm_extra": (
            "Win a player aged 25 or younger. Options:\n"
            "Pau Cubarsí (18), Désiré Doué (20), Lewis Hall (21), Adam Wharton (21), "
            "Gavi (21), Harvey Elliott (22), Marc Casadó (22), Šeško (22), Xavi Simons (22), "
            "Calafiori (23), Udogie (23), Barcola (23), Branthwaite (23), Cole Palmer (23), "
            "Gravenberch (23), Vlahović (25), Bellanova (25), De Cuyper (25), Gibbs-White (25)."
        ),
    },
    # 30
    {
        "key": "buy_86_plus",
        "text": "Buy a 86+ rated player.",
        "type": "goal",
        "check": "buy_ovr_min",
        "params": {"ovr": 86},
        "dm_extra": (
            "Win any 86+ OVR player. Options: Maradona (97), Rijkaard (92), Dalglish (91), "
            "Kaka (88), Harry Kane (88), Roberto Carlos (88), Desailly (87), Zanetti (87), "
            "Brehme (86), Pirès (86), Cole Palmer (86)."
        ),
    },
    # 31
    {
        "key": "max_bid_110m",
        "text": "The max you can spend on a player is £110M.",
        "type": "restriction",
        "params": {"max_bid": 110_000_000},
        "dm_extra": "Single bids over £110M are blocked.",
    },
    # 32
    {
        "key": "min_ovr_85",
        "text": "You can't buy players below 85 rated.",
        "type": "restriction",
        "params": {"min_ovr": 85},
        "dm_extra": "Only 85+ OVR signings allowed.",
    },
]

assert len(MANAGEMENT_CARDS) == 32, len(MANAGEMENT_CARDS)
assert len({c["key"] for c in MANAGEMENT_CARDS}) == 32

LA_LIGA_CLUBS = {
    "Real Madrid", "Barcelona", "Atletico Madrid", "Atlético Madrid",
    "Sevilla", "Real Sociedad", "Villarreal", "Athletic Bilbao", "Athletic Club",
    "Real Betis", "Osasuna", "Celta", "Celta de Vigo", "Mallorca", "Girona",
    "Getafe", "Valencia", "Alaves", "Alavés", "Las Palmas", "Rayo Vallecano",
    "Espanyol", "Leganes", "Leganés", "Valladolid", "Cadiz", "Cádiz",
}

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
# FINANCE — 32 cards
# Max positive: +£50M. Max negative: -£20M.
# ---------------------------------------------------------------------------

FINANCE_CARDS = [
    {"key": "f_p50_a", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_p50_b", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_p50_c", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_p50_d", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_p40_a", "text": "+£40M", "delta": 40_000_000},
    {"key": "f_p40_b", "text": "+£40M", "delta": 40_000_000},
    {"key": "f_p40_c", "text": "+£40M", "delta": 40_000_000},
    {"key": "f_p30_a", "text": "+£30M", "delta": 30_000_000},
    {"key": "f_p30_b", "text": "+£30M", "delta": 30_000_000},
    {"key": "f_p25_a", "text": "+£25M", "delta": 25_000_000},
    {"key": "f_p25_b", "text": "+£25M", "delta": 25_000_000},
    {"key": "f_p20_a", "text": "+£20M", "delta": 20_000_000},
    {"key": "f_p20_b", "text": "+£20M", "delta": 20_000_000},
    {"key": "f_p15_a", "text": "+£15M", "delta": 15_000_000},
    {"key": "f_p15_b", "text": "+£15M", "delta": 15_000_000},
    {"key": "f_p10", "text": "+£10M", "delta": 10_000_000},
    {"key": "f_zero", "text": "£0 - nothing happens. Pure vibes.", "delta": 0},
    {"key": "f_m5", "text": "-£5M", "delta": -5_000_000},
    {"key": "f_m5_b", "text": "-£5M", "delta": -5_000_000},
    {"key": "f_m10_a", "text": "-£10M", "delta": -10_000_000},
    {"key": "f_m10_b", "text": "-£10M", "delta": -10_000_000},
    {"key": "f_m10_c", "text": "-£10M", "delta": -10_000_000},
    {"key": "f_m15_a", "text": "-£15M", "delta": -15_000_000},
    {"key": "f_m15_b", "text": "-£15M", "delta": -15_000_000},
    {"key": "f_m15_c", "text": "-£15M", "delta": -15_000_000},
    {"key": "f_m20_a", "text": "-£20M", "delta": -20_000_000},
    {"key": "f_m20_b", "text": "-£20M", "delta": -20_000_000},
    {"key": "f_m20_c", "text": "-£20M", "delta": -20_000_000},
    {"key": "f_m10_d", "text": "-£10M", "delta": -10_000_000},
    {"key": "f_m5_c", "text": "-£5M", "delta": -5_000_000},
    {"key": "f_m15_d", "text": "-£15M", "delta": -15_000_000},
    {"key": "f_m20_d", "text": "-£20M", "delta": -20_000_000},
]

assert len(FINANCE_CARDS) == 32, len(FINANCE_CARDS)
assert len({c["key"] for c in FINANCE_CARDS}) == 32

MANAGEMENT_BY_KEY = {c["key"]: c for c in MANAGEMENT_CARDS}
FINANCE_BY_KEY = {c["key"]: c for c in FINANCE_CARDS}

MANAGEMENT_PENALTY = 50_000_000  # £50M incomplete goals at day end
