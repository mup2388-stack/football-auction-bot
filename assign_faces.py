"""
Assign SoFiFA face URLs to all players using the verified ID mapping CSV.

The CSV has 18,000+ players with SoFiFA/FIFA IDs. CDN URL pattern:
    https://cdn.sofifa.net/players/{first3}/{rest}/26_240.png

Matching strategy (3 passes for maximum coverage):
  1. Exact slug match (name or full_name)
  2. Last-name match (extract surname from our player, match CSV)
  3. Fuzzy: our slug contains or is contained by a CSV slug

Run:
    python assign_faces.py
"""
import os
import csv
import json
import sqlite3
import unicodedata

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fc26_sofifa_ids_players_icons.csv")
DB_PATH = os.environ.get("DB_PATH", "data/auction.db")


def slug(text):
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    out = ""
    for ch in ascii_only.lower():
        out += ch if ch.isalnum() else "-"
    return "-".join(part for part in out.split("-") if part)


def sofifa_url(sofifa_id):
    s = str(sofifa_id).zfill(6)
    return f"https://cdn.sofifa.net/players/{s[:3]}/{s[3:]}/26_240.png"


def load_csv():
    """Load CSV into multiple lookup structures for fuzzy matching."""
    by_slug = {}
    by_lastname = {}
    all_entries = []

    # Manual overrides for known name mismatches (PES name slug -> SoFiFA ID)
    OVERRIDES = {
        # Spelling differences between PES and FC26
        "johan-cruijff": 190045,        # CSV has "Johan Cruyff"
        "mane-garrincha": 247553,       # CSV has "Garrincha"
        "diego-armando-maradona": 190042,  # PES "Diego Maradona", CSV full name
        "diego-maradona": 190042,
    }
    for k, v in OVERRIDES.items():
        by_slug[k] = v

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=","):
            pid_str = row.get("player_id", "").strip()
            if not pid_str:
                continue
            pid = int(pid_str)

            for field in ("name", "display_name", "full_name", "short_name"):
                name = row.get(field, "").strip()
                if not name or len(name) < 2:
                    continue
                s = slug(name)
                if s and s not in by_slug:
                    by_slug[s] = pid
                    all_entries.append((s, pid))

                    parts = s.split("-")
                    if parts:
                        ln = parts[-1]
                        if len(ln) >= 3:
                            by_lastname.setdefault(ln, []).append((s, pid))
    return by_slug, by_lastname, all_entries


def load_our_players():
    pool = []
    for fname in ("data/players_fl26.json", "data/icons_fl26.json"):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                pool.extend(json.load(f))
    return pool


def match_player(name, by_slug, by_lastname, all_entries):
    """Try to find a SoFiFA ID for a player name. Returns (id, method) or (None, None)."""
    s = slug(name)
    if not s:
        return None, None

    # PASS 1: exact slug match
    if s in by_slug:
        return by_slug[s], "exact"

    # PASS 2: last-name match
    parts = s.split("-")
    if parts:
        ln = parts[-1]
        candidates = by_lastname.get(ln, [])
        if len(candidates) == 1:
            return candidates[0][1], "lastname-unique"
        if candidates:
            # Multiple candidates — find the one whose slug best matches ours
            best = None
            best_score = 0
            for csv_slug, pid in candidates:
                # score = how many words match
                csv_words = set(csv_slug.split("-"))
                our_words = set(s.split("-"))
                overlap = len(csv_words & our_words)
                if overlap > best_score:
                    best_score = overlap
                    best = pid
            if best and best_score > 0:
                return best, "lastname-best"

    # PASS 3: substring match (our slug contains or is contained by a CSV slug)
    for csv_slug, pid in all_entries:
        if len(s) >= 5 and s in csv_slug:
            return pid, "substring-our-in-csv"
        if len(csv_slug) >= 5 and csv_slug in s:
            return pid, "substring-csv-in-our"

    return None, None


def main():
    print("Loading SoFiFA ID mapping...")
    by_slug, by_lastname, all_entries = load_csv()
    print(f"  {len(by_slug)} unique slug entries")

    print("Loading our player database...")
    players = load_our_players()
    print(f"  {len(players)} players to match")

    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_faces (
            player_key TEXT PRIMARY KEY,
            face_url   TEXT    NOT NULL
        )
    """)

    assigned = 0
    missed = 0
    method_counts = {}
    missed_names = []

    for p in sorted(players, key=lambda x: -x.get("ovr", 0)):
        key = slug(p["name"])
        sofifa_id, method = match_player(p["name"], by_slug, by_lastname, all_entries)

        if sofifa_id:
            url = sofifa_url(sofifa_id)
            conn.execute(
                "INSERT OR REPLACE INTO player_faces (player_key, face_url) VALUES (?, ?)",
                (key, url),
            )
            assigned += 1
            method_counts[method] = method_counts.get(method, 0) + 1
        else:
            missed += 1
            if p.get("ovr", 0) >= 85:
                missed_names.append((p["name"], p.get("ovr", 0)))

    conn.commit()
    conn.close()

    total = assigned + missed
    print(f"\n{'=' * 55}")
    print(f"ASSIGNED: {assigned} / {total} players ({assigned * 100 // total}%)")
    print(f"MISSED:   {missed}")
    print(f"\nMatch methods used:")
    for m, c in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"  {m:25} {c:>5}")

    if missed_names:
        missed_names.sort(key=lambda x: -x[1])
        print(f"\nHigh-OVR players still missing ({len(missed_names)}):")
        for name, ovr in missed_names[:20]:
            print(f"  {ovr:>3}  {name}")

    print(f"\nRestart the bot — faces will appear on all cards.")


if __name__ == "__main__":
    main()
