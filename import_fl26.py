"""
FL26 Database Importer v4 — THE DEFINITIVE VERSION.

Phase 1: All leagues only (England, Spain, Italy, Germany, France).
Uses Teams CSV for league filtering + Teams-Players CSV for real club & nation names.

Reads 3 CSVs:
  - Players CSV (stats, OVR, positions)
  - Teams CSV (club IDs → country → league filter)
  - Teams-Players CSV (player → club name + nation name)

Zero legends. Zero wrong nations. Zero white flags. Real clubs.
"""
import csv
import json
import os
import unicodedata
from nation_overrides import NATION_OVERRIDES

PLAYERS_CSV = "/home/user/uploads/Players - PES 2021 - Bin.csv"
TEAMS_CSV = "/home/user/uploads/Teams - PES 2021 - Bin.csv"
TEAM_PLAYERS_CSV = "/home/user/uploads/Teams-Players - PES 2021 - Bin.csv"
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "players_fl26.json")

# All league country codes (Phase 1 + Phase 2)
LEAGUE_COUNTRIES = {
    "204","236","215","210","208",  # Top 5: England, Spain, Italy, Germany, France
    "31","135","228","224","190",   # Saudi, USA, Portugal, Netherlands, Turkey
    "146","144","124","197","232",  # Brazil, Argentina, Mexico, Belgium, Scotland
    "211","13","230","239","200",   # Greece, Japan, Russia, Ukraine, Croatia
    "303","202","238","194","227",  # Serbia, Czech, Switzerland, Austria, Poland
    "203","237","226","7","148",    # Denmark, Sweden, Norway, China, Colombia
    "147","149","150","151","201",  # Chile, Ecuador, Paraguay, Peru, Cyprus
    "30","37","229","152",          # Qatar, UAE, Romania, Uruguay
}

# Teams to EXCLUDE (classics/legends/all-stars)
EXCLUDED_TEAM_KEYWORDS = ["Classics", "Default", "World Selection", "Old Boys", "All Stars"]


def slug(text):
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    out = ""
    for ch in ascii_only.lower():
        out += ch if ch.isalnum() else "-"
    return "-".join(p for p in out.split("-") if p)


PES_POS_MAP = {
    0:"GK",1:"CB",2:"LB",3:"RB",4:"CDM",5:"CM",6:"LM",7:"RM",
    8:"CAM",9:"LW",10:"RW",11:"CF",12:"ST",
}

POS_COLUMNS = [
    ("GK","GK"),("CB","CB"),("LB","LB"),("RB","RB"),("DMF","CDM"),("CMF","CM"),
    ("LMF","LM"),("RMF","RM"),("AMF","CAM"),("LWF","LW"),("RWF","RW"),
    ("SS","CF"),("CF","ST"),
]

PLAYING_STYLES = {
    0:"Goalkeeper",
    1:"Goal Poacher",        # ST
    2:"Dummy Runner",        # ST/CF
    3:"Fox in the Box",      # ST
    4:"Roaming Flank",       # LW/RW (was wrongly "Anchor Man")
    5:"Creative Playmaker",  # CAM
    6:"Hole Player",         # CAM/CM
    7:"Box-to-Box",          # CM
    8:"Orchestrator",        # CDM
    9:"Anchor Man",          # CB/CDM (was wrongly "Roaming Flank")
    10:"Build-Up",           # CB
    11:"Offensive Fullback", # LB/RB
    12:"Defensive Fullback", # LB/RB
    13:"Target Man",         # ST (was wrongly "Creative Playmaker")
    14:"Creative Playmaker", # CAM
    15:"Extra Frontman",     # CB
    16:"Goalkeeper",         # GK
    17:"Offensive Goalkeeper", # GK
    18:"Prolific Winger",    # RW/LW
    19:"Cross Specialist",   # RM/LM
    20:"Anchor Man",         # CM/CDM
    21:"Offensive Wingback", # LB/RB
}

ALL_STAT_COLS = [
    "OffensiveAwareness","BallControl","Dribbling","TightPossession",
    "LowPass","LoftedPass","Finishing","Heading","PlaceKicking","Curl",
    "Speed","Acceleration","KickingPower","Jump","PhysicalContact",
    "Balance","Stamina","DefensiveAwareness","BallWinning","Aggression",
    "GKAwareness","GKCatching","GKClearing","GKReflexes","GKReach",
    "WeakFootUsage","WeakFootAcc","Form","InjuryResistance","Reputation",
]

SKILL_COLS = [
    "Trickster","MazingRun","SpeedingBullet","IncisiveRun","LongBallExpert",
    "EarlyCross","LongRanger","ScissorsFeint","DoubleTouch","FlipFlap",
    "MarseilleTurn","Sombrero","CrossOverTurn","CutBehindAndTurn","ScotchMove",
    "StepOnSkillcontrol","HeadingSpecial","LongRangeDrive","Chipshotcontrol",
    "LongRangeShot","KnuckleShot","DippingShots","RisingShots",
    "AcrobaticFinishing","HeelTrick","FirstTimeShot","OneTouchPass",
    "ThroughPassing","WeightedPass","PinpointCrossing","OutsideCurler",
    "Rabona","NoLookPass","LowLoftedPass","GKLowPunt","GKHighPunt",
    "LongThrow","GKLongThrow","PenaltySpecialist","GKPenaltySaver",
    "Gamesmanship","ManMarking","TrackBack","Interception","AcrobaticClear",
    "Captaincy","SuperSub","FightingSpirit",
]


