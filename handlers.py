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
            await query.edit_message_text(text, reply_markup=get_main_menu(), parse_mode='Markdown')
        
        elif data == "menu_create_task":
            text = (
                "📝 **СОЗДАНИЕ ЗАДАЧИ**\n\n"
                "Введите название задачи:"
            )
            context.user_data['creating_task'] = {}
            await query.edit_message_text(text, parse_mode='Markdown')
            # Здесь нужно будет использовать ConversationHandler
        
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
        
        elif data == "menu_help":
            text = (
                "❓ **ПОМОЩЬ**\n\n"
                "📝 **Создать задачу** - добавить новую задачу\n"
                "📋 **Просмотреть задачи** - список ваших задач\n"
                "✅ **Завершить задачу** - отметить задачу как выполненную\n"
                "⚙️ **Настройки** - настройки бота\n\n"
                "⏰ **Отметка присутствия**\n"
                "Каждый день в 07:50 в общем чате появляются кнопки для отметки присутствия."
            )
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад в меню", callback_data="menu_main")
            ]])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
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
        
        username = user.username
        user_id = user.id
        
        if data == "presence_here":
            # На рабочем месте
            time_str = datetime.now().strftime("%H:%M")
            db.save_presence(username, user_id, "here", time=time_str)
            
            text = f"✅ **@{username}** на рабочем месте\n⏰ Время: {time_str}"
            await query.edit_message_text(text, parse_mode='Markdown')
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
        
        username = user.username
        user_id = user.id
        
        parts = data.split("_")
        
        if parts[1] == "hour":
            # Выбрали часы, показываем минуты
            hour = int(parts[2])
            context.user_data['delay_hour'] = hour
            text = f"⏰ **ОПОЗДАНИЕ**\n\nВыбрано: {hour}ч\n\nВыберите минуты:"
            await query.edit_message_text(text, reply_markup=get_delay_minutes_menu(hour), parse_mode='Markdown')
            await query.answer()
        
        elif parts[1] == "minute":
            # Выбрали минуты, запрашиваем причину
            hour = int(parts[2])
            minute = int(parts[3])
            delay_minutes = hour * 60 + minute
            context.user_data['delay_minutes'] = delay_minutes
            
            text = (
                f"⏰ **ОПОЗДАНИЕ**\n\n"
                f"Выбрано: {hour}ч {minute}м\n\n"
                f"Введите краткую причину опоздания (одним сообщением):"
            )
            context.user_data['waiting_reason'] = True
            await query.edit_message_text(text, parse_mode='Markdown')
            await query.answer()
            # Здесь нужно будет использовать ConversationHandler для получения причины
    
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
        task_id = int(parts[2])
        
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


async def handle_old_task_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE):
    """Обработка старых задач (существующая логика)"""
    # Эта функция будет содержать весь старый код из button_callback
    # Пока оставляем заглушку
    await query.answer("Обработка старых задач...")


async def handle_confirm_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE, db, get_task_actions_menu, get_tasks_menu):
    """Обработка подтверждений"""
    try:
        await query.answer()
        parts = data.split("_")
        
        if len(parts) < 3:
            return
        
        action_type = parts[0]  # confirm или cancel
        action = parts[1]  # delete, complete и т.д.
        item_id = int(parts[2])
        
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
        
        if 'creating_task' in context.user_data:
            context.user_data['creating_task']['assignee'] = assignee
            text = f"👤 Исполнитель выбран: {assignee}\n\nЗадача будет создана."
            await query.edit_message_text(text)
            # Здесь нужно создать задачу
    
    except Exception as e:
        logger.error(f"Ошибка в handle_assignee_callback: {e}", exc_info=True)
        await query.answer("❌ Произошла ошибка")

