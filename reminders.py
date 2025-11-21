"""
МОДУЛЬ ДЛЯ НАПОМИНАНИЙ О РУЧНЫХ ЗАДАЧАХ
"""

import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, ContextTypes
import pytz

logger = logging.getLogger(__name__)

MOSCOW_TZ = pytz.timezone('Europe/Moscow')


def parse_deadline(deadline_str: str) -> datetime:
    """
    Парсит строку дедлайна в datetime объект
    Поддерживает форматы:
    - ДД.ММ.ГГГГ ЧЧ:ММ
    - ДД.ММ.ГГГГ
    - сегодня до 15:00
    - сегодня до 3:00 PM
    """
    if not deadline_str:
        return None
    
    now = datetime.now(MOSCOW_TZ)
    today = now.date()
    
    deadline_str = deadline_str.strip()
    
    # Формат: "сегодня до 15:00" или "сегодня до 3:00 PM"
    if deadline_str.lower().startswith("сегодня"):
        try:
            time_part = deadline_str.split("до")[-1].strip()
            # Парсим время
            if "PM" in time_part.upper() or "AM" in time_part.upper():
                # 12-часовой формат
                time_str = time_part.replace("PM", "").replace("pm", "").replace("AM", "").replace("am", "").strip()
                hour = int(time_str.split(":")[0])
                minute = int(time_str.split(":")[1]) if ":" in time_str else 0
                if "PM" in time_part.upper() and hour != 12:
                    hour += 12
                elif "AM" in time_part.upper() and hour == 12:
                    hour = 0
            else:
                # 24-часовой формат
                if ":" in time_part:
                    hour = int(time_part.split(":")[0])
                    minute = int(time_part.split(":")[1])
                else:
                    hour = int(time_part)
                    minute = 0
            
            deadline = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return MOSCOW_TZ.localize(deadline)
        except Exception as e:
            logger.error(f"Ошибка парсинга 'сегодня до': {e}")
            return None
    
    # Формат: ДД.ММ.ГГГГ ЧЧ:ММ или ДД.ММ.ГГГГ
    try:
        if " " in deadline_str:
            deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
        else:
            deadline = datetime.strptime(deadline_str, "%d.%m.%Y")
            # Если только дата, ставим время 23:59
            deadline = deadline.replace(hour=23, minute=59)
        
        return MOSCOW_TZ.localize(deadline)
    except ValueError:
        logger.error(f"Не удалось распарсить дедлайн: {deadline_str}")
        return None


