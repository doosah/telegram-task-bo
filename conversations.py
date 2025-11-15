"""
МОДУЛЬ ДЛЯ ОБРАБОТКИ МНОГОШАГОВЫХ ДИАЛОГОВ (CONVERSATION HANDLERS)
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from menu import get_assignee_menu, get_main_menu

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(TITLE, DESCRIPTION, DEADLINE, ASSIGNEE) = range(4)
(EDIT_TITLE, EDIT_DESCRIPTION, EDIT_DEADLINE, EDIT_ASSIGNEE) = range(4, 8)
(COMPLETE_RESULT, COMPLETE_PHOTO) = range(8, 10)


async def start_create_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания задачи - запрос названия"""
    try:
        user = update.effective_user
        logger.info(f"Начало создания задачи пользователем @{user.username}")
        
        context.user_data['creating_task'] = {}
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 1/4: Название задачи\n\n"
            "Введите название задачи:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_create_task")
        ]])
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        return TITLE
    except Exception as e:
        logger.error(f"Ошибка в start_create_task: {e}", exc_info=True)
        return -1


async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия задачи"""
    try:
        title = update.message.text.strip()
        
        if len(title) < 3:
            await update.message.reply_text("❌ Название слишком короткое (минимум 3 символа). Попробуйте снова:")
            return TITLE
        
        if len(title) > 100:
            await update.message.reply_text("❌ Название слишком длинное (максимум 100 символов). Попробуйте снова:")
            return TITLE
        
        context.user_data['creating_task']['title'] = title
        logger.info(f"Название задачи получено: {title}")
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 2/4: Описание задачи\n\n"
            "Введите описание задачи (или отправьте /skip для пропуска):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_description")
        ]])
        
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return DESCRIPTION
    except Exception as e:
        logger.error(f"Ошибка в receive_title: {e}", exc_info=True)
        return -1


async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение описания задачи"""
    try:
        description = update.message.text.strip()
        
        if len(description) > 500:
            await update.message.reply_text("❌ Описание слишком длинное (максимум 500 символов). Попробуйте снова:")
            return DESCRIPTION
        
        context.user_data['creating_task']['description'] = description
        logger.info(f"Описание задачи получено: {description[:50]}...")
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 3/4: Срок выполнения\n\n"
            "Введите срок выполнения в формате ДД.ММ.ГГГГ (например, 25.12.2024)\n"
            "Или отправьте /skip для пропуска:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_deadline")
        ]])
        
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return DEADLINE
    except Exception as e:
        logger.error(f"Ошибка в receive_description: {e}", exc_info=True)
        return -1


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск описания"""
    try:
        context.user_data['creating_task']['description'] = ""
        logger.info("Описание пропущено")
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 3/4: Срок выполнения\n\n"
            "Введите срок выполнения в формате ДД.ММ.ГГГГ (например, 25.12.2024)\n"
            "Или отправьте /skip для пропуска:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_deadline")
        ]])
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        return DEADLINE
    except Exception as e:
        logger.error(f"Ошибка в skip_description: {e}", exc_info=True)
        return -1


async def receive_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение срока выполнения"""
    try:
        deadline_str = update.message.text.strip()
        
        # Парсим дату в формате ДД.ММ.ГГГГ
        try:
            deadline = datetime.strptime(deadline_str, "%d.%m.%Y")
            context.user_data['creating_task']['deadline'] = deadline_str
            logger.info(f"Срок выполнения получен: {deadline_str}")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например, 25.12.2024):")
            return DEADLINE
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 4/4: Выбор исполнителя\n\n"
            "Выберите исполнителя задачи:"
        )
        
        await update.message.reply_text(text, reply_markup=get_assignee_menu(), parse_mode='Markdown')
        return ASSIGNEE
    except Exception as e:
        logger.error(f"Ошибка в receive_deadline: {e}", exc_info=True)
        return -1


async def skip_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск срока выполнения"""
    try:
        context.user_data['creating_task']['deadline'] = ""
        logger.info("Срок выполнения пропущен")
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 4/4: Выбор исполнителя\n\n"
            "Выберите исполнителя задачи:"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=get_assignee_menu(), parse_mode='Markdown')
        elif update.message:
            await update.message.reply_text(text, reply_markup=get_assignee_menu(), parse_mode='Markdown')
        
        return ASSIGNEE
    except Exception as e:
        logger.error(f"Ошибка в skip_deadline: {e}", exc_info=True)
        return -1


async def receive_assignee(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Получение исполнителя и завершение создания задачи"""
    try:
        assignee = update.callback_query.data.split("_")[1] if update.callback_query else "all"
        
        if assignee not in ["AG", "KA", "SA", "all"]:
            await update.callback_query.answer("❌ Неверный выбор исполнителя")
            return ASSIGNEE
        
        context.user_data['creating_task']['assignee'] = assignee
        
        # Получаем данные задачи
        task_data = context.user_data.get('creating_task', {})
        title = task_data.get('title', '')
        description = task_data.get('description', '')
        deadline = task_data.get('deadline', '')
        assignee = task_data.get('assignee', 'all')
        
        # Получаем создателя
        user = update.effective_user
        creator = user.username if user.username else f"user_{user.id}"
        
        # Сохраняем задачу в БД
        from database import Database
        db_instance = Database()
        task_id = db_instance.save_custom_task(title, description, deadline, assignee, creator)
        
        if task_id:
            assignee_names = {
                "AG": "АГ",
                "KA": "КА",
                "SA": "СА",
                "all": "Все"
            }
            
            text = (
                f"✅ **ЗАДАЧА СОЗДАНА!**\n\n"
                f"📝 Название: {title}\n"
                f"📄 Описание: {description if description else 'Нет описания'}\n"
                f"⏰ Срок: {deadline if deadline else 'Не указан'}\n"
                f"👤 Исполнитель: {assignee_names.get(assignee, assignee)}\n\n"
                f"ID задачи: #{task_id}"
            )
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 В главное меню", callback_data="menu_main")
            ]])
            
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
            await update.callback_query.answer("✅ Задача успешно создана!")
            
            # Очищаем данные
            context.user_data.pop('creating_task', None)
            
            logger.info(f"Задача #{task_id} создана пользователем @{creator}")
            return -1  # Завершаем диалог
        else:
            await update.callback_query.answer("❌ Ошибка создания задачи", show_alert=True)
            return ASSIGNEE
            
    except Exception as e:
        logger.error(f"Ошибка в receive_assignee: {e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.answer("❌ Произошла ошибка", show_alert=True)
        return -1


async def cancel_create_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена создания задачи"""
    try:
        context.user_data.pop('creating_task', None)
        
        text = "❌ Создание задачи отменено."
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 В главное меню", callback_data="menu_main")
        ]])
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
            await update.callback_query.answer("Создание задачи отменено")
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard)
        
        logger.info("Создание задачи отменено пользователем")
        return -1  # Завершаем диалог
    except Exception as e:
        logger.error(f"Ошибка в cancel_create_task: {e}", exc_info=True)
        return -1

