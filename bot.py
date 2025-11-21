"""
ГЛАВНЫЙ ФАЙЛ БОТА
Этот файл - это "мозг" бота. Он управляет всеми командами и сообщениями.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import time as time_module
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Импортируем наши модули
from database import Database
from tasks import Tasks
from reminders import send_custom_task_reminders
from menu import (
    get_main_menu, get_testing_menu, get_tasks_menu, get_task_actions_menu,
    get_confirm_menu, get_assignee_menu, get_presence_menu,
    get_delay_time_menu, get_delay_minutes_menu
)
from handlers import (
    handle_menu_callback, handle_presence_callback, handle_delay_callback,
    handle_new_task_callback, handle_old_task_callback, handle_confirm_callback,
    handle_assignee_callback, handle_work_task_take, handle_work_task_done
)

# Настройка логирования (записи о работе бота)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter(_fmt))
_fh = RotatingFileHandler('bot.log', maxBytes=1_000_000, backupCount=5, encoding='utf-8')
_fh.setFormatter(logging.Formatter(_fmt))
logger.handlers = []
logger.addHandler(_sh)
logger.addHandler(_fh)

# Получаем данные из переменных окружения (секретные данные)
# ВАЖНО: В production НЕ используйте дефолтные значения!
# Все значения должны быть установлены через переменные окружения
BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
CHAT_ID = os.getenv('CHAT_ID', '').strip()
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', '').strip()

# Проверяем все обязательные переменные
if not BOT_TOKEN or len(BOT_TOKEN) < 10:
    raise ValueError("BOT_TOKEN is invalid or empty! Set it via environment variable.")
if not CHAT_ID:
    raise ValueError("CHAT_ID is empty! Set it via environment variable.")
if not ADMIN_USERNAME:
    raise ValueError("ADMIN_USERNAME is empty! Set it via environment variable.")

# Инициализация базы данных и задач
db = Database()
tasks_manager = Tasks()

# Часовой пояс (Москва)
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

MORNING_TIME = os.getenv('MORNING_TIME', '08:00')
SUMMARY_TIME = os.getenv('SUMMARY_TIME', '16:50')

def _parse_time_str(t: str):
    try:
        parts = t.split(':')
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return 8, 0
        return h, m
    except Exception:
        return 8, 0

# Список известных спамеров (черный список)
SPAM_BLACKLIST = [
    "HRmanagerYOUTUBE",
    "performance manager"
]

# Список спам-фраз для обнаружения
SPAM_KEYWORDS = [
    "fucked",
    "fuck",
    "YOUR BOT IS",
    "ADDITIONAL INFORMATION",
    "personal ACCOUNT",
    "performance manager"
]


def is_spam_message(text: str, username: str = None) -> bool:
    """Проверяет, является ли сообщение спамом"""
    if not text:
        return False
    
    text_lower = text.lower()
    username_lower = username.lower() if username else ""
    
    # Проверка черного списка
    for spam_user in SPAM_BLACKLIST:
        if spam_user.lower() in username_lower:
            return True
    
    # Проверка ключевых слов
    for keyword in SPAM_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    
    # Проверка на повторяющиеся сообщения (более 3 одинаковых символов подряд)
    if len(set(text)) < 3 and len(text) > 10:
        return True
    
    # Проверка на слишком много заглавных букв (более 50%)
    if len(text) > 20:
        uppercase_count = sum(1 for c in text if c.isupper())
        if uppercase_count / len(text) > 0.5:
            return True
    
    return False


async def spam_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Фильтр спама - проверяет сообщения перед обработкой"""
    try:
        user = update.effective_user
        if not user:
            return False
        
        user_id = user.id
        username = user.username if user.username else f"user_{user_id}"
        
        # Проверяем, не заблокирован ли пользователь
        if db.is_user_blocked(user_id):
            logger.warning(f"Заблокированный пользователь {username} (ID: {user_id}) попытался отправить сообщение")
            return True  # Блокируем
        
        # Проверяем текстовые сообщения
        if update.message and update.message.text:
            message_text = update.message.text
            
            if is_spam_message(message_text, username):
                # Логируем попытку спама
                db.log_spam_attempt(user_id, username, message_text)
                
                # Автоматически блокируем спамера
                db.block_user(user_id, username, "Spam detected")
                
                # Уведомляем администратора
                try:
                    admin_id = context.bot_data.get('admin_id')
                    if not admin_id:
                        admin_username = context.bot_data.get('ADMIN_USERNAME', ADMIN_USERNAME)
                        admin_id = db.get_user_id_by_username(admin_username)
                    
                    if admin_id:
                        spam_notification = (
                            f"🚫 **СПАМ ОБНАРУЖЕН И ЗАБЛОКИРОВАН**\n\n"
                            f"👤 Пользователь: @{username}\n"
                            f"🆔 ID: {user_id}\n"
                            f"📝 Сообщение: {message_text[:200]}\n\n"
                            f"Пользователь автоматически заблокирован."
                        )
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=spam_notification,
                            parse_mode='Markdown'
                        )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления администратору о спаме: {e}", exc_info=True)
                
                logger.warning(f"🚫 СПАМ ОБНАРУЖЕН от @{username} (ID: {user_id}): {message_text[:100]}")
                return True  # Блокируем сообщение
        
        return False  # Не спам, пропускаем
        
    except Exception as e:
        logger.error(f"Ошибка в spam_filter: {e}", exc_info=True)
        return False  # В случае ошибки пропускаем (безопаснее)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - главное меню бота"""
    try:
        # Проверка на спам перед обработкой
        if await spam_filter(update, context):
            return  # Блокируем спам
        
        user = update.effective_user
        logger.info(f"Команда /start от пользователя @{user.username} (ID: {user.id})")
        
        # Сохраняем пользователя в БД
        if user.username:
            user_mapping = {
                "alex301182": {"initials": "AG", "name": "АГ", "full_name": "Lysenko Alexander"},
                "Korudirp": {"initials": "KA", "name": "КА", "full_name": "Cherenkov Ruslan"}
            }
            if user.username in user_mapping:
                db.save_user_id(user.username, user.id, user_mapping[user.username]["initials"])
            
            # Если это администратор, сохраняем его ID
            if user.username == ADMIN_USERNAME:
                db.save_user_id(ADMIN_USERNAME, user.id, "ADMIN")
                context.bot_data['admin_id'] = user.id
                logger.info(f"Admin ID сохранен: {user.id}")
        
        response = (
            f"👋 Добро пожаловать!\n\n"
            f"🤖 Я бот для управления задачами\n\n"
            f"📱 Выберите действие из меню ниже:"
        )
        
        await update.message.reply_text(response, reply_markup=get_main_menu())
        logger.info(f"Главное меню отправлено пользователю @{user.username}")
    except Exception as e:
        logger.error(f"Ошибка в start_command: {e}", exc_info=True)
        try:
            await update.message.reply_text(f"❌ Ошибка: {e}")
        except:
            pass


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help - список всех доступных команд"""
    try:
        user = update.effective_user
        is_admin = user.username == ADMIN_USERNAME if user.username else False
        
        text = "📋 **ДОСТУПНЫЕ КОМАНДЫ**\n\n"
        
        text += "**Для всех:**\n"
        text += "/start - Главное меню бота\n"
        text += "/help - Список команд (это сообщение)\n"
        text += "/cancel - Отменить текущее действие\n\n"
        
        if is_admin:
            text += "**Только для администратора:**\n"
            text += "/force_morning - Отправить ежедневные задачи сейчас\n"
            text += "/add_urgent ТЕКСТ - Добавить срочную задачу в группу\n\n"
        
        text += "**Меню бота:**\n"
        text += "📝 Создать задачу - Создать новую задачу\n"
        text += "🧪 Тестирование - Тестовые функции\n"
        text += "❓ Помощь - Справка по использованию\n\n"
        
        text += "**Примечание:**\n"
        text += "Используйте /cancel для отмены любого действия"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.info(f"Команда /help выполнена пользователем @{user.username}")
    except Exception as e:
        logger.error(f"Ошибка в help_command: {e}", exc_info=True)
        try:
            await update.message.reply_text(f"❌ Ошибка: {e}")
        except:
            pass


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cancel - отмена текущего действия"""
    try:
        # Проверка на спам перед обработкой
        if await spam_filter(update, context):
            return  # Блокируем спам
        
        user = update.effective_user
        
        # Очищаем все данные пользователя
        context.user_data.clear()
        
        text = "❌ **ОТМЕНА**\n\nВсе действия отменены. Вы можете начать заново."
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 В главное меню", callback_data="menu_main")
        ]])
        
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        logger.info(f"Команда /cancel выполнена пользователем @{user.username}")
    except Exception as e:
        logger.error(f"Ошибка в cancel_command: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Ошибка при отмене")
        except:
            pass


