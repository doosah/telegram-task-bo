"""
ФАЙЛ ДЛЯ РАБОТЫ С БАЗОЙ ДАННЫХ
Здесь хранятся статусы задач (⚪, ⏳, ✅) и ID пользователей
"""

import sqlite3
import os
import logging
from threading import Lock

# Настройка логирования для модуля database
logger_db = logging.getLogger(__name__)

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
        # Используем timeout для предотвращения блокировок
        return sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
    
    def init_database(self):
        """Создает таблицы в базе данных, если их еще нет"""
        try:
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
                        user_id INTEGER,
                        initials TEXT NOT NULL
                    )
                ''')
                
                # Таблица для новых задач (созданных через меню)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS custom_tasks (
                        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT,
                        deadline TEXT,
                        assignee TEXT,
                        creator TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        created_at TEXT NOT NULL,
                        completed_at TEXT,
                        result_text TEXT,
                        result_photo TEXT,
                        completed_assignees TEXT,
                        in_progress_assignees TEXT
                    )
                ''')
                
                # Добавляем поля, если их еще нет
                try:
                    cursor.execute('ALTER TABLE custom_tasks ADD COLUMN completed_assignees TEXT')
                except sqlite3.OperationalError:
                    pass
                try:
                    cursor.execute('ALTER TABLE custom_tasks ADD COLUMN in_progress_assignees TEXT')
                except sqlite3.OperationalError:
                    pass
                
                # Таблица для отметок присутствия
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS presence (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        status TEXT NOT NULL,
                        time TEXT,
                        delay_minutes INTEGER,
                        reason TEXT,
                        created_at TEXT NOT NULL,
                        UNIQUE(username, date)
                    )
                ''')
                
                # Таблица для блокировки спамеров
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS blocked_users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        reason TEXT,
                        blocked_at TEXT NOT NULL
                    )
                ''')
                
                # Таблица для логирования спам-попыток
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS spam_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT,
                        message_text TEXT,
                        detected_at TEXT NOT NULL
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
        except Exception as e:
            # Логируем ошибку, но не падаем
            logger_db.error(f"Ошибка инициализации БД: {e}", exc_info=True)
    
    def get_task_status(self, task_key: str) -> str:
        """
        Получить статус задачи
        task_key - уникальный ключ задачи (например, "0_1_AG")
        Возвращает статус: ⚪, ⏳ или ✅
        """
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT status FROM task_statuses WHERE task_key = ?',
                        (task_key,)
                    )
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                    else:
                        # Если статуса нет, возвращаем дефолтный без создания записи
                        # Запись будет создана при первом set_task_status
                        return '⚪'
                finally:
                    conn.close()
        except Exception as e:
            # В случае ошибки возвращаем дефолтный статус
            logger_db.error(f"Ошибка получения статуса задачи {task_key}: {e}", exc_info=True)
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
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO task_statuses (task_key, status)
                        VALUES (?, ?)
                    ''', (task_key, status))
                    conn.commit()
                finally:
                    conn.close()
        except Exception as e:
            # Логируем ошибку, но не падаем
            logger_db.error(f"Ошибка сохранения статуса {task_key}={status}: {e}", exc_info=True)
    
    def save_user_id(self, username: str, user_id: int, initials: str):
        """
        Сохранить ID пользователя
        username - имя пользователя в Telegram (например, "alex301182")
        user_id - ID пользователя в Telegram
        initials - инициалы (AG, KA)
        """
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO users (username, user_id, initials)
                        VALUES (?, ?, ?)
                    ''', (username, user_id, initials))
                    conn.commit()
                finally:
                    conn.close()
        except Exception as e:
            # Логируем ошибку, но не падаем
            logger_db.error(f"Ошибка сохранения ID пользователя {username}: {e}", exc_info=True)

    def save_user(self, username: str, initials: str):
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO users (username, user_id, initials)
                        VALUES (?, COALESCE((SELECT user_id FROM users WHERE username = ?), NULL), ?)
                    ''', (username, username, initials))
                    conn.commit()
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка сохранения пользователя {username}: {e}", exc_info=True)

    def remove_user(self, username: str):
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM users WHERE username = ?', (username,))
                    conn.commit()
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка удаления пользователя {username}: {e}", exc_info=True)

    def get_team(self) -> list:
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT username, user_id, initials FROM users')
                    rows = cursor.fetchall()
                    return [{"username": r[0], "user_id": r[1], "initials": r[2]} for r in rows]
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error("Ошибка получения команды", exc_info=True)
            return []

    def get_team_initials(self) -> list:
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT initials FROM users')
                    return [row[0] for row in cursor.fetchall()]
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error("Ошибка получения инициалов команды", exc_info=True)
            return []
    
    def get_user_ids(self) -> list:
        """
        Получить список всех ID пользователей
        Возвращает список ID для отправки личных сообщений
        """
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM users WHERE user_id IS NOT NULL')
                    results = cursor.fetchall()
                    return [row[0] for row in results if row[0] is not None]
                finally:
                    conn.close()
        except Exception as e:
            # Логируем ошибку, но не падаем
            logger_db.error(f"Ошибка получения списка ID пользователей: {e}", exc_info=True)
            return []
    
    def get_user_id_by_username(self, username: str) -> int:
        """
        Получить ID пользователя по его username
        username - имя пользователя в Telegram
        Возвращает ID пользователя или None
        """
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT user_id FROM users WHERE username = ?',
                        (username,)
                    )
                    result = cursor.fetchone()
                    if result and result[0] is not None:
                        return result[0]
                    return None
                finally:
                    conn.close()
        except Exception as e:
            # Логируем ошибку, но не падаем
            logger_db.error(f"Ошибка получения ID пользователя {username}: {e}", exc_info=True)
            return None
    
    def get_all_employees(self) -> list:
        """
        Получить список всех сотрудников
        Возвращает список словарей с информацией о сотрудниках
        """
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT username, user_id, initials FROM users ORDER BY initials')
                    results = cursor.fetchall()
                    employees = []
                    for row in results:
                        employees.append({
                            'username': row[0],
                            'user_id': row[1],
                            'initials': row[2]
                        })
                    return employees
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка получения списка сотрудников: {e}", exc_info=True)
            return []
    
    def save_custom_task(self, title: str, description: str, deadline: str, assignee: str, creator: str) -> int:
        """Сохраняет новую задачу, созданную через меню"""
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    from datetime import datetime
                    created_at = datetime.now().isoformat()
                    cursor.execute('''
                        INSERT INTO custom_tasks (title, description, deadline, assignee, creator, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (title, description, deadline, assignee, creator, created_at))
                    task_id = cursor.lastrowid
                    conn.commit()
                    logger_db.info(f"Задача #{task_id} сохранена: {title}")
                    return task_id
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка сохранения новой задачи: {e}", exc_info=True)
            return None
    
    def get_custom_tasks(self, status: str = None) -> list:
        """Получает список новых задач"""
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    if status:
                        cursor.execute('SELECT * FROM custom_tasks WHERE status = ?', (status,))
                    else:
                        cursor.execute('SELECT * FROM custom_tasks')
                    tasks = []
                    for row in cursor.fetchall():
                        tasks.append({
                            'task_id': row[0], 'title': row[1], 'description': row[2],
                            'deadline': row[3], 'assignee': row[4], 'creator': row[5],
                            'status': row[6], 'created_at': row[7], 'completed_at': row[8],
                            'result_text': row[9], 'result_photo': row[10],
                            'completed_assignees': row[11] if len(row) > 11 else '',
                            'in_progress_assignees': row[12] if len(row) > 12 else ''
                        })
                    return tasks
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка получения списка задач: {e}", exc_info=True)
            return []
    
    def get_custom_task(self, task_id: int) -> dict:
        """Получает одну новую задачу по ID"""
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM custom_tasks WHERE task_id = ?', (task_id,))
                    row = cursor.fetchone()
                    if row:
                        return {
                            'task_id': row[0], 'title': row[1], 'description': row[2],
                            'deadline': row[3], 'assignee': row[4], 'creator': row[5],
                            'status': row[6], 'created_at': row[7], 'completed_at': row[8],
                            'result_text': row[9], 'result_photo': row[10],
                            'completed_assignees': row[11] if len(row) > 11 else '',
                            'in_progress_assignees': row[12] if len(row) > 12 else ''
                        }
                    return None
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка получения задачи {task_id}: {e}", exc_info=True)
            return None
    
    def update_custom_task(self, task_id: int, **kwargs):
        """Обновляет поля новой задачи"""
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    set_clauses = []
                    values = []
                    for key, value in kwargs.items():
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                    
                    if set_clauses:
                        values.append(task_id)
                        query = f"UPDATE custom_tasks SET {', '.join(set_clauses)} WHERE task_id = ?"
                        cursor.execute(query, tuple(values))
                        conn.commit()
                    logger_db.info(f"Задача #{task_id} обновлена: {list(kwargs.keys())}")
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка обновления задачи {task_id}: {e}", exc_info=True)
    
    def delete_custom_task(self, task_id: int):
        """Удаляет новую задачу"""
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM custom_tasks WHERE task_id = ?', (task_id,))
                    conn.commit()
                    logger_db.info(f"Задача #{task_id} удалена")
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка удаления задачи {task_id}: {e}", exc_info=True)
    
    def save_presence(self, username: str, user_id: int, status: str, time: str = None, delay_minutes: int = None, reason: str = None):
        """Сохраняет отметку присутствия"""
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    from datetime import datetime
                    date_str = datetime.now().strftime("%Y-%m-%d")
                    created_at = datetime.now().isoformat()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO presence (username, user_id, date, status, time, delay_minutes, reason, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (username, user_id, date_str, status, time, delay_minutes, reason, created_at))
                    conn.commit()
                    logger_db.info(f"Отметка присутствия сохранена для {username}: {status}")
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка сохранения отметки присутствия для {username}: {e}", exc_info=True)
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Проверяет, заблокирован ли пользователь"""
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM blocked_users WHERE user_id = ?', (user_id,))
                    result = cursor.fetchone()
                    return result is not None
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка проверки блокировки пользователя {user_id}: {e}", exc_info=True)
            return False
    
    def block_user(self, user_id: int, username: str = None, reason: str = "Spam"):
        """Блокирует пользователя"""
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    from datetime import datetime
                    blocked_at = datetime.now().isoformat()
                    cursor.execute('''
                        INSERT OR REPLACE INTO blocked_users (user_id, username, reason, blocked_at)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, username, reason, blocked_at))
                    conn.commit()
                    logger_db.warning(f"Пользователь {username} (ID: {user_id}) заблокирован: {reason}")
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка блокировки пользователя {user_id}: {e}", exc_info=True)
    
    def log_spam_attempt(self, user_id: int, username: str = None, message_text: str = None):
        """Логирует попытку спама"""
        try:
            with db_lock:
                conn = self.get_connection()
                try:
                    cursor = conn.cursor()
                    from datetime import datetime
                    detected_at = datetime.now().isoformat()
                    # Ограничиваем длину текста сообщения
                    if message_text and len(message_text) > 500:
                        message_text = message_text[:500] + "..."
                    cursor.execute('''
                        INSERT INTO spam_log (user_id, username, message_text, detected_at)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, username, message_text, detected_at))
                    conn.commit()
                finally:
                    conn.close()
        except Exception as e:
            logger_db.error(f"Ошибка логирования спама для {user_id}: {e}", exc_info=True)

