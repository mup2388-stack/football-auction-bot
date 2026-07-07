"""
Central configuration for the Football Auction management bot.
All tunable game-balance values live here.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _admin_ids():
    raw = os.getenv("ADMIN_IDS", "")
    return {int(x) for x in raw.replace(";", ",").split(",") if x.strip().isdigit()}


class Config:
    # --- Discord ---
    TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    PREFIX: str = os.getenv("PREFIX", "!")
    ADMIN_IDS: set = _admin_ids()

    # --- Currency flavour ---
    CURRENCY_SYMBOL: str = os.getenv("CURRENCY_SYMBOL", "£")
    CURRENCY_NAME: str = os.getenv("CURRENCY_NAME", "coins")

    # --- Economy (auction management — no daily bonuses) ---
    # Sized so a manager can build a ~15 player squad from the pool.
    # Rule of thumb:  managers × balance  ≈  total value of all players you
    # expect to sell. With ~270 players averaging ~£8M that's ~£2.1B of value.
    STARTING_BALANCE: int = 800_000_000          # £800M per manager

    # --- Auction engine ---
    AUCTION_DURATION: int = 60                   # seconds an auction runs
    ANTI_SNIPE_WINDOW: int = 15                  # bids inside this (sec) extend the timer
    ANTI_SNIPE_EXTEND: int = 15                  # seconds added on a late bid
    MIN_BID_INCREMENT_PCT: float = 0.02          # min next bid = +2% of current
    MIN_BID_INCREMENT_FLAT: int = 1_000_000       # floor on the increment (£1M)

    # Opening bid (reserve) = market value * this factor.
    START_PRICE_RATIO: float = 0.50

    # --- Files ---
    DB_PATH: str = os.getenv("DB_PATH", "data/auction.db")
    # --- Custom server emojis (optional) ---
    # Upload the PNGs from emojis/custom/ to your Discord server
    # (Server Settings > Emoji), then paste the emoji ID here.
    # Format: "<:name:id>" e.g. "<:gavel:123456789>"
    # Leave as None to use plain text instead.
    EMOJI_SOLD: str = os.getenv("EMOJI_SOLD", "")    # gavel_sold.png
    EMOJI_BID: str = os.getenv("EMOJI_BID", "")       # coin_bid.png

    PLAYERS_FILE: str = os.getenv("PLAYERS_FILE", "data/players.json")
    PLAYERS_EXTRA_FILE: str = os.getenv("PLAYERS_EXTRA_FILE", "data/players_extra.json")

    # --- Website (Flask dashboard, runs alongside the bot) ---
    WEB_ENABLED: bool = os.getenv("WEB_ENABLED", "true").lower() == "true"
    WEB_PORT: int = int(os.getenv("PORT", os.getenv("WEB_PORT", "5000")))  # Render uses PORT

    # --- Discord OAuth (for website login) ---
    OAUTH_CLIENT_ID: str = os.getenv("DISCORD_CLIENT_ID", "")
    OAUTH_CLIENT_SECRET: str = os.getenv("DISCORD_CLIENT_SECRET", "")
    OAUTH_REDIRECT_URI: str = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")
    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "change-this-to-a-random-string")

    # --- Webhook (lineup change notifications) ---
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")


def is_admin(user_id: int) -> bool:
    """True if a user is configured as an admin. Empty ADMIN_IDS = everyone admin."""
    if not Config.ADMIN_IDS:
        return True
    return user_id in Config.ADMIN_IDS