async def send_custom_task_reminders(app: Application):
    """Отправка напоминаний о ручных задачах"""
    try:
        db = app.bot_data.get('db')
        if not db:
            logger.error("База данных не найдена в bot_data")
            return
        
        # Получаем все активные задачи
        active_tasks = db.get_custom_tasks(status='active')
        if not active_tasks:
            return
        
        now = datetime.now(MOSCOW_TZ)
        chat_id = app.bot_data.get('CHAT_ID')
        if not chat_id:
            import os
            chat_id = os.getenv('CHAT_ID', '').strip()
        
        if not chat_id:
            logger.error("CHAT_ID не найден")
            return
        
        chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
        
        assignee_names = {
            "AG": "Lysenko Alexander",
            "KA": "Ruslan Cherenkov",
            "all": "Все"
        }
        
        for task in active_tasks:
            deadline_str = task.get('deadline', '')
            if not deadline_str:
                continue
            
            deadline = parse_deadline(deadline_str)
            if not deadline:
                continue
            
            # Пропускаем просроченные задачи
            if deadline < now:
                continue
            
            time_until_deadline = deadline - now
            days_until = time_until_deadline.days
            hours_until = time_until_deadline.total_seconds() / 3600
            
            # Определяем, нужно ли отправлять напоминание
            should_remind = False
            reminder_text = ""
            reminder_key = None  # Ключ для отслеживания отправленных напоминаний
            
            # Если задача на день (дедлайн сегодня)
            if days_until == 0:
                # Напоминания в день дедлайна: 9:00, 12:00, 14:00, 16:00
                current_hour = now.hour
                if current_hour in [9, 12, 14, 16] and now.minute < 5:
                    reminder_key = f"task_{task['task_id']}_hour_{current_hour}"
                    if not hasattr(app.bot_data, 'sent_reminders'):
                        app.bot_data['sent_reminders'] = set()
                    if reminder_key not in app.bot_data['sent_reminders']:
                        should_remind = True
                        app.bot_data['sent_reminders'].add(reminder_key)
                        reminder_text = (
                            f"⏰ **НАПОМИНАНИЕ О ЗАДАЧЕ**\n\n"
                            f"📝 Задача: {task['title']}\n"
                            f"⏰ Срок: {deadline_str}\n"
                            f"👤 Исполнитель: {assignee_names.get(task.get('assignee', 'all'), 'Все')}\n\n"
                            f"⚠️ Не забудьте выполнить задачу!"
                        )
                
                # Напоминания за определенное время до дедлайна
                if hours_until <= 4 and hours_until > 0:
                    # За 4 часа, 2 часа, 1 час, 30 минут
                    if 3.5 <= hours_until <= 4.5:
                        reminder_key = f"task_{task['task_id']}_4h"
                        # Проверяем, не отправляли ли уже это напоминание
                        if not hasattr(app.bot_data, 'sent_reminders'):
                            app.bot_data['sent_reminders'] = set()
                        if reminder_key not in app.bot_data['sent_reminders']:
                            should_remind = True
                            app.bot_data['sent_reminders'].add(reminder_key)
                            reminder_text = (
                                f"⏰ **НАПОМИНАНИЕ О ЗАДАЧЕ**\n\n"
                                f"📝 Задача: {task['title']}\n"
                                f"⏰ Срок: {deadline_str}\n"
                                f"⏳ До дедлайна осталось ~4 часа\n"
                                f"👤 Исполнитель: {assignee_names.get(task.get('assignee', 'all'), 'Все')}"
                            )
                    elif 1.5 <= hours_until <= 2.5:
                        reminder_key = f"task_{task['task_id']}_2h"
                        if not hasattr(app.bot_data, 'sent_reminders'):
                            app.bot_data['sent_reminders'] = set()
                        if reminder_key not in app.bot_data['sent_reminders']:
                            should_remind = True
                            app.bot_data['sent_reminders'].add(reminder_key)
                            reminder_text = (
                                f"⏰ **НАПОМИНАНИЕ О ЗАДАЧЕ**\n\n"
                                f"📝 Задача: {task['title']}\n"
                                f"⏰ Срок: {deadline_str}\n"
                                f"⏳ До дедлайна осталось ~2 часа\n"
                                f"👤 Исполнитель: {assignee_names.get(task.get('assignee', 'all'), 'Все')}"
                            )
                    elif 0.5 <= hours_until <= 1.5:
                        reminder_key = f"task_{task['task_id']}_1h"
                        if not hasattr(app.bot_data, 'sent_reminders'):
                            app.bot_data['sent_reminders'] = set()
                        if reminder_key not in app.bot_data['sent_reminders']:
                            should_remind = True
                            app.bot_data['sent_reminders'].add(reminder_key)
                            reminder_text = (
                                f"⏰ **НАПОМИНАНИЕ О ЗАДАЧЕ**\n\n"
                                f"📝 Задача: {task['title']}\n"
                                f"⏰ Срок: {deadline_str}\n"
                                f"⏳ До дедлайна осталось ~1 час\n"
                                f"👤 Исполнитель: {assignee_names.get(task.get('assignee', 'all'), 'Все')}"
                            )
                    elif 0.25 <= hours_until <= 0.5:
                        reminder_key = f"task_{task['task_id']}_30m"
                        if not hasattr(app.bot_data, 'sent_reminders'):
                            app.bot_data['sent_reminders'] = set()
                        if reminder_key not in app.bot_data['sent_reminders']:
                            should_remind = True
                            app.bot_data['sent_reminders'].add(reminder_key)
                            reminder_text = (
                                f"⏰ **НАПОМИНАНИЕ О ЗАДАЧЕ**\n\n"
                                f"📝 Задача: {task['title']}\n"
                                f"⏰ Срок: {deadline_str}\n"
                                f"⏳ До дедлайна осталось ~30 минут\n"
                                f"👤 Исполнитель: {assignee_names.get(task.get('assignee', 'all'), 'Все')}"
                            )
            else:
                # За несколько дней до дедлайна - напоминание раз в день
                # Отправляем в 9:00 каждый день
                if now.hour == 9 and now.minute < 5:
                    reminder_key = f"task_{task['task_id']}_day_{now.date()}"
                    if not hasattr(app.bot_data, 'sent_reminders'):
                        app.bot_data['sent_reminders'] = set()
                    if reminder_key not in app.bot_data['sent_reminders']:
                        should_remind = True
                        app.bot_data['sent_reminders'].add(reminder_key)
                        reminder_text = (
                            f"⏰ **НАПОМИНАНИЕ О ЗАДАЧЕ**\n\n"
                            f"📝 Задача: {task['title']}\n"
                            f"⏰ Срок: {deadline_str}\n"
                            f"📅 До дедлайна осталось {days_until} {'день' if days_until == 1 else 'дня' if days_until < 5 else 'дней'}\n"
                            f"👤 Исполнитель: {assignee_names.get(task.get('assignee', 'all'), 'Все')}"
                        )
            
            if should_remind and reminder_text:
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=reminder_text,
                        parse_mode='Markdown'
                    )
                    logger.info(f"✅ Напоминание о задаче #{task['task_id']} отправлено в чат {chat_id}")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки напоминания: {e}", exc_info=True)
    
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА в send_custom_task_reminders: {e}", exc_info=True)

