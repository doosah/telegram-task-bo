"""
ФАЙЛ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
Здесь хранятся статусы задач (⚪, ⏳, ✅) и ID пользователей
"""

import sqlite3
import os
from threading import Lock

# Блокировка для безопасной работы с базой данных
db_lock = Lock()


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path='bot_database.db'):
        """
        Инициализация базы данных
        db_path - путь к файлу базы данных
        """
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Создает соединение с базой данных"""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def init_database(self):
        """Создает таблицы в базе данных, если их еще нет"""
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Таблица для статусов задач
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_statuses (
                    task_key TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT '⚪'
                )
            ''')
            
            # Таблица для хранения ID пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    initials TEXT NOT NULL
                )
            ''')
            
            # Добавляем начальных пользователей, если их еще нет
            initial_users = [
                ('alex301182', None, 'AG'),
                ('Korudirp', None, 'KA')
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO users (username, user_id, initials)
                VALUES (?, ?, ?)
            ''', initial_users)
            
            conn.commit()
            conn.close()
    
    def get_task_status(self, task_key: str) -> str:
        """
        Получить статус задачи
        task_key - уникальный ключ задачи (например, "0_1_AG")
        Возвращает статус: ⚪, ⏳ или ✅
        """
        try:
            with db_lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT status FROM task_statuses WHERE task_key = ?',
                    (task_key,)
                )
                
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    return result[0]
                else:
                    # Если статуса нет, возвращаем дефолтный без создания записи
                    # Запись будет создана при первом set_task_status
                    return '⚪'
        except Exception as e:
            # В случае ошибки возвращаем дефолтный статус
            return '⚪'
    
    def set_task_status(self, task_key: str, status: str):
        """
        Установить статус задачи
        task_key - уникальный ключ задачи
        status - новый статус (⚪, ⏳ или ✅)
        """
        try:
            with db_lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO task_statuses (task_key, status)
                    VALUES (?, ?)
                ''', (task_key, status))
                
                conn.commit()
                conn.close()
        except Exception as e:
            # Логируем ошибку, но не падаем
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка сохранения статуса {task_key}={status}: {e}", exc_info=True)
    
    def save_user_id(self, username: str, user_id: int, initials: str):
        """
        Сохранить ID пользователя
        username - имя пользователя в Telegram (например, "alex301182")
        user_id - ID пользователя в Telegram
        initials - инициалы (AG, KA или SA)
        """
        try:
            with db_lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO users (username, user_id, initials)
                    VALUES (?, ?, ?)
                ''', (username, user_id, initials))
                
                conn.commit()
                conn.close()
        except Exception as e:
            # Логируем ошибку, но не падаем
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка сохранения ID пользователя {username}: {e}", exc_info=True)
    
    def get_user_ids(self) -> list:
        """
        Получить список всех ID пользователей
        Возвращает список ID для отправки личных сообщений
        """
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT user_id FROM users WHERE user_id IS NOT NULL')
            results = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in results if row[0] is not None]
    
    def get_user_id_by_username(self, username: str) -> int:
        """
        Получить ID пользователя по его username
        username - имя пользователя в Telegram
        Возвращает ID пользователя или None
        """
        try:
            with db_lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT user_id FROM users WHERE username = ?',
                    (username,)
                )
                
                result = cursor.fetchone()
                conn.close()
                
                if result and result[0] is not None:
                    return result[0]
                return None
        except Exception as e:
            # Логируем ошибку, но не падаем
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка получения ID пользователя {username}: {e}", exc_info=True)
            return None