async def add_urgent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add_urgent - добавить внеплановую задачу"""
    try:
        # Проверка на спам перед обработкой
        if await spam_filter(update, context):
            return  # Блокируем спам
        
        user = update.effective_user
        if not user:
            logger.error("user is None in add_urgent_command")
            return
        
        # Проверяем, что команду запускает админ
        if user.username != ADMIN_USERNAME:
            await update.message.reply_text(
                "❌ У вас нет прав для использования этой команды."
            )
            return
    except Exception as e:
        logger.error(f"Ошибка проверки прав в add_urgent_command: {e}", exc_info=True)
        return
    
    try:
        # Получаем текст задачи
        if not context.args:
            await update.message.reply_text(
                "❌ Использование: /add_urgent ТЕКСТ ЗАДАЧИ\n\n"
                "Пример: /add_urgent Проверить отчет"
            )
            return
        
        task_text = " ".join(context.args)
        urgent_task = f"🔥 {task_text}"
        
        # Преобразуем CHAT_ID в int если это строка
        chat_id = int(CHAT_ID) if isinstance(CHAT_ID, str) else CHAT_ID
        
        logger.info(f"Отправка срочной задачи в чат {chat_id}: {urgent_task}")
        
        # Отправляем задачу в группу
        logger.info("Создание клавиатуры для задачи...")
        try:
            # Используем уникальный ID для срочных задач, чтобы избежать конфликтов
            urgent_task_id = f"urgent_{int(time_module.time())}"
            keyboard = create_task_keyboard(urgent_task, urgent_task_id)
            logger.info(f"✅ Клавиатура создана успешно для задачи: {urgent_task} (ID: {urgent_task_id})")
        except Exception as kb_error:
            logger.error(f"❌ ОШИБКА создания клавиатуры: {kb_error}")
            logger.error(f"   Тип ошибки: {type(kb_error).__name__}")
            raise
        
        try:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔥 **ВНЕПЛАНОВАЯ ЗАДАЧА**\n\n{urgent_task}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Срочная задача успешно отправлена в чат {chat_id}. Message ID: {msg.message_id}")
        except Exception as send_error:
            logger.error(f"❌ ОШИБКА отправки сообщения в чат {chat_id}: {send_error}")
            logger.error(f"   Тип ошибки: {type(send_error).__name__}")
            raise
        
        await update.message.reply_text(f"✅ Задача добавлена в группу!")
        logger.info("Подтверждение отправлено пользователю")
    except Exception as e:
        error_msg = f"❌ Ошибка отправки задачи: {e}"
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в add_urgent_command: {e}", exc_info=True)
        try:
            await update.message.reply_text(error_msg)
        except:
            pass


async def force_morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /force_morning - отправить задачи прямо сейчас"""
    try:
        # Проверка на спам перед обработкой
        if await spam_filter(update, context):
            return  # Блокируем спам
        
        user = update.effective_user
        if not user:
            logger.error("user is None in force_morning_command")
            return
        
        # Проверяем, что команду запускает админ
        if user.username != ADMIN_USERNAME:
            await update.message.reply_text(
                "❌ У вас нет прав для использования этой команды."
            )
            return
    except Exception as e:
        logger.error(f"Ошибка проверки прав в force_morning_command: {e}", exc_info=True)
        return
    
    try:
        logger.info("Команда /force_morning выполнена")
        
        # Создаем объект приложения для функции
        class AppWrapper:
            def __init__(self, bot):
                self.bot = bot
        
        app_wrapper = AppWrapper(context.bot)
        # force_weekend=True позволяет отправлять задачи даже в выходные
        await send_morning_tasks(app_wrapper, force_weekend=True)
        await update.message.reply_text("✅ Задачи отправлены в группу!")
        logger.info("Задачи успешно отправлены через /force_morning")
    except Exception as e:
        error_msg = f"❌ Ошибка отправки задач: {e}"
        logger.error(f"Ошибка в force_morning_command: {e}", exc_info=True)
        await update.message.reply_text(error_msg)


