from __future__ import annotations

import hashlib
import hmac
import math
import os
import secrets
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(__file__).resolve().with_name('wardrobe_system.db')
UPLOAD_FOLDER = Path('uploads/wardrobe')
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

OPENWEATHER_API_KEY: str = os.getenv('OPENWEATHER_API_KEY', '')
PASSWORD_SCHEME = 'pbkdf2_sha256'
PASSWORD_ITERATIONS = 390000

FRONTEND_CATEGORIES = ('Top 👚', 'Bottom 🩳', 'Outerwear 🧥', 'Accessories ⌚')
DEFAULT_LOCATION = ('Australia', 'Melbourne')

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

AI_CATEGORY_MAPPING: dict[str, str] = {
    't-shirt': 'Top 👚',
    'dress': 'Top 👚',
    'sweater': 'Top 👚',
    'shorts': 'Bottom 🩳',
    'skirt': 'Bottom 🩳',
    'jeans': 'Bottom 🩳',
    'pants': 'Bottom 🩳',
    'blazer': 'Outerwear 🧥',
    'jacket': 'Outerwear 🧥',
    'coat': 'Outerwear 🧥',
    'hoodie': 'Outerwear 🧥',
}

_TEMP_RANGES: dict[str, tuple[float, float]] = {
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
    't-shirt': (22, 40),
    'hoodie': (10, 20),
    'blazer': (15, 25),
    'coat': (-5, 12),
    'shorts': (25, 45),
    'jeans': (12, 28),
    'pants': (12, 28),
    'dress': (20, 35),
    'skirt': (20, 35),
    'sweater': (8, 20),
    'jacket': (8, 20),
}


def _temp_range_for_cloth_type(cloth_type: str | None) -> tuple[float, float]:
    return _TEMP_RANGES.get(cloth_type or '', (15, 30))


_category_model = None
_color_model = None


def _get_category_model():
    global _category_model
    if _category_model is None:
        from ultralytics import YOLO  # lazy import to avoid startup cost

        model_path = Path('runs_category_classifier/yolov8n_category/weights/best.pt')
        if not model_path.exists():
            raise FileNotFoundError(f'Category model not found: {model_path}')
        _category_model = YOLO(str(model_path))
    return _category_model


def _get_color_model():
    global _color_model
    if _color_model is None:
        from ultralytics import YOLO  # lazy import to avoid startup cost

        model_path = Path('runs_color_classifier/yolov8m_color/weights/best.pt')
        if not model_path.exists():
            raise FileNotFoundError(f'Color model not found: {model_path}')
        _color_model = YOLO(str(model_path))
    return _color_model


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _format_location(country: str, city: str) -> str:
    parts = [p.strip() for p in (city, country) if p and p.strip()]
    return ', '.join(parts)


def _ensure_user_columns(conn: sqlite3.Connection) -> None:
    existing = {
        row['name'] for row in conn.execute('PRAGMA table_info(users)').fetchall()
    }
    additions = {
        'first_name': "TEXT DEFAULT ''",
        'auth_provider': "TEXT NOT NULL DEFAULT 'local'",
        'google_subject': 'TEXT',
        'saved_country': "TEXT DEFAULT ''",
        'saved_city': "TEXT DEFAULT ''",
        'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    }
    for col, defn in additions.items():
        if col not in existing:
            conn.execute(f'ALTER TABLE users ADD COLUMN {col} {defn}')
    conn.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_subject '
        'ON users(google_subject) WHERE google_subject IS NOT NULL'
    )


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                username            TEXT UNIQUE NOT NULL,
                password            TEXT NOT NULL,
                first_name          TEXT DEFAULT '',
                auth_provider       TEXT NOT NULL DEFAULT 'local',
                google_subject      TEXT,
                location            TEXT DEFAULT '',
                saved_country       TEXT DEFAULT '',
                saved_city          TEXT DEFAULT '',
                last_at_temp        REAL,
                last_weather_update TIMESTAMP,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _ensure_user_columns(conn)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS clothes (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           INTEGER NOT NULL,
                item_name         TEXT NOT NULL,
                wardrobe_category TEXT NOT NULL,
                cloth_type        TEXT,
                color             TEXT,
                image_data        TEXT,
                min_temp          REAL,
                max_temp          REAL,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()
    print('[+] Database initialized.')


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt.encode('utf-8'), PASSWORD_ITERATIONS
    ).hex()
    return f'{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${digest}'


def _is_hashed_password(value: str) -> bool:
    return value.startswith(f'{PASSWORD_SCHEME}$')


def _verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    if not _is_hashed_password(stored):
        return hmac.compare_digest(stored, password)
    try:
        _, iter_str, salt, stored_digest = stored.split('$', 3)
        computed = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt.encode('utf-8'), int(iter_str)
        ).hex()
        return hmac.compare_digest(stored_digest, computed)
    except ValueError:
        return False


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


