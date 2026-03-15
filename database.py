from __future__ import annotations

import hashlib
import hmac
import math
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


DB_PATH = Path(__file__).resolve().with_name('wardrobe_system.db')
FRONTEND_CATEGORIES = ('Top 👚', 'Bottom 🩳', 'Outerwear 🧥', 'Accessories ⌚')
DEFAULT_LOCATION = ('Australia', 'Melbourne')
PASSWORD_SCHEME = 'pbkdf2_sha256'
PASSWORD_ITERATIONS = 390000

WARDROBE_CATEGORY_BY_CLOTH_TYPE = {
    '👕 T-Shirt': 'Top 👚',
    '👗 Dress': 'Top 👚',
    '🧶 Sweater': 'Top 👚',
    '🩲 Shorts': 'Bottom 🩳',
    '👗 Skirt': 'Bottom 🩳',
    '👖 Jeans': 'Bottom 🩳',
    '👖 Pants': 'Bottom 🩳',
    '🧥 Blazer': 'Outerwear 🧥',
    '🧥 Jacket': 'Outerwear 🧥',
    '🥼 Coat': 'Outerwear 🧥',
    '🧥 Hoodie': 'Outerwear 🧥',
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _format_location(country: str, city: str) -> str:
    parts = [part.strip() for part in (city, country) if part and part.strip()]
    return ', '.join(parts)


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt.encode('utf-8'), PASSWORD_ITERATIONS
    ).hex()
    return f'{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${digest}'


def _is_hashed_password(value: str) -> bool:
    return value.startswith(f'{PASSWORD_SCHEME}$')


def _verify_password(password: str, stored_value: str) -> bool:
    if not stored_value:
        return False

    if not _is_hashed_password(stored_value):
        return hmac.compare_digest(stored_value, password)

    try:
        _, iteration_text, salt, stored_digest = stored_value.split('$', 3)
        iterations = int(iteration_text)
    except ValueError:
        return False

    computed_digest = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations
    ).hex()
    return hmac.compare_digest(stored_digest, computed_digest)


def _ensure_user_columns(conn: sqlite3.Connection) -> None:
    existing_columns = {
        row['name'] for row in conn.execute('PRAGMA table_info(users)').fetchall()
    }
    column_definitions = {
        'first_name': "TEXT DEFAULT ''",
        'auth_provider': "TEXT NOT NULL DEFAULT 'local'",
        'google_subject': 'TEXT',
        'saved_country': "TEXT DEFAULT ''",
        'saved_city': "TEXT DEFAULT ''",
        'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    }

    for column_name, column_definition in column_definitions.items():
        if column_name not in existing_columns:
            conn.execute(
                f'ALTER TABLE users ADD COLUMN {column_name} {column_definition}'
            )

    conn.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_subject ON users(google_subject) WHERE google_subject IS NOT NULL'
    )


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                first_name TEXT DEFAULT '',
                auth_provider TEXT NOT NULL DEFAULT 'local',
                google_subject TEXT,
                location TEXT DEFAULT '',
                saved_country TEXT DEFAULT '',
                saved_city TEXT DEFAULT '',
                last_at_temp REAL,
                last_weather_update TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_user_columns(conn)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS clothes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                wardrobe_category TEXT NOT NULL,
                cloth_type TEXT,
                color TEXT,
                image_data BLOB,
                min_temp REAL,
                max_temp REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )
        conn.commit()


def _resolve_user(email: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            'SELECT * FROM users WHERE username = ?', (_normalize_email(email),)
        ).fetchone()


def _resolve_user_id(email: str) -> int:
    user = _resolve_user(email)
    if user is None:
        raise ValueError(f"User '{email}' was not found")
    return int(user['id'])


def _temp_range_for_cloth_type(cloth_type: str | None) -> tuple[float, float]:
    temp_ranges = {
        '👕 T-Shirt': (22, 40),
        '🧥 Hoodie': (10, 20),
        '🧥 Blazer': (15, 25),
        '🥼 Coat': (-5, 12),
        '🩲 Shorts': (25, 45),
        '👖 Jeans': (12, 28),
        '👖 Pants': (12, 28),
        '👗 Dress': (20, 35),
        '👗 Skirt': (20, 35),
        '🧶 Sweater': (8, 20),
        '🧥 Jacket': (8, 20),
    }
    return temp_ranges.get(cloth_type, (15, 30))


def calculate_apparent_temp(t: float, rh: float, ws: float) -> float:
    e = (rh / 100) * 6.105 * math.exp((17.27 * t) / (237.7 + t))
    at = t + 0.33 * e - 0.70 * ws - 4.00
    return round(at, 1)


