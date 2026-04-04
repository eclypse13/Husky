# nkp_project/celery.py

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nkp_project.settings')

app = Celery('nkp_project')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.update(
    # Пул
    worker_pool='prefork',
    worker_pool_restarts=True,

    # Таймауты — увеличены для рекурсивного парсинга с предками
    # Одна страница (10 собак × 3 поколения) может занимать до 30-40 мин
    task_soft_time_limit=3600,   # 60 мин graceful stop
    task_time_limit=4200,        # 70 мин жёсткий kill

    # Результаты
    result_backend='redis://redis:6379/0',
    result_expires=3600,

    # Сериализация
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # Timezone
    timezone='Europe/Moscow',
    enable_utc=True,

    # Автообнаружение
    imports=['dogs_module.tasks'],

    # Память
    worker_max_memory_per_child=400000,  # (400MB — мало для Playwright)
    worker_max_tasks_per_child=50,       # перезапуск чаще (было 100) — чистим память

    # Prefetch = 1: воркер берёт следующую задачу только закончив текущую
    # Важно для длинных задач парсинга — не копим очередь в одном воркере
    worker_prefetch_multiplier=1,

    task_track_started=True,
)

app.autodiscover_tasks()

# ══════════════════════════════════════════════════════════════════════════════
# ПЕРИОДИЧЕСКИЕ ЗАДАЧИ
# ══════════════════════════════════════════════════════════════════════════════

app.conf.beat_schedule = {

    'monitor-kennels-sites': {
        'task': 'celery_tasks.tasks.monitor_kennel_sites',
        'schedule': crontab(hour=2, minute=0),  # Каждый день в 2:00
    },

    'send-event-reminders': {
        'task': 'celery_tasks.tasks.send_event_reminders',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Каждый понедельник в 10:00
    },

    # Ежедневная синхронизация Zooportal, страницы 1-10, каждый день в 4:00
    # 'daily-zooportal-sync': {
    #     'task': 'dogs_module.daily_zooportal_sync',
    #     'schedule': crontab(hour=2, minute=0),
    #     'kwargs': {
    #         'start_page': 1,
    #         'end_page': 5,
    #         'max_dogs_per_page': 11,
    #         'generations': 3,
    #         'countdown_between_pages': 60,
    #     },
    #     'options': {
    #         'expires': 3600,  # пропустить если beat опоздал > 1ч
    #     },
    # },

    'refresh-cookies': {
        'task': 'dogs_module.refresh_cookies',
        'schedule': crontab(hour='*/20', minute=0),  # каждые 20 часов
    },

}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')