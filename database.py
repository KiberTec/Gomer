# ═══════════════════════════════════════════════════════════
# 🗄️ РАБОТА С БАЗОЙ ДАННЫХ
# ═══════════════════════════════════════════════════════════

import sqlite3
import os
from datetime import datetime
from typing import List, Tuple, Optional

# Путь к базе данных рядом с этим файлом
DATABASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")


def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            category INTEGER DEFAULT 0,
            joined_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    conn.commit()
    conn.close()


def add_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Добавить нового пользователя"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, joined_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, first_name, last_name, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()


def get_all_users() -> List[Tuple]:
    """Получить всех пользователей"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id, username, first_name, category, joined_at FROM users WHERE is_active = 1")
    users = cursor.fetchall()
    
    conn.close()
    return users


def get_all_user_ids() -> List[int]:
    """Получить все ID пользователей"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users WHERE is_active = 1")
    user_ids = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return user_ids


def get_users_by_category(category: int) -> List[int]:
    """Получить пользователей по категории"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users WHERE category = ? AND is_active = 1", (category,))
    user_ids = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return user_ids


def set_user_category(user_id: int, category: int):
    """Установить категорию пользователю"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET category = ? WHERE user_id = ?", (category, user_id))
    
    conn.commit()
    conn.close()


def get_user_count() -> int:
    """Получить количество пользователей"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    count = cursor.fetchone()[0]
    
    conn.close()
    return count


def get_category_stats() -> dict:
    """Получить статистику по категориям"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    stats = {}
    for cat in [0, 1, 2, 3]:
        cursor.execute("SELECT COUNT(*) FROM users WHERE category = ? AND is_active = 1", (cat,))
        stats[cat] = cursor.fetchone()[0]
    
    conn.close()
    return stats


def deactivate_user(user_id: int):
    """Деактивировать пользователя (заблокировал бота)"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()

