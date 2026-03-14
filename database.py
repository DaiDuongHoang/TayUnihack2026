# database.py

import sqlite3
import hashlib

DB_NAME = "wardrobe_system.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():  
    with get_connection() as conn:
# Users Table: Stores account information and weather cache
# Function: Manages each user separately and saves API calls
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            location TEXT DEFAULT 'Hanoi',
            last_at_temp REAL,           -- Save the most recent AT temperature
            last_weather_update TIMESTAMP -- Save time to know when to call new API
        )""")

        # Wadrobe
        # Function: Store classification, color and appropriate temperature threesholds
        conn.execute("""CREATE TABLE IF NOT EXISTS clothes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,      -- Blazer, T-shirt, Hoodie...
            color TEXT,    -- Red, Blue,...
            appropriate_weather -- hot/cold
            image_path TEXT,    -- image
            FOREIGN KEY (user_id) REFERENCES users (id)
        )""")
        conn.commit()
    


import math
import requests
from datetime import datetime, timedelta

def calculate_apparent_temp(t, rh, ws):
    """
    Apparent Temperature - AT
    t: Temperature (°C), rh: humidity (%), ws: wind speed (m/s)
    """
    # Calculate the steam pressure (e)
    e = (rh / 100) * 6.105 * math.exp((17.27 * t) / (237.7 + t))
    
    # AT formula
    at = t + 0.33 * e - 0.70 * ws - 4.00
    return round(at, 1)

def get_smart_weather(user_id):
    """
    Retrieves weather data from the API but checks the database cache
    =>  Avoids wasting API calls every time a button is clicked
    """
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    
    # If the new data is taken within 30 minutes, use the data that currently is stored in DB
    if user['last_weather_update']:
        last_time = datetime.strptime(user['last_weather_update'], '%Y-%m-%d %H:%M:%S')
        if datetime.now() - last_time < timedelta(minutes=30):
            return user['last_at_temp']

    # If it doesn't exist or is too old, call the actual API
    # API_KEY = "your_key"
    # response = requests.get(f"api_url_with_{user['location']}").json()
    # Then calculate the AT and update the DB
    return 20.5 


def change_user_password(user_id, old_pwd, new_pwd):
    with get_connection() as conn:
        user = conn.execute("SELECT password FROM users WHERE id = ?", (user_id,)).fetchone()
        if user['password'] == old_pwd:
            conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_pwd, user_id))
            return True
        return False

def add_new_clothes(user_id, category, color, img_path):
    temp_ranges = {
        'T-shirt': (22, 40),
        'Hoodie': (10, 20),
        'Blazer': (15, 25),
        'Coat': (-5, 12),
        'Short': (25, 45)
    }
    min_t, max_t = temp_ranges.get(category, (15, 30)) 

    with get_connection() as conn:
        conn.execute("""INSERT INTO clothes (user_id, category, color, min_temp, max_temp, image_path)
                     VALUES (?, ?, ?, ?, ?, ?)""", (user_id, category, color, min_t, max_t, img_path))

def get_outfit_suggestion(user_id):
    """
    Function: Load Weather -> Calculate AT -> Filter Wardrobe.
    Effect: show clothes suggestions
    """
    at_temp = get_smart_weather(user_id)
    
    with get_connection() as conn:
        query = "SELECT * FROM clothes WHERE user_id = ? AND min_temp <= ? AND max_temp >= ?"
        return conn.execute(query, (user_id, at_temp, at_temp)).fetchall()



def register_user(username, password, location='Melbourne'):
    # Everyone has an own id
    with get_connection() as conn:
        try:
            conn.execute("""INSERT INTO users (username, password, location) 
                         VALUES (?, ?, ?)""", (username, password, location))
            conn.commit()
            return True
        except:
            # False if username has already existed
            return False

def login_user(username, password):
    with get_connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE username = ? AND password = ?", 
                         (username, password)).fetchone()
        return user['id'] if user else None
    
def remove_clothes(clothes_id, user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM clothes WHERE id = ? AND user_id = ?", (clothes_id, user_id))
        conn.commit()


def update_user_location(user_id, new_location):
    with get_connection() as conn:
        conn.execute("""
            UPDATE users 
            SET location = ?, last_weather_update = NULL 
            WHERE id = ?
        """, (new_location, user_id))
        conn.commit()
