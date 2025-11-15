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
(TITLE, DESCRIPTION, ASSIGNEE, DEADLINE, PHOTO) = range(5)
(EDIT_TITLE, EDIT_DESCRIPTION, EDIT_DEADLINE, EDIT_ASSIGNEE) = range(5, 9)
(COMPLETE_RESULT, COMPLETE_PHOTO) = range(9, 11)


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
            "Шаг 2/5: Описание задачи\n\n"
            "Введите описание задачи (или нажмите кнопку для пропуска):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить описание", callback_data="skip_description")
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
            "Шаг 3/5: Выбор исполнителя\n\n"
            "Выберите исполнителя задачи:"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=get_assignee_menu(), parse_mode='Markdown')
        elif update.message:
            await update.message.reply_text(text, reply_markup=get_assignee_menu(), parse_mode='Markdown')
        
        return ASSIGNEE
    except Exception as e:
        logger.error(f"Ошибка в skip_description: {e}", exc_info=True)
        return -1


async def receive_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение срока выполнения - переход к фото"""
    try:
        deadline_str = update.message.text.strip()
        
        # Парсим дату в формате ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ
        try:
            if " " in deadline_str:
                deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
            else:
                deadline = datetime.strptime(deadline_str, "%d.%m.%Y")
            context.user_data['creating_task']['deadline'] = deadline_str
            logger.info(f"Срок выполнения получен: {deadline_str}")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ или ДД.ММ.ГГГГ (например, 25.12.2024 14:30):")
            return DEADLINE
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 5/5: Фото или видео (опционально)\n\n"
            "Отправьте фото или видео для задачи\n"
            "Или нажмите кнопку для пропуска:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить фото", callback_data="skip_photo")
        ]])
        
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return PHOTO
    except Exception as e:
        logger.error(f"Ошибка в receive_deadline: {e}", exc_info=True)
        return -1


async def skip_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск срока выполнения - переход к фото"""
    try:
        context.user_data['creating_task']['deadline'] = ""
        logger.info("Срок выполнения пропущен")
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 5/5: Фото или видео (опционально)\n\n"
            "Отправьте фото или видео для задачи\n"
            "Или нажмите кнопку для завершения:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить фото", callback_data="skip_photo")
        ]])
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        return PHOTO
    except Exception as e:
        logger.error(f"Ошибка в skip_deadline: {e}", exc_info=True)
        return -1


