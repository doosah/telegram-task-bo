"""
ГЛАВНЫЙ ФАЙЛ БОТА
Этот файл - это "мозг" бота. Он управляет всеми командами и сообщениями.
"""

import os
import logging
from datetime import datetime, time
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
from scheduler import Scheduler

# Настройка логирования (записи о работе бота)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем данные из переменных окружения (секретные данные)
BOT_TOKEN = os.getenv('BOT_TOKEN', '8448041977:AAGa4-EZ9dTfn-GgYArZU83FteWfisBOEUo')
CHAT_ID = os.getenv('CHAT_ID', '-1003107822060')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'Doosahyasno')

# Инициализация базы данных и задач
db = Database()
tasks_manager = Tasks()
scheduler_manager = Scheduler()

# Часовой пояс (Москва)
MOSCOW_TZ = pytz.timezone('Europe/Moscow')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - проверка работы бота"""
    user = update.effective_user
    
    # Проверяем, что команду запускает админ
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text(
            "❌ У вас нет прав для использования этой команды."
        )
        return
    
    await update.message.reply_text(
        f"✅ Бот работает!\n\n"
        f"👤 Пользователь: @{user.username}\n"
        f"🆔 ID: {user.id}\n"
        f"📅 Время: {datetime.now(MOSCOW_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Доступные команды:\n"
        f"/start - проверка работы\n"
        f"/add_urgent ТЕКСТ - добавить срочную задачу\n"
        f"/force_morning - отправить задачи сейчас"
    )


async def add_urgent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /add_urgent - добавить внеплановую задачу"""
    user = update.effective_user
    
    # Проверяем, что команду запускает админ
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text(
            "❌ У вас нет прав для использования этой команды."
        )
        return
    
    # Получаем текст задачи
    if not context.args:
        await update.message.reply_text(
            "❌ Использование: /add_urgent ТЕКСТ ЗАДАЧИ\n\n"
            "Пример: /add_urgent Проверить отчет"
        )
        return
    
    task_text = " ".join(context.args)
    urgent_task = f"🔥 {task_text}"
    
    # Отправляем задачу в группу
    keyboard = create_task_keyboard(urgent_task, "urgent")
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=f"🔥 **ВНЕПЛАНОВАЯ ЗАДАЧА**\n\n{urgent_task}",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    await update.message.reply_text(f"✅ Задача добавлена в группу!")


