"""
SQLite persistence layer. Supports two modes:

1. LOCAL (default): file-based SQLite at data/auction.db
   - Set DB_PATH in env (default: data/auction.db)

2. TURSO CLOUD (persistent, survives restarts on Render/Heroku):
   - Set TURSO_URL and TURSO_AUTH_TOKEN in your env vars
   - Uses embedded replica: local file for speed + cloud sync for persistence
   - Data survives restarts, never wipes

Both modes use the exact same sqlite3-compatible API.
"""
import threading
from contextlib import contextmanager

from config import Config

_local = threading.local()


def _connect():
    """Connect to SQLite (local) or libSQL (Turso cloud) depending on env vars."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        return conn

    import os

    turso_url = os.getenv("TURSO_URL", "")
    turso_token = os.getenv("TURSO_AUTH_TOKEN", "")

    if turso_url and turso_token:
        # ── Turso cloud mode (embedded replica) ──
        # Local file for fast reads + cloud sync for persistence
        import libsql
        local_path = Config.DB_PATH
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        conn = libsql.connect(
            local_path,
            sync_url=turso_url,
            auth_token=turso_token,
        )
        # Pull latest from cloud on connect
        try:
            conn.sync()
        except Exception:
            pass  # first run, no cloud data yet
        conn.row_factory = _row_factory
        print(f"[✓] Connected to Turso cloud: {turso_url}")
    else:
        # ── Local SQLite mode ──
        import sqlite3
        os.makedirs(os.path.dirname(Config.DB_PATH) or ".", exist_ok=True)
        conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

    _local.conn = conn
    return conn


# Row factory that works with both sqlite3 and libsql
try:
    import sqlite3
    _row_factory = sqlite3.Row
except Exception:
    _row_factory = None


@contextmanager
def cursor():
    conn = _connect()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
        # If Turso, sync changes to cloud
        if hasattr(conn, "sync"):
            try:
                conn.sync()
            except Exception:
                pass
    except Exception:
        conn.rollback()
        raise


def _columns(table: str):
    """Return the set of column names for an existing table (empty if missing)."""
    with cursor() as c:
        rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def _add_column(table: str, column: str, definition: str):
    """Add a column to an existing table, if it isn't already there."""
    cols = _columns(table)
    if column not in cols:
        with cursor() as c:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    """Create tables if missing AND migrate any old database to the new schema."""
    with cursor() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                guild_id     INTEGER NOT NULL,
                user_id      INTEGER NOT NULL,
                balance      INTEGER NOT NULL DEFAULT 0,
                team_name    TEXT,
                team_logo    TEXT,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS squads (
                guild_id       INTEGER NOT NULL,
                user_id        INTEGER NOT NULL,
                player_key     TEXT    NOT NULL,
                position       TEXT,
                acquired_price INTEGER NOT NULL DEFAULT 0,
                acquired_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (guild_id, user_id, player_key)
            );

            CREATE TABLE IF NOT EXISTS auction_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                player_key  TEXT    NOT NULL,
                position    TEXT,
                winner_id   INTEGER,
                final_price INTEGER NOT NULL DEFAULT 0,
                finished_at TEXT    NOT NULL DEFAULT (datetime('now')),
                status     TEXT    NOT NULL DEFAULT 'sold'
            );

            CREATE TABLE IF NOT EXISTS guild_state (
                guild_id       INTEGER PRIMARY KEY,
                current_phase  TEXT    NOT NULL DEFAULT 'ALL'
            );

            CREATE TABLE IF NOT EXISTS draft_queue (
                guild_id    INTEGER NOT NULL,
                position    INTEGER NOT NULL,
                player_key  TEXT    NOT NULL,
                PRIMARY KEY (guild_id, position)
            );

            CREATE TABLE IF NOT EXISTS player_faces (
                player_key TEXT PRIMARY KEY,
                face_url   TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS formations (
                guild_id  INTEGER NOT NULL,
                user_id   INTEGER NOT NULL,
                formation TEXT    NOT NULL DEFAULT '4-3-3',
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS lineup_overrides (
                guild_id    INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                slot_index  INTEGER NOT NULL,
                player_key  TEXT    NOT NULL,
                PRIMARY KEY (guild_id, user_id, slot_index)
            );

            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                from_user   INTEGER NOT NULL,
                to_user     INTEGER NOT NULL,
                offering    TEXT    NOT NULL,
                requesting  TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'pending',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                resolved_at TEXT
            );

            CREATE TABLE IF NOT EXISTS player_match_stats (
                guild_id      INTEGER NOT NULL,
                player_key    TEXT    NOT NULL,
                matches       INTEGER NOT NULL DEFAULT 0,
                goals         INTEGER NOT NULL DEFAULT 0,
                assists       INTEGER NOT NULL DEFAULT 0,
                tackles       INTEGER NOT NULL DEFAULT 0,
                saves         INTEGER NOT NULL DEFAULT 0,
                motm          INTEGER NOT NULL DEFAULT 0,
                yellow_cards  INTEGER NOT NULL DEFAULT 0,
                red_cards     INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, player_key)
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                guild_id    INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                player_key  TEXT    NOT NULL,
                PRIMARY KEY (guild_id, user_id, player_key)
            );
            """
        )

    # --- Migrate older databases: add any columns introduced after v1 ---
    # users: team_name, team_logo
    _add_column("users", "team_name", "TEXT")
    _add_column("users", "team_logo", "TEXT")
    _add_column("squads", "position", "TEXT")
    _add_column("squads", "acquired_price", "INTEGER NOT NULL DEFAULT 0")
    # auction_history: position was added alongside.
    _add_column("auction_history", "position", "TEXT")
    _add_column("auction_history", "status", "TEXT NOT NULL DEFAULT 'sold'")
    _add_column("guild_state", "trades_enabled", "INTEGER NOT NULL DEFAULT 1")

    # --- Season-scoped match stats (season_id added to player_match_stats) ---
    _add_column("player_match_stats", "season_id", "INTEGER")
    # unique index so ON CONFLICT can upsert per (guild, season, player)
    with cursor() as c:
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_season "
            "ON player_match_stats (guild_id, season_id, player_key)"
        )

    # Sync to Turso after migration
    conn = _connect()
    if hasattr(conn, "sync"):
        try:
            conn.sync()
            print("[✓] Database synced to Turso cloud")
        except Exception as e:
            print(f"[!] Turso sync warning: {e}")


# --------------------------------------------------------------------------
# Phase / state
# --------------------------------------------------------------------------
def get_phase(guild_id: int) -> str:
    with cursor() as c:
        row = c.execute(
            "SELECT current_phase FROM guild_state WHERE guild_id=?",
            (guild_id,),
        ).fetchone()
        return row["current_phase"] if row else "ALL"


def set_phase(guild_id: int, phase: str):
    with cursor() as c:
        c.execute(
            "INSERT INTO guild_state (guild_id, current_phase) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET current_phase=excluded.current_phase",
            (guild_id, phase),
        )