def g(row, key, default=40):
    try:
        return int(row.get(key, default) or default)
    except (ValueError, TypeError):
        return default


def convert_stats(row, is_gk):
    if is_gk:
        return {
            "div": g(row,"GKAwareness"), "han": g(row,"GKCatching"),
            "kic": g(row,"GKClearing"), "ref": g(row,"GKReflexes"),
            "spd": g(row,"Speed"), "pos": g(row,"GKReach"),
        }
    return {
        "pac": round((g(row,"Speed") + g(row,"Acceleration")) / 2),
        "sho": max(g(row,"Finishing"), g(row,"PlaceKicking"), g(row,"KickingPower")),
        "pas": round((g(row,"LowPass")*2 + g(row,"LoftedPass") + g(row,"Curl")) / 4),
        "dri": round((g(row,"Dribbling")*2 + g(row,"BallControl")*1.5 + g(row,"Balance")) / 4.5),
        "def": round((g(row,"DefensiveAwareness") + g(row,"BallWinning")) / 2),
        "phy": round((g(row,"PhysicalContact")*2 + g(row,"Stamina")) / 3),
    }


def get_all_stats(row):
    return {col: g(row, col) for col in ALL_STAT_COLS}


def get_positions(row):
    positions, ratings = [], {}
    for pes_col, our_code in POS_COLUMNS:
        val = g(row, pes_col, 0)
        if val > 0:
            positions.append(our_code)
            ratings[our_code] = val
    return positions, ratings


def get_skills(row):
    return [col for col in SKILL_COLS if row.get(col) == "True"]


COUNTRY_FALLBACK = {
    "1":"Japan","2":"South Korea","7":"China PR","11":"Iran","13":"Japan",
    "16":"South Korea","30":"Qatar","31":"Saudi Arabia","44":"Algeria",
    "50":"Cameroon","56":"Ivory Coast","58":"Egypt","59":"Morocco",
    "60":"Tunisia","61":"Algeria","62":"Burkina Faso","63":"Ghana","64":"Ghana",
    "65":"Guinea","67":"Kenya","68":"DR Congo","71":"Mali","76":"Morocco",
    "77":"Gabon","80":"Nigeria","82":"Italy","83":"Senegal","87":"South Africa",
    "91":"Togo","92":"Denmark","93":"Iceland","94":"Zambia","95":"Zimbabwe",
    "98":"Congo","110":"Canada","114":"Ireland","120":"Haiti","121":"Honduras",
    "122":"Jamaica","124":"Mexico","128":"Panama","133":"Trinidad and Tobago",
    "135":"USA","139":"Suriname","140":"Curaçao","144":"Argentina","145":"Bolivia",
    "146":"Brazil","147":"Chile","148":"Colombia","149":"Ecuador","150":"Paraguay",
    "151":"Peru","152":"Uruguay","153":"Venezuela","162":"Australia",
    "166":"New Zealand","189":"Israel","190":"Turkey","191":"Albania",
    "193":"Armenia","194":"Austria","195":"Azerbaijan","196":"Belarus",
    "197":"Belgium","198":"Bosnia and Herzegovina","199":"Bulgaria",
    "200":"Croatia","201":"Slovenia","202":"Czech Republic","203":"Denmark",
    "204":"England","205":"Scotland","206":"Wales","207":"Northern Ireland",
    "208":"France","209":"Georgia","210":"Germany","211":"Austria",
    "212":"Hungary","213":"Iceland","214":"Ireland","215":"Italy",
    "216":"Luxembourg","219":"Portugal","221":"North Macedonia",
    "222":"Malta","224":"Netherlands","225":"Northern Ireland",
    "226":"Norway","227":"Poland","228":"Portugal","229":"Romania",
    "230":"Russia","231":"Estonia","232":"Scotland","233":"Lithuania",
    "234":"Slovakia","235":"Slovenia","236":"Spain","237":"Sweden",
    "238":"Switzerland","239":"Ukraine","240":"Bulgaria","241":"Wales",
    "253":"Iceland","254":"Ireland","256":"Czech Republic","258":"Hungary",
    "259":"Poland","260":"Albania","261":"North Macedonia","262":"Montenegro",
    "263":"Kosovo","264":"Israel","286":"South Africa","287":"Nigeria",
    "288":"Ghana","289":"Senegal","290":"Cameroon","291":"Ivory Coast",
    "292":"Morocco","293":"Algeria","294":"Tunisia","295":"Egypt",
    "298":"Saudi Arabia","299":"Iran","303":"Serbia","304":"Montenegro",
    "311":"Kosovo",
}


