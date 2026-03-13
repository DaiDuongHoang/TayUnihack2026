"""
database.py – SQLite CRUD operations for the virtual wardrobe.

Tables
------
wardrobe_items
    id          INTEGER PRIMARY KEY AUTOINCREMENT
    name        TEXT    – human-readable label (e.g. "Blue Hoodie")
    category    TEXT    – clothing category (e.g. "top", "bottom", "shoes")
    image_path  TEXT    – path to the stored image file
    tags        TEXT    – comma-separated descriptive tags (e.g. "casual,warm")
    added_at    TEXT    – ISO-8601 timestamp
"""

import sqlite3
from datetime import datetime, timezone

DB_PATH = "wardrobe.db"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create the wardrobe_items table if it does not already exist."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wardrobe_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                category   TEXT    NOT NULL,
                image_path TEXT,
                tags       TEXT    DEFAULT '',
                added_at   TEXT    NOT NULL
            )
            """
        )
        conn.commit()


def add_item(
    name: str,
    category: str,
    image_path: str = "",
    tags: str = "",
    db_path: str = DB_PATH,
) -> int:
    """Insert a new clothing item and return its row id."""
    added_at = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO wardrobe_items (name, category, image_path, tags, added_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, category, image_path, tags, added_at),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_items(db_path: str = DB_PATH) -> list[dict]:
    """Return all wardrobe items as a list of dicts."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM wardrobe_items ORDER BY added_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def delete_item(item_id: int, db_path: str = DB_PATH) -> None:
    """Delete a wardrobe item by its id."""
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM wardrobe_items WHERE id = ?", (item_id,))
        conn.commit()
