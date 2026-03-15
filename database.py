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
from ultralytics import YOLO
 
# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()
 
DB_PATH = Path(__file__).resolve().with_name("wardrobe_system.db")
UPLOAD_FOLDER = Path("uploads/wardrobe")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
 
OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390000
 
# Match wardrobe_system.db — column is wardrobe_category
FRONTEND_CATEGORIES = ("Top 👚", "Bottom 🩳", "Outerwear 🧥", "Accessories ⌚")
DEFAULT_LOCATION = ("Australia", "Melbourne")
 
# AI label  →  wardrobe_category  (matches WARDROBE_CATEGORY_BY_CLOTH_TYPE in file 1)
CATEGORY_MAPPING: dict[str, str] = {
    "t-shirt":  "Top 👚",
    "dress":    "Top 👚",
    "sweater":  "Top 👚",
    "shorts":   "Bottom 🩳",
    "skirt":    "Bottom 🩳",
    "jeans":    "Bottom 🩳",
    "pants":    "Bottom 🩳",
    "blazer":   "Outerwear 🧥",
    "jacket":   "Outerwear 🧥",
    "coat":     "Outerwear 🧥",
    "hoodie":   "Outerwear 🧥",
}
 
# Temperature ranges per cloth type (°C apparent temp)
TEMP_RANGES: dict[str, tuple[float, float]] = {
    "t-shirt": (22, 40),
    "hoodie":  (10, 20),
    "blazer":  (15, 25),
    "coat":    (-5, 16),
    "shorts":  (25, 45),
    "jeans":   (12, 28),
    "pants":   (12, 28),
    "dress":   (20, 35),
    "skirt":   (20, 35),
    "sweater": (8, 20),
    "jacket":  (8, 20),
}
 
# ---------------------------------------------------------------------------
# AI Models — lazy-loaded so missing .pt files don't crash on import
# ---------------------------------------------------------------------------
_category_model: YOLO | None = None
_color_model: YOLO | None = None
 
 
def _get_category_model() -> YOLO:
    global _category_model
    if _category_model is None:
        model_path = Path("runs_category_classifier/yolov8n_category/weights/best.pt")
        if not model_path.exists():
            raise FileNotFoundError(f"Category model not found: {model_path}")
        _category_model = YOLO(str(model_path))
    return _category_model
 
 
def _get_color_model() -> YOLO:
    global _color_model
    if _color_model is None:
        model_path = Path("runs_color_classifier/yolov8m_color/weights/best.pt")
        if not model_path.exists():
            raise FileNotFoundError(f"Color model not found: {model_path}")
        _color_model = YOLO(str(model_path))
    return _color_model
 
 
# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
 
 
def init_db() -> None:
    """Create tables using the exact schema from wardrobe_system.db (file 1)."""
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
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_subject
            ON users(google_subject) WHERE google_subject IS NOT NULL
        """)
        # wardrobe_category — matches file 1 exactly
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
    print("[+] Database initialized.")
 
 
# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PASSWORD_ITERATIONS
    ).hex()
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${digest}"
 
 
def _verify_password(password: str, stored: str) -> bool:
    if not stored:
        return False
    if not stored.startswith(f"{PASSWORD_SCHEME}$"):
        return hmac.compare_digest(stored, password)
    try:
        _, iter_str, salt, stored_digest = stored.split("$", 3)
        computed = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(iter_str)
        ).hex()
        return hmac.compare_digest(stored_digest, computed)
    except ValueError:
        return False
 
 
# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------
def calculate_apparent_temp(t: float, rh: float, ws: float) -> float:
    e = (rh / 100) * 6.105 * math.exp((17.27 * t) / (237.7 + t))
    return round(t + 0.33 * e - 0.70 * ws - 4.00, 1)
 
 
def _fetch_weather(location: str) -> float | None:
    """Call OpenWeatherMap outside any DB connection; return apparent temp or None."""
    if not OPENWEATHER_API_KEY:
        print("[weather] OPENWEATHER_API_KEY not set in .env")
        return None
    try:
        url = (
            "http://api.openweathermap.org/data/2.5/weather"
            f"?q={location}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        return calculate_apparent_temp(
            data["main"]["temp"],
            data["main"]["humidity"],
            data["wind"]["speed"],
        )
    except Exception as exc:
        print(f"[weather] fetch failed: {exc}")
        return None
 
 
def get_smart_weather(user_id: int) -> float:
    """Return cached apparent temp if < 30 min old, otherwise refresh from API."""
    with get_connection() as conn:
        user = conn.execute(
            "SELECT location, last_at_temp, last_weather_update FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
 
    if user is None:
        return 20.0
 
    # Return cache if still fresh
    if user["last_weather_update"] and user["last_at_temp"] is not None:
        last = datetime.strptime(user["last_weather_update"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() - last < timedelta(minutes=30):
            return float(user["last_at_temp"])
 
    # Fetch outside DB connection to avoid holding it during network I/O
    location = user["location"] or f"{DEFAULT_LOCATION[1]}, {DEFAULT_LOCATION[0]}"
    at_temp = _fetch_weather(location)
 
    if at_temp is None:
        return float(user["last_at_temp"]) if user["last_at_temp"] is not None else 20.0
 
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET last_at_temp = ?, last_weather_update = ? WHERE id = ?",
            (at_temp, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id),
        )
        conn.commit()
 
    return at_temp
 
 
# ---------------------------------------------------------------------------
# AI-powered clothing intake
# ---------------------------------------------------------------------------
def process_and_add_clothing(
    user_id: int,
    image_path: str,
    custom_name: str | None = None,
) -> tuple[bool, str | None, str | None]:
    """
    Run YOLO inference on image_path, map result to wardrobe_category,
    copy file to UPLOAD_FOLDER, then insert into clothes (file-1 schema).
 
    Returns (success, wardrobe_category, color_name).
    """
    try:
        # AI inference
        cat_results = _get_category_model().predict(image_path, imgsz=224, verbose=False)
        raw_cat     = cat_results[0].names[cat_results[0].probs.top1].lower()
 
        col_results = _get_color_model().predict(image_path, imgsz=224, verbose=False)
        color_name  = col_results[0].names[col_results[0].probs.top1]
 
        # Map AI label → wardrobe_category
        wardrobe_category = CATEGORY_MAPPING.get(raw_cat, "Accessories ⌚")
        min_t, max_t      = TEMP_RANGES.get(raw_cat, (15, 30))
 
        # Copy image to uploads/
        ext         = Path(image_path).suffix
        unique_name = f"{user_id}_{secrets.token_hex(8)}{ext}"
        save_path   = str(UPLOAD_FOLDER / unique_name)
        shutil.copy2(image_path, save_path)
 
        # Insert using wardrobe_category (matches file-1 schema)
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO clothes
                    (user_id, item_name, wardrobe_category, cloth_type,
                     color, image_data, min_temp, max_temp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, custom_name or raw_cat, wardrobe_category,
                 raw_cat, color_name, save_path, min_t, max_t),
            )
            conn.commit()
 
        return True, wardrobe_category, color_name
 
    except Exception as exc:
        print(f"[process_and_add_clothing] error: {exc}")
        return False, None, None
 
 
# ---------------------------------------------------------------------------
# Outfit suggestion
# ---------------------------------------------------------------------------
def get_outfit_suggestion(user_id: int) -> list[dict]:
    """Return 1 Top + 1 Bottom + optional Outerwear suited to current temp."""
    at_temp = get_smart_weather(user_id)
    outfit: list[dict] = []
 
    with get_connection() as conn:
        for category in ("Top 👚", "Bottom 🩳"):
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
 
 
# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------
def _resolve_user_id(email: str) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", (email.strip().lower(),)
        ).fetchone()
    if row is None:
        raise ValueError(f"User '{email}' not found")
    return int(row["id"])
 
 
def get_user_catalog(email: str) -> dict[str, list[dict]]:
    """Return wardrobe grouped by wardrobe_category — matches file-1 structure."""
    user_id = _resolve_user_id(email)
    catalog: dict[str, list[dict]] = {cat: [] for cat in FRONTEND_CATEGORIES}
 
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, item_name, wardrobe_category, cloth_type, color, image_data
            FROM clothes WHERE user_id = ? ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
 
    for row in rows:
        cat = row["wardrobe_category"] or "Accessories ⌚"
        catalog.setdefault(cat, []).append({
            "id":         int(row["id"]),
            "name":       row["item_name"],
            "image":      row["image_data"],
            "color":      row["color"],
            "cloth_type": row["cloth_type"],
        })
 
    return catalog


