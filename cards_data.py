"""
Static card definitions — Management (today's deck) + Finance (unchanged).

Money amounts are full pounds (e.g. 90_000_000 = £90M).

TODAY'S POOL: 50 players. Heavy CB, lots of CDM/CM, some CAM/LW, a few ST.
Icons: Bonucci, Bergkamp, Riise, Hummels, Piqué, Thiago, Seedorf, Maldini,
Drogba, Hugo Sánchez, Ribéry, Makelele, Hierro, David Silva.
"""

# ---------------------------------------------------------------------------
# MANAGEMENT — 32 unique cards (today)
# Normal difficulty. DM extras reference ONLY today's player list.
# ---------------------------------------------------------------------------

MANAGEMENT_CARDS = [
    # --- GOALS (position-based) ---
    {
        "key": "buy_cb_today",
        "text": "Buy 1 centre-back (CB).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position": "CB"},
        "dm_extra": "Win any CB. Options: Bonucci (88), Rüdiger (86), Hummels (83), Tah (84), Romero (84), Laporte (83), Koulibaly (82), Medina (81) etc. Auto-completes.",
    },
    {
        "key": "buy_st_today",
        "text": "Buy 1 striker (ST or CF).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position_any": ["ST", "CF"]},
        "dm_extra": "Win any ST or CF. Options: Drogba (89), Lewandowski (86), Hugo Sánchez (91), Boniface (82), Sørloth (82), Okafor (80), Dybala (83), Lookman (83) etc. Auto-completes.",
    },
    {
        "key": "buy_gk_today",
        "text": "Buy 1 goalkeeper.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "GK"},
        "dm_extra": "Win any GK. Options: De Gea (83), Cássio Ramos (80), Hugo Lloris (80), Justin Bijlow (79) etc. Auto-completes.",
    },
    {
        "key": "buy_fullback",
        "text": "Buy a full-back (LB or RB).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position_any": ["LB", "RB"]},
        "dm_extra": "Win any LB or RB. Options: John Arne Riise (85), Raphaël Guerreiro (83), Daniel Carvajal (83), Nuno Tavares (81) etc. Auto-completes.",
    },
    {
        "key": "buy_cdm_or_cm",
        "text": "Buy a central midfielder (CDM or CM).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position_any": ["CDM", "CM"]},
        "dm_extra": "Win any CDM or CM. Options: Seedorf (87), Thiago (86), Barella (85), Reijnders (84), Hjulmand (83), de Roon (82), Anderson (82), Paredes (82), Matić (80) etc. Auto-completes.",
    },
    {
        "key": "buy_cam",
        "text": "Buy an attacking midfielder (CAM).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position": "CAM"},
        "dm_extra": "Win any CAM. Options: Asensio (84), David Silva (84), Julian Brandt (82), James Maddison (83). Auto-completes.",
    },
    {
        "key": "buy_winger",
        "text": "Buy a winger (LW or RW or LM).",
        "type": "goal",
        "check": "buy_position_exact",
        "params": {"position_any": ["LW", "RW", "LM"]},
        "dm_extra": "Win any LW, RW, or LM. Options: Federico Dimarco (84), Álex Baena (84), Ferran Torres (83), Noni Madueke (83) etc. Auto-completes.",
    },
    {
        "key": "buy_defender",
        "text": "Buy 1 defender.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "DEF"},
        "dm_extra": "Win any defender (CB/LB/RB). Lots today. Auto-completes.",
    },
    {
        "key": "buy_midfielder",
        "text": "Sign 1 midfielder.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "MID"},
        "dm_extra": "Win any MID player (CM/CDM/CAM/LM/RM). Lots today. Auto-completes.",
    },
    {
        "key": "buy_forward",
        "text": "Sign 1 forward.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "FWD"},
        "dm_extra": "Win any forward. Options: Hugo Sánchez, Bergkamp, Dybala, etc. Auto-completes.",
    },
    {
        "key": "buy_two_players",
        "text": "Buy at least 2 players today.",
        "type": "goal",
        "check": "buy_count",
        "params": {"count": 2},
        "dm_extra": "Win 2 auctions today. Auto-completes when you hit 2.",
    },
    # --- GOALS (general) ---
    {
        "key": "buy_icon_today",
        "text": "Buy 1 icon/legend.",
        "type": "goal",
        "check": "buy_icon",
        "params": {},
        "dm_extra": "Win any ICON. Options: Drogba (89), Bonucci (88), Riise (85), Hummels (83), Seedorf (87), Makelele (87), Thiago (86), Ribéry (89), Hierro (89), David Silva (84). Auto-completes.",
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
        "key": "buy_under_50m",
        "text": "Sign 1 player for under £50M.",
        "type": "goal",
        "check": "buy_price_under",
        "params": {"max_price": 50_000_000},
        "dm_extra": "Your winning bid must be under £50M. Auto-completes.",
    },
    {
        "key": "buy_spanish",
        "text": "Buy 1 Spanish player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Spain"},
        "dm_extra": "Win any Spanish player. Options: Piqué, Asensio, Thiago, Carvajal, Baena, De Gea, Ferran Torres, Hierro, David Silva. Auto-completes.",
    },
    {
        "key": "buy_italian",
        "text": "Buy 1 Italian player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Italy"},
        "dm_extra": "Win any Italian. Options: Bonucci, Dimarco, Barella. Auto-completes.",
    },
    {
        "key": "buy_german",
        "text": "Buy 1 German player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Germany"},
        "dm_extra": "Win any German. Options: Hummels, Tah, Rüdiger, Julian Brandt. Auto-completes.",
    },
    {
        "key": "buy_dutch",
        "text": "Buy 1 Dutch player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Netherlands"},
        "dm_extra": "Win any Dutch player. Options: Bergkamp, Seedorf, Reijnders, de Roon. Auto-completes.",
    },
    {
        "key": "buy_argentine",
        "text": "Buy 1 Argentine player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Argentina"},
        "dm_extra": "Win any Argentine. Options: Dybala, Facundo Medina, Leandro Paredes, Cristian Romero. Auto-completes.",
    },
    # --- FREE PASSES (6) ---
    {
        "key": "no_task_a",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine.",
    },
    {
        "key": "no_task_b",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine.",
    },
    {
        "key": "no_task_c",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine.",
    },
    {
        "key": "no_task_d",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine.",
    },
    {
        "key": "no_task_e",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine.",
    },
    {
        "key": "no_task_f",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine.",
    },
    {
        "key": "no_task_g",
        "text": "No task. Bid freely.",
        "type": "free",
        "params": {},
        "dm_extra": "Free pass. No goal, no fine.",
    },
    # --- RESTRICTIONS (4) ---
    {
        "key": "max_bid_100m",
        "text": "You can't spend more than £100M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 100_000_000},
        "dm_extra": "Bids over £100M on one player are blocked.",
    },
    {
        "key": "spend_cap_350m",
        "text": "You can't spend more than £350M in total today.",
        "type": "restriction",
        "params": {"max_night_spend": 350_000_000},
        "dm_extra": "All your winning bids today add up. Over £350M total is blocked.",
    },
    {
        "key": "no_bid_first_2",
        "text": "You can't bid for the first 2 auctions today.",
        "type": "restriction",
        "params": {"ban_first_n": 2},
        "dm_extra": "Sit out the first 2 finished auctions, then bid normal.",
    },
    {
        "key": "min_ovr_80",
        "text": "You can't buy a player below 80 rated.",
        "type": "restriction",
        "params": {"min_ovr": 80},
        "dm_extra": "You can only bid on players with 80+ OVR. Most of today's pool qualifies.",
    },
    # --- POWER CARDS (2) ---
    {
        "key": "power_steal_5",
        "text": "You can steal one player from anyone for the price they paid. After using it, you can't bid for the next 5 auctions.",
        "type": "power",
        "params": {"power": "steal", "ban_after_use": 5},
        "dm_extra": (
            "IMPORTANT RULES:\n"
            "1. The player you steal MUST have been bought in TODAY'S auction only.\n"
            "2. You must use this BEFORE the finance cards are dropped (around 30-35 players in).\n"
            "3. Tell an admin you have this card. The admin will announce when finance cards are coming so you know the deadline.\n"
            "4. You pay the same price they bought him for.\n"
            "5. Then you sit out 5 auctions.\n"
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
            "3. You must use this BEFORE the finance cards are dropped (around 30-35 players in).\n"
            "4. Tell an admin you have this card. The admin will announce when finance cards are coming.\n"
            "5. You pay them HALF of what they paid for the player you're taking.\n"
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

# ---------------------------------------------------------------------------
# FINANCE — 32 cards
# Max negative: -£20M. Big positives: +£150M, +£120M, +£100M
# ---------------------------------------------------------------------------

FINANCE_CARDS = [
    {"key": "f_p150", "text": "+£150M", "delta": 150_000_000},
    {"key": "f_p120", "text": "+£120M", "delta": 120_000_000},
    {"key": "f_p100", "text": "+£100M", "delta": 100_000_000},
    {"key": "f_p75", "text": "+£75M", "delta": 75_000_000},
    {"key": "f_p60", "text": "+£60M", "delta": 60_000_000},
    {"key": "f_p50_a", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_p50_b", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_p50_c", "text": "+£50M", "delta": 50_000_000},
    {"key": "f_p40_a", "text": "+£40M", "delta": 40_000_000},
    {"key": "f_p40_b", "text": "+£40M", "delta": 40_000_000},
    {"key": "f_p40_c", "text": "+£40M", "delta": 40_000_000},
    {"key": "f_p30_a", "text": "+£30M", "delta": 30_000_000},
    {"key": "f_p30_b", "text": "+£30M", "delta": 30_000_000},
    {"key": "f_p25_a", "text": "+£25M", "delta": 25_000_000},
    {"key": "f_p25_b", "text": "+£25M", "delta": 25_000_000},
    {"key": "f_p20_a", "text": "+£20M", "delta": 20_000_000},
    {"key": "f_p20_b", "text": "+£20M", "delta": 20_000_000},
    {"key": "f_p15", "text": "+£15M", "delta": 15_000_000},
    {"key": "f_p10", "text": "+£10M", "delta": 10_000_000},
    {"key": "f_zero", "text": "£0 - nothing happens. Pure vibes.", "delta": 0},
    {"key": "f_m5", "text": "-£5M", "delta": -5_000_000},
    {"key": "f_m10_a", "text": "-£10M", "delta": -10_000_000},
    {"key": "f_m10_b", "text": "-£10M", "delta": -10_000_000},
    {"key": "f_m15", "text": "-£15M", "delta": -15_000_000},
    {"key": "f_m15_b", "text": "-£15M", "delta": -15_000_000},
    {"key": "f_m20_a", "text": "-£20M", "delta": -20_000_000},
    {"key": "f_m20_b", "text": "-£20M", "delta": -20_000_000},
    {"key": "f_m20_c", "text": "-£20M", "delta": -20_000_000},
    {"key": "f_m10_c", "text": "-£10M", "delta": -10_000_000},
    {"key": "f_m5_b", "text": "-£5M", "delta": -5_000_000},
    {"key": "f_m15_c", "text": "-£15M", "delta": -15_000_000},
    {"key": "f_m20_d", "text": "-£20M", "delta": -20_000_000},
]

assert len(FINANCE_CARDS) == 32, len(FINANCE_CARDS)
assert len({c["key"] for c in FINANCE_CARDS}) == 32

MANAGEMENT_BY_KEY = {c["key"]: c for c in MANAGEMENT_CARDS}
FINANCE_BY_KEY = {c["key"]: c for c in FINANCE_CARDS}

MANAGEMENT_PENALTY = 50_000_000  # £50M incomplete goals at day end