async def receive_assignee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение исполнителя - переход к дате"""
    try:
        assignee = update.callback_query.data.split("_")[1] if update.callback_query else "all"
        
        if assignee not in ["AG", "KA", "SA", "all"]:
            await update.callback_query.answer("❌ Неверный выбор исполнителя")
            return ASSIGNEE
        
        context.user_data['creating_task']['assignee'] = assignee
        await update.callback_query.answer("✅ Исполнитель выбран")
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 4/5: Дата и время выполнения\n\n"
            "Введите дату и время в формате:\n"
            "ДД.ММ.ГГГГ ЧЧ:ММ (например, 25.12.2024 14:30)\n"
            "Или только дату: ДД.ММ.ГГГГ\n\n"
            "Нажмите кнопку для пропуска:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить дату", callback_data="skip_deadline")
        ]])
        
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return DEADLINE
            
    except Exception as e:
        logger.error(f"Ошибка в receive_assignee: {e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.answer("❌ Произошла ошибка", show_alert=True)
        return -1


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение фото/видео и завершение создания задачи"""
    try:
        photo_file_id = None
        if update.message.photo:
            photo_file_id = update.message.photo[-1].file_id
        elif update.message.video:
            photo_file_id = update.message.video.file_id
        elif update.message.document:
            photo_file_id = update.message.document.file_id
        
        if photo_file_id:
            context.user_data['creating_task']['photo'] = photo_file_id
            logger.info(f"Фото/видео получено: {photo_file_id}")
        
        # Завершаем создание задачи
        return await finish_create_task(update, context)
        
    except Exception as e:
        logger.error(f"Ошибка в receive_photo: {e}", exc_info=True)
        return -1


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск фото и завершение создания задачи"""
    try:
        context.user_data['creating_task']['photo'] = None
        logger.info("Фото пропущено")
        
        # Завершаем создание задачи
        return await finish_create_task(update, context)
        
    except Exception as e:
        logger.error(f"Ошибка в skip_photo: {e}", exc_info=True)
        return -1


async def finish_create_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершение создания задачи - сохранение в БД"""
    try:
        # Получаем данные задачи
        task_data = context.user_data.get('creating_task', {})
        title = task_data.get('title', '')
        description = task_data.get('description', '')
        deadline = task_data.get('deadline', '')
        assignee = task_data.get('assignee', 'all')
        photo = task_data.get('photo')
        
        # Получаем создателя
        user = update.effective_user
        creator = user.username if user.username else f"user_{user.id}"
        
        # Сохраняем задачу в БД
        if 'db' in context.bot_data:
            db_instance = context.bot_data['db']
        else:
            from database import Database
            db_instance = Database()
        
        # Сохраняем фото в description или создаем отдельное поле
        if photo:
            description = f"{description}\n\n📎 Фото/видео: {photo}" if description else f"📎 Фото/видео: {photo}"
        
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
                f"👤 Исполнитель: {assignee_names.get(assignee, assignee)}\n"
                f"📎 Фото/видео: {'Да' if photo else 'Нет'}\n\n"
                f"ID задачи: #{task_id}"
            )
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 В главное меню", callback_data="menu_main")
            ]])
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
                await update.callback_query.answer("✅ Задача успешно создана!")
            elif update.message:
                await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
            
            # Очищаем данные
            context.user_data.pop('creating_task', None)
            
            logger.info(f"Задача #{task_id} создана пользователем @{creator}")
            return -1  # Завершаем диалог
        else:
            error_text = "❌ Ошибка создания задачи"
            if update.callback_query:
                await update.callback_query.answer(error_text, show_alert=True)
            elif update.message:
                await update.message.reply_text(error_text)
            return -1
            
    except Exception as e:
        logger.error(f"Ошибка в finish_create_task: {e}", exc_info=True)
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


# ========== РЕДАКТИРОВАНИЕ ЗАДАЧИ ==========

async def start_edit_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало редактирования задачи"""
    try:
        query = update.callback_query
        if not query:
            return -1
        
        # Извлекаем task_id из callback_data (формат: task_edit_1)
        task_id = int(query.data.split("_")[-1])
        context.user_data['editing_task_id'] = task_id
        
        # Получаем задачу из БД
        # Используем глобальный экземпляр db из context.bot_data
        if 'db' in context.bot_data:
            db = context.bot_data['db']
        else:
            from database import Database
            db = Database()
        task = db.get_custom_task(task_id)
        
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return -1
        
        # Сохраняем текущие данные задачи
        context.user_data['editing_task'] = {
            'title': task['title'],
            'description': task.get('description', ''),
            'deadline': task.get('deadline', ''),
            'assignee': task.get('assignee', 'all')
        }
        
        text = (
            f"✏️ **РЕДАКТИРОВАНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Текущее название: {task['title']}\n\n"
            f"Введите новое название задачи (или отправьте /skip чтобы оставить текущее):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Оставить текущее", callback_data="skip_edit_title"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit_task")
        ]])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return EDIT_TITLE
    except Exception as e:
        logger.error(f"Ошибка в start_edit_task: {e}", exc_info=True)
        return -1


async def receive_edit_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение нового названия задачи"""
    try:
        title = update.message.text.strip()
        
        if len(title) < 3:
            await update.message.reply_text("❌ Название слишком короткое (минимум 3 символа). Попробуйте снова:")
            return EDIT_TITLE
        
        if len(title) > 100:
            await update.message.reply_text("❌ Название слишком длинное (максимум 100 символов). Попробуйте снова:")
            return EDIT_TITLE
        
        context.user_data['editing_task']['title'] = title
        logger.info(f"Новое название задачи: {title}")
        
        task_id = context.user_data.get('editing_task_id')
        current_desc = context.user_data['editing_task'].get('description', '')
        
        text = (
            f"✏️ **РЕДАКТИРОВАНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Текущее описание: {current_desc if current_desc else 'Нет описания'}\n\n"
            f"Введите новое описание (или отправьте /skip чтобы оставить текущее):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Оставить текущее", callback_data="skip_edit_description"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit_task")
        ]])
        
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return EDIT_DESCRIPTION
    except Exception as e:
        logger.error(f"Ошибка в receive_edit_title: {e}", exc_info=True)
        return -1