def register_user(
    first_name: str,
    email: str,
    password: str,
    country: str = DEFAULT_LOCATION[0],
    city: str = DEFAULT_LOCATION[1],
) -> bool:
    clean_first_name = first_name.strip()
    normalized_email = _normalize_email(email)
    if not clean_first_name or not normalized_email or not password:
        return False

    password_hash = _hash_password(password)
    location = _format_location(country, city)

    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (
                    username, password, first_name, auth_provider, location, saved_country, saved_city
                )
                VALUES (?, ?, ?, 'local', ?, ?, ?)
                """,
                (
                    normalized_email,
                    password_hash,
                    clean_first_name,
                    location,
                    country.strip(),
                    city.strip(),
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def authenticate_user(email: str, password: str) -> dict[str, str] | None:
    normalized_email = _normalize_email(email)
    with get_connection() as conn:
        user = conn.execute(
            'SELECT id, username, password, first_name, auth_provider FROM users WHERE username = ?',
            (normalized_email,),
        ).fetchone()

        if user is None or user['auth_provider'] != 'local':
            return None

        if not _verify_password(password, user['password']):
            return None

        if not _is_hashed_password(user['password']):
            conn.execute(
                'UPDATE users SET password = ? WHERE id = ?',
                (_hash_password(password), int(user['id'])),
            )
            conn.commit()

        return {
            'id': str(user['id']),
            'email': user['username'],
            'first_name': (user['first_name'] or '').strip() or 'User',
            'auth_provider': user['auth_provider'],
        }


def verify_user(email: str, password: str) -> bool:
    return authenticate_user(email, password) is not None


def reset_password(email: str, new_password: str) -> bool:
    """Reset the password for an existing local account."""
    normalized_email = _normalize_email(email)
    with get_connection() as conn:
        user = conn.execute(
            'SELECT id, auth_provider FROM users WHERE username = ?',
            (normalized_email,),
        ).fetchone()
        if user is None or user['auth_provider'] != 'local':
            return False
        conn.execute(
            'UPDATE users SET password = ? WHERE id = ?',
            (_hash_password(new_password), int(user['id'])),
        )
        conn.commit()
        return True


def get_user_profile(email: str) -> dict[str, str] | None:
    user = _resolve_user(email)
    if user is None:
        return None

    return {
        'id': str(user['id']),
        'email': user['username'],
        'first_name': (user['first_name'] or '').strip() or 'User',
        'auth_provider': user['auth_provider'] or 'local',
    }


def update_user_name(email: str, new_first_name: str) -> bool:
    normalized_email = _normalize_email(email)
    clean_name = new_first_name.strip()
    if not normalized_email or not clean_name:
        return False
    with get_connection() as conn:
        cursor = conn.execute(
            'UPDATE users SET first_name = ? WHERE username = ?',
            (clean_name, normalized_email),
        )
        conn.commit()
        return cursor.rowcount > 0


def upsert_google_user(
    email: str, first_name: str, google_subject: str | None = None
) -> dict[str, str] | None:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None

    clean_first_name = first_name.strip() or 'Google user'

    with get_connection() as conn:
        existing = conn.execute(
            'SELECT id FROM users WHERE username = ?', (normalized_email,)
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO users (username, password, first_name, auth_provider, google_subject)
                VALUES (?, '', ?, 'google', ?)
                """,
                (normalized_email, clean_first_name, google_subject),
            )
        else:
            conn.execute(
                """
                UPDATE users
                SET first_name = ?, google_subject = COALESCE(?, google_subject)
                WHERE username = ?
                """,
                (clean_first_name, google_subject, normalized_email),
            )

        conn.commit()

    return get_user_profile(normalized_email)


def login_user(email: str, password: str) -> int | None:
    profile = authenticate_user(email, password)
    if profile is None:
        return None
    return int(profile['id'])


def change_user_password(user_id: int, old_pwd: str, new_pwd: str) -> bool:
    with get_connection() as conn:
        user = conn.execute(
            'SELECT password, auth_provider FROM users WHERE id = ?', (user_id,)
        ).fetchone()

        if user is None or user['auth_provider'] != 'local':
            return False

        if not _verify_password(old_pwd, user['password']):
            return False

        conn.execute(
            'UPDATE users SET password = ? WHERE id = ?',
            (_hash_password(new_pwd), user_id),
        )
        conn.commit()
        return True


def save_user_location(email: str, country: str, city: str) -> bool:
    normalized_email = _normalize_email(email)
    clean_country = country.strip()
    clean_city = city.strip()

    if not normalized_email:
        return False

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE users
            SET location = ?, saved_country = ?, saved_city = ?
            WHERE username = ?
            """,
            (
                _format_location(clean_country, clean_city),
                clean_country,
                clean_city,
                normalized_email,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_user_location(email: str) -> dict[str, str] | None:
    user = _resolve_user(email)
    if user is None:
        return None

    country = (user['saved_country'] or '').strip() or DEFAULT_LOCATION[0]
    city = (user['saved_city'] or '').strip() or DEFAULT_LOCATION[1]
    return {'country': country, 'city': city}


def update_user_location(user_id: int, new_location: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET location = ?, saved_city = ?, last_weather_update = NULL
            WHERE id = ?
            """,
            (new_location.strip(), new_location.strip(), user_id),
        )
        conn.commit()


