"""
Icon importer — extracts ALL icon/classic players from the PES 2021 CSV.

Pulls every player assigned to the 10 "Classics" teams (IDs 900-909) in FL26.
Each team has 40 players = 400 total icons. All get club="ICON".

Run:
    python import_icons.py

Output:
    data/icons_fl26.json
"""
import csv
import json
import os

from import_fl26 import (
    g, slug, PES_POS_MAP, PLAYING_STYLES,
    convert_stats, get_all_stats, get_positions, get_skills,
    COUNTRY_FALLBACK,
)
from nation_overrides import NATION_OVERRIDES

TEAMS_PLAYERS_CSV = "/home/user/uploads/Teams-Players - PES 2021 - Bin.csv"
PLAYERS_CSV = "/home/user/uploads/Players - PES 2021 - Bin.csv"
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "icons_fl26.json")

# The 10 classic/icon team IDs in PES 2021
ICON_TEAM_IDS = {str(i) for i in range(900, 910)}


def main():
    # 1. Get all player IDs + nations from the 10 classic teams
    icon_players_raw = {}
    with open(TEAMS_PLAYERS_CSV, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            club_id = row.get("Id Club", "").strip()
            if club_id not in ICON_TEAM_IDS:
                continue
            pid = row.get("Id", "").strip()
            nation = row.get("National", "").strip()
            if pid:
                icon_players_raw[pid] = nation

    print(f"Found {len(icon_players_raw)} players across 10 classic teams")

    # 2. Pull full data for each from the Players CSV
    players = []
    seen = set()

    with open(PLAYERS_CSV, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            pid_str = row.get("Id", "").strip()
            if pid_str not in icon_players_raw:
                continue

            name = row.get("Name", "").strip()
            if not name or len(name) < 2:
                continue
            if name.lower().startswith("face edit"):
                continue  # skip editor placeholder cards

            ovr = g(row, "OverallStats", 0)
            if ovr < 60:
                continue  # skip manager/coach cards (40-55 OVR)

            key = slug(name) + f"-ovr{ovr}"
            if key in seen:
                continue
            seen.add(key)

            pos_code = g(row, "POS", 12)
            position = PES_POS_MAP.get(pos_code, "ST")
            is_gk = position == "GK"
            style_code = g(row, "PlayingStyle", 0)
            alt_pos, pos_ratings = get_positions(row)

            # Nation: from Teams-Players CSV, then PES code, then override
            nation = icon_players_raw.get(pid_str, "")
            if not nation or nation == "Unknown":
                cc = row.get("Country", "")
                nation = COUNTRY_FALLBACK.get(cc, "")
            if not nation or nation == "Unknown":
                nation = NATION_OVERRIDES.get(pid_str, "")

            player = {
                "name": name,
                "position": position,
                "club": "ICON",
                "country": nation,
                "ovr": ovr,
                "stats": convert_stats(row, is_gk),
                "all_stats": get_all_stats(row),
                "alt_positions": alt_pos,
                "position_ratings": pos_ratings,
                "age": g(row, "Age", 30),
                "height": g(row, "Height", 180),
                "weight": g(row, "Weight", 75),
                "foot": "Left" if row.get("Foot") == "True" else "Right",
                "weak_foot": g(row, "WeakFootUsage", 4),
                "weak_foot_acc": g(row, "WeakFootAcc", 4),
                "playing_style": PLAYING_STYLES.get(style_code, ""),
                "skills": get_skills(row),
                "pes_id": pid_str,
            }
            players.append(player)

    players.sort(key=lambda p: p["ovr"], reverse=True)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

    no_nation = sum(1 for p in players if p["country"] in ("", "Unknown"))
    print(f"\nImported {len(players)} ICON players")
    print(f"   Missing nations: {no_nation}")
    print(f"   OVR range: {players[-1]['ovr']} - {players[0]['ovr']}")

    from collections import Counter
    pos_counts = Counter(p["position"] for p in players)
    print(f"   By position: {dict(sorted(pos_counts.items()))}")

    print(f"\n   Top 15:")
    for p in players[:15]:
        print(f"     {p['ovr']} {p['name']:25} {p['position']:4} {p['country'] or '??'}")
    print(f"   ...")
    print(f"   Bottom 5:")
    for p in players[-5:]:
        print(f"     {p['ovr']} {p['name']:25} {p['position']:4} {p['country'] or '??'}")


if __name__ == "__main__":
    main()
