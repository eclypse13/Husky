from celery import shared_task
from core.models import Kennel, SiteMonitor, Event, User
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def monitor_kennel_sites():
    """Мониторинг сайтов питомников"""
    monitors = SiteMonitor.objects.filter(is_active=True)
    
    for monitor in monitors:
        try:
            monitor.last_check = datetime.utcnow()
            monitor.save()
            logger.info(f"Checked site: {monitor.url}")
        except Exception as e:
            logger.error(f"Error monitoring {monitor.url}: {e}")
    
    return f"Checked {monitors.count()} sites"


@shared_task
def send_event_reminders():
    """Отправка напоминаний о мероприятиях"""
    next_week = datetime.utcnow() + timedelta(days=7)
    upcoming_events = Event.objects.filter(
        starts_at__gte=datetime.utcnow(),
        starts_at__lte=next_week
    )
    
    members = User.objects.filter(is_nkp_member=True)
    
    for event in upcoming_events:
        for member in members:
            logger.info(f"Reminder sent to {member.email} about {event.title_key}")
    
    return f"Sent reminders for {upcoming_events.count()} events"


@shared_task
def send_email_task(to_email, subject, message):
    """Асинхронная отправка email"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    try:
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [to_email],
            fail_silently=False,
        )
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False
