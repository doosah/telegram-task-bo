"""
НОВЫЕ ОБРАБОТЧИКИ ДЛЯ МЕНЮ И ФУНКЦИЙ
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Импортируем глобальные объекты из bot.py через параметры
# Это нужно, чтобы избежать циклических импортов

# Состояния для ConversationHandler
(TITLE, DESCRIPTION, DEADLINE, ASSIGNEE, REASON) = range(5)


async def handle_menu_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE, db):
    """Обработка нажатий на кнопки меню"""
    try:
        await query.answer()
        user = query.from_user
        username = user.username if user else None
        
        if data == "menu_main" or data == "menu_back":
            from menu import get_main_menu
            text = (
                "👋 **ГЛАВНОЕ МЕНЮ**\n\n"
                "Выберите действие:"
            )
            try:
                await query.edit_message_text(text, reply_markup=get_main_menu(), parse_mode='Markdown')
            except Exception as edit_error:
                # Если не удалось отредактировать (например, сообщение с фото), отправляем новое
                logger.warning(f"Не удалось отредактировать сообщение, отправляем новое: {edit_error}")
                await query.message.reply_text(text, reply_markup=get_main_menu(), parse_mode='Markdown')
        
        elif data == "menu_create_task":
            # ConversationHandler обработает это через entry_points
            # НЕ обрабатываем здесь, чтобы ConversationHandler мог перехватить
            # Возвращаемся без обработки - ConversationHandler сам обработает
            return
        
        elif data == "menu_view_tasks":
            from menu import get_tasks_menu, get_main_menu
            tasks = db.get_custom_tasks(status='active')
            if not tasks:
                text = "📋 **МОИ ЗАДАЧИ**\n\nУ вас пока нет активных задач."
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад в меню", callback_data="menu_main")
                ]])
            else:
                text = f"📋 **МОИ ЗАДАЧИ**\n\nНайдено задач: {len(tasks)}"
                keyboard = get_tasks_menu(tasks)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        elif data == "menu_complete_task":
            tasks = db.get_custom_tasks(status='active')
            if not tasks:
                text = "✅ **ЗАВЕРШЕНИЕ ЗАДАЧИ**\n\nУ вас нет активных задач для завершения."
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Назад в меню", callback_data="menu_main")
                ]])
            else:
                text = "✅ **ЗАВЕРШЕНИЕ ЗАДАЧИ**\n\nВыберите задачу:"
                keyboard = get_tasks_menu(tasks)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        elif data == "menu_settings":
            text = (
                "⚙️ **НАСТРОЙКИ**\n\n"
                "Здесь будут настройки бота"
            )
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад в меню", callback_data="menu_main")
            ]])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        elif data == "menu_testing":
            from menu import get_testing_menu
            text = (
                "🧪 **ТЕСТИРОВАНИЕ**\n\n"
                "Выберите действие для тестирования:"
            )
            await query.edit_message_text(text, reply_markup=get_testing_menu(), parse_mode='Markdown')
        
        elif data == "menu_help":
            text = (
                "❓ **ПОМОЩЬ**\n\n"
                "📝 **Создать задачу** - добавить новую задачу\n\n"
                "🧪 **Тестирование** - тестовые функции бота\n\n"
                "⏰ **Отметка присутствия**\n"
                "Каждый день в 07:50 в общем чате появляются кнопки для отметки присутствия."
            )
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад в меню", callback_data="menu_main")
            ]])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        elif data == "test_daily_tasks":
            # Тестовая отправка ежедневных задач - вызываем send_morning_tasks напрямую
            try:
                await query.answer("⏳ Отправка задач...")
                
                # Используем функцию из bot_data или импортируем напрямую
                if 'send_morning_tasks' in context.bot_data:
                    send_morning_tasks_func = context.bot_data['send_morning_tasks']
                else:
                    # Если нет в bot_data, импортируем напрямую
                    import sys
                    import importlib
                    if 'bot' in sys.modules:
                        bot_module = sys.modules['bot']
                        send_morning_tasks_func = bot_module.send_morning_tasks
                    else:
                        raise ImportError("Не удалось найти функцию send_morning_tasks")
                
                # Создаем обертку для app, как в force_morning_command
                class AppWrapper:
                    def __init__(self, bot):
                        self.bot = bot
                
                app_wrapper = AppWrapper(context.bot)
                
                # Вызываем функцию
                await send_morning_tasks_func(app_wrapper, force_weekend=True)
                
                text = "✅ **ЕЖЕДНЕВНЫЕ ЗАДАЧИ**\n\nЗадачи успешно отправлены в группу!"
                
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 К тестированию", callback_data="menu_testing")
                ]])
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Ошибка отправки ежедневных задач: {e}", exc_info=True)
                try:
                    text = f"❌ **ОШИБКА**\n\nНе удалось отправить задачи:\n{str(e)[:200]}"
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 К тестированию", callback_data="menu_testing")
                    ]])
                    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                except:
                    await query.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)
        
        elif data == "test_employees":
            # Контроль сотрудников - отправка кнопок присутствия (как в 07:50)
            try:
                await query.answer("⏳ Отправка кнопок...")
                
                # Используем функцию из bot_data или импортируем напрямую
                if 'send_presence_buttons' in context.bot_data:
                    send_presence_buttons_func = context.bot_data['send_presence_buttons']
                else:
                    # Если нет в bot_data, импортируем напрямую
                    import sys
                    if 'bot' in sys.modules:
                        bot_module = sys.modules['bot']
                        send_presence_buttons_func = bot_module.send_presence_buttons
                    else:
                        raise ImportError("Не удалось найти функцию send_presence_buttons")
                
                # Создаем обертку для app
                class AppWrapper:
                    def __init__(self, bot):
                        self.bot = bot
                
                app_wrapper = AppWrapper(context.bot)
                
                # Вызываем функцию с force_weekend=True для тестирования
                await send_presence_buttons_func(app_wrapper, force_weekend=True)
                
                text = "✅ **КОНТРОЛЬ СОТРУДНИКОВ**\n\nКнопки 'На рабочем месте' и 'Опаздываю' отправлены в группу!"
                
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 К тестированию", callback_data="menu_testing")
                ]])
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Ошибка отправки кнопок присутствия: {e}", exc_info=True)
                try:
                    text = f"❌ **ОШИБКА**\n\nНе удалось отправить кнопки:\n{str(e)[:200]}"
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 К тестированию", callback_data="menu_testing")
                    ]])
                    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                except:
                    await query.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_menu_callback: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка")


async def handle_presence_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE, db):
    """Обработка отметки присутствия"""
    try:
        user = query.from_user
        if not user:
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        username = user.username if user.username else f"user_{user.id}"
        user_id = user.id
        
        if data == "presence_here":
            # На рабочем месте - отправляем сообщение в общий чат
            time_str = datetime.now().strftime("%H:%M")
            db.save_presence(username, user_id, "here", time=time_str)
            
            # Отправляем сообщение в общий чат от пользователя
            try:
                chat_id = context.bot_data.get('CHAT_ID')
                if not chat_id:
                    import os
                    chat_id = os.getenv('CHAT_ID', '').strip()
                
                if chat_id:
                    chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
                    message_text = f"На рабочем месте. {time_str}"
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message_text
                    )
                    logger.info(f"Сообщение о прибытии отправлено в общий чат {chat_id} от @{username}")
                
                await query.answer("✅ Отметка сохранена!")
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения в общий чат: {e}", exc_info=True)
                await query.answer("✅ Отметка сохранена!")
        
        elif data == "presence_late":
            # Опаздываю - показываем меню выбора времени
            from menu import get_delay_time_menu
            text = "⏰ **ОПОЗДАНИЕ**\n\nВыберите количество часов опоздания:"
            await query.edit_message_text(text, reply_markup=get_delay_time_menu(), parse_mode='Markdown')
            await query.answer()
        
        elif data == "presence_cancel":
            text = "❌ Отметка отменена"
            await query.edit_message_text(text)
            await query.answer()
    
    except Exception as e:
        logger.error(f"Ошибка в handle_presence_callback: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка")


async def handle_delay_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE, db, get_delay_time_menu, get_delay_minutes_menu):
    """Обработка выбора времени опоздания"""
    try:
        user = query.from_user
        if not user:
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        username = user.username if user.username else f"user_{user.id}"
        user_id = user.id
        
        parts = data.split("_")
        
        # Проверка на минимальную длину parts
        if len(parts) < 3:
            await query.answer("❌ Неверный формат данных", show_alert=True)
            return
        
        if parts[1] == "hour":
            # Выбрали часы, показываем минуты
            try:
                hour = int(parts[2])
            except (ValueError, IndexError):
                await query.answer("❌ Ошибка формата времени", show_alert=True)
                return
            context.user_data['delay_hour'] = hour
            text = f"⏰ **ОПОЗДАНИЕ**\n\nВыбрано: {hour}ч\n\nВыберите минуты:"
            await query.edit_message_text(text, reply_markup=get_delay_minutes_menu(hour), parse_mode='Markdown')
            await query.answer()
        
        elif parts[1] == "minute":
            # Выбрали минуты - отправляем сообщение в общий чат и уведомление сотруднику
            try:
                hour = int(parts[2])
                minute = int(parts[3])
            except (ValueError, IndexError):
                await query.answer("❌ Ошибка формата времени", show_alert=True)
                return
            delay_minutes = hour * 60 + minute
            context.user_data['delay_minutes'] = delay_minutes
            context.user_data['delay_hour'] = hour
            context.user_data['delay_minute'] = minute
            
            # Отправляем сообщение в общий чат от сотрудника
            try:
                chat_id = context.bot_data.get('CHAT_ID')
                if not chat_id:
                    import os
                    chat_id = os.getenv('CHAT_ID', '').strip()
                
                if chat_id:
                    chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
                    
                    # Маппинг username -> имя для опозданий
                    user_name_mapping = {
                        "alex301182": "Lysenko Alexander",
                        "Korudirp": "Ruslan Cherenkov",
                        "sanya_hui_sosi1488": "Test"
                    }
                    
                    # Получаем имя пользователя
                    user_display_name = user_name_mapping.get(username, username)
                    
                    # Формат: "Test опоздание 0ч 15 мин"
                    delay_text = f"{user_display_name} опоздание {hour}ч {minute} мин"
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=delay_text
                    )
                    logger.info(f"Сообщение об опоздании отправлено в общий чат {chat_id} от @{username} ({user_display_name})")
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения в общий чат: {e}", exc_info=True)
            
            # Пытаемся отправить сотруднику сообщение о необходимости написать причину
            # Но только если пользователь уже начал диалог с ботом
            try:
                reason_text = "Напишите руководителю причину опоздания."
                await context.bot.send_message(
                    chat_id=user_id,
                    text=reason_text
                )
                await query.answer("✅ Сообщение отправлено в общий чат")
            except Exception as e:
                # Если пользователь не начал диалог с ботом, просто игнорируем ошибку
                # Сообщение в общий чат уже отправлено
                logger.warning(f"Не удалось отправить уведомление сотруднику (возможно, не начал диалог): {e}")
                await query.answer("✅ Сообщение отправлено в общий чат")
            
            # Сохраняем в БД
            time_str = datetime.now().strftime("%H:%M")
            db.save_presence(username, user_id, "late", time=time_str, delay_minutes=delay_minutes)
    
    except Exception as e:
        logger.error(f"Ошибка в handle_delay_callback: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка")


async def handle_new_task_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE, db, get_task_actions_menu, get_confirm_menu):
    """Обработка новых задач из меню"""
    try:
        await query.answer()
        parts = data.split("_")
        
        if len(parts) < 3:
            await query.answer("❌ Неверный формат", show_alert=True)
            return
        
        action = parts[1]  # view, edit, delete, complete, share
        try:
            task_id = int(parts[2])
        except (ValueError, IndexError):
            await query.answer("❌ Ошибка формата ID задачи", show_alert=True)
            return
        
        task = db.get_custom_task(task_id)
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        if action == "view":
            text = (
                f"📋 **ЗАДАЧА #{task_id}**\n\n"
                f"📝 Название: {task['title']}\n"
                f"📄 Описание: {task.get('description', 'Нет описания')}\n"
                f"⏰ Срок: {task.get('deadline', 'Не указан')}\n"
                f"👤 Исполнитель: {task.get('assignee', 'Не назначен')}\n"
                f"📊 Статус: {task['status']}\n"
                f"👨‍💼 Создатель: {task['creator']}"
            )
            await query.edit_message_text(text, reply_markup=get_task_actions_menu(task_id), parse_mode='Markdown')
        
        elif action == "edit":
            text = "✏️ Редактирование задачи будет доступно в следующей версии"
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data=f"task_view_{task_id}")
            ]])
            await query.edit_message_text(text, reply_markup=keyboard)
        
        elif action == "delete":
            text = f"🗑️ **УДАЛЕНИЕ ЗАДАЧИ**\n\nВы уверены, что хотите удалить задачу:\n\n**{task['title']}**?"
            await query.edit_message_text(text, reply_markup=get_confirm_menu("delete", task_id), parse_mode='Markdown')
        
        elif action == "complete":
            text = f"✅ **ЗАВЕРШЕНИЕ ЗАДАЧИ**\n\nЗадача: **{task['title']}**\n\nВведите результат выполнения (или нажмите 'Быстро завершить'):"
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚡ Быстро завершить", callback_data=f"task_complete_fast_{task_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data=f"task_view_{task_id}")]
            ])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        elif action == "complete_fast":
            # Быстрое завершение без формы
            from datetime import datetime
            db.update_custom_task(task_id, status='completed', completed_at=datetime.now().isoformat())
            await query.answer("✅ Задача завершена!")
            text = f"✅ **ЗАДАЧА ЗАВЕРШЕНА**\n\nЗадача: **{task['title']}**\n\nСтатус изменен на 'Завершена'"
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К задачам", callback_data="menu_view_tasks")
            ]])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        elif action == "share":
            text = f"📤 Задача будет отправлена в общий чат"
            await query.answer(text, show_alert=True)
    
    except Exception as e:
        logger.error(f"Ошибка в handle_new_task_callback: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка")


async def handle_old_task_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE, db):
    """Обработка старых задач (формат task_0_1)"""
    try:
        await query.answer()
        
        # Парсим task_id (формат: task_0_1 -> task_id = "0_1")
        parts = data.split("_")
        if len(parts) < 3:
            logger.error(f"Неверный формат task_id: {data}, parts={parts}")
            await query.answer("❌ Ошибка формата", show_alert=True)
            return
        
        task_id = "_".join(parts[1:])  # "0_1"
        logger.info(f"Обработка старой задачи: task_id={task_id}")
        
        # Определяем пользователя
        user = query.from_user
        if not user:
            await query.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        username = user.username if user.username else f"user_{user.id}"
        user_id = user.id
        
        # Маппинг пользователей
        user_mapping = {
            "alex301182": {"initials": "AG", "name": "АГ"},
            "Korudirp": {"initials": "KA", "name": "КА"},
            "sanya_hui_sosi1488": {"initials": "SA", "name": "СА"}
        }
        
        # Определяем инициалы пользователя
        user_info = user_mapping.get(username)
        if not user_info:
            # Пробуем найти по user_id
            for uname, info in user_mapping.items():
                stored_id = db.get_user_id_by_username(uname)
                if stored_id == user_id:
                    user_info = info
                    username = uname
                    break
        
        if not user_info:
            await query.answer("❌ Вы не авторизованы для работы с задачами", show_alert=True)
            return
        
        initials = user_info["initials"]
        logger.info(f"Пользователь: {username} ({initials})")
        
        # Сохраняем user_id в БД
        db.save_user_id(username, user_id, initials)
        logger.info(f"ID пользователя сохранен в БД")
        
        # Получаем текущий статус пользователя для этой задачи
        status_key = f"{task_id}_{initials}"
        current_status = db.get_task_status(status_key)
        logger.info(f"Текущий статус для {status_key}: {current_status}")
        
        # Циклически меняем статус: ⚪ → ⏳ → ✅ → ⚪
        status_cycle = {"⚪": "⏳", "⏳": "✅", "✅": "⚪"}
        new_status = status_cycle.get(current_status, "⚪")
        
        # Сохраняем новый статус
        db.set_task_status(status_key, new_status)
        logger.info(f"Новый статус для {status_key}: {new_status}")
        
        # Получаем статусы всех пользователей для этой задачи
        status_ag = db.get_task_status(f"{task_id}_AG")
        status_ka = db.get_task_status(f"{task_id}_KA")
        status_sa = db.get_task_status(f"{task_id}_SA")
        
        logger.info(f"Статусы: AG={status_ag}, KA={status_ka}, SA={status_sa}")
        
        # Определяем общий статус задачи
        # ✅ только если все выполнили
        if status_ag == "✅" and status_ka == "✅" and status_sa == "✅":
            overall_status = "✅"
        else:
            # Считаем количество исполнителей, которые взяли задачу (⏳ или ✅)
            active_count = sum(1 for status in [status_ag, status_ka, status_sa] if status in ["⏳", "✅"])
            
            if active_count > 0:
                # Показываем количество исполнителей эмодзи 👤
                overall_status = "👤" * active_count
            else:
                overall_status = "⚪"
        
        logger.info(f"Общий статус задачи: {overall_status}")
        
        # Обновляем кнопку в сообщении
        message = query.message
        if not message or not message.text:
            logger.error("Не удалось получить сообщение для обновления")
            return
        
        # Извлекаем оригинальный текст задачи из сообщения
        message_lines = message.text.split("\n")
        task_text = None
        task_number = None
        
        # Ищем строку с задачей (формат: "1. Название задачи")
        for line in message_lines:
            if line.strip().startswith(f"{task_id.split('_')[1]}."):
                task_text = line.split(".", 1)[1].strip()
                task_number = task_id.split("_")[1]
                break
        
        if not task_text:
            # Если не нашли, пытаемся извлечь из текущего текста кнопки
            if message.reply_markup and message.reply_markup.inline_keyboard:
                for row in message.reply_markup.inline_keyboard:
                    for button in row:
                        if button.callback_data == data:
                            # Убираем статус из текста кнопки
                            button_text = button.text
                            # Убираем эмодзи статуса в конце (⚪, ⏳, ✅, или 👤)
                            # Сначала проверяем множественные 👤
                            if "👤" in button_text:
                                # Убираем все 👤 из конца
                                task_text = button_text.rstrip("👤").strip()
                            else:
                                # Проверяем одиночные эмодзи
                                for status_emoji in ["⚪", "⏳", "✅"]:
                                    if button_text.endswith(f" {status_emoji}"):
                                        task_text = button_text[:-2].strip()
                                        break
                            # Убираем номер задачи если есть
                            if task_text and task_text.startswith(f"{task_id.split('_')[1]}."):
                                task_text = task_text.split(".", 1)[1].strip()
                            break
        
        if not task_text:
            logger.error(f"Не удалось извлечь текст задачи для task_id={task_id}")
            await query.answer("❌ Ошибка обновления", show_alert=True)
            return
        
        # Формируем новый текст кнопки
        # ОПТИМИЗАЦИЯ ДЛЯ МОБИЛЬНЫХ: ограничиваем длину до 30 символов
        max_mobile_length = 30
        if len(task_text) > max_mobile_length:
            task_text_short = task_text[:max_mobile_length-3] + "..."
            button_text = f"{task_number}. {task_text_short} {overall_status}" if task_number else f"{task_text_short} {overall_status}"
        else:
            button_text = f"{task_number}. {task_text} {overall_status}" if task_number else f"{task_text} {overall_status}"
        
        # Обновляем клавиатуру
        current_markup = message.reply_markup
        if not current_markup or not current_markup.inline_keyboard:
            logger.error("Не удалось получить клавиатуру для обновления")
            return
        
        # Находим и обновляем нужную кнопку
        new_keyboard = []
        for row in current_markup.inline_keyboard:
            new_row = []
            for button in row:
                if button.callback_data == data:
                    # Обновляем эту кнопку
                    from telegram import InlineKeyboardButton
                    new_row.append(InlineKeyboardButton(button_text, callback_data=data))
                else:
                    new_row.append(button)
            if new_row:
                new_keyboard.append(new_row)
        
        from telegram import InlineKeyboardMarkup
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
        logger.info(f"Кнопка обновлена: {button_text}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_old_task_callback: {e}", exc_info=True)
        try:
            await query.answer("❌ Произошла ошибка", show_alert=True)
        except:
            pass


async def handle_confirm_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE, db, get_task_actions_menu, get_tasks_menu):
    """Обработка подтверждений"""
    try:
        await query.answer()
        parts = data.split("_")
        
        if len(parts) < 3:
            await query.answer("❌ Неверный формат", show_alert=True)
            return
        
        action_type = parts[0]  # confirm или cancel
        action = parts[1]  # delete, complete и т.д.
        try:
            item_id = int(parts[2])
        except (ValueError, IndexError):
            await query.answer("❌ Ошибка формата ID", show_alert=True)
            return
        
        if action_type == "cancel":
            # Отмена действия
            if action == "delete":
                task = db.get_custom_task(item_id)
                if task:
                    text = f"📋 **ЗАДАЧА #{item_id}**\n\nУдаление отменено."
                    await query.edit_message_text(text, reply_markup=get_task_actions_menu(item_id), parse_mode='Markdown')
            return
        
        if action_type == "confirm":
            if action == "delete":
                task = db.get_custom_task(item_id)
                if task:
                    db.delete_custom_task(item_id)
                    text = "🗑️ **ЗАДАЧА УДАЛЕНА**\n\nЗадача успешно удалена."
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 К задачам", callback_data="menu_view_tasks")
                    ]])
                    await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Ошибка в handle_confirm_callback: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка")


async def handle_assignee_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE, db):
    """Обработка выбора исполнителя"""
    try:
        await query.answer()
        assignee = data.split("_")[1]  # AG, KA, SA, all
        
        # Это обрабатывается ConversationHandler, не нужно здесь
    
    except Exception as e:
        logger.error(f"Ошибка в handle_assignee_callback: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка")


async def handle_work_task_take(query, data: str, context: ContextTypes.DEFAULT_TYPE, db):
    """Обработка кнопки 'Взять в работу' - просто отмечает, что задача взята"""
    try:
        await query.answer()
        
        # Парсим данные: work_take_{task_id}_{assignee}
        parts = data.split("_")
        if len(parts) < 4:
            await query.answer("❌ Неверный формат", show_alert=True)
            return
        
        try:
            task_id = int(parts[2])
            assignee = parts[3]
            if assignee not in ["AG", "KA", "SA"]:
                await query.answer("❌ Неверный исполнитель", show_alert=True)
                return
        except (ValueError, IndexError):
            await query.answer("❌ Ошибка формата данных", show_alert=True)
            return
        
        # Получаем задачу
        task = db.get_custom_task(task_id)
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        # Определяем пользователя
        user = query.from_user
        username = user.username if user.username else f"user_{user.id}"
        user_id = user.id
        
        # Обновляем статус задачи на "in_progress" и добавляем индикатор ⏰ в сообщение
        from datetime import datetime
        db.update_custom_task(task_id, status='in_progress')
        
        # Обновляем сообщение в группе - добавляем ⏰ к тексту задачи
        if query.message and query.message.chat.type in ['group', 'supergroup']:
            try:
                assignee_names = {
                    "AG": "Lysenko Alexander",
                    "KA": "Ruslan Cherenkov",
                    "SA": "Test"
                }
                assignee_name = assignee_names.get(assignee, assignee)
                
                # Получаем текущий текст сообщения
                current_text = query.message.text or query.message.caption or ""
                
                # Добавляем индикатор ⏰ к названию задачи, если его еще нет
                if "⏰" not in current_text and task['title'] in current_text:
                    # Заменяем название задачи на название с индикатором
                    new_text = current_text.replace(
                        f"📝 **{task['title']}**",
                        f"📝 **{task['title']}** ⏰"
                    )
                    # Если не нашлось, пробуем другой формат
                    if new_text == current_text:
                        new_text = current_text.replace(
                            task['title'],
                            f"{task['title']} ⏰"
                        )
                    
                    if new_text != current_text:
                        await query.message.edit_text(
                            text=new_text,
                            reply_markup=query.message.reply_markup,
                            parse_mode='Markdown'
                        )
            except Exception as e:
                logger.error(f"Ошибка обновления текста сообщения: {e}", exc_info=True)
        
        # Отправляем уведомление в общий чат о взятии в работу
        try:
            chat_id = context.bot_data.get('CHAT_ID')
            if not chat_id:
                import os
                chat_id = os.getenv('CHAT_ID', '').strip()
            
            if chat_id:
                chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
                assignee_names = {
                    "AG": "Lysenko Alexander",
                    "KA": "Ruslan Cherenkov",
                    "SA": "Test"
                }
                assignee_name = assignee_names.get(assignee, assignee)
                
                take_text = f"{assignee_name} взял задачу в работу"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=take_text
                )
                logger.info(f"Уведомление о взятии задачи #{task_id} в работу отправлено в общий чат {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления в общий чат: {e}", exc_info=True)
        
        # Обновляем кнопку в сообщении группы (если это сообщение из группы)
        if query.message and query.message.chat.type in ['group', 'supergroup']:
            # Обновляем клавиатуру - убираем кнопку "Взять в работу" для этого исполнителя, оставляем "Готово"
            current_markup = query.message.reply_markup
            if current_markup and current_markup.inline_keyboard:
                new_keyboard = []
                for row in current_markup.inline_keyboard:
                    new_row = []
                    for button in row:
                        # Если это кнопка "Взять в работу" для этого исполнителя - заменяем на "Готово"
                        if button.callback_data == data:
                            assignee_names = {
                                "AG": "Lysenko Alexander",
                                "KA": "Ruslan Cherenkov",
                                "SA": "Test"
                            }
                            assignee_name = assignee_names.get(assignee, assignee)
                            new_row.append(InlineKeyboardButton(
                                f"✅ {assignee_name} - Готово",
                                callback_data=f"work_done_{task_id}_{assignee}"
                            ))
                        else:
                            new_row.append(button)
                    if new_row:
                        new_keyboard.append(new_row)
                
                try:
                    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
                except Exception as e:
                    logger.error(f"Ошибка обновления клавиатуры: {e}", exc_info=True)
        
        # Отправляем описание задачи пользователю в личные сообщения
        try:
            assignee_names = {
                "AG": "Lysenko Alexander",
                "KA": "Ruslan Cherenkov",
                "SA": "Test"
            }
            confirm_text = (
                f"📋 **ЗАДАЧА #{task_id} ВЗЯТА В РАБОТУ**\n\n"
                f"📝 **{task['title']}**\n\n"
                f"📄 **Описание:**\n{task.get('description', 'Нет описания')}\n\n"
                f"⏰ Срок: {task.get('deadline', 'Не указан')}\n"
                f"👤 Исполнитель: {assignee_names.get(assignee, assignee)}"
            )
            await context.bot.send_message(
                chat_id=user_id,
                text=confirm_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка отправки описания задачи пользователю: {e}", exc_info=True)
        
        logger.info(f"Задача #{task_id} взята в работу пользователем @{username} ({assignee})")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_work_task_take: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка", show_alert=True)


async def handle_work_task_done(query, data: str, context: ContextTypes.DEFAULT_TYPE, db):
    """Обработка кнопки 'Готово' - отмечает задачу как выполненную"""
    try:
        await query.answer()
        
        # Парсим данные: work_done_{task_id}_{assignee}
        parts = data.split("_")
        if len(parts) < 4:
            await query.answer("❌ Неверный формат", show_alert=True)
            return
        
        try:
            task_id = int(parts[2])
            assignee = parts[3]
            if assignee not in ["AG", "KA", "SA"]:
                await query.answer("❌ Неверный исполнитель", show_alert=True)
                return
        except (ValueError, IndexError):
            await query.answer("❌ Ошибка формата данных", show_alert=True)
            return
        
        # Получаем задачу
        task = db.get_custom_task(task_id)
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        # Определяем пользователя
        user = query.from_user
        username = user.username if user.username else f"user_{user.id}"
        user_id = user.id
        
        # Обновляем статус задачи - отмечаем этого исполнителя как завершившего
        from datetime import datetime
        
        # Получаем текущую задачу для проверки assignee
        task_assignee = task.get('assignee', 'all')
        
        # Если задача назначена конкретному исполнителю - сразу завершаем
        # Если задача назначена "всем" - проверяем, все ли завершили
        if task_assignee == 'all':
            # Получаем список завершенных исполнителей из БД
            completed_assignees = task.get('completed_assignees', '') or ''
            completed_list = completed_assignees.split(',') if completed_assignees else []
            
            # Добавляем текущего исполнителя в список завершенных
            if assignee not in completed_list:
                completed_list.append(assignee)
            
            # Обновляем задачу с новым списком завершенных
            completed_str = ','.join(completed_list)
            db.update_custom_task(
                task_id,
                completed_assignees=completed_str
            )
            
            # Проверяем, все ли исполнители завершили (AG, KA, SA)
            all_assignees = ['AG', 'KA', 'SA']
            all_completed = all(assignee_code in completed_list for assignee_code in all_assignees)
            
            if all_completed:
                # Все завершили - задача полностью завершена
                db.update_custom_task(
                    task_id,
                    status='completed',
                    completed_at=datetime.now().isoformat()
                )
        else:
            # Конкретный исполнитель - сразу завершаем
            db.update_custom_task(
                task_id,
                status='completed',
                completed_at=datetime.now().isoformat()
            )
        
        # Отправляем уведомление в общий чат
        try:
            chat_id = context.bot_data.get('CHAT_ID')
            if not chat_id:
                import os
                chat_id = os.getenv('CHAT_ID', '').strip()
            
            if chat_id:
                chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
                assignee_names = {
                    "AG": "Lysenko Alexander",
                    "KA": "Ruslan Cherenkov",
                    "SA": "Test"
                }
                assignee_name = assignee_names.get(assignee, assignee)
                
                # Проверяем, полностью ли завершена задача
                task_assignee = task.get('assignee', 'all')
                if task_assignee == 'all':
                    # Получаем обновленную задачу
                    updated_task = db.get_custom_task(task_id)
                    completed_assignees = updated_task.get('completed_assignees', '') or ''
                    completed_list = completed_assignees.split(',') if completed_assignees else []
                    all_assignees = ['AG', 'KA', 'SA']
                    all_completed = all(assignee_code in completed_list for assignee_code in all_assignees)
                    
                    if all_completed:
                        completion_text = (
                            f"✅ **ЗАДАЧА ПОЛНОСТЬЮ ЗАВЕРШЕНА**\n\n"
                            f"📝 Задача: {task['title']}\n"
                            f"👤 Все исполнители завершили работу\n"
                            f"🆔 ID задачи: #{task_id}\n"
                            f"🕐 Время: {datetime.now().strftime('%H:%M')}"
                        )
                    else:
                        # Еще не все завершили
                        remaining = [a for a in all_assignees if a not in completed_list]
                        remaining_names = [assignee_names.get(a, a) for a in remaining]
                        completion_text = (
                            f"✅ **ЧАСТИЧНО ЗАВЕРШЕНО**\n\n"
                            f"📝 Задача: {task['title']}\n"
                            f"👤 {assignee_name} завершил свою часть\n"
                            f"⏳ Ожидаются: {', '.join(remaining_names)}\n"
                            f"🆔 ID задачи: #{task_id}\n"
                            f"🕐 Время: {datetime.now().strftime('%H:%M')}"
                        )
                else:
                    completion_text = (
                        f"✅ **ЗАДАЧА ЗАВЕРШЕНА**\n\n"
                        f"📝 Задача: {task['title']}\n"
                        f"👤 Исполнитель: {assignee_name}\n"
                        f"🆔 ID задачи: #{task_id}\n"
                        f"🕐 Время: {datetime.now().strftime('%H:%M')}"
                    )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=completion_text,
                    parse_mode='Markdown'
                )
                logger.info(f"Уведомление о завершении задачи #{task_id} отправлено в общий чат {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления в общий чат: {e}", exc_info=True)
        
        # Уведомление администратору отправляется только при полном завершении
        # (уже отправлено выше в общий чат)
        
        # Обновляем кнопку в сообщении группы (если это сообщение из группы)
        if query.message and query.message.chat.type in ['group', 'supergroup']:
            # Обновляем клавиатуру - убираем обе кнопки для этого исполнителя, показываем "✅ Выполнено"
            current_markup = query.message.reply_markup
            if current_markup and current_markup.inline_keyboard:
                new_keyboard = []
                for row in current_markup.inline_keyboard:
                    new_row = []
                    for button in row:
                        # Если это кнопка для этого исполнителя - заменяем на "✅ Выполнено"
                        if f"work_take_{task_id}_{assignee}" in button.callback_data or f"work_done_{task_id}_{assignee}" in button.callback_data:
                            assignee_names = {
                                "AG": "Lysenko Alexander",
                                "KA": "Ruslan Cherenkov",
                                "SA": "Test"
                            }
                            assignee_name = assignee_names.get(assignee, assignee)
                            new_row.append(InlineKeyboardButton(
                                f"✅ {assignee_name} - Выполнено",
                                callback_data=f"work_status_{task_id}_{assignee}"
                            ))
                        else:
                            new_row.append(button)
                    if new_row:
                        new_keyboard.append(new_row)
                
                try:
                    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
                except Exception as e:
                    logger.error(f"Ошибка обновления клавиатуры: {e}", exc_info=True)
        
        # Отправляем подтверждение пользователю в личные сообщения
        try:
            confirm_text = f"✅ Задача #{task_id} отмечена как выполненная!\n\n📝 {task['title']}"
            await context.bot.send_message(
                chat_id=user_id,
                text=confirm_text
            )
        except Exception as e:
            logger.error(f"Ошибка отправки подтверждения пользователю: {e}", exc_info=True)
        
        logger.info(f"Задача #{task_id} отмечена как выполненная пользователем @{username} ({assignee})")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_work_task_done: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка", show_alert=True)