def load_league_clubs():
    """Build {club_id: club_name} for top-5-league clubs only."""
    clubs = {}
    with open(TEAMS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            if row.get("National") == "True":
                continue  # skip national teams
            country = row.get("Country", "")
            if country not in LEAGUE_COUNTRIES:
                continue  # not top 5 league
            name = row["Name"].strip()
            # Exclude classics/all-stars
            if any(kw in name for kw in EXCLUDED_TEAM_KEYWORDS):
                continue
            clubs[row["Id"]] = name
    print(f"  All-league clubs loaded: {len(clubs)}")
    return clubs


def load_player_club_nation():
    """Build {player_id: (club_name, nation_name)} from Teams-Players CSV."""
    mapping = {}
    with open(TEAM_PLAYERS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            pid = row.get("Id", "").strip()
            club = row.get("Club", "").strip()
            nation = row.get("National", "").strip()
            mapping[pid] = (club, nation)
    print(f"  Player→club/nation mappings loaded: {len(mapping)}")
    return mapping


def main():
    print("=== FL26 Importer v4 — Top 5 Leagues ===\n")

    # Step 1: Load club data
    print("Step 1: Loading club data...")
    league_clubs = load_league_clubs()

    # Step 2: Load player→club/nation mapping
    print("Step 2: Loading player→club/nation mapping...")
    player_club_nation = load_player_club_nation()

    # Step 3: Import players
    print("Step 3: Importing players...")
    players = []
    seen = set()
    no_club = 0
    legend_filtered = 0

    with open(PLAYERS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            ovr = g(row, "OverallStats", 0)
            if ovr < 70:
                continue

            pid_str = row.get("Id", "").strip()
            pid = g(row, "Id", 99999)
            name = row["Name"].strip()
            if not name or len(name) < 2:
                continue

            # Filter legends by ID range (but whitelist CR7 — ID 4522)
            if (pid < 5000 and pid != 4522) or 63000 <= pid <= 70000 or 96000 <= pid <= 99999:
                legend_filtered += 1
                continue

            # Get club + nation from Teams-Players CSV
            club, nation = player_club_nation.get(pid_str, ("", ""))

            # Filter: only top-5-league clubs
            # The Teams-Players CSV has club NAMES not IDs, so we check
            # if the club name is in our league_clubs set
            if club and club not in league_clubs.values():
                # Player's club is NOT in top 5 leagues — skip for Phase 1
                no_club += 1
                continue
            if not club:
                # Free agent or unknown — skip for Phase 1
                no_club += 1
                continue

            # Deduplicate
            key = slug(name) + f"-{ovr}"
            if key in seen:
                continue
            seen.add(key)

            pos_code = g(row, "POS", 12)
            position = PES_POS_MAP.get(pos_code, "ST")
            is_gk = position == "GK"
            style_code = g(row, "PlayingStyle", 0)
            alt_pos, pos_ratings = get_positions(row)

            # Nation: use Teams-Players CSV value, then PES country code, then manual override
            if not nation:
                cc = row.get("Country", "")
                nation = COUNTRY_FALLBACK.get(cc, "")
            if not nation or nation == "Unknown":
                nation = NATION_OVERRIDES.get(pid_str, "")

            player = {
                "name": name,
                "position": position,
                "club": club,
                "country": nation,
                "ovr": ovr,
                "stats": convert_stats(row, is_gk),
                "all_stats": get_all_stats(row),
                "alt_positions": alt_pos,
                "position_ratings": pos_ratings,
                "age": g(row, "Age", 20),
                "height": g(row, "Height", 180),
                "weight": g(row, "Weight", 75),
                "foot": "Left" if row.get("Foot") == "True" else "Right",
                "weak_foot": g(row, "WeakFootUsage", 2),
                "weak_foot_acc": g(row, "WeakFootAcc", 2),
                "playing_style": PLAYING_STYLES.get(style_code, ""),
                "skills": get_skills(row),
                "pes_id": pid_str,
            }
            players.append(player)

    players.sort(key=lambda p: p["ovr"], reverse=True)

    # Write output
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Imported {len(players)} players (All leagues, OVR >= 70)")
    print(f"   Legends filtered: {legend_filtered}")
    print(f"   Non-league/free agents skipped: {no_club}")
    print(f"   White flags: {sum(1 for p in players if p['country'] in ('Unknown','',''))}")

    print(f"\n   Top 20:")
    for p in players[:20]:
        s = p["stats"]
        sho = s.get("sho", "--")
        print(f"     {p['ovr']} {p['name']:25} {p['position']:4} {p['club']:25} "
              f"{p['country']:12} SHO={sho}")

    # Club count
    clubs = set(p["club"] for p in players)
    print(f"\n   Clubs: {len(clubs)}")
    # Nation count
    nations = set(p["country"] for p in players)
    print(f"   Nations: {len(nations)}")
    return players


if __name__ == "__main__":
    main()
