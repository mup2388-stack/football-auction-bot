"""
SQLite persistence layer.

Two modes, selected by environment variable:

  1. LOCAL (default)  — pure sqlite3 on a file. Use for local testing / the
                        event when everything runs on one machine.

  2. CLOUD (Turso)    — set TURSO_URL + TURSO_AUTH_TOKEN and EVERY query goes
                        to a hosted libSQL database over plain HTTPS, using the
                        `requests` library (pure Python, NO native compiler
                        needed). This is how the local bot and the public
                        website share ONE database (24/7 website, bot can sleep).

The public API is identical in both modes:
    with db.cursor() as c:
        row = c.execute("SELECT ... WHERE id=?", (id,)).fetchone()
        value = row["column"]          # dict-style access works in BOTH modes
"""
import os
import base64
import threading
from contextlib import contextmanager

from config import Config

USE_TURSO = bool(os.getenv("TURSO_URL", "").strip())

_local = threading.local()


# ============================================================================
#  MODE 2 — CLOUD (Turso / libSQL over plain HTTPS, pure Python)
#
#  This replaces the Rust `libsql_experimental` driver, which has no prebuilt
#  Windows wheel and forces a Rust/MSVC compile that fails on most machines.
#  Instead we talk to Turso's documented HTTP API (/v2/pipeline) using the
#  `requests` library that is already a dependency. Zero native code.
# ============================================================================
if USE_TURSO:
    import requests

    # One shared Session across the whole process → HTTP keep-alive, so we
    # don't pay a fresh TCP+TLS handshake on every query. Thread-safe.
    _session = requests.Session()

    class _Row:
        """Behaves like sqlite3.Row: row["col"], row[0], .keys(), etc.
        Built from the column names + a plain tuple of values."""
        __slots__ = ("_values", "_map")

        def __init__(self, cols, values):
            self._values = tuple(values)
            self._map = dict(zip(cols, self._values))

        def __getitem__(self, key):
            if isinstance(key, int):
                return self._values[key]
            return self._map[key]

        def __iter__(self):
            return iter(self._values)

        def __len__(self):
            return len(self._values)

        def keys(self):
            return list(self._map.keys())

        def values(self):
            return list(self._values)

        def items(self):
            return list(self._map.items())

        def get(self, key, default=None):
            return self._map.get(key, default)

        def __contains__(self, key):
            return key in self._map

        def __eq__(self, other):
            if isinstance(other, _Row):
                return self._values == other._values
            return tuple(other) == self._values

        def __repr__(self):
            return f"_Row({self._map})"

    def _to_arg(val):
        """Convert a Python value into the JSON arg object Turso expects."""
        if val is None:
            return {"type": "null"}
        # bool MUST be checked before int (isinstance(True, int) is True)
        if isinstance(val, bool):
            return {"type": "integer", "value": "1" if val else "0"}
        if isinstance(val, int):
            return {"type": "integer", "value": str(val)}
        if isinstance(val, float):
            return {"type": "float", "value": repr(val)}
        if isinstance(val, (bytes, bytearray)):
            return {"type": "blob", "base64": base64.b64encode(bytes(val)).decode()}
        return {"type": "text", "value": str(val)}

    def _from_cell(cell):
        """Convert a JSON cell object back into a Python value."""
        if isinstance(cell, dict):
            t = cell.get("type")
            if t == "null" or t is None:
                return None
            if t == "integer":
                return int(cell["value"])
            if t == "float":
                return float(cell["value"])
            if t == "blob":
                return base64.b64decode(cell.get("base64", ""))
            return cell.get("value")  # text
        return cell  # already a raw value (defensive)

    class _HttpConn:
        """A minimal Turso HTTP client. One per thread."""

        def __init__(self, url, token):
            # libsql://  →  https://
            if url.startswith("libsql://"):
                url = "https://" + url[len("libsql://"):]
            self._url = url.rstrip("/") + "/v2/pipeline"
            self._token = token
            self._headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

        def _post(self, body):
            # One retry on transient network errors (NOT on SQL errors).
            last_err = None
            for attempt in range(2):
                try:
                    resp = _session.post(
                        self._url, json=body, headers=self._headers, timeout=30
                    )
                    if resp.status_code == 401:
                        raise RuntimeError(
                            "Turso auth failed (401) — check TURSO_AUTH_TOKEN."
                        )
                    if resp.status_code != 200:
                        raise RuntimeError(
                            f"Turso HTTP {resp.status_code}: {resp.text[:300]}"
                        )
                    return resp.json()
                except requests.exceptions.RequestException as e:
                    last_err = e
            raise RuntimeError(f"Turso connection failed: {last_err}")

        def execute(self, sql, params=()):
            body = {
                "baton": None,
                "requests": [
                    {
                        "type": "execute",
                        "stmt": {
                            "sql": sql,
                            "args": [_to_arg(p) for p in (params or ())],
                        },
                    },
                    {"type": "close"},
                ],
            }
            data = self._post(body)
            return self._parse_result(data)

        def executescript(self, script):
            """Run a multi-statement script in ONE HTTP call by splitting on
            ';' and sending each as a separate execute in the same pipeline."""
            stmts = [s.strip() for s in script.split(";") if s.strip()]
            if not stmts:
                return
            reqs = [
                {"type": "execute", "stmt": {"sql": s}} for s in stmts
            ] + [{"type": "close"}]
            self._post({"baton": None, "requests": reqs})

        @staticmethod
        def _parse_result(data):
            """Extract (cols, rows, lastrowid, rowcount) from a pipeline
            response. Raises on any error result."""
            results = data.get("results", [])
            # surface errors first
            for r in results:
                if r.get("type") == "error":
                    err = r.get("error", {})
                    msg = err.get("message", "unknown Turso error")
                    raise RuntimeError(f"Turso SQL error: {msg}")
            for r in results:
                resp = r.get("response", {})
                if resp.get("type") == "execute":
                    result = resp.get("result", {})
                    cols = [c.get("name", "") for c in result.get("cols", [])]
                    rows = [
                        [_from_cell(cell) for cell in row]
                        for row in result.get("rows", [])
                    ]
                    lrid = result.get("last_insert_rowid")
                    if isinstance(lrid, str):
                        lrid = int(lrid) if lrid else 0
                    rowcount = result.get("affected_row_count", -1)
                    if isinstance(rowcount, str):
                        rowcount = int(rowcount)
                    return cols, rows, lrid, rowcount
            return [], [], None, -1

        def commit(self):
            pass  # each statement auto-commits over HTTP

        def rollback(self):
            pass  # best-effort; HTTP statements are already committed

    class _Cursor:
        """Wraps an _HttpConn so fetchone()/fetchall() return _Row objects."""

        def __init__(self, conn):
            self._conn = conn
            self._cols = []
            self._rows = []
            self._lastrowid = None
            self._rowcount = -1

        def execute(self, sql, params=()):
            cols, rows, lrid, rc = self._conn.execute(sql, params)
            self._cols, self._rows = cols, rows
            self._lastrowid, self._rowcount = lrid, rc
            return self

        def executemany(self, sql, seq_of_params):
            for params in seq_of_params:
                self._conn.execute(sql, params)
            return self

        def executescript(self, sql_script):
            self._conn.executescript(sql_script)
            return self

        def _wrap(self, row):
            return _Row(self._cols, row)

        def fetchone(self):
            return self._wrap(self._rows[0]) if self._rows else None

        def fetchall(self):
            return [self._wrap(r) for r in self._rows]

        def fetchmany(self, size=1):
            return [self._wrap(r) for r in self._rows[:size]]

        @property
        def lastrowid(self):
            return self._lastrowid

        @property
        def rowcount(self):
            return self._rowcount

        @property
        def description(self):
            return [(c, None, None, None, None, None, None) for c in self._cols]

    def _connect():
        conn = getattr(_local, "conn", None)
        if conn is not None:
            return conn
        conn = _HttpConn(os.environ["TURSO_URL"], os.getenv("TURSO_AUTH_TOKEN", ""))
        _local.conn = conn
        return conn

    @contextmanager
    def cursor():
        conn = _connect()
        cur = _Cursor(conn)
        try:
            yield cur
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

    print("[✓] Database mode: CLOUD (Turso over HTTPS, pure Python)", flush=True)


# ============================================================================
#  MODE 1 — LOCAL (pure sqlite3, unchanged)
# ============================================================================
else:
    import sqlite3

    def _connect():
        conn = getattr(_local, "conn", None)
        if conn is not None:
            return conn
        path = Config.DB_PATH
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
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

    print("[✓] Database mode: LOCAL (sqlite3)", flush=True)


# ============================================================================
#  Schema + helpers (identical for both modes)
# ============================================================================
def _columns(table: str):
    with cursor() as c:
        rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def _add_column(table: str, column: str, definition: str):
    cols = _columns(table)
    if column not in cols:
        with cursor() as c:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
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
