# nkp_project/celery.py

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nkp_project.settings')

app = Celery('nkp_project')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.update(
    worker_pool='prefork',
    worker_pool_restarts=True,

    # Таймауты для Playwright-задач (могут идти 30-40 мин)
    task_soft_time_limit=3600,
    task_time_limit=4200,

    result_backend='redis://redis:6379/0',
    result_expires=3600,

    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    timezone='Europe/Moscow',
    enable_utc=True,

    imports=['dogs_module.tasks'],

    worker_max_tasks_per_child=50,

    # Один worker не берёт задач больше чем может обработать
    worker_prefetch_multiplier=1,

    task_track_started=True,

    # Задача подтверждается после выполнения, а не при получении
    task_acks_late=True,
)

app.autodiscover_tasks()

# Периодические задачи
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

    # 'sync-breedarchive-browse': {
    #     'task': 'dogs_module.sync_breedarchive_browse',
    #     'schedule': crontab(hour=3, minute=0, day_of_month='*/3'),
    #     'kwargs': {'recent_days': 5},
    # },
    #
    # 'weekly-show-list': {
    #     'task': 'dogs_module.weekly_show_list',
    #     'schedule': crontab(hour=2, minute=0, day_of_week=1),  # каждый понедельник в 2:00
    # },
    #
    # 'weekly-show-results': {
    #     'task': 'dogs_module.weekly_show_results',
    #     'schedule': crontab(hour=3, minute=0, day_of_week=1),  # каждый понедельник в 3:00
    # },
    #
    # 'weekly-recalculate-ratings-task': {
    #     'task': 'dogs_module.weekly_recalculate_ratings_task',
    #     'schedule': crontab(hour=5, minute=0, day_of_week=1),  # каждый понедельник в 5:00
    # },

}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
