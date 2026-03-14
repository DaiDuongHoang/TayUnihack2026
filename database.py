import math
import sqlite3
from datetime import datetime, timedelta


DB_NAME = "wardrobe_system.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                location TEXT DEFAULT 'Hanoi',
                last_at_temp REAL,
                last_weather_update TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clothes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                color TEXT,
                min_temp REAL,
                max_temp REAL,
                image_path TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        conn.commit()


def calculate_apparent_temp(t, rh, ws):
    e = (rh / 100) * 6.105 * math.exp((17.27 * t) / (237.7 + t))
    at = t + 0.33 * e - 0.70 * ws - 4.00
    return round(at, 1)


def get_smart_weather(user_id):
    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

        if user is None:
            raise ValueError(f"User with id {user_id} was not found")

        if user["last_weather_update"]:
            last_time = datetime.strptime(
                user["last_weather_update"], "%Y-%m-%d %H:%M:%S"
            )
            if datetime.now() - last_time < timedelta(minutes=30):
                return user["last_at_temp"]

    return 20.5


def change_user_password(user_id, old_pwd, new_pwd):
    with get_connection() as conn:
        user = conn.execute(
            "SELECT password FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        if user is None or user["password"] != old_pwd:
            return False

        conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_pwd, user_id))
        conn.commit()
        return True


def add_new_clothes(user_id, category, color, img_path):
    temp_ranges = {
        "T-shirt": (22, 40),
        "Hoodie": (10, 20),
        "Blazer": (15, 25),
        "Coat": (-5, 12),
        "Short": (25, 45),
    }
    min_t, max_t = temp_ranges.get(category, (15, 30))

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO clothes (user_id, category, color, min_temp, max_temp, image_path)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, category, color, min_t, max_t, img_path),
        )
        conn.commit()


def get_outfit_suggestion(user_id):
    at_temp = get_smart_weather(user_id)

    with get_connection() as conn:
        query = """
            SELECT *
            FROM clothes
            WHERE user_id = ? AND min_temp <= ? AND max_temp >= ?
        """
        return conn.execute(query, (user_id, at_temp, at_temp)).fetchall()


def register_user(username, password, location="Melbourne"):
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password, location) VALUES (?, ?, ?)",
                (username, password, location),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def login_user(username, password):
    with get_connection() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
        return user["id"] if user else None


def remove_clothes(clothes_id, user_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM clothes WHERE id = ? AND user_id = ?",
            (clothes_id, user_id),
        )
        conn.commit()


def update_user_location(user_id, new_location):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET location = ?, last_weather_update = NULL
            WHERE id = ?
            """,
            (new_location, user_id),
        )
        conn.commit()
