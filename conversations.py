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
(WORK_RESULT, WORK_PHOTO) = range(11, 13)  # Состояния для работы с задачей


async def start_create_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания задачи - запрос названия"""
    try:
        user = update.effective_user
        logger.info(f"Начало создания задачи пользователем @{user.username}")
        
        context.user_data['creating_task'] = {}
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 1/5: Название задачи\n\n"
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
        if not update.message or not update.message.text:
            logger.error("Нет сообщения или текста в receive_title")
            return -1
        
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
        if not update.message or not update.message.text:
            logger.error("Нет сообщения или текста в receive_description")
            return -1
        
        description = update.message.text.strip()
        
        if len(description) > 500:
            await update.message.reply_text("❌ Описание слишком длинное (максимум 500 символов). Попробуйте снова:")
            return DESCRIPTION
        
        context.user_data['creating_task']['description'] = description
        logger.info(f"Описание задачи получено: {description[:50]}...")
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 3/5: Выбор исполнителя\n\n"
            "Выберите исполнителя задачи:"
        )
        
        keyboard = get_assignee_menu()
        
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return ASSIGNEE
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
        if not update.message or not update.message.text:
            logger.error("Нет сообщения или текста в receive_deadline")
            return -1
        
        deadline_str = update.message.text.strip()
        
        # Парсим дату в различных форматах
        deadline_parsed = None
        
        # Формат: "сегодня до 15:00" или "сегодня до 3:00 PM"
        if "сегодня" in deadline_str.lower() or "today" in deadline_str.lower():
            today = datetime.now()
            # Ищем время после "до"
            if "до" in deadline_str.lower() or "до" in deadline_str:
                time_part = deadline_str.split("до")[-1].strip()
                try:
                    # Пробуем разные форматы времени
                    if ":" in time_part:
                        hour, minute = time_part.split(":")[:2]
                        hour = int(hour.strip())
                        minute = int(minute.strip().split()[0] if " " in minute else minute.strip())
                        deadline_parsed = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        deadline_str = f"сегодня до {hour:02d}:{minute:02d}"
                    else:
                        hour = int(time_part.strip().split()[0])
                        deadline_parsed = today.replace(hour=hour, minute=0, second=0, microsecond=0)
                        deadline_str = f"сегодня до {hour:02d}:00"
                except:
                    deadline_str = f"сегодня до {time_part}"
            else:
                deadline_str = "сегодня"
        
        # Формат: ДД.ММ.ГГГГ ЧЧ:ММ или ДД.ММ.ГГГГ
        if not deadline_parsed:
            try:
                if " " in deadline_str:
                    deadline_parsed = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
                else:
                    deadline_parsed = datetime.strptime(deadline_str, "%d.%m.%Y")
            except ValueError:
                # Если не удалось распарсить, просто сохраняем как есть
                pass
        
        context.user_data['creating_task']['deadline'] = deadline_str
        logger.info(f"Срок выполнения получен: {deadline_str}")
        
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
        if not update.callback_query or not update.callback_query.data:
            logger.error("Нет callback_query или data в receive_assignee")
            return -1
        
        parts = update.callback_query.data.split("_")
        if len(parts) < 2:
            await update.callback_query.answer("❌ Неверный формат данных", show_alert=True)
            return ASSIGNEE
        
        assignee = parts[1]
        
        if assignee not in ["AG", "KA", "SA", "all"]:
            await update.callback_query.answer("❌ Неверный выбор исполнителя", show_alert=True)
            return ASSIGNEE
        
        context.user_data['creating_task']['assignee'] = assignee
        await update.callback_query.answer("✅ Исполнитель выбран")
        
        text = (
            "📝 **СОЗДАНИЕ НОВОЙ ЗАДАЧИ**\n\n"
            "Шаг 4/5: Дата и время выполнения\n\n"
            "Введите дату и время:\n"
            "• ДД.ММ.ГГГГ ЧЧ:ММ (например, 25.12.2024 14:30)\n"
            "• ДД.ММ.ГГГГ (только дата)\n"
            "• сегодня до 15:00\n"
            "• сегодня до 3:00 PM\n\n"
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
            
            # Отправляем задачу в группу
            try:
                chat_id = context.bot_data.get('CHAT_ID')
                if not chat_id:
                    # Пытаемся получить из переменных окружения
                    import os
                    chat_id = os.getenv('CHAT_ID', '').strip()
                
                if chat_id:
                    chat_id = int(chat_id) if isinstance(chat_id, str) else chat_id
                    
                    # Формируем сообщение для группы
                    group_text = (
                        f"📋 **НОВАЯ ЗАДАЧА #{task_id}**\n\n"
                        f"📝 **{title}**\n"
                        f"📄 {description if description else 'Без описания'}\n"
                        f"⏰ Срок: {deadline if deadline else 'Не указан'}\n"
                        f"👤 Исполнитель: {assignee_names.get(assignee, assignee)}\n"
                        f"👨‍💼 Создатель: @{creator}"
                    )
                    
                    # Создаем простые кнопки: "Взять в работу" и "Готово"
                    work_buttons = []
                    if assignee == "all":
                        # Если исполнитель "Все", показываем кнопки для всех
                        work_buttons = [
                            [InlineKeyboardButton("👤 АГ - Взять в работу", callback_data=f"work_take_{task_id}_AG")],
                            [InlineKeyboardButton("✅ АГ - Готово", callback_data=f"work_done_{task_id}_AG")],
                            [InlineKeyboardButton("👤 КА - Взять в работу", callback_data=f"work_take_{task_id}_KA")],
                            [InlineKeyboardButton("✅ КА - Готово", callback_data=f"work_done_{task_id}_KA")],
                            [InlineKeyboardButton("👤 СА - Взять в работу", callback_data=f"work_take_{task_id}_SA")],
                            [InlineKeyboardButton("✅ СА - Готово", callback_data=f"work_done_{task_id}_SA")]
                        ]
                    else:
                        # Если конкретный исполнитель, показываем две кнопки
                        assignee_full = assignee_names.get(assignee, assignee)
                        work_buttons = [
                            [InlineKeyboardButton(f"👤 {assignee_full} - Взять в работу", callback_data=f"work_take_{task_id}_{assignee}")],
                            [InlineKeyboardButton(f"✅ {assignee_full} - Готово", callback_data=f"work_done_{task_id}_{assignee}")]
                        ]
                    
                    work_keyboard = InlineKeyboardMarkup(work_buttons)
                    
                    # Отправляем в группу
                    if photo:
                        # Если есть фото, отправляем с фото
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=group_text,
                            reply_markup=work_keyboard,
                            parse_mode='Markdown'
                        )
                    else:
                        # Если нет фото, отправляем просто текст
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=group_text,
                            reply_markup=work_keyboard,
                            parse_mode='Markdown'
                        )
                    logger.info(f"Задача #{task_id} отправлена в группу {chat_id} с кнопками 'Взять в работу'")
            except Exception as e:
                logger.error(f"Ошибка отправки задачи в группу: {e}", exc_info=True)
                # Не прерываем процесс, просто логируем ошибку
            
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
        try:
            task_id = int(query.data.split("_")[-1])
        except (ValueError, IndexError):
            await query.answer("❌ Ошибка формата ID задачи", show_alert=True)
            return -1
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
        if not update.message or not update.message.text:
            logger.error("Нет сообщения или текста в receive_edit_title")
            return -1
        
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
        if not update.message or not update.message.text:
            logger.error("Нет сообщения или текста в receive_edit_description")
            return -1
        
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
        if not update.message or not update.message.text:
            logger.error("Нет сообщения или текста в receive_edit_deadline")
            return -1
        
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
        if not update.callback_query or not update.callback_query.data:
            logger.error("Нет callback_query или data в receive_edit_assignee")
            return -1
        
        parts = update.callback_query.data.split("_")
        if len(parts) < 2:
            await update.callback_query.answer("❌ Неверный формат данных", show_alert=True)
            return EDIT_ASSIGNEE
        
        assignee = parts[1]
        
        if assignee not in ["AG", "KA", "SA", "all"]:
            await update.callback_query.answer("❌ Неверный выбор исполнителя", show_alert=True)
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
        try:
            task_id = int(query.data.split("_")[-1])
        except (ValueError, IndexError):
            await query.answer("❌ Ошибка формата ID задачи", show_alert=True)
            return -1
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
        if not update.message or not update.message.text:
            logger.error("Нет сообщения или текста в receive_complete_result")
            return -1
        
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
            try:
                task_id = int(query.data.split("_")[-1])
            except (ValueError, IndexError):
                if query:
                    await query.answer("❌ Ошибка формата ID задачи", show_alert=True)
                return -1
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


# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАДАЧЕЙ (ВЗЯТЬ В РАБОТУ) ==========

async def start_work_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с задачей - показываем описание и кнопку 'Выполнена работа'"""
    try:
        query = update.callback_query
        if not query:
            return -1
        
        # Извлекаем task_id и assignee из callback_data: work_task_{task_id}_{assignee}
        parts = query.data.split("_")
        if len(parts) < 4:
            await query.answer("❌ Неверный формат", show_alert=True)
            return -1
        
        try:
            task_id = int(parts[2])
            assignee = parts[3]
            if assignee not in ["AG", "KA", "SA"]:
                await query.answer("❌ Неверный исполнитель", show_alert=True)
                return -1
        except (ValueError, IndexError):
            await query.answer("❌ Ошибка формата данных", show_alert=True)
            return -1
        
        # Получаем задачу из БД
        if 'db' in context.bot_data:
            db = context.bot_data['db']
        else:
            from database import Database
            db = Database()
        
        task = db.get_custom_task(task_id)
        if not task:
            await query.answer("❌ Задача не найдена", show_alert=True)
            return -1
        
        # Сохраняем данные в context
        context.user_data['working_task_id'] = task_id
        context.user_data['working_assignee'] = assignee
        
        # Формируем текст с описанием задачи
        text = (
            f"📋 **ЗАДАЧА #{task_id}**\n\n"
            f"📝 **{task['title']}**\n\n"
            f"📄 **Описание:**\n{task.get('description', 'Нет описания')}\n\n"
            f"⏰ Срок: {task.get('deadline', 'Не указан')}\n"
            f"👤 Исполнитель: {task.get('assignee', 'Не назначен')}\n\n"
            f"Нажмите кнопку 'Выполнена работа' для продолжения:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Выполнена работа", callback_data="work_done")
        ], [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_work_task")
        ]])
        
        await query.answer()
        
        # Проверяем, это сообщение из группы или личное
        if query.message and query.message.chat.type in ['group', 'supergroup']:
            # Это группа - отправляем в личные сообщения
            try:
                user = query.from_user
                await context.bot.send_message(
                    chat_id=user.id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                await query.answer("✅ Информация отправлена в личные сообщения")
            except Exception as e:
                logger.error(f"Ошибка отправки в личные сообщения: {e}", exc_info=True)
                await query.answer("❌ Не удалось отправить. Напишите боту в личные сообщения.")
        else:
            # Это личное сообщение - редактируем
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        logger.info(f"Начало работы с задачей #{task_id} для исполнителя {assignee}")
        # Возвращаем -1, так как кнопка "work_done" будет обработана через entry_points
        return -1
        
    except Exception as e:
        logger.error(f"Ошибка в start_work_task: {e}", exc_info=True)
        if query:
            await query.answer("❌ Произошла ошибка", show_alert=True)
        return -1


async def work_done_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка кнопки 'Выполнена работа' - запрос текста результата"""
    try:
        query = update.callback_query
        await query.answer()
        
        text = (
            "📝 **ВЫПОЛНЕНА РАБОТА**\n\n"
            "Введите текст 'Выполнена работа' или опишите результат:\n\n"
            "Или нажмите кнопку для пропуска:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить текст", callback_data="skip_work_result")
        ], [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_work_task")
        ]])
        
        # Проверяем, это сообщение из группы или личное
        if query.message and query.message.chat.type in ['group', 'supergroup']:
            # Это группа - отправляем в личные сообщения
            try:
                user = query.from_user
                await context.bot.send_message(
                    chat_id=user.id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                await query.answer("✅ Информация отправлена в личные сообщения")
            except Exception as e:
                logger.error(f"Ошибка отправки в личные сообщения: {e}", exc_info=True)
                await query.answer("❌ Не удалось отправить. Напишите боту в личные сообщения.")
        else:
            # Это личное сообщение - редактируем
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        return WORK_RESULT
        
    except Exception as e:
        logger.error(f"Ошибка в work_done_button: {e}", exc_info=True)
        return -1


async def receive_work_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение текста 'Выполнена работа' - переход к прикреплению материалов"""
    try:
        if not update.message or not update.message.text:
            logger.error("Нет сообщения или текста в receive_work_result")
            return -1
        
        # Пользователь ввел текст
        result_text = update.message.text.strip()
        if not result_text:
            await update.message.reply_text("❌ Текст не может быть пустым. Попробуйте снова:")
            return WORK_RESULT
        
        context.user_data['working_result'] = result_text
        
        text = (
            "📎 **ПРИКРЕПИТЬ МАТЕРИАЛЫ**\n\n"
            "Отправьте фото или видео материалы:\n\n"
            "Или нажмите кнопку для пропуска:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить материалы", callback_data="skip_work_photo")
        ], [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_work_task")
        ]])
        
        # Отправляем в личные сообщения пользователю
        user = update.effective_user
        user_id = user.id if user else None
        
        if user_id:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        return WORK_PHOTO
        
    except Exception as e:
        logger.error(f"Ошибка в receive_work_result: {e}", exc_info=True)
        return -1