def update_weather_cache(user_id: int, apparent_temp: float) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE users
            SET last_at_temp = ?, last_weather_update = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (apparent_temp, user_id),
        )
        conn.commit()


def get_smart_weather(user_id: int) -> float:
    with get_connection() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

        if user is None:
            raise ValueError(f'User with id {user_id} was not found')

        if user['last_weather_update']:
            last_time = datetime.strptime(
                user['last_weather_update'], '%Y-%m-%d %H:%M:%S'
            )
            if datetime.now() - last_time < timedelta(minutes=30):
                return float(user['last_at_temp'])

    return 20.5


def add_clothing_item(
    email: str | None,
    item_name: str,
    cloth_type: str | None = None,
    color: str | None = None,
    image_data: bytes | None = None,
    wardrobe_category: str | None = None,
    username: str | None = None,
) -> int:
    clean_name = item_name.strip()
    if not clean_name:
        raise ValueError('Item name is required')

    resolved_email = (email or username or '').strip()
    if not resolved_email:
        raise ValueError('Email is required')

    user_id = _resolve_user_id(resolved_email)
    resolved_category = wardrobe_category or WARDROBE_CATEGORY_BY_CLOTH_TYPE.get(
        cloth_type, 'Accessories ⌚'
    )
    min_temp, max_temp = _temp_range_for_cloth_type(cloth_type)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO clothes (
                user_id, item_name, wardrobe_category, cloth_type, color, image_data, min_temp, max_temp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                clean_name,
                resolved_category,
                cloth_type,
                color,
                image_data,
                min_temp,
                max_temp,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_clothing_item(
    email: str,
    clothing_id: int,
    item_name: str,
    cloth_type: str | None = None,
    color: str | None = None,
    wardrobe_category: str | None = None,
) -> bool:
    clean_name = item_name.strip()
    if not clean_name:
        return False

    user_id = _resolve_user_id(email)
    resolved_category = wardrobe_category or WARDROBE_CATEGORY_BY_CLOTH_TYPE.get(
        cloth_type, 'Accessories ⌚'
    )
    min_temp, max_temp = _temp_range_for_cloth_type(cloth_type)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE clothes
            SET item_name = ?, wardrobe_category = ?, cloth_type = ?, color = ?, min_temp = ?, max_temp = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                clean_name,
                resolved_category,
                cloth_type,
                color,
                min_temp,
                max_temp,
                clothing_id,
                user_id,
            ),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_clothing_item(email: str, clothing_id: int) -> bool:
    user_id = _resolve_user_id(email)
    with get_connection() as conn:
        cursor = conn.execute(
            'DELETE FROM clothes WHERE id = ? AND user_id = ?',
            (clothing_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def add_new_clothes(
    user_id: int, category: str, color: str | None, img_path: str | None
) -> None:
    min_t, max_t = _temp_range_for_cloth_type(category)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO clothes (
                user_id, item_name, wardrobe_category, cloth_type, color, image_data, min_temp, max_temp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                category,
                WARDROBE_CATEGORY_BY_CLOTH_TYPE.get(category, 'Accessories ⌚'),
                category,
                color,
                img_path,
                min_t,
                max_t,
            ),
        )
        conn.commit()


def get_user_catalog(email: str) -> dict[str, list[dict[str, object]]]:
    user_id = _resolve_user_id(email)
    catalog: dict[str, list[dict[str, object]]] = {
        category: [] for category in FRONTEND_CATEGORIES
    }

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, item_name, wardrobe_category, cloth_type, color, image_data
            FROM clothes
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()

    for row in rows:
        category = row['wardrobe_category'] or 'Accessories ⌚'
        catalog.setdefault(category, [])
        catalog[category].append(
            {
                'id': int(row['id']),
                'name': row['item_name'],
                'image': row['image_data'],
                'color': row['color'],
                'cloth_type': row['cloth_type'],
            }
        )

    return catalog


def get_outfit_suggestion(user_id: int):
    at_temp = get_smart_weather(user_id)

    with get_connection() as conn:
        return conn.execute(
            """
            SELECT *
            FROM clothes
            WHERE user_id = ? AND min_temp <= ? AND max_temp >= ?
            ORDER BY id DESC
            """,
            (user_id, at_temp, at_temp),
        ).fetchall()


def remove_clothes(clothes_id: int, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            'DELETE FROM clothes WHERE id = ? AND user_id = ?',
            (clothes_id, user_id),
        )
        conn.commit()


init_db()
