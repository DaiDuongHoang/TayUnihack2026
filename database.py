# database.py
# import sqlite3

# DB_NAME = "wadrobe.db"


# def get_connection():
#     return sqlite3.connect(DB_NAME)


# def init_db():
#     with get_connection() as conn:
#         conn.execute("""CREATE TABLE IF NOT EXISTS clothes (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             category TEXT,   -- Hoodie, T-shirt, Short, Pants
#             color TEXT,
#             weather_type TEXT, -- Cold, Hot, Rainy
#             image_path TEXT
#         )""")


# def get_all_clothes():
#     with get_connection() as conn:
#         cursor = conn.execute("SELECT * FROM clothes")
#         return cursor.fetchall()

import sqlite3
import hashlib

DB_NAME = "wardrobe_system.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        # Bảng Users: Lưu thông tin tài khoản và Cache thời tiết
        # Tác dụng: Quản lý riêng biệt từng người dùng và tiết kiệm lượt gọi API
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            location TEXT DEFAULT 'Hanoi',
            last_at_temp REAL,           -- Lưu nhiệt độ AT gần nhất
            last_weather_update TIMESTAMP -- Lưu thời gian để biết khi nào cần gọi API mới
        )""")

        # Bảng Clothes: Lưu tủ đồ (Wardrobe)
        # Tác dụng: Lưu trữ phân loại AI (category), màu sắc và ngưỡng nhiệt độ phù hợp
        conn.execute("""CREATE TABLE IF NOT EXISTS clothes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,      -- Blazer, T-shirt, Hoodie...
            color_tone TEXT,    -- Light / Dark
            min_temp INTEGER,   -- Ngưỡng lạnh nhất món này chịu được
            max_temp INTEGER,   -- Ngưỡng nóng nhất món này còn thấy thoải mái
            image_path TEXT,    -- Đường dẫn ảnh chụp từ điện thoại
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")

        # Bảng Usage History: Lưu lịch sử mặc đồ
        # Tác dụng: Cung cấp dữ liệu để làm phần Thống kê (Statistics)
        conn.execute("""CREATE TABLE IF NOT EXISTS usage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            clothes_id INTEGER,
            worn_date DATE DEFAULT CURRENT_DATE,
            worn_at_temp REAL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (clothes_id) REFERENCES clothes (id)
        )""")
        conn.commit()
    


import math
import requests
from datetime import datetime, timedelta

def calculate_apparent_temp(t, rh, ws):
    """
    Công thức tính Nhiệt độ cảm nhận (Apparent Temperature - AT)
    t: Nhiệt độ (°C), rh: Độ ẩm (%), ws: Tốc độ gió (m/s)
    """
    # Tính áp suất hơi nước (e) - yếu tố cực quan trọng gây cảm giác oi bức
    e = (rh / 100) * 6.105 * math.exp((17.27 * t) / (237.7 + t))
    
    # Công thức AT kết hợp giữa nhiệt độ, độ ẩm và sức gió
    at = t + 0.33 * e - 0.70 * ws - 4.00
    return round(at, 1)

def get_smart_weather(user_id):
    """
    Lấy thời tiết từ API nhưng có kiểm tra Cache trong Database.
    Tác dụng: Tránh việc mỗi lần bấm nút lại tốn 1 lượt gọi API (tiết kiệm tiền/quota).
    """
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    
    # Nếu dữ liệu mới cập nhật dưới 30 phút, lấy luôn trong DB ra dùng
    if user['last_weather_update']:
        last_time = datetime.strptime(user['last_weather_update'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() - last_time < timedelta(minutes=30):
            return user['last_at_temp']

    # Nếu chưa có hoặc quá cũ, gọi API thật (Ví dụ OpenWeatherMap)
    # API_KEY = "your_key"
    # response = requests.get(f"api_url_with_{user['location']}").json()
    # Sau đó tính AT và cập nhật lại vào DB
    # code cập nhật...
    return 20.5 # Giả lập kết quả trả về


def change_user_password(user_id, old_pwd, new_pwd):
    """
    Đổi mật khẩu: Yêu cầu pass cũ (giống như trên bảng bạn vẽ).
    Tác dụng: Đảm bảo chính chủ mới được đổi thông tin.
    """
    with get_connection() as conn:
        user = conn.execute("SELECT password FROM users WHERE id = ?", (user_id,)).fetchone()
        if user['password'] == old_pwd:
            conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_pwd, user_id))
            return True
        return False

def add_new_clothes(user_id, category, color, img_path):
    """
    Thêm đồ vào tủ sau khi AI đã nhận diện ảnh chụp.
    Tác dụng: Tự động gán ngưỡng nhiệt độ mặc định cho từng loại đồ.
    """
    # Logic "Dạy" AI: Tự động gán ngưỡng nhiệt độ cho từng Category
    temp_ranges = {
        'T-shirt': (22, 40),
        'Hoodie': (10, 20),
        'Blazer': (15, 25),
        'Coat': (-5, 12),
        'Short': (25, 45)
    }
    min_t, max_t = temp_ranges.get(category, (15, 30)) # Mặc định nếu không rõ loại

    with get_connection() as conn:
        conn.execute("""INSERT INTO clothes (user_id, category, color_tone, min_temp, max_temp, image_path)
                     VALUES (?, ?, ?, ?, ?, ?)""", (user_id, category, color, min_t, max_t, img_path))

def get_outfit_suggestion(user_id):
    """
    CHỨC NĂNG CHÍNH: Load Weather -> Calculate AT -> Filter Wardrobe.
    Tác dụng: Hiển thị các món đồ phù hợp với nhiệt độ cảm nhận hiện tại.
    """
    at_temp = get_smart_weather(user_id)
    
    with get_connection() as conn:
        # Lọc đồ: Nhiệt độ cảm nhận phải nằm giữa min_temp và max_temp của món đồ đó
        query = "SELECT * FROM clothes WHERE user_id = ? AND min_temp <= ? AND max_temp >= ?"
        return conn.execute(query, (user_id, at_temp, at_temp)).fetchall()



def register_user(username, password, location='Melbourne'):
    """
    Tác dụng: Tạo tài khoản mới cho người dùng.
    Mỗi người dùng sẽ có một ID riêng để quản lý tủ đồ riêng.
    """
    with get_connection() as conn:
        try:
            conn.execute("""INSERT INTO users (username, password, location) 
                         VALUES (?, ?, ?)""", (username, password, location))
            conn.commit()
            return True
        except:
            # Trả về False nếu username đã tồn tại (do ta để UNIQUE trong DB)
            return False

def login_user(username, password):
    """
    Tác dụng: Kiểm tra đăng nhập.
    Trả về user_id để các hàm sau (gợi ý đồ, thêm đồ) biết là đang phục vụ ai.
    """
    with get_connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE username = ? AND password = ?", 
                         (username, password)).fetchone()
        return user['id'] if user else None