async def skip_edit_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск редактирования названия"""
    try:
        query = update.callback_query
        task_id = context.user_data.get('editing_task_id')
        current_desc = context.user_data['editing_task'].get('description', '')
        
        text = (
            f"✏️ **РЕДАКТИРОВАНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Текущее описание: {current_desc if current_desc else 'Нет описания'}\n\n"
            f"Введите новое описание (или отправьте /skip чтобы оставить текущее):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Оставить текущее", callback_data="skip_edit_description"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit_task")
        ]])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return EDIT_DESCRIPTION
    except Exception as e:
        logger.error(f"Ошибка в skip_edit_title: {e}", exc_info=True)
        return -1


async def receive_edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение нового описания задачи"""
    try:
        description = update.message.text.strip()
        
        if len(description) > 500:
            await update.message.reply_text("❌ Описание слишком длинное (максимум 500 символов). Попробуйте снова:")
            return EDIT_DESCRIPTION
        
        context.user_data['editing_task']['description'] = description
        logger.info(f"Новое описание задачи: {description[:50]}...")
        
        task_id = context.user_data.get('editing_task_id')
        current_deadline = context.user_data['editing_task'].get('deadline', '')
        
        text = (
            f"✏️ **РЕДАКТИРОВАНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Текущий срок: {current_deadline if current_deadline else 'Не указан'}\n\n"
            f"Введите новый срок в формате ДД.ММ.ГГГГ (или отправьте /skip чтобы оставить текущий):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Оставить текущий", callback_data="skip_edit_deadline"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit_task")
        ]])
        
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return EDIT_DEADLINE
    except Exception as e:
        logger.error(f"Ошибка в receive_edit_description: {e}", exc_info=True)
        return -1


async def skip_edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск редактирования описания"""
    try:
        query = update.callback_query
        task_id = context.user_data.get('editing_task_id')
        current_deadline = context.user_data['editing_task'].get('deadline', '')
        
        text = (
            f"✏️ **РЕДАКТИРОВАНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Текущий срок: {current_deadline if current_deadline else 'Не указан'}\n\n"
            f"Введите новый срок в формате ДД.ММ.ГГГГ (или отправьте /skip чтобы оставить текущий):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Оставить текущий", callback_data="skip_edit_deadline"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_edit_task")
        ]])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return EDIT_DEADLINE
    except Exception as e:
        logger.error(f"Ошибка в skip_edit_description: {e}", exc_info=True)
        return -1


async def receive_edit_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение нового срока выполнения"""
    try:
        deadline_str = update.message.text.strip()
        
        # Парсим дату в формате ДД.ММ.ГГГГ
        try:
            deadline = datetime.strptime(deadline_str, "%d.%m.%Y")
            context.user_data['editing_task']['deadline'] = deadline_str
            logger.info(f"Новый срок выполнения: {deadline_str}")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например, 25.12.2024):")
            return EDIT_DEADLINE
        
        task_id = context.user_data.get('editing_task_id')
        
        text = (
            f"✏️ **РЕДАКТИРОВАНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Шаг 4/4: Выбор исполнителя\n\n"
            f"Выберите нового исполнителя задачи:"
        )
        
        await update.message.reply_text(text, reply_markup=get_assignee_menu(), parse_mode='Markdown')
        return EDIT_ASSIGNEE
    except Exception as e:
        logger.error(f"Ошибка в receive_edit_deadline: {e}", exc_info=True)
        return -1