async def force_morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /force_morning - отправить задачи прямо сейчас"""
    user = update.effective_user
    
    # Проверяем, что команду запускает админ
    if user.username != ADMIN_USERNAME:
        await update.message.reply_text(
            "❌ У вас нет прав для использования этой команды."
        )
        return
    
    # Создаем объект приложения для функции
    class AppWrapper:
        def __init__(self, bot):
            self.bot = bot
    
    app_wrapper = AppWrapper(context.bot)
    await send_morning_tasks(app_wrapper)
    await update.message.reply_text("✅ Задачи отправлены в группу!")


def create_task_keyboard(task_text: str, task_id: str) -> InlineKeyboardMarkup:
    """Создает кнопки для задачи (АГ и КА)"""
    # Получаем текущий статус из базы данных
    status_ag = db.get_task_status(f"{task_id}_AG")
    status_ka = db.get_task_status(f"{task_id}_KA")
    
    # Создаем кнопки
    buttons = [
        [
            InlineKeyboardButton(
                f"АГ {status_ag}",
                callback_data=f"task_{task_id}_AG"
            ),
            InlineKeyboardButton(
                f"КА {status_ka}",
                callback_data=f"task_{task_id}_KA"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(buttons)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    # Парсим данные из кнопки
    data = query.data
    if not data.startswith("task_"):
        return
    
    parts = data.split("_")
    if len(parts) != 3:
        return
    
    task_id = parts[1]
    user_initials = parts[2]  # AG или KA
    
    # Получаем пользователя
    user = query.from_user
    user_id = user.id
    username = user.username
    
    # Определяем, какой пользователь нажал
    user_mapping = {
        "AG": {"username": "alex301182", "initials": "АГ"},
        "KA": {"username": "Korudirp", "initials": "КА"}
    }
    
    if user_initials not in user_mapping:
        await query.answer("❌ Неизвестный пользователь", show_alert=True)
        return
    
    expected_username = user_mapping[user_initials]["username"]
    
    # Проверяем, что правильный пользователь нажал кнопку
    if username != expected_username:
        await query.answer(
            f"❌ Эта кнопка для @{expected_username}",
            show_alert=True
        )
        return
    
    # Сохраняем ID пользователя в базу данных (для отправки напоминаний)
    db.save_user_id(username, user_id, user_initials)
    
    # Меняем статус: ⚪ → ⏳ → ✅ → ⚪
    status_key = f"{task_id}_{user_initials}"
    current_status = db.get_task_status(status_key)
    
    status_cycle = {"⚪": "⏳", "⏳": "✅", "✅": "⚪"}
    new_status = status_cycle.get(current_status, "⚪")
    
    # Сохраняем в базу данных
    db.set_task_status(status_key, new_status)
    
    # Обновляем сообщение
    keyboard = create_task_keyboard("", task_id)
    
    await query.edit_message_reply_markup(reply_markup=keyboard)
    
    # Отправляем подтверждение
    await query.answer(f"✅ Статус изменен: {new_status}", show_alert=False)


async def send_morning_tasks(app: Application):
    """Отправка задач на день в 08:00"""
    # Проверяем, что сегодня рабочий день (пн-пт)
    today = datetime.now(MOSCOW_TZ).weekday()  # 0=понедельник, 4=пятница
    
    if today > 4:  # Суббота или воскресенье
        return
    
    # Получаем задачи на сегодня
    day_tasks = tasks_manager.get_tasks_for_day(today)
    
    if not day_tasks:
        return
    
    # Формируем сообщение
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
    day_name = day_names[today]
    date_str = datetime.now(MOSCOW_TZ).strftime("%d.%m.%Y")
    
    message = f"📋 **ЗАДАЧИ НА {day_name.upper()}** ({date_str})\n\n"
    
    # Отправляем каждую задачу отдельным сообщением с кнопками
    for i, task in enumerate(day_tasks, 1):
        task_id = f"{today}_{i}"
        keyboard = create_task_keyboard(task, task_id)
        
        await app.bot.send_message(
            chat_id=CHAT_ID,
            text=f"{i}. {task}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )


async def send_reminders(app: Application):
    """Отправка напоминаний в личные сообщения в 13:00"""
    today = datetime.now(MOSCOW_TZ).weekday()
    
    if today > 4:
        return
    
    # Получаем задачи на сегодня
    day_tasks = tasks_manager.get_tasks_for_day(today)
    
    if not day_tasks:
        return
    
    # Получаем невыполненные задачи для каждого пользователя
    user_mapping = {
        "AG": {"username": "alex301182", "initials": "АГ"},
        "KA": {"username": "Korudirp", "initials": "КА"}
    }
    
    # Собираем невыполненные задачи для каждого пользователя
    for initials, user_info in user_mapping.items():
        incomplete_tasks = []
        
        for i, task in enumerate(day_tasks, 1):
            task_id = f"{today}_{i}"
            status_key = f"{task_id}_{initials}"
            status = db.get_task_status(status_key)
            
            if status != "✅":
                incomplete_tasks.append(task)
        
        if not incomplete_tasks:
            continue
        
        # Формируем сообщение для пользователя
        message = f"⏰ **НАПОМИНАНИЕ**\n\n"
        message += f"У вас есть невыполненные задачи:\n\n"
        
        for i, task in enumerate(incomplete_tasks, 1):
            message += f"{i}. {task}\n"
        
        # Получаем ID пользователя из базы данных
        user_id = db.get_user_id_by_username(user_info["username"])
        
        if user_id:
            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания пользователю {user_info['username']}: {e}")
        else:
            # Если ID еще не сохранен, пытаемся отправить через username
            # (это не всегда работает, но попробуем)
            logger.warning(f"ID пользователя {user_info['username']} не найден в базе данных")


async def send_evening_summary(app: Application):
    """Отправка итогов дня в 16:50"""
    today = datetime.now(MOSCOW_TZ).weekday()
    
    if today > 4:
        return
    
    # Получаем задачи на сегодня
    day_tasks = tasks_manager.get_tasks_for_day(today)
    
    if not day_tasks:
        return
    
    # Собираем невыполненные задачи
    incomplete = []
    for i, task in enumerate(day_tasks, 1):
        task_id = f"{today}_{i}"
        status_ag = db.get_task_status(f"{task_id}_AG")
        status_ka = db.get_task_status(f"{task_id}_KA")
        
        if status_ag != "✅" or status_ka != "✅":
            users_needed = []
            if status_ag != "✅":
                users_needed.append("@alex301182")
            if status_ka != "✅":
                users_needed.append("@Korudirp")
            
            incomplete.append({
                "task": task,
                "users": " ".join(users_needed)
            })
    
    if not incomplete:
        message = "✅ **ИТОГИ ДНЯ**\n\nВсе задачи выполнены! 🎉"
    else:
        message = "📊 **ИТОГИ ДНЯ**\n\nНевыполненные задачи:\n\n"
        for item in incomplete:
            message += f"• {item['task']} {item['users']}\n"
    
    # Отправляем в группу
    await app.bot.send_message(
        chat_id=CHAT_ID,
        text=message,
        parse_mode='Markdown'
    )


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
    logger.info("Запуск бота...")
    
    # Создаем приложение бота
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("add_urgent", add_urgent_command))
    application.add_handler(CommandHandler("force_morning", force_morning_command))
    
    # Регистрируем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Настраиваем расписание
    setup_scheduler(application)
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

