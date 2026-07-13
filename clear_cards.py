import sqlite3, glob, os

# Find the DB file
db_path = os.environ.get("DB_PATH", "data/auction.db")
if not os.path.exists(db_path):
    # Search for it
    for p in glob.glob("**/*.db", recursive=True):
        if "auction" in p.lower() or "football" in p.lower():
            db_path = p
            break

print(f"Using DB: {db_path}")
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Check if tables exist
tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"Tables: {tables}")

for table in ["card_assignments", "card_days", "card_day_events"]:
    if table in tables:
        count = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        c.execute(f"DELETE FROM {table}")
        print(f"Cleared {count} rows from {table}")
    else:
        print(f"Table {table} not found")

conn.commit()
conn.close()
print("Done. Restart the bot now.")