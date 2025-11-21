"""
ФАЙЛ С ЗАДАЧАМИ ПО ДНЯМ НЕДЕЛИ
Теперь задачи хранятся в БД, этот класс используется для обратной совместимости
"""


class Tasks:
    """Класс для управления задачами по дням недели (использует БД)"""
    
    def __init__(self, db=None):
        """Инициализация - сохраняем ссылку на БД"""
        self.db = db
    
    def get_tasks_for_day(self, day: int) -> list:
        """
        Получить список задач для указанного дня
        day - номер дня недели (0=понедельник, 4=пятница)
        Возвращает список текстов задач
        """
        if self.db:
            tasks = self.db.get_weekly_tasks(day)
            return [task['task_text'] for task in tasks]
        return []
    
    def add_task(self, day: int, task: str):
        """
        Добавить новую задачу для дня
        day - номер дня недели
        task - текст задачи
        """
        if self.db:
            self.db.add_weekly_task(day, task)
    
    def remove_task(self, day: int, task_index: int):
        """
        Удалить задачу
        day - номер дня недели
        task_index - номер задачи в списке (начиная с 0)
        """
        if self.db:
            tasks = self.db.get_weekly_tasks(day)
            if 0 <= task_index < len(tasks):
                task_id = tasks[task_index]['id']
                self.db.delete_weekly_task(task_id)