async def skip_edit_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск редактирования срока выполнения"""
    try:
        query = update.callback_query
        task_id = context.user_data.get('editing_task_id')
        
        text = (
            f"✏️ **РЕДАКТИРОВАНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Шаг 4/4: Выбор исполнителя\n\n"
            f"Выберите нового исполнителя задачи:"
        )
        
        await query.edit_message_text(text, reply_markup=get_assignee_menu(), parse_mode='Markdown')
        return EDIT_ASSIGNEE
    except Exception as e:
        logger.error(f"Ошибка в skip_edit_deadline: {e}", exc_info=True)
        return -1


async def receive_edit_assignee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение нового исполнителя и завершение редактирования"""
    try:
        assignee = update.callback_query.data.split("_")[1] if update.callback_query else "all"
        
        if assignee not in ["AG", "KA", "SA", "all"]:
            await update.callback_query.answer("❌ Неверный выбор исполнителя")
            return EDIT_ASSIGNEE
        
        context.user_data['editing_task']['assignee'] = assignee
        
        # Получаем данные задачи
        task_id = context.user_data.get('editing_task_id')
        task_data = context.user_data.get('editing_task', {})
        
        # Обновляем задачу в БД
        # Используем глобальный экземпляр db из context.bot_data
        if 'db' in context.bot_data:
            db = context.bot_data['db']
        else:
            from database import Database
            db = Database()
        db.update_custom_task(
            task_id,
            title=task_data.get('title'),
            description=task_data.get('description'),
            deadline=task_data.get('deadline'),
            assignee=task_data.get('assignee')
        )
        
        assignee_names = {
            "AG": "АГ",
            "KA": "КА",
            "SA": "СА",
            "all": "Все"
        }
        
        text = (
            f"✅ **ЗАДАЧА ОБНОВЛЕНА!**\n\n"
            f"📝 Название: {task_data.get('title')}\n"
            f"📄 Описание: {task_data.get('description') if task_data.get('description') else 'Нет описания'}\n"
            f"⏰ Срок: {task_data.get('deadline') if task_data.get('deadline') else 'Не указан'}\n"
            f"👤 Исполнитель: {assignee_names.get(assignee, assignee)}\n\n"
            f"ID задачи: #{task_id}"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 К задаче", callback_data=f"task_view_{task_id}")
        ]])
        
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        await update.callback_query.answer("✅ Задача успешно обновлена!")
        
        # Очищаем данные
        context.user_data.pop('editing_task', None)
        context.user_data.pop('editing_task_id', None)
        
        logger.info(f"Задача #{task_id} обновлена")
        return -1  # Завершаем диалог
        
    except Exception as e:
        logger.error(f"Ошибка в receive_edit_assignee: {e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.answer("❌ Произошла ошибка", show_alert=True)
        return -1


async def cancel_edit_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена редактирования задачи"""
    try:
        task_id = context.user_data.pop('editing_task_id', None)
        context.user_data.pop('editing_task', None)
        
        text = "❌ Редактирование задачи отменено."
        
        if task_id:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К задаче", callback_data=f"task_view_{task_id}")
            ]])
        else:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 В главное меню", callback_data="menu_main")
            ]])
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
            await update.callback_query.answer("Редактирование отменено")
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard)
        
        logger.info("Редактирование задачи отменено пользователем")
        return -1  # Завершаем диалог
    except Exception as e:
        logger.error(f"Ошибка в cancel_edit_task: {e}", exc_info=True)
        return -1


# ========== ЗАВЕРШЕНИЕ ЗАДАЧИ С РЕЗУЛЬТАТОМ ==========

async def start_complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало завершения задачи - запрос результата"""
    try:
        query = update.callback_query
        if not query:
            return -1
        
        # Извлекаем task_id из callback_data (формат: task_complete_1)
        task_id = int(query.data.split("_")[-1])
        context.user_data['completing_task_id'] = task_id
        
        # Получаем задачу из БД
        # Используем глобальный экземпляр db из context.bot_data
        if 'db' in context.bot_data:
            db = context.bot_data['db']
        else:
            from database import Database
            db = Database()
        task = db.get_custom_task(task_id)
        
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return -1
        
        text = (
            f"✅ **ЗАВЕРШЕНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Задача: **{task['title']}**\n\n"
            f"Шаг 1/2: Результат выполнения\n\n"
            f"Опишите результат выполнения задачи (или отправьте /skip для пропуска):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_complete_result"),
            InlineKeyboardButton("⚡ Быстро завершить", callback_data="complete_fast")
        ]])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return COMPLETE_RESULT
    except Exception as e:
        logger.error(f"Ошибка в start_complete_task: {e}", exc_info=True)
        return -1


