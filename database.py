"""
Database access, schema definition, and connection management for Emoji Team Generator.
Uses SQLite with foreign key enforcement and row factory.
"""

import sqlite3
import os
from flask import g, current_app


def connect_db(db_path=None):
    """
    Creates and returns a new database connection with foreign keys enabled
    and row factory configured for dictionary-like column access.
    """
    if db_path is None:
        db_path = current_app.config["DATABASE_PATH"]

    # Ensure parent directory exists for file-based databases
    if db_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    conn = sqlite3.connect(
        db_path,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_db():
    """Returns the database connection associated with the current Flask request context."""
    if "db" not in g:
        g.db = connect_db()
    return g.db


def close_db(e=None):
    """Closes the current request's database connection if one was opened."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app=None):
    """
    Initializes database tables, indexes, and a default session if absent.
    Can be run within Flask app context or by passing an app instance.
    """
    if app:
        with app.app_context():
            _execute_init(app.config["DATABASE_PATH"])
    else:
        _execute_init(current_app.config["DATABASE_PATH"])


def _execute_init(db_path):
    conn = connect_db(db_path)
    try:
        with conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_name TEXT NOT NULL,
                    expected_participants INTEGER DEFAULT 20,
                    team_count INTEGER DEFAULT 4,
                    max_team_size INTEGER DEFAULT 5,
                    team_formation_mode TEXT DEFAULT 'team_count',
                    registration_status TEXT DEFAULT 'open',
                    allow_emoji_reuse INTEGER DEFAULT 0,
                    results_published INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    team_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    selected_emoji TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_session_normalized_name UNIQUE (session_id, normalized_name)
                );

                CREATE INDEX IF NOT EXISTS idx_participants_session ON participants(session_id);
                CREATE INDEX IF NOT EXISTS idx_participants_emoji ON participants(session_id, selected_emoji);
                CREATE INDEX IF NOT EXISTS idx_participants_token ON participants(token);
                CREATE INDEX IF NOT EXISTS idx_teams_session ON teams(session_id);
            """)

            # Seed default session if no session exists
            cur = conn.execute("SELECT id FROM sessions LIMIT 1")
            if not cur.fetchone():
                conn.execute("""
                    INSERT INTO sessions (
                        session_name,
                        expected_participants,
                        team_count,
                        max_team_size,
                        team_formation_mode,
                        registration_status,
                        allow_emoji_reuse,
                        results_published
                    ) VALUES (
                        'Emoji Team Generator #1',
                        20,
                        4,
                        5,
                        'team_count',
                        'open',
                        0,
                        0
                    )
                """)
    finally:
        conn.close()


def get_active_session(conn=None):
    """Returns the most recent active session as a dict."""
    db = conn or get_db()
    row = db.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def normalize_participant_name(name: str) -> str:
    """
    Normalizes a name for uniqueness checks:
    Collapses multiple spaces, strips edges, converts to lowercase.
    e.g. '  Arun   Kumar  ' -> 'arun kumar'
    """
    if not name:
        return ""
    return " ".join(name.strip().split()).lower()
