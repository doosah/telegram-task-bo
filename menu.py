"""
МОДУЛЬ ДЛЯ РАБОТЫ С МЕНЮ
Создает и обрабатывает Inline Keyboard меню
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    keyboard = [
        [
            InlineKeyboardButton("📝 Создать задачу", callback_data="menu_create_task"),
            InlineKeyboardButton("📋 Просмотреть задачи", callback_data="menu_view_tasks")
        ],
        [
            InlineKeyboardButton("✅ Завершить задачу", callback_data="menu_complete_task"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings")
        ],
        [
            InlineKeyboardButton("❓ Помощь", callback_data="menu_help"),
            InlineKeyboardButton("🔙 Назад", callback_data="menu_back")
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
        
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"task_view_{task_id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад в меню", callback_data="menu_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_task_actions_menu(task_id: int) -> InlineKeyboardMarkup:
    """Меню действий с задачей"""
    keyboard = [
        [
            InlineKeyboardButton("✏️ Редактировать", callback_data=f"task_edit_{task_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"task_delete_{task_id}")
        ],
        [
            InlineKeyboardButton("✅ Завершить", callback_data=f"task_complete_{task_id}"),
            InlineKeyboardButton("📤 Поделиться", callback_data=f"task_share_{task_id}")
        ],
        [
            InlineKeyboardButton("🔙 Назад к задачам", callback_data="menu_view_tasks")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_menu(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Меню подтверждения действия"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, подтвердить", callback_data=f"confirm_{action}_{item_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_{action}_{item_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_assignee_menu() -> InlineKeyboardMarkup:
    """Меню выбора исполнителя"""
    keyboard = [
        [
            InlineKeyboardButton("👤 АГ (alex301182)", callback_data="assignee_AG"),
            InlineKeyboardButton("👤 КА (Korudirp)", callback_data="assignee_KA")
        ],
        [
            InlineKeyboardButton("👤 СА (sanya_hui_sosi1488)", callback_data="assignee_SA"),
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

