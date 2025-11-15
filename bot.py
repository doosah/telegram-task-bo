"""
ГЛАВНЫЙ ФАЙЛ БОТА
Этот файл - это "мозг" бота. Он управляет всеми командами и сообщениями.
"""

import os
import logging
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
from menu import (
    get_main_menu, get_testing_menu, get_tasks_menu, get_task_actions_menu,
    get_confirm_menu, get_assignee_menu, get_presence_menu,
    get_delay_time_menu, get_delay_minutes_menu
)
from handlers import (
    handle_menu_callback, handle_presence_callback, handle_delay_callback,
    handle_new_task_callback, handle_old_task_callback, handle_confirm_callback,
    handle_assignee_callback
)

# Настройка логирования (записи о работе бота)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - главное меню бота"""
    try:
        user = update.effective_user
        logger.info(f"Команда /start от пользователя @{user.username} (ID: {user.id})")
        
        # Сохраняем пользователя в БД
        if user.username:
            user_mapping = {
                "alex301182": {"initials": "AG", "name": "АГ"},
                "Korudirp": {"initials": "KA", "name": "КА"},
                "sanya_hui_sosi1488": {"initials": "SA", "name": "СА"}
            }
            if user.username in user_mapping:
                db.save_user_id(user.username, user.id, user_mapping[user.username]["initials"])
        
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
    
    # ОПТИМИЗАЦИЯ ДЛЯ МОБИЛЬНЫХ: ограничиваем длину текста кнопки до 30 символов
    # Это обеспечит полную видимость на мобильных устройствах
    max_mobile_length = 30
    if len(task_text) > max_mobile_length:
        # Укорачиваем текст задачи для мобильных
        task_text_short = task_text[:max_mobile_length-3] + "..."
        button_text = f"{task_text_short} {task_status}"
    else:
        button_text = f"{task_text} {task_status}"
    
    # Дополнительная проверка на случай, если статус делает текст слишком длинным
    if len(button_text) > 35:  # Оставляем запас
        max_text_len = 35 - len(f" {task_status}")
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


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    try:
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
        
        # Обработка меню (кроме menu_create_task - его обрабатывает ConversationHandler)
        if data.startswith("menu_") and data != "menu_create_task":
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
            
            # ОПТИМИЗАЦИЯ ДЛЯ МОБИЛЬНЫХ: ограничиваем длину текста кнопки до 30 символов
            # Это обеспечит полную видимость на мобильных устройствах
            max_mobile_length = 30
            if len(task) > max_mobile_length:
                # Укорачиваем текст задачи для мобильных
                task_short = task[:max_mobile_length-3] + "..."
                button_text = f"{i}. {task_short} ⚪"
            else:
                button_text = f"{i}. {task} ⚪"
            
            # Дополнительная проверка на случай, если номер задачи делает текст слишком длинным
            if len(button_text) > 35:  # Оставляем запас
                max_text_len = 35 - len(f"{i}. ⚪")
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
        "AG": {"username": "alex301182", "initials": "АГ"},
        "KA": {"username": "Korudirp", "initials": "КА"},
        "SA": {"username": "sanya_hui_sosi1488", "initials": "СА"}
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
                    users_needed.append("@alex301182")
                if status_ka != "✅":
                    users_needed.append("@Korudirp")
                if status_sa != "✅":
                    users_needed.append("@sanya_hui_sosi1488")
                
                incomplete.append({
                    "task": task,
                    "users": " ".join(users_needed)
                })
    except Exception as e:
        logger.error(f"❌ Ошибка обработки задач для итогов дня: {e}", exc_info=True)
        incomplete = []
    
    if not incomplete:
        message = "✅ **ИТОГИ ДНЯ**\n\nВсе задачи выполнены! 🎉"
    else:
        message = "📊 **ИТОГИ ДНЯ**\n\nНевыполненные задачи:\n\n"
        # Валидация: Telegram ограничивает длину сообщения до 4096 символов
        max_message_length = 4000  # Оставляем запас
        current_length = len(message)
        
        for idx, item in enumerate(incomplete):
            task_line = f"• {item['task']} {item['users']}\n"
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


async def send_presence_buttons(app: Application):
    """Отправка кнопок присутствия в 07:50"""
    try:
        today = datetime.now(MOSCOW_TZ).weekday()
        
        if today > 4:  # Выходной
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


def setup_scheduler(app: Application):
    """Настройка расписания отправки сообщений"""
    scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)
    
    # 08:00 - задачи на день
    scheduler.add_job(
        send_morning_tasks,
        trigger=CronTrigger(hour=8, minute=0, day_of_week='mon-fri'),
        args=[app]
    )
    
    # 13:00 - напоминания
    scheduler.add_job(
        send_reminders,
        trigger=CronTrigger(hour=13, minute=0, day_of_week='mon-fri'),
        args=[app]
    )
    
    # 16:50 - итоги дня
    scheduler.add_job(
        send_evening_summary,
        trigger=CronTrigger(hour=16, minute=50, day_of_week='mon-fri'),
        args=[app]
    )
    
    # 07:50 - кнопки присутствия
    scheduler.add_job(
        send_presence_buttons,
        trigger=CronTrigger(hour=7, minute=50, day_of_week='mon-fri'),
        args=[app]
    )
    
    scheduler.start()
    logger.info("Расписание настроено: 07:50 (присутствие), 08:00, 13:00, 16:50 (пн-пт)")


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
        
        # Сохраняем функции для тестирования
        application.bot_data['send_morning_tasks'] = send_morning_tasks
        application.bot_data['send_presence_buttons'] = send_presence_buttons
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
            skip_complete_result, skip_complete_photo, complete_fast, cancel_complete_task
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
                ],
                PHOTO: [
                    MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, receive_photo),
                    CallbackQueryHandler(skip_photo, pattern="^skip_photo$")
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
        application.add_handler(create_task_conv)
        logger.info("ConversationHandler для создания задач зарегистрирован")
        
        application.add_handler(edit_task_conv)
        logger.info("ConversationHandler для редактирования задач зарегистрирован")
        
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
        
        application.add_handler(complete_task_conv)
        logger.info("ConversationHandler для завершения задач зарегистрирован")
        
        # Регистрируем обработчик кнопок ПОСЛЕ всех ConversationHandlers
        # чтобы ConversationHandlers могли перехватить свои callback_data
        application.add_handler(CallbackQueryHandler(button_callback))
        logger.info("Обработчик кнопок зарегистрирован")
        
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

