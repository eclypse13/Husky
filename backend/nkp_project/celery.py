import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nkp_project.settings')

app = Celery('nkp_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
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
}
