"""
DataPace Database Layer
=======================
Schema SQLite + fonctions CRUD pour remplacer les fichiers Excel/JSON.
Sert de fondation pour la future API REST.
"""
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from .config import DB_FILE


SCHEMA = """
-- ── Events ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    city            TEXT DEFAULT '',
    country         TEXT DEFAULT '',
    distance        TEXT CHECK(distance IN ('MARATHON','SEMI','10KM','AUTRE')) NOT NULL,
    period          TEXT DEFAULT '',
    badge           TEXT CHECK(badge IN ('WMM','ASO','Autre')) DEFAULT 'Autre',
    first_edition   INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, distance)
);

-- ── Finishers (one row per event per year) ──────────────────────────────────
CREATE TABLE IF NOT EXISTS finishers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER NOT NULL REFERENCES events(id),
    year        INTEGER NOT NULL CHECK(year >= 1950 AND year <= 2030),
    count       INTEGER,  -- NULL = unknown, -1 = cancelled, -2 = elite only
    source      TEXT DEFAULT '',
    confidence  REAL DEFAULT 1.0,
    collected   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, year)
);

-- ── Winner times ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS winners (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER NOT NULL REFERENCES events(id),
    year        INTEGER NOT NULL,
    men_time    TEXT,     -- HH:MM:SS format
    women_time  TEXT,     -- HH:MM:SS format
    source      TEXT DEFAULT '',
    UNIQUE(event_id, year)
);

-- ── Average times ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS avg_times (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id    INTEGER NOT NULL REFERENCES events(id),
    year        INTEGER NOT NULL,
    avg_time    TEXT,     -- HH:MM:SS
    men_time    TEXT,
    women_time  TEXT,
    source      TEXT DEFAULT '',
    UNIQUE(event_id, year)
);

-- ── Crawl log (audit trail) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crawl_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL,
    event_name  TEXT,
    race_name   TEXT,
    distance_m  INTEGER,
    year        INTEGER,
    finishers   INTEGER,
    avg_time    TEXT,
    raw_json    TEXT,
    crawled_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_finishers_event_year ON finishers(event_id, year);
CREATE INDEX IF NOT EXISTS idx_winners_event_year ON winners(event_id, year);
CREATE INDEX IF NOT EXISTS idx_avg_times_event_year ON avg_times(event_id, year);
CREATE INDEX IF NOT EXISTS idx_events_name ON events(name);
CREATE INDEX IF NOT EXISTS idx_events_distance ON events(distance);
CREATE INDEX IF NOT EXISTS idx_crawl_log_source ON crawl_log(source);
"""


@contextmanager
def get_db(db_path: Optional[Path] = None):
    """Context manager pour obtenir une connexion SQLite."""
    path = db_path or DB_FILE
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        conn.execute("PRAGMA journal_mode=DELETE")  # fallback for mounted FS
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None):
    """Cree toutes les tables si elles n'existent pas."""
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA)
    print(f"Base de donnees initialisee : {db_path or DB_FILE}")


def get_or_create_event(conn, name: str, distance: str, city: str = "",
                        period: str = "", badge: str = "Autre") -> int:
    """Retourne l'id d'un evenement, le cree s'il n'existe pas.
    La cle unique est (name, distance) pour gerer les evenements multi-distances."""
    row = conn.execute("SELECT id FROM events WHERE name = ? AND distance = ?", (name, distance)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO events (name, distance, city, period, badge) VALUES (?, ?, ?, ?, ?)",
        (name, distance, city, period, badge)
    )
    return cur.lastrowid


def upsert_finisher(conn, event_id: int, year: int, count: int,
                    source: str = "", confidence: float = 1.0, skip_existing: bool = True):
    """Insere ou met a jour un finisher count. Respecte la regle SKIP par defaut."""
    if skip_existing:
        existing = conn.execute(
            "SELECT count FROM finishers WHERE event_id = ? AND year = ?",
            (event_id, year)
        ).fetchone()
        if existing and existing["count"] is not None:
            return False  # SKIP — ne jamais ecraser
    conn.execute(
        """INSERT INTO finishers (event_id, year, count, source, confidence)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(event_id, year)
           DO UPDATE SET count=excluded.count, source=excluded.source,
                         confidence=excluded.confidence, collected=CURRENT_TIMESTAMP""",
        (event_id, year, count, source, confidence)
    )
    return True


def upsert_winner(conn, event_id: int, year: int,
                  men_time: Optional[str] = None, women_time: Optional[str] = None,
                  source: str = ""):
    """Insere ou met a jour les temps vainqueurs."""
    conn.execute(
        """INSERT INTO winners (event_id, year, men_time, women_time, source)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(event_id, year)
           DO UPDATE SET men_time=COALESCE(excluded.men_time, winners.men_time),
                         women_time=COALESCE(excluded.women_time, winners.women_time),
                         source=excluded.source""",
        (event_id, year, men_time, women_time, source)
    )


def upsert_avg_time(conn, event_id: int, year: int,
                    avg_time: Optional[str] = None,
                    men_time: Optional[str] = None,
                    women_time: Optional[str] = None,
                    source: str = ""):
    """Insere ou met a jour un temps moyen."""
    conn.execute(
        """INSERT INTO avg_times (event_id, year, avg_time, men_time, women_time, source)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(event_id, year)
           DO UPDATE SET avg_time=COALESCE(excluded.avg_time, avg_times.avg_time),
                         men_time=COALESCE(excluded.men_time, avg_times.men_time),
                         women_time=COALESCE(excluded.women_time, avg_times.women_time),
                         source=excluded.source""",
        (event_id, year, avg_time, men_time, women_time, source)
    )


def log_crawl(conn, source: str, event_name: str, race_name: str = "",
              distance_m: int = 0, year: int = 0, finishers: int = 0,
              avg_time: Optional[str] = None, raw_json: Optional[str] = None):
    """Log chaque resultat de crawl pour tracabilite."""
    conn.execute(
        """INSERT INTO crawl_log (source, event_name, race_name, distance_m,
                                  year, finishers, avg_time, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (source, event_name, race_name, distance_m, year, finishers, avg_time, raw_json)
    )


def get_stats(db_path: Optional[Path] = None) -> dict:
    """Retourne des statistiques sur la base de donnees."""
    with get_db(db_path) as conn:
        events = conn.execute("SELECT COUNT(*) as n FROM events").fetchone()["n"]
        fin = conn.execute("SELECT COUNT(*) as n FROM finishers WHERE count > 0").fetchone()["n"]
        winners = conn.execute("SELECT COUNT(*) as n FROM winners").fetchone()["n"]
        avg = conn.execute("SELECT COUNT(*) as n FROM avg_times").fetchone()["n"]
        crawls = conn.execute("SELECT COUNT(*) as n FROM crawl_log").fetchone()["n"]
        sources = conn.execute(
            "SELECT source, COUNT(*) as n FROM crawl_log GROUP BY source ORDER BY n DESC"
        ).fetchall()
    return {
        "events": events,
        "finisher_entries": fin,
        "winner_entries": winners,
        "avg_time_entries": avg,
        "crawl_log_entries": crawls,
        "sources": {row["source"]: row["n"] for row in sources},
    }