async def team_add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if await spam_filter(update, context):
            return
        user = update.effective_user
        if not user or user.username != ADMIN_USERNAME:
            await update.message.reply_text("❌ Недостаточно прав")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /team_add @username INITIALS")
            return
        username = context.args[0].lstrip('@')
        initials = context.args[1].upper()
        db.save_user(username, initials)
        await update.message.reply_text(f"✅ Добавлен: @{username} ({initials})")
    except Exception as e:
        logger.error(f"Ошибка team_add_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка")


async def team_remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if await spam_filter(update, context):
            return
        user = update.effective_user
        if not user or user.username != ADMIN_USERNAME:
            await update.message.reply_text("❌ Недостаточно прав")
            return
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /team_remove @username")
            return
        username = context.args[0].lstrip('@')
        db.remove_user(username)
        await update.message.reply_text(f"✅ Удален: @{username}")
    except Exception as e:
        logger.error(f"Ошибка team_remove_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка")


async def team_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if await spam_filter(update, context):
            return
        team = db.get_team()
        if not team:
            await update.message.reply_text("👥 Список пуст")
            return
        lines = []
        for m in team:
            u = m.get('username')
            i = m.get('initials')
            lines.append(f"@{u} ({i})")
        await update.message.reply_text("👥 Команда:\n" + "\n".join(lines))
    except Exception as e:
        logger.error(f"Ошибка team_list_command: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка")

def create_task_keyboard(task_text: str, task_id: str) -> InlineKeyboardMarkup:
    """Создает одну кнопку для задачи"""
    # Одна кнопка с названием задачи
    # Статус будет обновляться при нажатии
    
    # Для новых задач всегда начинаем с ⚪ (не обращаемся к БД, чтобы избежать блокировок)
    # Реальный статус будет загружен и обновлен при нажатии кнопки
    task_status = "⚪"
    
    # Валидация: Telegram ограничивает callback_data до 64 байт
    callback_data = f"task_{task_id}"
    if len(callback_data.encode('utf-8')) > 64:
        logger.error(f"⚠️ callback_data слишком длинный: {len(callback_data.encode('utf-8'))} байт")
        # Укорачиваем task_id если нужно
        max_task_id_len = 64 - len("task_".encode('utf-8'))
        task_id = task_id[:max_task_id_len]
        callback_data = f"task_{task_id}"
        logger.warning(f"Укорочен task_id до: {task_id}")
    
    # ОПТИМИЗАЦИЯ ДЛЯ МОБИЛЬНЫХ: ограничиваем длину текста кнопки до 20 символов
    # Это обеспечит полную видимость на мобильных устройствах
    max_mobile_length = 20
    if len(task_text) > max_mobile_length:
        # Укорачиваем текст задачи для мобильных
        task_text_short = task_text[:max_mobile_length-3] + "..."
        button_text = f"{task_text_short} {task_status}"
    else:
        button_text = f"{task_text} {task_status}"
    
    # Дополнительная проверка на случай, если статус делает текст слишком длинным
    if len(button_text) > 25:  # Оставляем запас для мобильных
        max_text_len = 25 - len(f" {task_status}")
        task_text_short = task_text[:max_text_len-3] + "..."
        button_text = f"{task_text_short} {task_status}"
        logger.warning(f"Текст кнопки укорочен для мобильных: '{button_text}'")
    
    buttons = [
        [
            InlineKeyboardButton(
                button_text,
                callback_data=callback_data
            )
        ]
    ]
    
    return InlineKeyboardMarkup(buttons)