def calculate_apparent_temp(t: float, rh: float, ws: float) -> float:
    e = (rh / 100) * 6.105 * math.exp((17.27 * t) / (237.7 + t))
    return round(t + 0.33 * e - 0.70 * ws - 4.00, 1)


def _fetch_weather(location: str) -> float | None:
    """Call OpenWeatherMap outside any DB connection; return apparent temp or None."""
    if not OPENWEATHER_API_KEY:
        print('[weather] OPENWEATHER_API_KEY not set in .env')
        return None
    try:
        url = (
            'http://api.openweathermap.org/data/2.5/weather'
            f'?q={location}&appid={OPENWEATHER_API_KEY}&units=metric'
        )
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        return calculate_apparent_temp(
            data['main']['temp'],
            data['main']['humidity'],
            data['wind']['speed'],
        )
    except Exception as exc:
        print(f'[weather] fetch failed: {exc}')
        return None


def update_weather_cache(user_id: int, apparent_temp: float) -> None:
    with get_connection() as conn:
        conn.execute(
            'UPDATE users SET last_at_temp = ?, last_weather_update = CURRENT_TIMESTAMP WHERE id = ?',
            (apparent_temp, user_id),
        )
        conn.commit()


def get_smart_weather(user_id: int) -> float:
    """Return cached apparent temp if < 30 min old, otherwise refresh from API."""
    with get_connection() as conn:
        user = conn.execute(
            'SELECT location, last_at_temp, last_weather_update FROM users WHERE id = ?',
            (user_id,),
        ).fetchone()

    if user is None:
        raise ValueError(f'User with id {user_id} was not found')

    if user['last_weather_update'] and user['last_at_temp'] is not None:
        last = datetime.strptime(user['last_weather_update'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() - last < timedelta(minutes=30):
            return float(user['last_at_temp'])

    location = user['location'] or f'{DEFAULT_LOCATION[1]}, {DEFAULT_LOCATION[0]}'
    at_temp = _fetch_weather(location)

    if at_temp is None:
        return float(user['last_at_temp']) if user['last_at_temp'] is not None else 20.5

    update_weather_cache(user_id, at_temp)
    return at_temp


def register_user(
    first_name: str,
    email: str,
    password: str,
    country: str = DEFAULT_LOCATION[0],
    city: str = DEFAULT_LOCATION[1],
) -> bool:
    clean_name = first_name.strip()
    normalized_email = _normalize_email(email)
    if not clean_name or not normalized_email or not password:
        return False

    with get_connection() as conn:
        try:
            conn.execute(
                """
                INSERT INTO users
                    (username, password, first_name, auth_provider, location, saved_country, saved_city)
                VALUES (?, ?, ?, 'local', ?, ?, ?)
                """,
                (
                    normalized_email,
                    _hash_password(password),
                    clean_name,
                    _format_location(country, city),
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


def login_user(email: str, password: str) -> int | None:
    profile = authenticate_user(email, password)
    return int(profile['id']) if profile else None


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
    clean = new_first_name.strip()
    if not clean:
        return False
    with get_connection() as conn:
        cur = conn.execute(
            'UPDATE users SET first_name = ? WHERE username = ?',
            (clean, _normalize_email(email)),
        )
        conn.commit()
        return cur.rowcount > 0


def upsert_google_user(
    email: str, first_name: str, google_subject: str | None = None
) -> dict[str, str] | None:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return None
    clean_name = first_name.strip() or 'Google user'

    with get_connection() as conn:
        existing = conn.execute(
            'SELECT id FROM users WHERE username = ?', (normalized_email,)
        ).fetchone()

        if existing is None:
            conn.execute(
                'INSERT INTO users (username, password, first_name, auth_provider, google_subject) '
                "VALUES (?, '', ?, 'google', ?)",
                (normalized_email, clean_name, google_subject),
            )
        else:
            conn.execute(
                'UPDATE users SET first_name = ?, google_subject = COALESCE(?, google_subject) '
                'WHERE username = ?',
                (clean_name, google_subject, normalized_email),
            )
        conn.commit()

    return get_user_profile(normalized_email)


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


def reset_password(email: str, new_password: str) -> bool:
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


def save_user_location(email: str, country: str, city: str) -> bool:
    normalized_email = _normalize_email(email)
    if not normalized_email:
        return False
    with get_connection() as conn:
        cur = conn.execute(
            'UPDATE users SET location = ?, saved_country = ?, saved_city = ? WHERE username = ?',
            (
                _format_location(country.strip(), city.strip()),
                country.strip(),
                city.strip(),
                normalized_email,
            ),
        )
        conn.commit()
        return cur.rowcount > 0


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
            'UPDATE users SET location = ?, saved_city = ?, last_weather_update = NULL WHERE id = ?',
            (new_location.strip(), new_location.strip(), user_id),
        )
        conn.commit()


def add_clothing_item(
    email: str | None,
    item_name: str,
    cloth_type: str | None = None,
    color: str | None = None,
    image_data: str | None = None,
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
        cur = conn.execute(
            """
            INSERT INTO clothes
                (user_id, item_name, wardrobe_category, cloth_type, color, image_data, min_temp, max_temp)
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
        return int(cur.lastrowid)


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
        cur = conn.execute(
            """
            UPDATE clothes
            SET item_name = ?, wardrobe_category = ?, cloth_type = ?,
                color = ?, min_temp = ?, max_temp = ?
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
        return cur.rowcount > 0


def delete_clothing_item(email: str, clothing_id: int) -> bool:
    user_id = _resolve_user_id(email)
    with get_connection() as conn:
        cur = conn.execute(
            'DELETE FROM clothes WHERE id = ? AND user_id = ?', (clothing_id, user_id)
        )
        conn.commit()
        return cur.rowcount > 0


def remove_clothes(clothes_id: int, user_id: int) -> None:
    """Alias used by older Streamlit pages."""
    with get_connection() as conn:
        conn.execute(
            'DELETE FROM clothes WHERE id = ? AND user_id = ?', (clothes_id, user_id)
        )
        conn.commit()


def add_new_clothes(
    user_id: int, category: str, color: str | None, img_path: str | None
) -> None:
    """Legacy helper used by older Streamlit pages."""
    min_t, max_t = _temp_range_for_cloth_type(category)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO clothes
                (user_id, item_name, wardrobe_category, cloth_type, color, image_data, min_temp, max_temp)
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


def process_and_add_clothing(
    user_id: int,
    image_path: str,
    custom_name: str | None = None,
) -> tuple[bool, str | None, str | None]:
    """
    Run YOLO inference on image_path, map to wardrobe_category,
    copy file to UPLOAD_FOLDER, insert into clothes.

    Returns (success, wardrobe_category, color_name).
    """
    try:
        cat_results = _get_category_model().predict(
            image_path, imgsz=224, verbose=False
        )
        raw_cat = cat_results[0].names[cat_results[0].probs.top1].lower()

        col_results = _get_color_model().predict(image_path, imgsz=224, verbose=False)
        color_name = col_results[0].names[col_results[0].probs.top1]

        wardrobe_category = AI_CATEGORY_MAPPING.get(raw_cat, 'Accessories ⌚')
        min_t, max_t = _temp_range_for_cloth_type(raw_cat)

        ext = Path(image_path).suffix
        unique_name = f'{user_id}_{secrets.token_hex(8)}{ext}'
        save_path = str(UPLOAD_FOLDER / unique_name)
        shutil.copy2(image_path, save_path)

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO clothes
                    (user_id, item_name, wardrobe_category, cloth_type,
                     color, image_data, min_temp, max_temp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    custom_name or raw_cat,
                    wardrobe_category,
                    raw_cat,
                    color_name,
                    save_path,
                    min_t,
                    max_t,
                ),
            )
            conn.commit()

        return True, wardrobe_category, color_name

    except Exception as exc:
        print(f'[process_and_add_clothing] error: {exc}')
        return False, None, None


def get_user_catalog(email: str) -> dict[str, list[dict[str, object]]]:
    user_id = _resolve_user_id(email)
    catalog: dict[str, list[dict[str, object]]] = {
        cat: [] for cat in FRONTEND_CATEGORIES
    }

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, item_name, wardrobe_category, cloth_type, color, image_data
            FROM clothes WHERE user_id = ? ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()

    for row in rows:
        cat = row['wardrobe_category'] or 'Accessories ⌚'
        catalog.setdefault(cat, []).append(
            {
                'id': int(row['id']),
                'name': row['item_name'],
                'image': row['image_data'],
                'color': row['color'],
                'cloth_type': row['cloth_type'],
            }
        )

    return catalog


def get_outfit_suggestion(user_id: int) -> list[dict]:
    """Return 1 Top + 1 Bottom + optional Outerwear suited to current temp."""
    at_temp = get_smart_weather(user_id)
    outfit: list[dict] = []

    with get_connection() as conn:
        for category in ('Top 👚', 'Bottom 🩳'):
            row = conn.execute(
                """
                SELECT * FROM clothes
                WHERE user_id = ? AND wardrobe_category = ?
                  AND min_temp <= ? AND max_temp >= ?
                ORDER BY RANDOM() LIMIT 1
                """,
                (user_id, category, at_temp, at_temp),
            ).fetchone()
            if row:
                outfit.append(dict(row))

        if at_temp < 20:
            row = conn.execute(
                """
                SELECT * FROM clothes
                WHERE user_id = ? AND wardrobe_category = 'Outerwear 🧥'
                  AND min_temp <= ? AND max_temp >= ?
                ORDER BY RANDOM() LIMIT 1
                """,
                (user_id, at_temp, at_temp),
            ).fetchone()
            if row:
                outfit.append(dict(row))

    return outfit


init_db()
