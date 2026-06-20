"""
Celery-таски для выставок.
"""

import logging
import time
from datetime import datetime, timedelta

from celery import shared_task, chord
from celery.utils.log import get_task_logger

from ..services.show_service import (
    save_show_event,
    save_show_results,
    mark_results_parsed,
    process_pending_results,
    process_all_pending_results,
    recalculate_all_ratings,
    get_shows_needing_results,
)
from ..repositories.dog_repository import get_missing_zoo_ids
from ..parsers.zooportal_shows import fetch_show_list, fetch_show_results

logger = get_task_logger(__name__)


# Парсит список выставок за дату. Для каждой с результатами — диспатчит import_show_results_task
@shared_task(
    bind=True,
    name='dogs_module.import_show_list',
    autoretry_for=(ConnectionError, TimeoutError, RuntimeError),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def import_show_list_task(self, date_str: str) -> dict:
    start = time.time()
    try:
        shows = fetch_show_list(date_str)
    except Exception as e:
        logger.error(f"import_show_list_task: ошибка за {date_str}: {e}")
        return {'status': 'error', 'error': str(e), 'date': date_str}

    if not shows:
        return {'status': 'success', 'found': 0, 'dispatched': 0, 'date': date_str}

    dispatched = 0
    for idx, show_data in enumerate(shows):
        event = save_show_event(show_data)
        if not event:
            continue
        if 'результат' in (show_data.get('status') or '').lower():
            import_show_results_task.apply_async(
                args=[show_data['zooportal_show_id']],
                countdown=idx * 5,
            )
            dispatched += 1

    return {
        'status': 'dispatched', 'date': date_str,
        'found': len(shows), 'dispatched': dispatched,
        'elapsed': round(time.time() - start, 1),
    }


# Парсит результаты выставки. Ненайденных собак откладывает в Redis
@shared_task(
    bind=True,
    name='dogs_module.import_show_results',
    soft_time_limit=3600,
    time_limit=4200,
    autoretry_for=(ConnectionError, TimeoutError, RuntimeError),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def import_show_results_task(self, show_id: str, import_missing_dogs: bool = True) -> dict:
    start = time.time()
    from ..repositories import show_repository as show_repo
    from ..constants.show_types import ShowType

    event = show_repo.get_event_by_show_id(show_id)
    if not event:
        event, _ = show_repo.get_or_create_event(
            show_id,
            {'title': f'Show {show_id}', 'show_type': ShowType.OTHER, 'multiplier': 0},
        )

    try:
        results = fetch_show_results(show_id)
    except Exception as e:
        logger.error(f"import_show_results_task show_id={show_id}: {e}")
        return {'status': 'error', 'show_id': show_id, 'error': str(e)}

    if not results:
        return {'status': 'success', 'show_id': show_id, 'found': 0, 'saved': 0}

    saved, failed, pending_count = save_show_results(event, results)
    mark_results_parsed(event)

    dogs_dispatched = 0
    if import_missing_dogs and pending_count > 0:
        dogs_dispatched = _dispatch_missing_dogs(results)
        if dogs_dispatched > 0:
            countdown = min(max(dogs_dispatched * 30, 120), 900)
            process_pending_results_task.apply_async(args=[show_id], countdown=countdown)

    return {
        'status': 'success', 'show_id': show_id,
        'found': len(results), 'saved': saved, 'pending': pending_count,
        'failed': failed, 'dogs_dispatched': dogs_dispatched,
        'elapsed': round(time.time() - start, 1),
    }


# Берёт ожидающие из Redis, сохраняет. Если остались перепланирует через 30 мин
@shared_task(bind=True, name='dogs_module.process_pending_results',
             soft_time_limit=600, time_limit=700)
def process_pending_results_task(self, show_id: str = None) -> dict:
    start = time.time()
    result = process_pending_results(show_id) if show_id else process_all_pending_results()

    if result.get('still_pending', 0) > 0:
        process_pending_results_task.apply_async(args=[show_id], countdown=60 * 10)

    return {'status': 'success', 'show_id': show_id, 'elapsed': round(time.time() - start, 1), **result}


# Обработать все ожидающие результаты по всем выставкам
@shared_task(bind=True, name='dogs_module.process_all_pending_results')
def process_all_pending_results_task(self) -> dict:
    return process_pending_results_task(show_id=None)


# Диспатчит import_show_list_task для каждой даты в диапазоне
@shared_task(bind=True, name='dogs_module.import_show_date_range')
def import_show_date_range_task(self, date_from: str, date_to: str, countdown_between: int = 10) -> dict:
    try:
        dt_from = datetime.strptime(date_from, '%d.%m.%Y')
        dt_to = datetime.strptime(date_to, '%d.%m.%Y')
    except ValueError as e:
        return {'status': 'error', 'error': f'Неверный формат даты: {e}'}

    dispatched = []
    dt, idx = dt_from, 0
    while dt <= dt_to:
        date_str = dt.strftime('%d.%m.%Y')
        task = import_show_list_task.apply_async(args=[date_str], countdown=idx * countdown_between)
        dispatched.append({'date': date_str, 'task_id': task.id})
        dt += timedelta(days=1)
        idx += 1

    return {'status': 'dispatched', 'date_from': date_from, 'date_to': date_to,
            'days': len(dispatched), 'dispatched': dispatched}


# Находит ShowEvent в БД за период и диспатчит import_show_results_task для каждой выставки без результатов
@shared_task(bind=True, name='dogs_module.import_results_for_date_range',
             soft_time_limit=60, time_limit=120)  # диспетчер — завершается быстро
def import_results_for_date_range_task(
        self, date_from: str, date_to: str = None,
        only_without_results: bool = True, import_missing_dogs: bool = True,
) -> dict:
    if not date_to:
        date_to = date_from
    try:
        dt_from = datetime.strptime(date_from, '%d.%m.%Y').date()
        dt_to = datetime.strptime(date_to, '%d.%m.%Y').date()
    except ValueError as e:
        return {'status': 'error', 'error': f'Неверный формат даты: {e}'}

    from ..repositories import show_repository as show_repo
    events = show_repo.get_events_in_range(
        dt_from, dt_to, only_without_results=only_without_results
    )

    if not events:
        return {
            'status': 'success',
            'message': f'Нет выставок без результатов за {date_from}–{date_to}',
        }

    dispatched = 0
    for idx, event in enumerate(events):
        import_show_results_task.apply_async(
            args=[event.zooportal_show_id],
            kwargs={'import_missing_dogs': import_missing_dogs},
            countdown=idx * 5,  # небольшой разброс чтобы не навалить сразу
        )
        dispatched += 1

    logger.info(f"📋 Диспатчено {dispatched} выставок за {date_from}–{date_to}")
    return {
        'status': 'dispatched',
        'period': f'{date_from}–{date_to}',
        'events_found': len(events),
        'dispatched': dispatched,
    }


@shared_task(bind=True, name='dogs_module.import_shows_full',
             soft_time_limit=60, time_limit=120)
def import_shows_full_task(self, date_from: str, date_to: str = None) -> dict:
    if not date_to:
        date_to = date_from
    try:
        dt_from = datetime.strptime(date_from, '%d.%m.%Y')
        dt_to = datetime.strptime(date_to, '%d.%m.%Y')
    except ValueError as e:
        return {'status': 'error', 'error': f'Неверный формат даты: {e}'}

    days = (dt_to - dt_from).days + 1

    dt = dt_from
    for idx in range(days):
        import_show_list_task.apply_async(
            args=[dt.strftime('%d.%m.%Y')],
            countdown=idx * 10,
        )
        dt += timedelta(days=1)

    results_countdown = days * 75
    import_results_for_date_range_task.apply_async(
        kwargs={
            'date_from': date_from,
            'date_to': date_to,
            'only_without_results': True,
            'import_missing_dogs': True,
        },
        countdown=results_countdown,
    )

    return {
        'status': 'dispatched',
        'days': days,
        'results_in_seconds': results_countdown,
    }


# Линкует ожидающие результаты (собаки теперь импортированы), Пересчитывает рейтинг
@shared_task(bind=True, name='dogs_module.finalize_shows',
             soft_time_limit=1200, time_limit=1500)
def finalize_shows_task(self, show_ids: list) -> dict:
    start = time.time()
    logger.info(f"🔗 finalize_shows: {len(show_ids)} выставок")

    total_saved = total_left = 0
    for show_id in show_ids:
        result = process_pending_results(show_id)
        total_saved += result.get('saved', 0)
        total_left += result.get('still_pending', 0)

    if total_left > 0:
        process_pending_results_task.apply_async(args=[None], countdown=60 * 15)
        logger.warning(f"  ⚠️ {total_left} результатов всё ещё ожидают, перепланировано")

    logger.info("📊 Пересчитываем рейтинги...")
    rating_result = recalculate_all_ratings()

    return {
        'status': 'success', 'shows_finalized': len(show_ids),
        'results_linked': total_saved, 'still_pending': total_left,
        'rating_updated': rating_result['updated'],
        'elapsed': round(time.time() - start, 1),
    }


@shared_task(bind=True, name='dogs_module.recalculate_show_ratings')
def recalculate_ratings_task(self, year: int = None) -> dict:
    result = recalculate_all_ratings(rating_year=year)
    return {'status': 'success', **result}


# Диспатчит import_zooportal_dog_task для каждой отсутствующей собаки
def _dispatch_missing_dogs(results: list) -> int:
    from ..tasks.tasks_zooportal import import_zooportal_dog_task
    zoo_ids = [r['zooportal_dog_id'] for r in results if r.get('zooportal_dog_id')]
    missing_ids = get_missing_zoo_ids(zoo_ids)
    for idx, zoo_id in enumerate(missing_ids):
        import_zooportal_dog_task.apply_async(args=[zoo_id], countdown=idx * 3)
    if missing_ids:
        logger.info(f"Диспатчен импорт {len(missing_ids)} отсутствующих собак")
    return len(missing_ids)
