import sqlite3
import hashlib
import math
import requests
import secrets
import hmac
from datetime import datetime, timedelta

# --- CẤU HÌNH ---
DB_NAME = "wardrobe_system.db"
PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390000
OPENWEATHER_API_KEY = "YOUR_API_KEY_HERE"  # Thay bằng key của bạn

# --- HỆ THỐNG DATABASE ---
def get_connection():
    """Tạo kết nối và đảm bảo trả về Row factory để truy cập theo tên cột"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():  
    with get_connection() as conn:
        # Bảng Users
        conn.execute(f"""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            first_name TEXT DEFAULT '',
            auth_provider TEXT DEFAULT 'local',
            location TEXT DEFAULT 'Melbourne',
            last_at_temp REAL,
            last_weather_update TIMESTAMP
        )""")

        # Bảng Clothes (Đã sửa lỗi và tối ưu cho CV)
        conn.execute("""CREATE TABLE IF NOT EXISTS clothes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            category TEXT,       -- Ví dụ: 't-shirt', 'hoodie' từ YOLO
            cloth_type TEXT,     -- Ví dụ: 'cotton', 'wool'
            color TEXT,
            image_data BLOB,     -- Dữ liệu ảnh binary
            min_temp REAL,
            max_temp REAL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        conn.commit()

# --- LOGIC BẢO MẬT ---
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
        if len(parts) != 4: return False
        _, iterations, salt, stored_digest = parts
        computed_digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
        ).hex()
        return hmac.compare_digest(stored_digest, computed_digest)
    except Exception:
        return False

# --- LOGIC THỜI TIẾT ---
def calculate_apparent_temp(t, rh, ws):
    """Công thức tính Nhiệt độ cảm nhận (Apparent Temperature)"""
    # e: áp suất hơi nước
    e = (rh / 100) * 6.105 * math.exp((17.27 * t) / (237.7 + t))
    at = t + 0.33 * e - 0.70 * ws - 4.00
    return round(at, 1)

def get_smart_weather(user_id):
    """Lấy thời tiết từ API hoặc Cache nếu chưa quá 30 phút"""
    with get_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user: return 20.0

        # Kiểm tra Cache
        now = datetime.now()
        if user['last_weather_update']:
            last_update = datetime.strptime(user['last_weather_update'], '%Y-%m-%d %H:%M:%S')
            if now - last_update < timedelta(minutes=30):
                return user['last_at_temp']

        # Gọi API thực tế (OpenWeatherMap)
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={user['location']}&appid={OPENWEATHER_API_KEY}&units=metric"
            res = requests.get(url, timeout=5).json()
            
            t = res['main']['temp']
            rh = res['main']['humidity']
            ws = res['wind']['speed']
            
            at_temp = calculate_apparent_temp(t, rh, ws)
            
            # Cập nhật Cache vào DB
            conn.execute("""UPDATE users SET last_at_temp = ?, last_weather_update = ? 
                         WHERE id = ?""", (at_temp, now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
            conn.commit()
            return at_temp
        except Exception as e:
            print(f"Weather API Error: {e}")
            return user['last_at_temp'] or 20.0

# --- QUẢN LÝ TÀI KHOẢN ---
def register_user(username, password, first_name="", location='Melbourne'):
    try:
        with get_connection() as conn:
            hashed_pwd = _hash_password(password)
            conn.execute("""INSERT INTO users (username, password, first_name, location) 
                         VALUES (?, ?, ?, ?)""", (username, hashed_pwd, first_name, location))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        print("Username đã tồn tại.")
        return False

def login_user(username, password):
    with get_connection() as conn:
        user = conn.execute("SELECT id, password FROM users WHERE username = ?", (username,)).fetchone()
        if user and _verify_password(password, user['password']):
            return user['id']
        return None

# --- QUẢN LÝ TỦ ĐỒ ---
def add_new_clothes(user_id, category, color, image_blob, item_name=None):
    """Lưu kết quả phân loại từ YOLO và tự động gán ngưỡng nhiệt độ"""
    # Từ điển mapping loại đồ -> ngưỡng nhiệt độ lý tưởng
    temp_ranges = {
        't-shirt': (22, 40), 
        'hoodie': (10, 22), 
        'blazer': (15, 25),
        'coat': (-10, 15), 
        'short': (25, 45), 
        'jeans': (10, 30),
        'sweater': (5, 18)
    }
    min_t, max_t = temp_ranges.get(category.lower(), (15, 30))

    with get_connection() as conn:
        conn.execute("""INSERT INTO clothes 
                     (user_id, item_name, category, color, image_data, min_temp, max_temp)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                     (user_id, item_name or category, category, color, image_blob, min_t, max_t))
        conn.commit()

def get_outfit_suggestion(user_id):
    """Gợi ý các món đồ phù hợp với nhiệt độ hiện tại (Ngẫu nhiên 3 món)"""
    at_temp = get_smart_weather(user_id)
    with get_connection() as conn:
        # Sử dụng ORDER BY RANDOM() để mỗi lần mở app là một gợi ý mới mẻ
        query = """SELECT * FROM clothes 
                   WHERE user_id = ? AND min_temp <= ? AND max_temp >= ?
                   ORDER BY RANDOM() LIMIT 3"""
        return conn.execute(query, (user_id, at_temp, at_temp)).fetchall()
    

def update_item_preference(item_id, feedback):
    """
    feedback: 'too_cold' (vẫn thấy lạnh) hoặc 'too_hot' (thấy nóng)
    """
    with get_connection() as conn:
        item = conn.execute("SELECT min_temp, max_temp FROM clothes WHERE id = ?", (item_id,)).fetchone()
        if not item: return
        
        new_min, new_max = item['min_temp'], item['max_temp']
        
        if feedback == 'too_cold':
            # Nếu mặc món này mà vẫn lạnh -> Tăng ngưỡng min lên (để lần sau trời ấm hơn mới gợi ý)
            new_min += 2
        elif feedback == 'too_hot':
            # Nếu mặc mà thấy nóng -> Giảm ngưỡng max xuống
            new_max -= 2
            
        conn.execute("UPDATE clothes SET min_temp = ?, max_temp = ? WHERE id = ?", 
                     (new_min, new_max, item_id))
        conn.commit()

