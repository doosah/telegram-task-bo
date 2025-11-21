"""
МОДУЛЬ ДЛЯ РАБОТЫ С МЕНЮ
Создает и обрабатывает Inline Keyboard меню
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)

# Экспортируем get_testing_menu для использования в handlers.py
__all__ = [
    'get_main_menu', 'get_testing_menu', 'get_tasks_menu', 
    'get_task_actions_menu', 'get_confirm_menu', 'get_assignee_menu',
    'get_presence_menu', 'get_delay_time_menu', 'get_delay_minutes_menu'
]


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    keyboard = [
        [
            InlineKeyboardButton("📝 Создать задачу", callback_data="menu_create_task")
        ],
        [
            InlineKeyboardButton("🧪 Тестирование", callback_data="menu_testing"),
            InlineKeyboardButton("❓ Помощь", callback_data="menu_help")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_testing_menu() -> InlineKeyboardMarkup:
    """Меню тестирования"""
    keyboard = [
        [
            InlineKeyboardButton("📋 Ежедневные задачи", callback_data="test_daily_tasks")
        ],
        [
            InlineKeyboardButton("🔙 Назад в меню", callback_data="menu_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_tasks_menu(tasks: list) -> InlineKeyboardMarkup:
    """Меню со списком задач"""
    keyboard = []
    
    for task in tasks[:10]:  # Ограничиваем до 10 задач
        task_id = task.get('task_id', 0)
        title = task.get('title', 'Без названия')[:25]  # Ограничиваем длину
        status = task.get('status', 'active')
        
        status_emoji = "✅" if status == "completed" else "⏳" if status == "in_progress" else "⚪"
        button_text = f"{status_emoji} {title}"
        
        # Валидация callback_data (Telegram ограничивает до 64 байт)
        callback_data = f"task_view_{task_id}"
        if len(callback_data.encode('utf-8')) > 64:
            logger.warning(f"callback_data слишком длинный для задачи {task_id}, пропускаем")
            continue
        
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=callback_data)
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад в меню", callback_data="menu_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_task_actions_menu(task_id: int) -> InlineKeyboardMarkup:
    """Меню действий с задачей"""
    # Валидация callback_data для всех кнопок
    buttons = []
    
    edit_callback = f"task_edit_{task_id}"
    delete_callback = f"task_delete_{task_id}"
    complete_callback = f"task_complete_{task_id}"
    share_callback = f"task_share_{task_id}"
    
    # Проверяем длину каждого callback_data
    max_callback_len = 64
    if len(edit_callback.encode('utf-8')) <= max_callback_len:
        buttons.append([
            InlineKeyboardButton("✏️ Редактировать", callback_data=edit_callback),
            InlineKeyboardButton("🗑️ Удалить", callback_data=delete_callback)
        ])
    
    if len(complete_callback.encode('utf-8')) <= max_callback_len:
        row = [
            InlineKeyboardButton("✅ Завершить", callback_data=complete_callback)
        ]
        if len(share_callback.encode('utf-8')) <= max_callback_len:
            row.append(InlineKeyboardButton("📤 Поделиться", callback_data=share_callback))
        buttons.append(row)
    
    buttons.append([
        InlineKeyboardButton("🔙 Назад к задачам", callback_data="menu_view_tasks")
    ])
    
    return InlineKeyboardMarkup(buttons)


def get_confirm_menu(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Меню подтверждения действия"""
    # Валидация callback_data
    confirm_callback = f"confirm_{action}_{item_id}"
    cancel_callback = f"cancel_{action}_{item_id}"
    
    max_callback_len = 64
    buttons = []
    
    if len(confirm_callback.encode('utf-8')) <= max_callback_len and len(cancel_callback.encode('utf-8')) <= max_callback_len:
        buttons.append([
            InlineKeyboardButton("✅ Да, подтвердить", callback_data=confirm_callback),
            InlineKeyboardButton("❌ Отмена", callback_data=cancel_callback)
        ])
    else:
        logger.warning(f"callback_data слишком длинный для подтверждения действия {action}_{item_id}")
        buttons.append([
            InlineKeyboardButton("❌ Ошибка: слишком длинный ID", callback_data="menu_main")
        ])
    
    return InlineKeyboardMarkup(buttons)


def get_assignee_menu() -> InlineKeyboardMarkup:
    """Меню выбора исполнителя"""
    keyboard = [
        [
            InlineKeyboardButton("👤 Lysenko Alexander", callback_data="assignee_AG"),
            InlineKeyboardButton("👤 Ruslan Cherenkov", callback_data="assignee_KA")
        ],
        [
            InlineKeyboardButton("👥 Все", callback_data="assignee_all")
        ],
        [
            InlineKeyboardButton("🔙 Отмена", callback_data="menu_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_presence_menu() -> InlineKeyboardMarkup:
    """Меню отметки присутствия (07:50)"""
    keyboard = [
        [
            InlineKeyboardButton("✅ На рабочем месте", callback_data="presence_here")
        ],
        [
            InlineKeyboardButton("⏰ Опаздываю", callback_data="presence_late")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_delay_time_menu() -> InlineKeyboardMarkup:
    """Меню выбора времени опоздания (часы)"""
    keyboard = []
    row = []
    for hour in range(0, 3):  # 0, 1, 2 часа
        row.append(InlineKeyboardButton(f"{hour}ч", callback_data=f"delay_hour_{hour}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("🔙 Отмена", callback_data="presence_cancel")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_delay_minutes_menu(hour: int) -> InlineKeyboardMarkup:
    """Меню выбора минут опоздания"""
    keyboard = []
    row = []
    for minute in [0, 15, 30, 45]:
        row.append(InlineKeyboardButton(f"{minute}м", callback_data=f"delay_minute_{hour}_{minute}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="presence_late")
    ])
    
    return InlineKeyboardMarkup(keyboard)

