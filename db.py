"""SQLite storage for one journal entry per ISO date (YYYY-MM-DD)."""

import os
import sqlite3
from pathlib import Path


def default_path():
    """Follow XDG on Linux, with a sensible home-directory fallback."""
    data_home = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return data_home / "terminal-journal" / "journal.db"


def open_database(path=None):
    path = Path(path) if path is not None else default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL DEFAULT '',
            favorite INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()
    return connection


def get_entry(connection, day):
    return connection.execute(
        "SELECT * FROM entries WHERE date = ?", (day.isoformat(),)
    ).fetchone()


def save_entry(connection, day, content):
    """Update text without changing the original creation time or favorite flag."""
    connection.execute(
        """
        INSERT INTO entries (date, content) VALUES (?, ?)
        ON CONFLICT(date) DO UPDATE SET
            content = excluded.content,
            updated_at = CURRENT_TIMESTAMP
        """,
        (day.isoformat(), content),
    )
    connection.commit()


def entry_days(connection, year, month):
    """Return day numbers with nonempty journal text in the chosen month."""
    prefix = f"{year:04d}-{month:02d}-"
    rows = connection.execute(
        "SELECT date FROM entries WHERE date LIKE ? AND content != ''",
        (prefix + "%",),
    ).fetchall()
    return {int(row["date"][-2:]) for row in rows}
