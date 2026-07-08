"""
Standalone website launcher — for hosting the Flask dashboard on Render
WITHOUT the Discord bot.

This exists because website/app.py imports sibling modules (database, economy,
players, league) as top-level imports. Running `python website/app.py` directly
would fail because Python wouldn't find those modules. This launcher sits at the
project root where those modules live, so imports work.

Usage on Render:
  Build Command:   pip install -r requirements.txt
  Start Command:   python web.py
  Env vars:        TURSO_URL, TURSO_AUTH_TOKEN, DISCORD_CLIENT_ID,
                   DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI,
                   FLASK_SECRET_KEY, WEB_GUILD_ID (optional), WEBHOOK_URL (optional)

Locally (to test the website alone):
  python web.py
"""
import os

os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

import database as db
from website.app import app

# Create the schema (the bot isn't running here to do it). Idempotent.
db.init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("WEB_PORT", "5000")))
    print(f"[*] Starting website (standalone, no bot) on port {port} ...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
