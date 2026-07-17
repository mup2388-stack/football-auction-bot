"""
Static card definitions — Management (today's deck) + Finance.

Money amounts are full pounds (e.g. 90_000_000 = £90M).

TODAY'S POOL: 65 players. Heavy CB/CDM/CAM. Some LW/RW. A few ST/GK.
Icons: David Silva, John Barnes, Mascherano, Pablo Aimar, Gattuso, Paul Scholes,
Peter Schmeichel, Lassana Diarra, Cristian Chivu, Verón, Frank Rijkaard, Chiellini.
"""

# ---------------------------------------------------------------------------
# MANAGEMENT — 32 unique cards
# ---------------------------------------------------------------------------

MANAGEMENT_CARDS = [
    # --- POWER CARDS (2) ---
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
    # --- GOALS (20) ---
    {
        "key": "buy_three_players",
        "text": "Buy at least 3 players today.",
        "type": "goal",
        "check": "buy_count",
        "params": {"count": 3},
        "dm_extra": "Win 3 auctions today. Auto-completes when you hit 3.",
    },
    {
        "key": "buy_ucl_winner",
        "text": "Buy 1 Champions League winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "Win a player who has won the UEFA Champions League. Options: Raphinha, Hakimi, Rúben Dias, Neymar, Chiellini, Rijkaard, Mascherano, Gattuso, Paul Scholes, David Silva, Brozović, John Barnes, Lassana Diarra, Peter Schmeichel. Admin marks complete.",
    },
    {
        "key": "buy_wc_winner",
        "text": "Buy 1 World Cup winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "Buy a player who has won the FIFA World Cup. Options: Emiliano Martínez, Neymar, Hakimi, Chiellini, Rijkaard, Peter Schmeichel, Gattuso, Paul Scholes. Not sure? Ask admin.",
    },
    {
        "key": "buy_multi_league_titles",
        "text": "Buy a player who has won multiple league titles.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "The player must have won 2+ top-flight league titles. Options: Rúben Dias, Hakimi, Paul Scholes, David Silva, Rijkaard, Chiellini, Mascherano, Brozović, Koke. Admin marks complete.",
    },
    {
        "key": "buy_brazilian",
        "text": "Buy 1 Brazilian player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Brazil"},
        "dm_extra": "Win any Brazilian. Options: Neymar, Gabriel Magalhães, Martinelli, Raphinha. Auto-completes.",
    },
    {
        "key": "buy_icon",
        "text": "Buy 1 icon.",
        "type": "goal",
        "check": "buy_icon",
        "params": {},
        "dm_extra": "Win an ICON. Options: David Silva, John Barnes, Mascherano, Pablo Aimar, Gattuso, Paul Scholes, Peter Schmeichel, Lassana Diarra, Chivu, Verón, Rijkaard, Chiellini. Auto-completes.",
    },
    {
        "key": "buy_german",
        "text": "Buy 1 German player.",
        "type": "goal",
        "check": "buy_country",
        "params": {"country": "Germany"},
        "dm_extra": "Win any German player. Options: Willi Orbán, Felix Nmecha. Check nationality before bidding. Auto-completes.",
    },
    {
        "key": "buy_5m_insta",
        "text": "Buy a player with more than 5M Instagram followers.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "The player's real IG must be over 5M followers. Options: Neymar, Raphinha, Hakimi, Paul Scholes, David Silva, Mahrez, Kvaratskhelia. Not sure? Ask admin.",
    },
    {
        "key": "buy_golden_boot",
        "text": "Buy a player who has won the Golden Boot for any league.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "Top scorer award in a recognized top league. Options: Guirassy, Raphinha, Mahrez, Kvaratskhelia, Neymar, Paul Scholes, Suárez (not today). Admin marks complete.",
    },
    {
        "key": "buy_laliga",
        "text": "Buy a player from La Liga.",
        "type": "goal",
        "check": "buy_la_liga",
        "params": {},
        "dm_extra": "Win a player whose current club is a La Liga side. Options: Ferran Torres, Raphinha, Oyarzabal, Arda Güler, Koke, Diego López, Dani Vivian. Icons don't count as La Liga. Auto-completes.",
    },
    {
        "key": "buy_current_player",
        "text": "Buy 1 current player (not an icon).",
        "type": "goal",
        "check": "buy_active",
        "params": {},
        "dm_extra": "Win any non-ICON player. Auto-completes.",
    },
    {
        "key": "buy_copa_america",
        "text": "Buy 1 Copa América winner.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "Player must have won the Copa América. Options: Neymar, Mascherano, Raphinha. Not sure? Ask admin.",
    },
    {
        "key": "buy_100_goals",
        "text": "Sign a player who has more than 100 career goals.",
        "type": "goal_manual",
        "params": {},
        "dm_extra": "100+ senior career goals. Options: Neymar, Guirassy, Mahrez, Paul Scholes, David Silva, Rafa Silva, Peter Schmeichel (no, GK). Admin marks complete.",
    },
    {
        "key": "buy_midfielder",
        "text": "Sign 1 midfielder.",
        "type": "goal",
        "check": "buy_group",
        "params": {"group": "MID"},
        "dm_extra": "Win any MID player (CM/CDM/CAM/LM/RM). Tons today: Rice, Guendouzi, Sancet, Maddison, Arda Güler, Koke, McTominay, Mascherano, Gattuso, Paul Scholes, Rijkaard, etc. Auto-completes.",
    },
    {
        "key": "buy_under_50m",
        "text": "Sign 1 player for under £50M (winning bid under £50M).",
        "type": "goal",
        "check": "buy_price_under",
        "params": {"max_price": 50_000_000},
        "dm_extra": "Your winning bid must be under £50M. Auto-completes.",
    },
    {
        "key": "buy_under_26",
        "text": "Buy a player under 26 years old.",
        "type": "goal",
        "check": "buy_age_under",
        "params": {"max_age": 25, "ignore_icons": True},
        "dm_extra": "Age 25 or younger. Icons don't count. Options: Kvaratskhelia, Arda Güler, Hincapié, Kudus, Kayode, Martinelli. Auto-completes.",
    },
    {
        "key": "buy_86_plus",
        "text": "Buy a 86+ rated player.",
        "type": "goal",
        "check": "buy_ovr_min",
        "params": {"ovr": 86},
        "dm_extra": "Win any 86+ OVR player. Options: Rice (87), Gabriel (87), Raphinha (88), Guirassy (86), Kvaratskhelia (86), Rúben Dias (86), Hakimi (86), Chiellini (86), Mascherano (86), Paul Scholes (87), Lassana Diarra (88), Chivu (89), Peter Schmeichel (90), Rijkaard (92). Auto-completes.",
    },
    # --- FREE PASSES (5) ---
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
    # --- RESTRICTIONS (5) ---
    {
        "key": "max_bid_90m",
        "text": "You can't spend more than £90M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 90_000_000},
        "dm_extra": "Bids over £90M on one player are blocked. Plenty of good options under £90M.",
    },
    {
        "key": "spend_cap_250m",
        "text": "You can't spend more than £250M in total today.",
        "type": "restriction",
        "params": {"max_night_spend": 250_000_000},
        "dm_extra": "All your winning bids today add up. Over £250M total is blocked.",
    },
    {
        "key": "no_bid_first_3_a",
        "text": "You can't bid for the first 3 auctions today.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
        "dm_extra": "Sit out the first 3 finished auctions, then bid normal.",
    },
    {
        "key": "no_bid_first_3_b",
        "text": "You can't bid for the first 3 auctions today.",
        "type": "restriction",
        "params": {"ban_first_n": 3},
        "dm_extra": "Sit out the first 3 finished auctions, then bid normal.",
    },
    {
        "key": "max_bid_pct_40",
        "text": "You can't spend more than 40% of your current budget on a single player.",
        "type": "restriction",
        "params": {"max_bid_pct": 0.40},
        "dm_extra": "If you have £800M left, your max bid is £320M. If you have £200M left, max is £80M. Scales with your balance.",
    },
    {
        "key": "max_bid_170m",
        "text": "You can't spend more than £170M on a single player.",
        "type": "restriction",
        "params": {"max_bid": 170_000_000},
        "dm_extra": "Bids over £170M on one player are blocked.",
    },
    {
        "key": "max_bid_110m",
        "text": "The max you can spend on a player is £110M.",
        "type": "restriction",
        "params": {"max_bid": 110_000_000},
        "dm_extra": "Bids over £110M on one player are blocked.",
    },
    {
        "key": "min_ovr_84",
        "text": "You can't buy a player below 84 rated.",
        "type": "restriction",
        "params": {"min_ovr": 84},
        "dm_extra": "You can only bid on players with 84+ OVR. Most of today's top players qualify.",
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
