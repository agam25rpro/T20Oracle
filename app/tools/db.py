import sqlite3
from pathlib import Path
from app.config import DB_PATH

_db_path = Path(DB_PATH)

def get_connection() -> sqlite3.Connection:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(_db_path)

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        match_id     TEXT PRIMARY KEY,
        date         TEXT,
        team1        TEXT,
        team2        TEXT,
        venue        TEXT,
        toss_winner  TEXT,
        toss_decision TEXT,
        winner       TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS innings_summary (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id       TEXT,
        batting_team   TEXT,
        total_runs     INTEGER,
        wickets        INTEGER,
        overs          REAL,
        innings_number INTEGER,
        UNIQUE(match_id, innings_number),
        FOREIGN KEY(match_id) REFERENCES matches(match_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_performances (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id       TEXT,
        player         TEXT,
        team           TEXT,
        runs_scored    INTEGER DEFAULT 0,
        balls_faced    INTEGER DEFAULT 0,
        wickets_taken  INTEGER DEFAULT 0,
        balls_bowled   INTEGER DEFAULT 0,
        runs_conceded  INTEGER DEFAULT 0,
        UNIQUE(match_id, player),
        FOREIGN KEY(match_id) REFERENCES matches(match_id)
    )
    """)

    conn.commit()
    conn.close()