async def handle_delay_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка причины опоздания"""
    try:
        # Проверка на спам перед обработкой
        if await spam_filter(update, context):
            return  # Блокируем спам
        
        if not context.user_data.get('waiting_reason'):
            return
        
        reason = update.message.text
        user = update.effective_user
        username = user.username if user.username else f"user_{user.id}"
        user_id = user.id
        
        delay_minutes = context.user_data.get('delay_minutes', 0)
        hour = context.user_data.get('delay_hour', 0)
        minute = context.user_data.get('delay_minute', 0)
        
        # Сохраняем в БД
        if 'db' in context.bot_data:
            db = context.bot_data['db']
        else:
            from database import Database
            db = Database()
        
        from datetime import datetime
        time_str = datetime.now(MOSCOW_TZ).strftime("%H:%M")
        db.save_presence(username, user_id, "late", time=time_str, delay_minutes=delay_minutes, reason=reason)
        
        # Отправляем уведомление администратору
        try:
            # Получаем admin_id
            admin_id = None
            if 'admin_id' in context.bot_data:
                admin_id = context.bot_data['admin_id']
            else:
                # Пытаемся получить из БД
                admin_username = context.bot_data.get('ADMIN_USERNAME', ADMIN_USERNAME)
                admin_id = db.get_user_id_by_username(admin_username)
                if admin_id:
                    context.bot_data['admin_id'] = admin_id
            
            if admin_id:
                text = (
                    f"⏰ **ОПОЗДАНИЕ**\n\n"
                    f"👤 Логин: @{username}\n"
                    f"⏰ Время опоздания: {hour}ч {minute}м\n"
                    f"📝 Причина: {reason}\n"
                    f"🕐 Время отметки: {time_str}"
                )
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode='Markdown'
                )
                logger.info(f"Уведомление об опоздании отправлено администратору {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления администратору: {e}", exc_info=True)
        
        # Отправляем подтверждение пользователю
        text = (
            f"✅ **ОПОЗДАНИЕ ЗАФИКСИРОВАНО**\n\n"
            f"⏰ Время опоздания: {hour}ч {minute}м\n"
            f"📝 Причина: {reason}\n"
            f"🕐 Время отметки: {time_str}"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
        
        # Очищаем данные
        context.user_data.pop('waiting_reason', None)
        context.user_data.pop('delay_minutes', None)
        context.user_data.pop('delay_hour', None)
        context.user_data.pop('delay_minute', None)
        
        logger.info(f"Опоздание сохранено для {username}: {hour}ч {minute}м, причина: {reason}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_delay_reason: {e}", exc_info=True)
        if update.message:
            await update.message.reply_text("❌ Произошла ошибка при сохранении опоздания")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    try:
        # Проверка на спам перед обработкой (для callback_query проверяем пользователя)
        user = update.effective_user if update.effective_user else None
        if user and db.is_user_blocked(user.id):
            logger.warning(f"Заблокированный пользователь {user.username} (ID: {user.id}) попытался нажать кнопку")
            if update.callback_query:
                await update.callback_query.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        query = update.callback_query
        if not query:
            logger.error("query is None")
            return
        
        # Парсим данные из кнопки
        data = query.data
        logger.info(f"Нажата кнопка: {data}")
        
        if not data:
            logger.warning(f"Пустые данные кнопки")
            await query.answer()
            return
        
        # Обработка меню (кроме menu_create_task, menu_add_employee и team_add - их обрабатывает ConversationHandler)
        # Если это menu_create_task, menu_add_employee или team_add, просто возвращаемся - ConversationHandler должен перехватить
        if data == "menu_create_task" or data == "menu_add_employee" or data == "team_add":
            return  # Не обрабатываем здесь, пусть ConversationHandler перехватит
        
        if data.startswith("menu_"):
            await handle_menu_callback(query, data, context, db)
            return
        
        # Обработка тестирования (test_daily_tasks, test_employees)
        if data.startswith("test_"):
            await handle_menu_callback(query, data, context, db)
            return
        
        # Обработка присутствия
        if data.startswith("presence_"):
            await handle_presence_callback(query, data, context, db)
            return
        
        # Обработка задержки
        if data.startswith("delay_"):
            await handle_delay_callback(query, data, context, db, get_delay_time_menu, get_delay_minutes_menu)
            return
        
        # Обработка задач из меню
        if data.startswith("task_"):
            # Проверяем, это старая система задач или новая
            if "_" in data and data.split("_")[1].isdigit():
                # Старая система (task_0_1)
                await handle_old_task_callback(query, data, context, db)
            else:
                # Новая система (task_view_1, task_edit_1 и т.д.)
                await handle_new_task_callback(query, data, context, db, get_task_actions_menu, get_confirm_menu)
            return
        
        # Обработка подтверждений
        if data.startswith("confirm_") or data.startswith("cancel_"):
            await handle_confirm_callback(query, data, context, db, get_task_actions_menu, get_tasks_menu)
            return
        
        # Обработка назначения исполнителя
        if data.startswith("assignee_"):
            await handle_assignee_callback(query, data, context, db)
            return
        
        # Обработка "Взять в работу" и "Готово"
        if data.startswith("work_take_"):
            await handle_work_task_take(query, data, context, db)
            return
        
        if data.startswith("work_done_"):
            await handle_work_task_done(query, data, context, db)
            return
        
        logger.warning(f"Неизвестный формат данных кнопки: {data}")
        await query.answer("❌ Неизвестная команда")
        
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в button_callback: {type(e).__name__}: {e}", exc_info=True)
        try:
            # Пытаемся получить query из update
            if update and hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.answer("❌ Произошла ошибка", show_alert=True)
        except Exception as answer_error:
            logger.error(f"Не удалось отправить ответ об ошибке: {answer_error}")
        # НЕ ПОДНИМАЕМ ИСКЛЮЧЕНИЕ - бот должен продолжать работать


async def send_morning_tasks(app, force_weekend=False):
    """Отправка задач на день в 08:00"""
    try:
        # Проверяем, что сегодня рабочий день (пн-пт)
        today = datetime.now(MOSCOW_TZ).weekday()  # 0=понедельник, 4=пятница, 5=суббота, 6=воскресенье
        
        logger.info(f"Текущий день недели: {today} (0=пн, 4=пт, 5=сб, 6=вс), force_weekend={force_weekend}")
        
        # Если выходной и не принудительная отправка - используем задачи понедельника для теста
        if today > 4 and not force_weekend:
            logger.info(f"Сегодня выходной (день {today}), используем задачи понедельника для теста")
            today = 0  # Используем задачи понедельника
        
        # Получаем задачи на сегодня
        day_tasks = tasks_manager.get_tasks_for_day(today)
        
        if not day_tasks:
            logger.warning(f"Нет задач для дня {today}, используем задачи понедельника")
            # Если нет задач, используем задачи понедельника
            day_tasks = tasks_manager.get_tasks_for_day(0)
            today = 0
            logger.info(f"Используем задачи понедельника: {len(day_tasks)} задач")
        
        # Формируем сообщение
        day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
        day_name = day_names[today] if today < 5 else "Понедельник"
        date_str = datetime.now(MOSCOW_TZ).strftime("%d.%m.%Y")
        
        logger.info(f"Отправка задач на {day_name} ({date_str}), всего задач: {len(day_tasks)}")
        
        # Преобразуем CHAT_ID в int если это строка
        chat_id = int(CHAT_ID) if isinstance(CHAT_ID, str) else CHAT_ID
        
        logger.info(f"Попытка отправить {len(day_tasks)} задач в чат {chat_id}")
        
        # Формируем одно сообщение со всеми задачами
        logger.info(f"Формирование сообщения с {len(day_tasks)} задачами...")
        
        # Создаем текст сообщения со всеми задачами
        message_text = f"📋 ЗАДАЧИ НА {day_name.upper()} ({date_str})\n\n"
        
        # Создаем кнопки для всех задач (ОДНА кнопка на задачу)
        all_buttons = []
        
        # Проверяем, что сообщение не превысит лимит
        estimated_length = len(message_text)
        
        for i, task in enumerate(day_tasks, 1):
            task_id = f"{today}_{i}"
            task_line = f"{i}. {task}\n"
            
            # Проверяем, не превысит ли сообщение лимит (4096 символов)
            if estimated_length + len(task_line) > 4000:  # Оставляем запас
                logger.warning(f"⚠️ Сообщение слишком длинное, останавливаемся на задаче {i-1}")
                break
            
            message_text += task_line
            estimated_length += len(task_line)
            
            # Валидация callback_data (Telegram ограничивает до 64 байт)
            callback_data = f"task_{task_id}"
            if len(callback_data.encode('utf-8')) > 64:
                logger.error(f"⚠️ callback_data слишком длинный для задачи {i}: {len(callback_data.encode('utf-8'))} байт")
                # Пропускаем эту задачу
                continue
            
            # ОПТИМИЗАЦИЯ ДЛЯ МОБИЛЬНЫХ: ограничиваем длину текста кнопки до 20 символов
            # Это обеспечит полную видимость на мобильных устройствах
            max_mobile_length = 20
            if len(task) > max_mobile_length:
                # Укорачиваем текст задачи для мобильных
                task_short = task[:max_mobile_length-3] + "..."
                button_text = f"{i}. {task_short} ⚪"
            else:
                button_text = f"{i}. {task} ⚪"
            
            # Дополнительная проверка на случай, если номер задачи делает текст слишком длинным
            if len(button_text) > 25:  # Оставляем запас для мобильных
                max_text_len = 25 - len(f"{i}. ⚪")
                task_short = task[:max_text_len-3] + "..."
                button_text = f"{i}. {task_short} ⚪"
                logger.warning(f"Текст кнопки для задачи {i} укорочен для мобильных: '{button_text}'")
            
            # Добавляем ОДНУ кнопку для этой задачи
            all_buttons.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=callback_data
                )
            ])
        
        # Проверяем, что есть хотя бы одна задача
        if not all_buttons:
            logger.error("❌ Нет задач для отправки (все были отфильтрованы)")
            return
        
        # Создаем клавиатуру со всеми кнопками
        keyboard = InlineKeyboardMarkup(all_buttons)
        
        # Валидация: Telegram ограничивает количество кнопок (до 100)
        if len(all_buttons) > 100:
            logger.warning(f"⚠️ Слишком много кнопок ({len(all_buttons)}), ограничиваем до 100")
            all_buttons = all_buttons[:100]
            keyboard = InlineKeyboardMarkup(all_buttons)
        
        # Отправляем одно сообщение со всеми задачами
        try:
            logger.info(f"Отправка сообщения с {len(all_buttons)} задачами в чат {chat_id}...")
            msg = await app.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=keyboard
            )
            logger.info(f"✅ Все {len(all_buttons)} задач отправлены одним сообщением! Message ID: {msg.message_id}")
        except Exception as e:
            logger.error(f"❌ ОШИБКА отправки сообщения: {type(e).__name__}: {e}")
            raise
                
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в send_morning_tasks: {e}", exc_info=True)
        raise


async def send_reminders(app: Application):
    """Отправка напоминаний в личные сообщения в 13:00"""
    try:
        today = datetime.now(MOSCOW_TZ).weekday()
        
        if today > 4:
            return
        
        # Получаем задачи на сегодня
        day_tasks = tasks_manager.get_tasks_for_day(today)
        
        if not day_tasks:
            return
    except Exception as e:
        logger.error(f"❌ Ошибка в начале send_reminders: {e}", exc_info=True)
        return
    
    # Получаем невыполненные задачи для каждого пользователя
    user_mapping = {
        "AG": {"username": "alex301182", "initials": "AG"},
        "KA": {"username": "Korudirp", "initials": "KA"}
    }
    
    # Собираем невыполненные задачи для каждого пользователя
    for initials, user_info in user_mapping.items():
        incomplete_tasks = []
        
        try:
            for i, task in enumerate(day_tasks, 1):
                task_id = f"{today}_{i}"
                status_key = f"{task_id}_{initials}"
                try:
                    status = db.get_task_status(status_key)
                except Exception as e:
                    logger.error(f"Ошибка получения статуса {status_key}: {e}", exc_info=True)
                    status = "⚪"
                
                if status != "✅":
                    incomplete_tasks.append(task)
        except Exception as e:
            logger.error(f"Ошибка обработки задач для {user_info['username']}: {e}", exc_info=True)
            continue
        
        if not incomplete_tasks:
            continue
        
        # Формируем сообщение для пользователя
        # Валидация: Telegram ограничивает длину сообщения до 4096 символов
        message = f"⏰ **НАПОМИНАНИЕ**\n\n"
        message += f"У вас есть невыполненные задачи:\n\n"
        
        max_message_length = 4000  # Оставляем запас
        current_length = len(message)
        
        for i, task in enumerate(incomplete_tasks, 1):
            task_line = f"{i}. {task}\n"
            if current_length + len(task_line) > max_message_length:
                message += f"\n... и еще {len(incomplete_tasks) - i + 1} задач"
                logger.warning(f"Сообщение для {user_info['username']} обрезано из-за лимита длины")
                break
            message += task_line
            current_length += len(task_line)
        
        # Получаем ID пользователя из базы данных
        try:
            user_id = db.get_user_id_by_username(user_info["username"])
        except Exception as e:
            logger.error(f"Ошибка получения ID пользователя {user_info['username']}: {e}", exc_info=True)
            user_id = None
        
        if user_id:
            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
                logger.info(f"✅ Напоминание отправлено пользователю {user_info['username']} (ID: {user_id})")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки напоминания пользователю {user_info['username']}: {type(e).__name__}: {e}", exc_info=True)
        else:
            # Если ID еще не сохранен, логируем предупреждение
            logger.warning(f"⚠️ ID пользователя {user_info['username']} не найден в базе данных")


async def send_evening_summary(app: Application):
    """Отправка итогов дня в 16:50"""
    try:
        today = datetime.now(MOSCOW_TZ).weekday()
        
        if today > 4:
            return
        
        # Получаем задачи на сегодня
        day_tasks = tasks_manager.get_tasks_for_day(today)
        
        if not day_tasks:
            return
    except Exception as e:
        logger.error(f"❌ Ошибка в начале send_evening_summary: {e}", exc_info=True)
        return
    
    # Собираем невыполненные задачи
    incomplete = []
    try:
        for i, task in enumerate(day_tasks, 1):
            task_id = f"{today}_{i}"
            try:
                status_ag = db.get_task_status(f"{task_id}_AG")
                status_ka = db.get_task_status(f"{task_id}_KA")
                status_sa = db.get_task_status(f"{task_id}_SA")
            except Exception as e:
                logger.error(f"Ошибка получения статусов для задачи {task_id}: {e}", exc_info=True)
                # Используем дефолтные статусы
                status_ag = "⚪"
                status_ka = "⚪"
                status_sa = "⚪"
            
            # Задача невыполнена, если хотя бы один не выполнил
            if status_ag != "✅" or status_ka != "✅" or status_sa != "✅":
                users_needed = []
                if status_ag != "✅":
                    users_needed.append("Lysenko Alexander")
                if status_ka != "✅":
                    users_needed.append("Ruslan Cherenkov")
                if status_sa != "✅":
                    users_needed.append("Test")
                
                # Формируем список исполнителей
                if len(users_needed) == 1:
                    users_str = users_needed[0]
                else:
                    users_str = ", ".join(users_needed)
                
                incomplete.append({
                    "task": task,
                    "users": users_str
                })
    except Exception as e:
        logger.error(f"❌ Ошибка обработки задач для итогов дня: {e}", exc_info=True)
        incomplete = []
    
    if not incomplete:
        message = "✅ **ИТОГИ ДНЯ**\n\nВсе задачи выполнены. Хорошей дороги домой."
    else:
        message = "📊 **ИТОГИ ДНЯ**\n\nНевыполненные задачи (нужно завершить сегодня):\n\n"
        # Валидация: Telegram ограничивает длину сообщения до 4096 символов
        max_message_length = 4000  # Оставляем запас
        current_length = len(message)
        
        for idx, item in enumerate(incomplete):
            task_line = f"• {item['task']}\n  Исполнитель: {item['users']}\n"
            if current_length + len(task_line) > max_message_length:
                message += f"\n... и еще {len(incomplete) - idx} задач"
                logger.warning("Сообщение итогов дня обрезано из-за лимита длины")
                break
            message += task_line
            current_length += len(task_line)
    
    # Отправляем в группу
    try:
        # Преобразуем CHAT_ID в int если это строка
        chat_id = int(CHAT_ID) if isinstance(CHAT_ID, str) else CHAT_ID
        await app.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Итоги дня отправлены в чат {chat_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки итогов дня: {type(e).__name__}: {e}", exc_info=True)


async def send_presence_buttons(app: Application, force_weekend=False):
    """Отправка кнопок присутствия в 08:30"""
    try:
        today = datetime.now(MOSCOW_TZ).weekday()
        
        # Если выходной и не принудительная отправка - не отправляем
        if today > 4 and not force_weekend:  # Выходной
            logger.info(f"Сегодня выходной (день {today}), кнопки присутствия не отправляются")
            return
        
        chat_id = int(CHAT_ID) if isinstance(CHAT_ID, str) else CHAT_ID
        date_str = datetime.now(MOSCOW_TZ).strftime("%d.%m.%Y")
        
        message = (
            f"⏰ **ОТМЕТКА ПРИСУТСТВИЯ**\n\n"
            f"📅 Дата: {date_str}\n\n"
            f"Пожалуйста, отметьте своё присутствие:"
        )
        
        await app.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=get_presence_menu(),
            parse_mode='Markdown'
        )
        logger.info(f"✅ Кнопки присутствия отправлены в чат {chat_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки кнопок присутствия: {type(e).__name__}: {e}", exc_info=True)


async def send_presence_reminder(app: Application):
    """Напоминание о присутствии в 08:30 для тех, кто не отметился"""
    try:
        today = datetime.now(MOSCOW_TZ).weekday()
        
        if today > 4:  # Выходной
            return
        
        db = app.bot_data.get('db')
        if not db:
            logger.error("База данных не найдена в bot_data")
            return
        
        # Получаем список всех пользователей
        all_users = [
            {"username": "alex301182", "name": "Lysenko Alexander", "user_id": None},
            {"username": "Korudirp", "name": "Ruslan Cherenkov", "user_id": None}
        ]
        
        # Получаем user_id для каждого пользователя
        for user in all_users:
            user_id = db.get_user_id_by_username(user["username"])
            if user_id:
                user["user_id"] = user_id
        
        # Получаем дату сегодня в формате YYYY-MM-DD
        today_str = datetime.now(MOSCOW_TZ).strftime("%Y-%m-%d")
        
        # Проверяем, кто отметился сегодня
        marked_users = set()
        try:
            from database import db_lock
            with db_lock:
                conn = db.get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT username FROM presence WHERE date = ?',
                        (today_str,)
                    )
                    results = cursor.fetchall()
                    marked_users = {row[0] for row in results}
                finally:
                    conn.close()
        except Exception as e:
            logger.error(f"Ошибка получения списка отметившихся: {e}", exc_info=True)
        
        # Находим тех, кто не отметился
        not_marked = [user for user in all_users if user["username"] not in marked_users and user["user_id"]]
        
        if not not_marked:
            logger.info("Все пользователи отметили присутствие")
            return
        
        # Отправляем напоминание в общий чат
        chat_id = app.bot_data.get('CHAT_ID')
        if not chat_id:
            import os
            chat_id = os.getenv('CHAT_ID', '').strip()
        
        if chat_id:
            chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
            
            names = [user["name"] for user in not_marked]
            if len(names) == 1:
                message = f"⏰ **НАПОМИНАНИЕ О ПРИСУТСТВИИ**\n\n{names[0]}, пожалуйста, отметьте своё присутствие на рабочем месте."
            else:
                names_str = ", ".join(names)
                message = f"⏰ **НАПОМИНАНИЕ О ПРИСУТСТВИИ**\n\n{names_str}, пожалуйста, отметьте своё присутствие на рабочем месте."
            
            try:
                await app.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=get_presence_menu()
                )
                logger.info(f"✅ Напоминание о присутствии отправлено в чат {chat_id} для {len(not_marked)} пользователей")
            except Exception as e:
                logger.error(f"❌ Ошибка отправки напоминания о присутствии: {e}", exc_info=True)
    
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в send_presence_reminder: {e}", exc_info=True)


def setup_scheduler(app: Application):
    """Настройка расписания отправки сообщений"""
    scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)
    h1, m1 = _parse_time_str(MORNING_TIME)
    h2, m2 = _parse_time_str(SUMMARY_TIME)
    scheduler.add_job(
        send_morning_tasks,
        trigger=CronTrigger(hour=h1, minute=m1, day_of_week='mon-fri', timezone=MOSCOW_TZ),
        args=[app]
    )
    scheduler.add_job(
        send_evening_summary,
        trigger=CronTrigger(hour=h2, minute=m2, day_of_week='mon-fri', timezone=MOSCOW_TZ),
        args=[app]
    )
    
    
    scheduler.start()
    logger.info("Расписание настроено: 08:00 (задачи), 16:50 (итоги дня)")


def main():
    """Главная функция - запуск бота"""
    try:
        logger.info("=" * 50)
        logger.info("ЗАПУСК БОТА")
        logger.info(f"BOT_TOKEN: {BOT_TOKEN[:10]}... (длина: {len(BOT_TOKEN)})")
        logger.info(f"CHAT_ID: {CHAT_ID}")
        logger.info(f"ADMIN_USERNAME: {ADMIN_USERNAME}")
        logger.info("=" * 50)
        
        # Создаем приложение бота
        application = Application.builder().token(BOT_TOKEN).build()
        logger.info("Приложение бота создано")
        
        # Сохраняем глобальный экземпляр db в bot_data для использования в ConversationHandlers
        application.bot_data['db'] = db
        logger.info("Глобальный экземпляр db сохранен в bot_data")
        
        # Сохраняем CHAT_ID для использования в ConversationHandlers
        application.bot_data['CHAT_ID'] = CHAT_ID
        logger.info("CHAT_ID сохранен в bot_data")
        
        # Сохраняем ADMIN_USERNAME для использования в handlers и conversations
        application.bot_data['ADMIN_USERNAME'] = ADMIN_USERNAME
        logger.info("ADMIN_USERNAME сохранен в bot_data")
        
        # Блокируем известных спамеров при старте
        for spam_username in SPAM_BLACKLIST:
            spam_user_id = db.get_user_id_by_username(spam_username)
            if spam_user_id:
                db.block_user(spam_user_id, spam_username, "Known spammer")
                logger.warning(f"Известный спамер {spam_username} (ID: {spam_user_id}) заблокирован при старте")
            else:
                logger.info(f"Спамер {spam_username} еще не найден в БД, будет заблокирован при первой попытке")
        
        application.bot_data['send_morning_tasks'] = send_morning_tasks
        logger.info("Функции тестирования сохранены в bot_data")
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        logger.info("Обработчик /start зарегистрирован")
        
        application.add_handler(CommandHandler("help", help_command))
        logger.info("Обработчик /help зарегистрирован")
        
        application.add_handler(CommandHandler("cancel", cancel_command))
        logger.info("Обработчик /cancel зарегистрирован")
        
        application.add_handler(CommandHandler("add_urgent", add_urgent_command))
        logger.info("Обработчик /add_urgent зарегистрирован")
        
        application.add_handler(CommandHandler("force_morning", force_morning_command))
        logger.info("Обработчик /force_morning зарегистрирован")

        application.add_handler(CommandHandler("team_add", team_add_command))
        application.add_handler(CommandHandler("team_remove", team_remove_command))
        application.add_handler(CommandHandler("team_list", team_list_command))
        logger.info("Команды управления командой зарегистрированы")
        
        # Регистрируем глобальный фильтр спама для всех текстовых сообщений
        async def global_spam_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Глобальный фильтр спама для всех сообщений"""
            if await spam_filter(update, context):
                # Если это спам, не обрабатываем дальше
                return
        
        # Регистрируем фильтр спама ПЕРЕД всеми обработчиками (группа 0 - самый высокий приоритет)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            global_spam_filter
        ), group=0)
        logger.info("Глобальный фильтр спама зарегистрирован")
        
        
        
        # Регистрируем ConversationHandler для создания задач
        from conversations import (
            TITLE, DESCRIPTION, ASSIGNEE, DEADLINE, PHOTO,
            start_create_task, receive_title, receive_description, receive_assignee, receive_deadline, receive_photo,
            skip_description, skip_deadline, skip_photo, cancel_create_task,
            EDIT_TITLE, EDIT_DESCRIPTION, EDIT_DEADLINE, EDIT_ASSIGNEE,
            start_edit_task, receive_edit_title, receive_edit_description, receive_edit_deadline, receive_edit_assignee,
            skip_edit_title, skip_edit_description, skip_edit_deadline, cancel_edit_task,
            COMPLETE_RESULT, COMPLETE_PHOTO,
            start_complete_task, receive_complete_result, receive_complete_photo,
            skip_complete_result, skip_complete_photo, complete_fast, cancel_complete_task,
            EMPLOYEE_USERNAME, EMPLOYEE_INITIALS, EMPLOYEE_INITIALS_INPUT,
            start_add_employee, receive_employee_username, receive_employee_initials,
            receive_employee_initials_input, cancel_add_employee
        )
        
        create_task_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(start_create_task, pattern="^menu_create_task$")
            ],
            states={
                TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
                DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description),
                    CallbackQueryHandler(skip_description, pattern="^skip_description$")
                ],
                ASSIGNEE: [
                    CallbackQueryHandler(
                        receive_assignee,
                        pattern="^assignee_"
                    )
                ],
                DEADLINE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_deadline),
                    CallbackQueryHandler(skip_deadline, pattern="^skip_deadline$")
                ]
            },
            fallbacks=[
                CallbackQueryHandler(cancel_create_task, pattern="^cancel_create_task$"),
                CommandHandler("cancel", cancel_create_task)
            ],
            name="create_task_conversation"
        )
        
        edit_task_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(start_edit_task, pattern="^task_edit_")
            ],
            states={
                EDIT_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_title),
                    CallbackQueryHandler(skip_edit_title, pattern="^skip_edit_title$")
                ],
                EDIT_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_description),
                    CallbackQueryHandler(skip_edit_description, pattern="^skip_edit_description$")
                ],
                EDIT_DEADLINE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_deadline),
                    CallbackQueryHandler(skip_edit_deadline, pattern="^skip_edit_deadline$")
                ],
                EDIT_ASSIGNEE: [
                    CallbackQueryHandler(
                        receive_edit_assignee,
                        pattern="^assignee_"
                    )
                ]
            },
            fallbacks=[
                CallbackQueryHandler(cancel_edit_task, pattern="^cancel_edit_task$"),
                CommandHandler("cancel", cancel_edit_task)
            ],
            name="edit_task_conversation"
        )
        
        # ConversationHandlers должны быть зарегистрированы ПЕРЕД обычными CallbackQueryHandler
        # чтобы они могли перехватить свои callback_data
        # Используем группу 2 для ConversationHandlers, чтобы они обрабатывались ПЕРЕД button_callback
        application.add_handler(create_task_conv, group=2)
        logger.info("ConversationHandler для создания задач зарегистрирован (группа 2)")
        
        application.add_handler(edit_task_conv, group=2)
        logger.info("ConversationHandler для редактирования задач зарегистрирован (группа 2)")
        
        # ConversationHandler для добавления сотрудника
        from conversations import (
            TEAM_USERNAME, TEAM_INITIALS, TEAM_CUSTOM_INITIALS,
            start_team_add, receive_team_username, receive_team_initials, receive_team_custom_initials
        )
        
        add_employee_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(start_team_add, pattern="^team_add$")
            ],
            states={
                TEAM_USERNAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_team_username)
                ],
                TEAM_INITIALS: [
                    CallbackQueryHandler(receive_team_initials, pattern="^team_init_")
                ],
                TEAM_CUSTOM_INITIALS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_team_custom_initials)
                ]
            },
            fallbacks=[
                CallbackQueryHandler(lambda u, c: -1, pattern="^team_init_cancel$"),
                CommandHandler("cancel", lambda u, c: -1)
            ],
            name="add_employee_conversation"
        )
        
        # Старый ConversationHandler для menu_add_employee (оставляем для совместимости)
        old_add_employee_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(start_add_employee, pattern="^menu_add_employee$")
            ],
            states={
                EMPLOYEE_USERNAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_employee_username)
                ],
                EMPLOYEE_INITIALS: [
                    CallbackQueryHandler(receive_employee_initials, pattern="^initials_"),
                    CallbackQueryHandler(cancel_add_employee, pattern="^cancel_add_employee$")
                ],
                EMPLOYEE_INITIALS_INPUT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_employee_initials_input)
                ]
            },
            fallbacks=[
                CallbackQueryHandler(cancel_add_employee, pattern="^cancel_add_employee$"),
                CommandHandler("cancel", cancel_add_employee)
            ],
            name="add_employee_conversation"
        )
        
        application.add_handler(add_employee_conv, group=2)
        application.add_handler(old_add_employee_conv, group=2)
        logger.info("ConversationHandler для добавления сотрудника зарегистрирован (группа 2)")
        
        complete_task_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(start_complete_task, pattern="^task_complete_[0-9]+$"),
                CallbackQueryHandler(complete_fast, pattern="^task_complete_fast_[0-9]+$")
            ],
            states={
                COMPLETE_RESULT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_complete_result),
                    CallbackQueryHandler(skip_complete_result, pattern="^skip_complete_result$"),
                    CallbackQueryHandler(complete_fast, pattern="^complete_fast$")
                ],
                COMPLETE_PHOTO: [
                    MessageHandler(filters.PHOTO, receive_complete_photo),
                    CallbackQueryHandler(skip_complete_photo, pattern="^skip_complete_photo$")
                ]
            },
            fallbacks=[
                CallbackQueryHandler(cancel_complete_task, pattern="^cancel_complete_task$"),
                CommandHandler("cancel", cancel_complete_task)
            ],
            name="complete_task_conversation"
        )
        
        application.add_handler(complete_task_conv, group=2)
        logger.info("ConversationHandler для завершения задач зарегистрирован (группа 2)")
        
        # Убрали ConversationHandler для работы с задачей - теперь используем простые кнопки
        # Обработчики handle_work_task_take и handle_work_task_done зарегистрированы через button_callback
        
        # Регистрируем обработчик кнопок ПОСЛЕ всех ConversationHandlers (группа 3)
        # чтобы ConversationHandlers могли перехватить свои callback_data
        application.add_handler(CallbackQueryHandler(button_callback), group=3)
        logger.info("Обработчик кнопок зарегистрирован (группа 3)")
        
        # Настраиваем расписание
        setup_scheduler(application)
        logger.info("Расписание настроено")
        
        # Добавляем обработчик ошибок ДО запуска
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Обработчик ошибок"""
            error = context.error
            if isinstance(error, Exception):
                if "Conflict" in str(type(error).__name__) or "409" in str(error):
                    logger.warning(f"Conflict error (возможно запущено несколько экземпляров): {error}")
                    # Не падаем, просто логируем
                else:
                    logger.error(f"Необработанная ошибка: {error}", exc_info=error)
                    admin_id = context.bot_data.get('admin_id')
                    if admin_id:
                        try:
                            msg = f"❌ Ошибка: {type(error).__name__}: {str(error)[:200]}"
                            await context.bot.send_message(chat_id=admin_id, text=msg)
                        except Exception:
                            pass
        
        application.add_error_handler(error_handler)
        logger.info("Обработчик ошибок зарегистрирован")
        
        # Запускаем бота
        logger.info("Бот запущен и готов к работе!")
        logger.info("Ожидание команд...")
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА при запуске бота: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()

