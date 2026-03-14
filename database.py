# database.py
import sqlite3

DB_NAME = "database.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    with get_connection() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS clothes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,   -- Hoodie, T-shirt, Short, Pants
            color TEXT,
            weather_type TEXT, -- Cold, Hot, Rainy
            image_path TEXT
        )""")


def get_all_clothes():
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM clothes")
        return cursor.fetchall()
