import sqlite3
import hashlib
import math
import requests
import secrets
import hmac
import os
import shutil
from datetime import datetime, timedelta
from ultralytics import YOLO 

# --- CONFIGURATION ---
DB_NAME = "wardrobe_system.db"
PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390000
OPENWEATHER_API_KEY = "YOUR_API_KEY_HERE"  # Thay key của bạn vào đây
UPLOAD_FOLDER = "uploads/wardrobe"

# Tạo thư mục upload nếu chưa có
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- MAPPING & TEMP RANGES ---
# Khớp nhãn từ AI YOLO sang nhóm của Frontend
CATEGORY_MAPPING = {
    "t-shirt": "Top 👚", "dress": "Top 👚", "sweater": "Top 👚",
    "shorts": "Bottom 🩳", "skirt": "Bottom 🩳", "jeans": "Bottom 🩳", "pants": "Bottom 🩳",
    "blazer": "Outerwear 🧥", "jacket": "Outerwear 🧥", "coat": "Outerwear 🧥", "hoodie": "Outerwear 🧥"
}

# Dải nhiệt độ cho từng loại đồ cụ thể (dùng để gợi ý thông minh)
TEMP_RANGES = {
    't-shirt': (22, 40), 'hoodie': (10, 22), 'blazer': (15, 25),
    'coat': (-10, 15), 'shorts': (25, 45), 'jeans': (10, 30),
    'sweater': (5, 18), 'dress': (20, 35), 'skirt': (18, 30), 'pants': (10, 30)
}

# --- DATABASE CORE ---
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Khởi tạo database với cấu hình cột đồng nhất."""
    with get_connection() as conn:
        # Bảng Users
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                first_name TEXT DEFAULT '',
                location TEXT DEFAULT 'Melbourne',
                last_at_temp REAL,
                last_weather_update TIMESTAMP
            )
        """)
        
        # Bảng Clothes (Đã chuyển image_data sang TEXT để lưu path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clothes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                category TEXT,        -- Lưu: 'Top 👚', 'Bottom 🩳', v.v.
                cloth_type TEXT,      -- Lưu: 't-shirt', 'hoodie', v.v.
                color TEXT,
                image_data TEXT,      -- Lưu đường dẫn file (path)
                min_temp REAL,
                max_temp REAL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()
    print("[+] Database initialized successfully.")

# --- SECURITY LOGIC ---
def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS
    ).hex()
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${digest}"

def _verify_password(password: str, stored_value: str) -> bool:
    if not stored_value or "$" not in stored_value: return False
    try:
        parts = stored_value.split("$")
        scheme, iterations, salt, stored_digest = parts
        computed_digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
        ).hex()
        return hmac.compare_digest(stored_digest, computed_digest)
    except: return False

# --- AI MODELS LOADING ---
try:
    # Đảm bảo đường dẫn này khớp với kết quả training Computer Vision của bạn
    category_model = YOLO("runs_category_classifier/yolov8n_category/weights/best.pt")
    color_model = YOLO("runs_color_classifier/yolov8m_color/weights/best.pt")
except Exception as e:
    print(f"[!] AI Model Load Error: {e}")

# --- WEATHER LOGIC ---
def calculate_apparent_temp(t, rh, ws):
    e = (rh / 100) * 6.105 * math.exp((17.27 * t) / (237.7 + t))
    at = t + 0.33 * e - 0.70 * ws - 4.00
    return round(at, 1)

def get_smart_weather(user_id):
    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user: return 20.0

        now = datetime.now()
        if user['last_weather_update']:
            last_update = datetime.strptime(user['last_weather_update'], '%Y-%m-%d %H:%M:%S')
            if now - last_update < timedelta(minutes=30):
                return user['last_at_temp']

        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={user['location']}&appid={OPENWEATHER_API_KEY}&units=metric"
            res = requests.get(url, timeout=5).json()
            t, rh, ws = res['main']['temp'], res['main']['humidity'], res['wind']['speed']
            at_temp = calculate_apparent_temp(t, rh, ws)
            
            conn.execute("UPDATE users SET last_at_temp = ?, last_weather_update = ? WHERE id = ?", 
                         (at_temp, now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
            conn.commit()
            return at_temp
        except:
            return user['last_at_temp'] if user['last_at_temp'] is not None else 20.0

# --- CORE FUNCTIONS ---
def process_and_add_clothing(user_id, image_path, custom_name=None):
    """Quy trình: Nhận diện AI -> Mapping Category -> Lưu File -> Lưu DB."""
    try:
        # 1. AI Inference
        cat_results = category_model.predict(image_path, imgsz=224, verbose=False)
        raw_cat = cat_results[0].names[cat_results[0].probs.top1].lower()
        
        color_results = color_model.predict(image_path, imgsz=224, verbose=False)
        color_name = color_results[0].names[color_results[0].probs.top1]

        # 2. Mapping & Temperature
        frontend_cat = CATEGORY_MAPPING.get(raw_cat, "Accessories ⌚")
        min_t, max_t = TEMP_RANGES.get(raw_cat, (15, 30))

        # 3. File Management (Lưu vào thư mục uploads)
        file_ext = os.path.splitext(image_path)[1]
        unique_name = f"{user_id}_{secrets.token_hex(8)}{file_ext}"
        save_path = os.path.join(UPLOAD_FOLDER, unique_name)
        shutil.copy2(image_path, save_path)

        # 4. DB Storage
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO clothes (user_id, item_name, category, cloth_type, color, image_data, min_temp, max_temp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, custom_name or raw_cat, frontend_cat, raw_cat, color_name, save_path, min_t, max_t))
            conn.commit()
        return True, frontend_cat, color_name
    except Exception as e:
        print(f"Error: {e}")
        return False, None, None

def get_outfit_suggestion(user_id):
    """Gợi ý bộ đồ thông minh: 1 Top + 1 Bottom + (Outerwear nếu lạnh)."""
    at_temp = get_smart_weather(user_id)
    outfit = []
    
    with get_connection() as conn:
        # Lấy Top
        top = conn.execute("SELECT * FROM clothes WHERE user_id=? AND category='Top 👚' AND min_temp<=? AND max_temp>=? ORDER BY RANDOM() LIMIT 1", (user_id, at_temp, at_temp)).fetchone()
        if top: outfit.append(dict(top))

        # Lấy Bottom
        bottom = conn.execute("SELECT * FROM clothes WHERE user_id=? AND category='Bottom 🩳' AND min_temp<=? AND max_temp>=? ORDER BY RANDOM() LIMIT 1", (user_id, at_temp, at_temp)).fetchone()
        if bottom: outfit.append(dict(bottom))

        # Lấy Outerwear nếu trời lạnh (< 20 độ)
        if at_temp < 20:
            outer = conn.execute("SELECT * FROM clothes WHERE user_id=? AND category='Outerwear 🧥' AND min_temp<=? AND max_temp>=? ORDER BY RANDOM() LIMIT 1", (user_id, at_temp, at_temp)).fetchone()
            if outer: outfit.append(dict(outer))
            
    return outfit