async def receive_complete_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение результата выполнения задачи"""
    try:
        result_text = update.message.text.strip()
        
        if len(result_text) > 1000:
            await update.message.reply_text("❌ Текст результата слишком длинный (максимум 1000 символов). Попробуйте снова:")
            return COMPLETE_RESULT
        
        context.user_data['completing_result'] = result_text
        logger.info(f"Результат выполнения получен: {result_text[:50]}...")
        
        task_id = context.user_data.get('completing_task_id')
        
        text = (
            f"✅ **ЗАВЕРШЕНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Шаг 2/2: Фото результата (опционально)\n\n"
            f"Отправьте фото результата выполнения задачи (или отправьте /skip для пропуска):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_complete_photo"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_complete_task")
        ]])
        
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return COMPLETE_PHOTO
    except Exception as e:
        logger.error(f"Ошибка в receive_complete_result: {e}", exc_info=True)
        return -1


async def skip_complete_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск результата выполнения"""
    try:
        context.user_data['completing_result'] = ""
        logger.info("Результат выполнения пропущен")
        
        query = update.callback_query
        task_id = context.user_data.get('completing_task_id')
        
        text = (
            f"✅ **ЗАВЕРШЕНИЕ ЗАДАЧИ #{task_id}**\n\n"
            f"Шаг 2/2: Фото результата (опционально)\n\n"
            f"Отправьте фото результата выполнения задачи (или отправьте /skip для пропуска):"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_complete_photo"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_complete_task")
        ]])
        
        if query:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        return COMPLETE_PHOTO
    except Exception as e:
        logger.error(f"Ошибка в skip_complete_result: {e}", exc_info=True)
        return -1


async def receive_complete_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение фото результата и завершение задачи"""
    try:
        if update.message.photo:
            # Получаем самое большое фото
            photo = update.message.photo[-1]
            photo_file_id = photo.file_id
            context.user_data['completing_photo'] = photo_file_id
            logger.info(f"Фото результата получено: {photo_file_id}")
        else:
            context.user_data['completing_photo'] = None
        
        # Завершаем задачу
        task_id = context.user_data.get('completing_task_id')
        result_text = context.user_data.get('completing_result', '')
        photo_file_id = context.user_data.get('completing_photo')
        
        # Обновляем задачу в БД
        # Используем глобальный экземпляр db из context.bot_data
        from datetime import datetime
        if 'db' in context.bot_data:
            db = context.bot_data['db']
        else:
            from database import Database
            db = Database()
        db.update_custom_task(
            task_id,
            status='completed',
            completed_at=datetime.now().isoformat(),
            result_text=result_text if result_text else None,
            result_photo=photo_file_id if photo_file_id else None
        )
        
        task = db.get_custom_task(task_id)
        
        text = (
            f"✅ **ЗАДАЧА ЗАВЕРШЕНА!**\n\n"
            f"📝 Задача: {task['title']}\n"
            f"📄 Результат: {result_text if result_text else 'Не указан'}\n"
            f"📸 Фото: {'Прикреплено' if photo_file_id else 'Не прикреплено'}\n\n"
            f"ID задачи: #{task_id}"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 К задачам", callback_data="menu_view_tasks")
        ]])
        
        # Если есть фото, отправляем его вместе с текстом
        if photo_file_id:
            await update.message.reply_photo(
                photo=photo_file_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        # Очищаем данные
        context.user_data.pop('completing_task_id', None)
        context.user_data.pop('completing_result', None)
        context.user_data.pop('completing_photo', None)
        
        logger.info(f"Задача #{task_id} завершена с результатом")
        return -1  # Завершаем диалог
        
    except Exception as e:
        logger.error(f"Ошибка в receive_complete_photo: {e}", exc_info=True)
        return -1


async def skip_complete_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск фото и завершение задачи"""
    try:
        query = update.callback_query
        
        # Завершаем задачу без фото
        task_id = context.user_data.get('completing_task_id')
        result_text = context.user_data.get('completing_result', '')
        
        # Обновляем задачу в БД
        # Используем глобальный экземпляр db из context.bot_data
        from datetime import datetime
        if 'db' in context.bot_data:
            db = context.bot_data['db']
        else:
            from database import Database
            db = Database()
        db.update_custom_task(
            task_id,
            status='completed',
            completed_at=datetime.now().isoformat(),
            result_text=result_text if result_text else None,
            result_photo=None
        )
        
        task = db.get_custom_task(task_id)
        
        text = (
            f"✅ **ЗАДАЧА ЗАВЕРШЕНА!**\n\n"
            f"📝 Задача: {task['title']}\n"
            f"📄 Результат: {result_text if result_text else 'Не указан'}\n\n"
            f"ID задачи: #{task_id}"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 К задачам", callback_data="menu_view_tasks")
        ]])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        await query.answer("✅ Задача успешно завершена!")
        
        # Очищаем данные
        context.user_data.pop('completing_task_id', None)
        context.user_data.pop('completing_result', None)
        context.user_data.pop('completing_photo', None)
        
        logger.info(f"Задача #{task_id} завершена без фото")
        return -1  # Завершаем диалог
        
    except Exception as e:
        logger.error(f"Ошибка в skip_complete_photo: {e}", exc_info=True)
        return -1


