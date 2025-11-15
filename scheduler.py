"""
ФАЙЛ ДЛЯ РАБОТЫ С РАСПИСАНИЕМ
Этот файл помогает настроить автоматическую отправку сообщений по времени
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz


class Scheduler:
    """Класс для управления расписанием"""
    
    def __init__(self):
        """Инициализация планировщика"""
        self.scheduler = None
        self.moscow_tz = pytz.timezone('Europe/Moscow')
    
    def get_scheduler(self) -> AsyncIOScheduler:
        """Получить планировщик"""
        if self.scheduler is None:
            self.scheduler = AsyncIOScheduler(timezone=self.moscow_tz)
        return self.scheduler
    
    def add_job(self, func, hour: int, minute: int, day_of_week: str = 'mon-fri'):
        """
        Добавить задачу в расписание
        func - функция, которую нужно выполнить
        hour - час (0-23)
        minute - минута (0-59)
        day_of_week - дни недели ('mon-fri' для пн-пт)
        """
        scheduler = self.get_scheduler()
        scheduler.add_job(
            func,
            trigger=CronTrigger(hour=hour, minute=minute, day_of_week=day_of_week),
            timezone=self.moscow_tz
        )
    
    def start(self):
        """Запустить планировщик"""
        if self.scheduler:
            self.scheduler.start()
    
    def shutdown(self):
        """Остановить планировщик"""
        if self.scheduler:
            self.scheduler.shutdown()

