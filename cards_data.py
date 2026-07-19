"""
Static card definitions — Management (TONIGHT'S deck) + Finance.

TONIGHT'S POOL: 70 players. Heavy CAM/CB. Some LW/RW. A few ST/GK.
Icons: Dalglish, Pirès, Carlos, Desailly, Zanetti, Campos, Hamšík, Agger,
Kaka, Zambrotta, Romário, Iniesta, Cannavaro, Zico, Cole, Touré, Nesta,
Best, Forlán, Cruijff, Kahn, Maicon, Giggs.

For career-achievement tasks (WC goals, UCL wins, IG followers, career goals,
transfers): dm_extra says "Ask admin" — never list specific players unless 100% sure.
"""

MANAGEMENT_CARDS = [
    # ===== RESTRICTIONS (10) =====
    {
        "key": "max_bid_90m",
        "text": "You can't spend more than 90M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 90_000_000},
        "dm_extra": "Single bids over 90M are blocked.",
    },
    {
        "key": "spend_cap_250m",
        "text": "You can't spend more than 250M in total tonight.",
        "type": "restriction",
        "params": {"max_night_spend": 250_000_000},
        "dm_extra": "All your winning bids add up. Over 250M total is blocked.",
    },
    {
        "key": "ban_first_3_a",
        "text": "You can't bid for the first 3 auctions today.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
        "dm_extra": "Sit out the first 3 finished auctions, then bid normal.",
    },
    {
        "key": "ban_first_3_b",
        "text": "You can't bid for the first 3 auctions today.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
        "dm_extra": "Sit out the first 3 finished auctions, then bid normal.",
    },
    {
        "key": "min_ovr_85",
        "text": "You can't buy players below 85 rated.",
        "type": "restriction",
        "params": {"min_ovr": 85},
        "dm_extra": "Only 85+ OVR signings allowed.",
    },
    {
        "key": "max_ovr_86",
        "text": "You can't buy players above 86 rating.",
        "type": "restriction",
        "params": {"max_ovr": 86},
        "dm_extra": "Players rated 86+ are blocked. Bargain hunting time.",
    },
    {
        "key": "max_bid_110m",
        "text": "The max you can spend on a player is 110M.",
        "type": "restriction",
        "params": {"max_bid": 110_000_000},
        "dm_extra": "Single bids over 110M are blocked.",
    },
    {
        "key": "no_attackers",
        "text": "You can't buy any attackers tonight.",
        "type": "restriction",
        "params": {"ban_groups": ["FWD"]},
        "dm_extra": "No ST, CF, LW, RW. Midfielders, defenders and GK are fine.",
    },
    {
        "key": "max_bid_140m",
        "text": "You can't spend more than 140M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 140_000_000},
        "dm_extra": "Single bids over 140M are blocked.",
    },
    {
        "key": "max_bid_pct_40",
        "text": "You can't spend more than 40% of your budget on a single player.",
        "type": "restriction",
        "params": {"max_bid_pct": 0.40},
        "dm_extra": "If you have 800M left, max bid is 320M. If 200M left, max is 80M. Scales with balance.",
    },

    # ===== AUTO GOALS (10) =====
    {
        "key": "buy_three",
        "text": "Buy at least 3 players today.",
        "type": "goal",
        "check": "buy_count",
        "params": {"count": 3},
        "dm_extra": "Win 3 auctions today. Auto-completes when you hit 3.",
    },
    {
        "key": "buy_brazilian",
        "text": "Buy 1 Brazilian player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Brazil"},
        "dm_extra": (
            "Win any Brazilian. Options: Zico (92), Romario (91), Kaka (88), "
            "Roberto Carlos (88), Maicon (84), Douglas Luiz (80), Yan Couto (80), "
            "Lucas Beraldo (81)."
        ),
    },
    {
        "key": "buy_icon",
        "text": "Buy 1 icon.",
        "type": "goal",
        "check": "buy_icon",
        "params": {},
        "dm_extra": (
            "Win any ICON. Options: Zico (92), Dalglish (91), Kahn (91), Romario (91), "
            "Best (90), Forlan (90), Cruijff (90), Kaka (88), Carlos (88), Iniesta (88), "
            "Toure (88), Pires (86), Cole (86), Giggs (86), Desailly (87), Zanetti (87), "
            "Cannavaro (89), Nesta (89), Hamšík (85), Agger (85), Zambrotta (85), "
            "Campos (84), Maicon (84)."
        ),
    },
    {
        "key": "buy_current",
        "text": "Buy 1 current player (not an icon).",
        "type": "goal",
        "check": "buy_active",
        "params": {},
        "dm_extra": "Win any non-ICON player. Auto-completes.",
    },
    {
        "key": "buy_midfielder",
        "text": "Sign 1 midfielder.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "MID"},
        "dm_extra": (
            "Win any MID (CM/CDM/CAM/LM/RM). Options: Zico (92), Kaka (88), Iniesta (88), "
            "Toure (88), Vitinha (87), Musiala (87), Pires (86),"
            "Hamšík (85), Palmer (86), Milinković-Savić (83), Xavi Simons (83), "
            "Isco (83), Gibbs-White (83), Goretzka (83), Rabiot (83), Parejo (82), "
            "Bentancur (82), Arrascaeta (82), Gallagher (82),"
            "Wharton (81), Elliott (80), Douglas Luiz (80)."
        ),
    },
    {
        "key": "buy_under_50m",
        "text": "Sign 1 player for under 50M (winning bid under 50M).",
        "type": "goal",
        "check": "buy_price_under",
        "params": {"max_price": 50_000_000},
        "dm_extra": "Your winning bid must be under 50M. Auto-completes.",
    },
    {
        "key": "buy_86_plus",
        "text": "Buy a 86+ rated player.",
        "type": "goal",
        "check": "buy_ovr_min",
        "params": {"ovr": 86},
        "dm_extra": (
            "Win any 86+ OVR player. Options: Zico (92), Dalglish (91), Kahn (91), "
            "Romario (91), Best (90), Forlan (90), Cruijff (90), Kaka (88), Carlos (88), "
            "Iniesta (88), Toure (88), Salah (87), Musiala (87), Vitinha (87), Saliba (87), "
            "Desailly (87), Zanetti (87), Cannavaro (89), Nesta (89), Pires (86), Cole (86), "
            "Giggs (86), Palmer (86)."
        ),
    },
    {
        "key": "buy_under_25",
        "text": "Buy a player aged 25 or under.",
        "type": "goal",
        "check": "buy_age_under",
        "params": {"max_age": 25, "ignore_icons": True},
        "dm_extra": (
            "Win a player aged 25 or younger. Options: Cubarsi (18), Doue (20), Tel (20), "
            "Xavi Simons (22), Elliott (22), Beraldo (22), Musiala (22), Palmer (23), "
            "Branthwaite (23), Williams (23), Yan Couto (23), Trafford (23), "
            "Wharton (21), Saliba (24), Greenwood (24), Maldini (24), Pavlovic (24). "
            "Icons don't count."
        ),
    },
    {
        "key": "buy_defender",
        "text": "Sign 1 defender.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "DEF"},
        "dm_extra": (
            "Win any DEF (CB/RB/LB/RWB/LWB). Options: Cannavaro (89), Nesta (89), "
            "Roberto Carlos (88), Saliba (87), Desailly (87), Zanetti (87), "
            "Theo Hernandez (85), Agger (85), Zambrotta (85), Davies (84), Cole (86), "
            "Cubarsi (83), Bellanova (83), Acerbi (83), Maicon (84), Konsa (82), "
            "Coates (82), Gaya (82), Branthwaite (81), Beraldo (81), Couto (80), "
            "De Cuyper (78), Ben Davies (79), Pavlovic (79)."
        ),
    },
    {
        "key": "buy_gk",
        "text": "Sign 1 goalkeeper.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "GK"},
        "dm_extra": (
            "Win any GK. Options: Kahn (91), Campos (84), Bounou (84), Svilar (83), "
            "Lunin (81), Jose Sa (80), Trafford (80)."
        ),
    },

    # ===== MANUAL GOALS (8) =====
    {
        "key": "buy_wc_winner",
        "text": "Buy 1 World Cup winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    {
        "key": "buy_ucl_winner",
        "text": "Buy 1 Champions League winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    {
        "key": "buy_5m_insta",
        "text": "Buy a player with more than 5M Instagram followers.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    {
        "key": "buy_copa_america",
        "text": "Buy 1 Copa America winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    {
        "key": "buy_golden_boot",
        "text": "Buy a player who has won the Golden Boot for any league.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    {
        "key": "buy_multi_titles",
        "text": "Buy a player who has won multiple league titles.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    {
        "key": "buy_100_goals",
        "text": "Sign a player who has more than 100 career goals.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },
    {
        "key": "buy_2x_ucl",
        "text": "Buy a player who has won the UCL more than once.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "If unsure which players qualify, ask the admin.",
    },

    # ===== FREE PASSES (2) =====
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

    # ===== POWER CARDS (2) =====
    {
        "key": "power_steal_7",
        "text": "You can steal one player from anyone for the price they paid. After using it, you can't bid for the next 7 auctions.",
        "type": "power",
        "params": {"power": "steal", "ban_after_use": 7},
        "dm_extra": (
            "IMPORTANT RULES:\n"
            "1. The player you steal MUST have been bought in TODAY'S auction only.\n"
            "2. You must use this BEFORE the finance cards are dropped.\n"
            "3. Tell an admin you have this card. The admin will announce when finance cards are coming.\n"
            "4. You pay the same price they bought him for.\n"
            "5. Then you sit out 7 auctions.\n"
            "Confused? DM an admin."
        ),
    },
    {
        "key": "power_swap_half",
        "text": "Swap one of your players (82+ OVR) with someone else's player. You pay them half of what they paid + give them your player.",
        "type": "power",
        "params": {"power": "swap", "min_give_ovr": 82},
        "dm_extra": (
            "IMPORTANT RULES:\n"
            "1. The player you take from someone MUST have been bought in TODAY'S auction only.\n"
            "2. The player you give MUST be 82+ OVR (can be from an older auction).\n"
            "3. You pay them HALF of what they paid for the player you're taking.\n"
            "4. You must use this BEFORE the finance cards are dropped.\n"
            "5. Tell an admin you have this card. The admin will announce when finance cards are coming.\n"
            "Confused? DM an admin."
        ),
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

FINANCE_CARDS = [
    {"key": "f_p50_a", "text": "+50M", "delta": 50_000_000},
    {"key": "f_p50_b", "text": "+50M", "delta": 50_000_000},
    {"key": "f_p50_c", "text": "+50M", "delta": 50_000_000},
    {"key": "f_p50_d", "text": "+50M", "delta": 50_000_000},
    {"key": "f_p40_a", "text": "+40M", "delta": 40_000_000},
    {"key": "f_p40_b", "text": "+40M", "delta": 40_000_000},
    {"key": "f_p40_c", "text": "+40M", "delta": 40_000_000},
    {"key": "f_p30_a", "text": "+30M", "delta": 30_000_000},
    {"key": "f_p30_b", "text": "+30M", "delta": 30_000_000},
    {"key": "f_p25_a", "text": "+25M", "delta": 25_000_000},
    {"key": "f_p25_b", "text": "+25M", "delta": 25_000_000},
    {"key": "f_p20_a", "text": "+20M", "delta": 20_000_000},
    {"key": "f_p20_b", "text": "+20M", "delta": 20_000_000},
    {"key": "f_p15_a", "text": "+15M", "delta": 15_000_000},
    {"key": "f_p15_b", "text": "+15M", "delta": 15_000_000},
    {"key": "f_p10", "text": "+10M", "delta": 10_000_000},
    {"key": "f_zero", "text": "0 - nothing happens. Pure vibes.", "delta": 0},
    {"key": "f_m5", "text": "-5M", "delta": -5_000_000},
    {"key": "f_m5_b", "text": "-5M", "delta": -5_000_000},
    {"key": "f_m10_a", "text": "-10M", "delta": -10_000_000},
    {"key": "f_m10_b", "text": "-10M", "delta": -10_000_000},
    {"key": "f_m10_c", "text": "-10M", "delta": -10_000_000},
    {"key": "f_m15_a", "text": "-15M", "delta": -15_000_000},
    {"key": "f_m15_b", "text": "-15M", "delta": -15_000_000},
    {"key": "f_m15_c", "text": "-15M", "delta": -15_000_000},
    {"key": "f_m20_a", "text": "-20M", "delta": -20_000_000},
    {"key": "f_m20_b", "text": "-20M", "delta": -20_000_000},
    {"key": "f_m20_c", "text": "-20M", "delta": -20_000_000},
    {"key": "f_m10_d", "text": "-10M", "delta": -10_000_000},
    {"key": "f_m5_c", "text": "-5M", "delta": -5_000_000},
    {"key": "f_m15_d", "text": "-15M", "delta": -15_000_000},
    {"key": "f_m20_d", "text": "-20M", "delta": -20_000_000},
]

assert len(FINANCE_CARDS) == 32, len(FINANCE_CARDS)
assert len({c["key"] for c in FINANCE_CARDS}) == 32

MANAGEMENT_BY_KEY = {c["key"]: c for c in MANAGEMENT_CARDS}
FINANCE_BY_KEY = {c["key"]: c for c in FINANCE_CARDS}

MANAGEMENT_PENALTY = 50_000_000