async def complete_fast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Быстрое завершение задачи без формы"""
    try:
        query = update.callback_query
        # Извлекаем task_id из callback_data или из context
        if query and query.data.startswith("task_complete_fast_"):
            task_id = int(query.data.split("_")[-1])
        else:
            task_id = context.user_data.get('completing_task_id')
        
        if not task_id:
            if query:
                await query.answer("❌ Ошибка: ID задачи не найден", show_alert=True)
            return -1
        
        # Обновляем задачу в БД
        # Используем глобальный экземпляр db из context.bot_data
        from datetime import datetime
        if 'db' in context.bot_data:
            db = context.bot_data['db']
        else:
            from database import Database
            db = Database()
        db.update_custom_task(
            task_id,
            status='completed',
            completed_at=datetime.now().isoformat()
        )
        
        task = db.get_custom_task(task_id)
        
        text = (
            f"✅ **ЗАДАЧА ЗАВЕРШЕНА!**\n\n"
            f"📝 Задача: {task['title']}\n\n"
            f"Статус изменен на 'Завершена'\n\n"
            f"ID задачи: #{task_id}"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 К задачам", callback_data="menu_view_tasks")
        ]])
        
        if query:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
            await query.answer("✅ Задача успешно завершена!")
        
        # Очищаем данные
        context.user_data.pop('completing_task_id', None)
        context.user_data.pop('completing_result', None)
        context.user_data.pop('completing_photo', None)
        
        logger.info(f"Задача #{task_id} быстро завершена")
        return -1  # Завершаем диалог
        
    except Exception as e:
        logger.error(f"Ошибка в complete_fast: {e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.answer("❌ Произошла ошибка", show_alert=True)
        return -1


async def cancel_complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена завершения задачи"""
    try:
        task_id = context.user_data.pop('completing_task_id', None)
        context.user_data.pop('completing_result', None)
        context.user_data.pop('completing_photo', None)
        
        text = "❌ Завершение задачи отменено."
        
        if task_id:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К задаче", callback_data=f"task_view_{task_id}")
            ]])
        else:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 В главное меню", callback_data="menu_main")
            ]])
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
            await update.callback_query.answer("Завершение отменено")
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard)
        
        logger.info("Завершение задачи отменено пользователем")
        return -1  # Завершаем диалог
    except Exception as e:
        logger.error(f"Ошибка в cancel_complete_task: {e}", exc_info=True)
        return -1

