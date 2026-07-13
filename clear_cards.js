import sqlite3
conn = sqlite3.connect("data/auction.db")
c = conn.cursor()
c.execute("DELETE FROM card_assignments")
c.execute("DELETE FROM card_days")
c.execute("DELETE FROM card_day_events")
conn.commit()
conn.close()
print("All cards cleared. Restart the bot now.")