# nkp_project/__init__.py
"""
Этот файл гарантирует, что Celery app загружается
при старте Django, чтобы @shared_task использовал правильный backend.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)