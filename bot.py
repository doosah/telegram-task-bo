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
    ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Импортируем наши модули
from database import Database
from tasks import Tasks

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
    """Команда /start - проверка работы бота"""
    try:
        user = update.effective_user
        logger.info(f"Команда /start от пользователя @{user.username} (ID: {user.id})")
        
        # Все могут использовать /start для проверки
        response = (
            f"✅ Бот работает!\n\n"
            f"👤 Пользователь: @{user.username if user.username else 'без username'}\n"
            f"🆔 ID: {user.id}\n"
            f"📅 Время: {datetime.now(MOSCOW_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )
        
        # Если это админ - показываем команды
        if user.username == ADMIN_USERNAME:
            response += (
                f"Доступные команды:\n"
                f"/start - проверка работы\n"
                f"/add_urgent ТЕКСТ - добавить срочную задачу\n"
                f"/force_morning - отправить задачи сейчас"
            )
        else:
            response += "Для использования команд нужны права администратора."
        
        await update.message.reply_text(response)
        logger.info(f"Ответ отправлен пользователю @{user.username}")
    except Exception as e:
        logger.error(f"Ошибка в start_command: {e}", exc_info=True)
        try:
            await update.message.reply_text(f"❌ Ошибка: {e}")
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
    
    try:
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
    
    # Создаем одну кнопку с названием задачи и статусом
    # Валидация: Telegram ограничивает текст кнопки до 64 символов
    button_text = f"{task_text} {task_status}"
    if len(button_text) > 64:
        # Укорачиваем текст задачи
        max_text_len = 64 - len(f" {task_status}")
        task_text_short = task_text[:max_text_len-3] + "..."
        button_text = f"{task_text_short} {task_status}"
        logger.warning(f"Текст кнопки укорочен до 64 символов")
    
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
        
        if not data or not data.startswith("task_"):
            logger.warning(f"Неверный формат данных кнопки: {data}")
            await query.answer()
            return
        
        # Парсим task_id: формат "task_0_1" -> task_id = "0_1"
        parts = data.split("_")
        if len(parts) < 3:  # минимум: ["task", "0", "1"]
            logger.warning(f"Неверный формат task_id: {data}, parts={parts}")
            await query.answer()
            return
        
        # task_id = все части после "task" (например, "0_1" из "task_0_1")
        task_id = "_".join(parts[1:])
        logger.info(f"Обработка задачи: {task_id}")
        
        # Получаем пользователя
        try:
            user = query.from_user
            if not user:
                logger.error("query.from_user is None")
                await query.answer("❌ Ошибка: пользователь не найден", show_alert=True)
                return
            
            user_id = user.id
            username = user.username
            logger.info(f"Пользователь: @{username} (ID: {user_id})")
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}", exc_info=True)
            await query.answer("❌ Ошибка получения данных пользователя", show_alert=True)
            return
        
        # Отвечаем на callback сразу, чтобы Telegram знал, что запрос обработан
        try:
            await query.answer()
        except Exception as e:
            logger.warning(f"Не удалось отправить answer: {e}")
            # Продолжаем работу, даже если answer не отправился
        
        # Определяем, какой пользователь нажал (АГ, КА или СА)
        user_mapping = {
            "alex301182": {"initials": "AG", "name": "АГ"},
            "Korudirp": {"initials": "KA", "name": "КА"},
            "sanya_hui_sosi1488": {"initials": "SA", "name": "СА"}
        }
        
        # Определяем, кто нажал
        user_initials = None
        user_name = None
        
        if username in user_mapping:
            user_initials = user_mapping[username]["initials"]
            user_name = user_mapping[username]["name"]
            logger.info(f"Пользователь найден: {user_name} ({user_initials})")
        else:
            # Проверяем по ID из базы
            logger.info(f"Username не найден, проверяем по ID...")
            for uname, info in user_mapping.items():
                saved_id = db.get_user_id_by_username(uname)
                if saved_id == user_id:
                    user_initials = info["initials"]
                    user_name = info["name"]
                    username = uname
                    logger.info(f"Пользователь найден по ID: {user_name} ({user_initials})")
                    break
        
        if not user_initials:
            logger.warning(f"Пользователь @{username} (ID: {user_id}) не в списке участников")
            try:
                await query.answer("❌ Вы не в списке участников", show_alert=True)
            except:
                pass
            return
        
        # Сохраняем ID пользователя в базу данных
        try:
            logger.info(f"Сохранение ID пользователя в БД: username={username}, user_id={user_id}, initials={user_initials}")
            db.save_user_id(username, user_id, user_initials)
            logger.info(f"✅ ID пользователя сохранен в БД")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения ID пользователя: {type(e).__name__}: {e}", exc_info=True)
            # Продолжаем работу, даже если не удалось сохранить
        
        # Получаем текущие статусы для АГ, КА и СА
        logger.info(f"Получение статусов из БД для задачи {task_id}...")
        try:
            status_key_ag = f"{task_id}_AG"
            status_key_ka = f"{task_id}_KA"
            status_key_sa = f"{task_id}_SA"
            logger.info(f"Ключи статусов: AG={status_key_ag}, KA={status_key_ka}, SA={status_key_sa}")
            
            status_ag = db.get_task_status(status_key_ag) or "⚪"
            logger.info(f"Статус АГ получен: {status_ag}")
            
            status_ka = db.get_task_status(status_key_ka) or "⚪"
            logger.info(f"Статус КА получен: {status_ka}")
            
            status_sa = db.get_task_status(status_key_sa) or "⚪"
            logger.info(f"Статус СА получен: {status_sa}")
            
            logger.info(f"✅ Текущие статусы: АГ={status_ag}, КА={status_ka}, СА={status_sa}")
        except Exception as e:
            logger.error(f"❌ Ошибка получения статусов из БД: {type(e).__name__}: {e}", exc_info=True)
            status_ag = "⚪"
            status_ka = "⚪"
            status_sa = "⚪"
            logger.warning(f"Используем дефолтные статусы: АГ={status_ag}, КА={status_ka}, СА={status_sa}")
        
        # Меняем статус для текущего пользователя: ⚪ → ⏳ → ✅
        status_key = f"{task_id}_{user_initials}"
        logger.info(f"Получение текущего статуса для ключа: {status_key}")
        try:
            current_status = db.get_task_status(status_key) or "⚪"
            logger.info(f"Текущий статус получен: {current_status}")
        except Exception as e:
            logger.error(f"❌ Ошибка получения текущего статуса: {type(e).__name__}: {e}", exc_info=True)
            current_status = "⚪"
            logger.warning(f"Используем дефолтный статус: {current_status}")
        
        # Цикл: ⚪ → ⏳ → ✅ → ⚪
        status_cycle = {"⚪": "⏳", "⏳": "✅", "✅": "⚪"}
        new_status = status_cycle.get(current_status, "⚪")
        logger.info(f"🔄 Статус {user_initials}: {current_status} → {new_status}")
        
        # Сохраняем новый статус
        logger.info(f"Сохранение нового статуса: {status_key} = {new_status}")
        try:
            db.set_task_status(status_key, new_status)
            logger.info(f"✅ Статус сохранен в БД: {status_key} = {new_status}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения статуса: {type(e).__name__}: {e}", exc_info=True)
            # Продолжаем работу, даже если не удалось сохранить
        
        # Обновляем статусы после изменения
        logger.info(f"Обновление локальных статусов для {user_initials}...")
        if user_initials == "AG":
            status_ag = new_status
            logger.info(f"Статус АГ обновлен: {status_ag}")
        elif user_initials == "KA":
            status_ka = new_status
            logger.info(f"Статус КА обновлен: {status_ka}")
        elif user_initials == "SA":
            status_sa = new_status
            logger.info(f"Статус СА обновлен: {status_sa}")
        else:
            logger.warning(f"Неизвестные инициалы: {user_initials}")
        
        # Определяем общий статус задачи для отображения (✅ только когда все 3 выполнили)
        logger.info(f"Вычисление общего статуса: АГ={status_ag}, КА={status_ka}, СА={status_sa}")
        if status_ag == "✅" and status_ka == "✅" and status_sa == "✅":
            task_status = "✅"  # Все трое выполнили
            logger.info("✅ Все участники выполнили задачу")
        elif status_ag != "⚪" or status_ka != "⚪" or status_sa != "⚪":
            task_status = "⏳"  # Кто-то взял в работу
            logger.info("⏳ Кто-то взял задачу в работу")
        else:
            task_status = "⚪"  # Никто не взял
            logger.info("⚪ Никто не взял задачу")
        
        logger.info(f"✅ Общий статус задачи: {task_status}")
        
        # Обновляем сообщение - обновляем кнопку для этой задачи
        if not query.message:
            logger.error("query.message is None")
            await query.answer("❌ Ошибка: сообщение не найдено", show_alert=True)
            return
        
        current_markup = query.message.reply_markup
        
        if not current_markup:
            logger.warning("Клавиатура не найдена в сообщении (current_markup is None)")
            await query.answer("✅ Статус обновлен", show_alert=False)
            return
        
        if not current_markup.inline_keyboard:
            logger.warning("Клавиатура пуста (inline_keyboard is None or empty)")
            await query.answer("✅ Статус обновлен", show_alert=False)
            return
        
        # Извлекаем номер задачи из task_id (формат: "0_1" -> номер "1")
        task_num = task_id.split("_")[-1] if "_" in task_id else task_id
        
        # Ищем текст задачи из кнопки (это надежнее)
        task_text = ""
        original_button_text = ""
        
        for row in current_markup.inline_keyboard:
            for button in row:
                if button.callback_data == f"task_{task_id}":
                    original_button_text = button.text
                    # Извлекаем текст задачи из кнопки
                    # Формат: "1. Название задачи ⚪"
                    if "." in original_button_text:
                        # Разделяем на номер и остальное
                        parts_btn = original_button_text.split(".", 1)
                        task_text = parts_btn[1].strip() if len(parts_btn) > 1 else original_button_text
                        # Убираем статусы
                        task_text = task_text.replace("⚪", "").replace("⏳", "").replace("✅", "").strip()
                    else:
                        task_text = original_button_text.replace("⚪", "").replace("⏳", "").replace("✅", "").strip()
                    logger.info(f"Текст задачи из кнопки: '{task_text}'")
                    break
            if task_text:
                break
        
        # Если не нашли в кнопке - ищем в тексте сообщения
        if not task_text:
            message_text = query.message.text or ""
            for line in message_text.split("\n"):
                line_stripped = line.strip()
                if line_stripped.startswith(f"{task_num}."):
                    task_text = line_stripped
                    if "." in task_text:
                        task_text = task_text.split(".", 1)[1].strip()
                    task_text = task_text.replace("⚪", "").replace("⏳", "").replace("✅", "").replace("**", "").strip()
                    logger.info(f"Текст задачи из сообщения: '{task_text}'")
                    break
        
        if not task_text:
            logger.error(f"Не удалось извлечь текст задачи для {task_id}")
            # Используем дефолтный текст
            task_text = f"Задача {task_num}" if task_num else "Задача"
            logger.warning(f"Используем дефолтный текст задачи: {task_text}")
        
        # Обновляем кнопки в текущей клавиатуре
        new_keyboard = []
        for row in current_markup.inline_keyboard:
            new_row = []
            for button in row:
                # Если это кнопка для нашей задачи - обновляем статус
                if button.callback_data == f"task_{task_id}":
                    # Сохраняем номер задачи в новом тексте
                    new_text = f"{task_num}. {task_text} {task_status}"
                    logger.info(f"Обновляем кнопку: '{original_button_text}' → '{new_text}'")
                    new_row.append(InlineKeyboardButton(new_text, callback_data=button.callback_data))
                else:
                    new_row.append(button)
            new_keyboard.append(new_row)
        
        updated_keyboard = InlineKeyboardMarkup(new_keyboard)
        try:
            await query.edit_message_reply_markup(reply_markup=updated_keyboard)
            logger.info(f"✅ Кнопка обновлена успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления кнопки: {type(e).__name__}: {e}", exc_info=True)
            # Не падаем, просто логируем ошибку
            # Возможно, сообщение было изменено другим пользователем
            pass
        
        # Отправляем подтверждение (query.answer уже был вызван в начале, но это второй вызов для уведомления)
        # Telegram позволяет вызывать answer несколько раз, но показывается только последний
        try:
            if task_status == "✅":
                await query.answer(f"✅ Задача выполнена! (все участники)", show_alert=False)
            else:
                await query.answer(f"⏳ {user_name} взял задачу в работу", show_alert=False)
        except Exception as e:
            logger.warning(f"Не удалось отправить подтверждение: {e}")
            # Это не критично, просто логируем
            # query.answer уже был вызван в начале функции
            
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
            
            # Валидация текста кнопки (Telegram ограничивает до 64 символов)
            button_text = f"{i}. {task} ⚪"
            if len(button_text) > 64:
                # Укорачиваем текст задачи
                max_text_len = 64 - len(f"{i}. ⚪")
                task_short = task[:max_text_len-3] + "..."
                button_text = f"{i}. {task_short} ⚪"
                logger.warning(f"Текст кнопки для задачи {i} укорочен до 64 символов")
            
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
    
    scheduler.start()
    logger.info("Расписание настроено: 08:00, 13:00, 16:50 (пн-пт)")


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
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        logger.info("Обработчик /start зарегистрирован")
        
        application.add_handler(CommandHandler("add_urgent", add_urgent_command))
        logger.info("Обработчик /add_urgent зарегистрирован")
        
        application.add_handler(CommandHandler("force_morning", force_morning_command))
        logger.info("Обработчик /force_morning зарегистрирован")
        
        # Регистрируем обработчик кнопок
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