async def skip_work_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск текста результата - переход к материалам"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Устанавливаем дефолтный текст
        context.user_data['working_result'] = 'Выполнена работа'
        
        text = (
            "📎 **ПРИКРЕПИТЬ МАТЕРИАЛЫ**\n\n"
            "Отправьте фото или видео материалы:\n\n"
            "Или нажмите кнопку для пропуска:"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Пропустить материалы", callback_data="skip_work_photo")
        ], [
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_work_task")
        ]])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        return WORK_PHOTO
        
    except Exception as e:
        logger.error(f"Ошибка в skip_work_result: {e}", exc_info=True)
        return -1


async def receive_work_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение фото/видео материалов - завершение работы"""
    try:
        task_id = context.user_data.get('working_task_id')
        result_text = context.user_data.get('working_result', 'Выполнена работа')
        
        # Получаем фото/видео
        photo_file_id = None
        if update.message.photo:
            photo_file_id = update.message.photo[-1].file_id
        elif update.message.video:
            photo_file_id = update.message.video.file_id
        elif update.message.document:
            photo_file_id = update.message.document.file_id
        
        # Обновляем задачу в БД
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
            result_text=result_text,
            result_photo=photo_file_id if photo_file_id else None
        )
        
        task = db.get_custom_task(task_id)
        user = update.effective_user
        username = user.username if user.username else f"user_{user.id}"
        
        # Отправляем уведомление администратору с результатом и материалами
        try:
            # Получаем admin_id
            admin_id = None
            if 'admin_id' in context.bot_data:
                admin_id = context.bot_data['admin_id']
            else:
                # Пытаемся получить из БД
                admin_username = context.bot_data.get('ADMIN_USERNAME')
                if not admin_username:
                    # Fallback: пытаемся получить из переменных окружения
                    import os
                    admin_username = os.getenv('ADMIN_USERNAME', '').strip()
                
                if admin_username:
                    admin_id = db.get_user_id_by_username(admin_username)
                    if admin_id:
                        context.bot_data['admin_id'] = admin_id
            
            if admin_id:
                admin_text = (
                    f"✅ **ЗАДАЧА ЗАВЕРШЕНА**\n\n"
                    f"📝 Задача: {task['title']}\n"
                    f"👤 Исполнитель: @{username}\n"
                    f"📄 Описание работы: {result_text}\n"
                    f"📸 Материалы: {'Прикреплены' if photo_file_id else 'Не прикреплены'}\n\n"
                    f"ID задачи: #{task_id}"
                )
                
                # Если есть фото, отправляем его администратору
                if photo_file_id:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=photo_file_id,
                        caption=admin_text,
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_text,
                        parse_mode='Markdown'
                    )
                logger.info(f"Уведомление о завершении задачи #{task_id} отправлено администратору {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления администратору: {e}", exc_info=True)
        
        # Отправляем подтверждение пользователю
        text = (
            f"✅ **ЗАДАЧА ЗАВЕРШЕНА!**\n\n"
            f"📝 Задача: {task['title']}\n"
            f"📄 Результат: {result_text}\n"
            f"📸 Материалы: {'Прикреплены' if photo_file_id else 'Не прикреплены'}\n\n"
            f"ID задачи: #{task_id}"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 В главное меню", callback_data="menu_main")
        ]])
        
        user_id = user.id if user else None
        
        if not user_id:
            logger.error("Не удалось получить user_id для отправки ответа")
            return -1
        
        # Если есть фото, отправляем его вместе с текстом в личные сообщения пользователю
        if photo_file_id:
            await context.bot.send_photo(
                chat_id=user_id,
                photo=photo_file_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        # Очищаем данные
        context.user_data.pop('working_task_id', None)
        context.user_data.pop('working_assignee', None)
        context.user_data.pop('working_result', None)
        
        logger.info(f"Задача #{task_id} завершена через 'Взять в работу', ответ отправлен в личные сообщения пользователю {user_id}")
        return -1  # Завершаем диалог
        
    except Exception as e:
        logger.error(f"Ошибка в receive_work_photo: {e}", exc_info=True)
        return -1


async def skip_work_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропуск материалов и завершение работы"""
    try:
        query = update.callback_query
        await query.answer()
        
        task_id = context.user_data.get('working_task_id')
        result_text = context.user_data.get('working_result', 'Выполнена работа')
        
        # Обновляем задачу в БД
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
            result_text=result_text,
            result_photo=None
        )
        
        task = db.get_custom_task(task_id)
        user = query.from_user
        username = user.username if user.username else f"user_{user.id}"
        
        # Отправляем уведомление администратору с результатом
        try:
            # Получаем admin_id
            admin_id = None
            if 'admin_id' in context.bot_data:
                admin_id = context.bot_data['admin_id']
            else:
                # Пытаемся получить из БД
                admin_username = context.bot_data.get('ADMIN_USERNAME')
                if not admin_username:
                    # Fallback: пытаемся получить из переменных окружения
                    import os
                    admin_username = os.getenv('ADMIN_USERNAME', '').strip()
                
                if admin_username:
                    admin_id = db.get_user_id_by_username(admin_username)
                    if admin_id:
                        context.bot_data['admin_id'] = admin_id
            
            if admin_id:
                admin_text = (
                    f"✅ **ЗАДАЧА ЗАВЕРШЕНА**\n\n"
                    f"📝 Задача: {task['title']}\n"
                    f"👤 Исполнитель: @{username}\n"
                    f"📄 Описание работы: {result_text}\n\n"
                    f"ID задачи: #{task_id}"
                )
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    parse_mode='Markdown'
                )
                logger.info(f"Уведомление о завершении задачи #{task_id} отправлено администратору {admin_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления администратору: {e}", exc_info=True)
        
        # Отправляем подтверждение пользователю
        text = (
            f"✅ **ЗАДАЧА ЗАВЕРШЕНА!**\n\n"
            f"📝 Задача: {task['title']}\n"
            f"📄 Результат: {result_text}\n\n"
            f"ID задачи: #{task_id}"
        )
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 В главное меню", callback_data="menu_main")
        ]])
        
        # Отправляем ответ в личные сообщения пользователю (не в группу)
        user_id = user.id if user else None
        
        if user_id:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                await query.answer("✅ Задача завершена! Ответ отправлен в личные сообщения.")
            except Exception as e:
                logger.error(f"Ошибка отправки ответа в личные сообщения: {e}", exc_info=True)
                await query.answer("✅ Задача завершена!")
        else:
            # Если не удалось получить user_id, редактируем сообщение
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
            await query.answer("✅ Задача успешно завершена!")
        
        # Очищаем данные
        context.user_data.pop('working_task_id', None)
        context.user_data.pop('working_assignee', None)
        context.user_data.pop('working_result', None)
        
        logger.info(f"Задача #{task_id} завершена без материалов")
        return -1  # Завершаем диалог
        
    except Exception as e:
        logger.error(f"Ошибка в skip_work_photo: {e}", exc_info=True)
        return -1


async def cancel_work_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена работы с задачей"""
    try:
        query = update.callback_query
        if query:
            await query.answer("❌ Отмена работы с задачей")
        
        text = "❌ **ОТМЕНА**\n\nРабота с задачей отменена."
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 В главное меню", callback_data="menu_main")
        ]])
        
        if query:
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')
        elif update.message:
            await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')
        
        # Очищаем данные
        context.user_data.pop('working_task_id', None)
        context.user_data.pop('working_assignee', None)
        context.user_data.pop('working_result', None)
        
        return -1
    except Exception as e:
        logger.error(f"Ошибка в cancel_work_task: {e}", exc_info=True)
        return -1

