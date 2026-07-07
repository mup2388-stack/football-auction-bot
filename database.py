"""
SQLite persistence layer with Turso cloud sync.

- LOCAL mode: regular sqlite3 file (default)
- TURSO mode: libsql embedded replica (local speed + cloud persistence)

Uses a cursor wrapper so ALL queries return dict rows (like sqlite3.Row),
regardless of whether we're in local or Turso mode.
"""
import os
import sqlite3
import threading
from contextlib import contextmanager

from config import Config

_local = threading.local()
_turso_url = os.getenv("TURSO_URL", "")
_turso_token = os.getenv("TURSO_AUTH_TOKEN", "")
_using_turso = bool(_turso_url and _turso_token)


class _DictCursor:
    """Wraps any cursor (sqlite3 or libsql) to return dict rows."""

    def __init__(self, cur):
        self._cur = cur
        self._cols = None

    def _get_cols(self):
        """Cache column names from cursor description."""
        if self._cols is None:
            try:
                if self._cur.description:
                    self._cols = [d[0] for d in self._cur.description]
            except Exception:
                self._cols = []
        return self._cols or []

    def _convert(self, row):
        """Convert any row type to a dict."""
        if row is None:
            return None
        # Already a dict? Done.
        if isinstance(row, dict):
            return row
        # sqlite3.Row? Convert directly.
        if isinstance(row, sqlite3.Row):
            return {k: row[k] for k in row.keys()}
        # Has a keys() method? Use it.
        if hasattr(row, "keys"):
            try:
                return {k: row[k] for k in row.keys()}
            except Exception:
                pass
        # It's a tuple/list — use column names from description.
        if isinstance(row, (tuple, list)):
            cols = self._get_cols()
            if cols and len(cols) == len(row):
                return {cols[i]: row[i] for i in range(len(row))}
            # No column info — return as-is (caller must handle)
            return row
        return row

    def execute(self, sql, params=()):
        self._cols = None  # reset for new query
        self._cur.execute(sql, params)
        return self

    def executescript(self, sql):
        return self._cur.executescript(sql)

    def fetchone(self):
        return self._convert(self._cur.fetchone())

    def fetchall(self):
        return [self._convert(r) for r in self._cur.fetchall()]

    def fetchmany(self, size):
        return [self._convert(r) for r in self._cur.fetchmany(size)]

    @property
    def description(self):
        return self._cur.description

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()


class _DictConnection:
    """Wraps a connection so cursor() returns _DictCursor."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return _DictCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()
        # Sync to Turso after every commit (if Turso mode)
        if _using_turso:
            try:
                self._conn.sync()
            except Exception:
                pass

    def rollback(self):
        self._conn.rollback()

    def execute(self, sql, params=()):
        return self._conn.execute(sql, params)

    def close(self):
        self._conn.close()

    @property
    def row_factory(self):
        return getattr(self._conn, "row_factory", None)

    @row_factory.setter
    def row_factory(self, value):
        try:
            self._conn.row_factory = value
        except (AttributeError, TypeError):
            pass  # libsql doesn't support this — our wrapper handles it


def _connect():
    """Connect to SQLite (local) or libSQL (Turso) depending on env."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        return conn

    db_path = Config.DB_PATH
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    if _using_turso:
        # ── Turso cloud mode (embedded replica) ──
        import libsql
        raw = libsql.connect(
            db_path,
            sync_url=_turso_url,
            auth_token=_turso_token,
        )
        # Pull latest from cloud
        try:
            raw.sync()
            print(f"[✓] Turso: synced from cloud")
        except Exception:
            pass
        conn = _DictConnection(raw)
        print(f"[✓] Connected to Turso: {_turso_url}")
    else:
        # ── Local SQLite mode ──
        raw = sqlite3.connect(db_path, check_same_thread=False)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA journal_mode=WAL;")
        raw.execute("PRAGMA foreign_keys=ON;")
        conn = _DictConnection(raw)

    _local.conn = conn
    return conn


@contextmanager
def cursor():
    conn = _connect()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _columns(table: str):
    """Return the set of column names for an existing table."""
    with cursor() as c:
        rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    result = set()
    for r in rows:
        if isinstance(r, dict):
            result.add(r.get("name", ""))
        elif isinstance(r, (tuple, list)) and len(r) > 1:
            result.add(r[1])  # PRAGMA table_info: col 1 = name
    return result


def _add_column(table: str, column: str, definition: str):
    cols = _columns(table)
    if column not in cols:
        with cursor() as c:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    """Create tables + migrate."""
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
                status      TEXT    NOT NULL DEFAULT 'sold'
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

    _add_column("users", "team_name", "TEXT")
    _add_column("users", "team_logo", "TEXT")
    _add_column("squads", "position", "TEXT")
    _add_column("squads", "acquired_price", "INTEGER NOT NULL DEFAULT 0")
    _add_column("auction_history", "position", "TEXT")
    _add_column("auction_history", "status", "TEXT NOT NULL DEFAULT 'sold'")
    _add_column("guild_state", "trades_enabled", "INTEGER NOT NULL DEFAULT 1")
    _add_column("player_match_stats", "season_id", "INTEGER")

    with cursor() as c:
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_season "
            "ON player_match_stats (guild_id, season_id, player_key)"
        )

    if _using_turso:
        conn = _connect()
        try:
            conn._conn.sync()
            print("[✓] Database synced to Turso after init")
        except Exception as e:
            print(f"[!] Turso sync after init: {e}")


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


def get_trades_enabled(guild_id: int) -> bool:
    _add_column("guild_state", "trades_enabled", "INTEGER NOT NULL DEFAULT 1")
    with cursor() as c:
        row = c.execute(
            "SELECT trades_enabled FROM guild_state WHERE guild_id=?",
            (guild_id,),
        ).fetchone()
    return bool(row["trades_enabled"]) if row else True


def set_trades_enabled(guild_id: int, enabled: bool):
    _add_column("guild_state", "trades_enabled", "INTEGER NOT NULL DEFAULT 1")
    with cursor() as c:
        c.execute(
            "INSERT INTO guild_state (guild_id, trades_enabled) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET trades_enabled=excluded.trades_enabled",
            (guild_id, 1 if enabled else 0),
        )
