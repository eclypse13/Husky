# dogs_module/tasks/tasks_shows.py
"""
Celery-таски для выставок.
Таски — чистые оркестраторы: вызывают сервисы, диспатчат задачи, ждут.
Никакой бизнес-логики и прямых обращений к моделям.
"""

import logging
import time
from datetime import datetime, timedelta

from celery import shared_task
from celery.utils.log import get_task_logger

from ..services.show_service import (
    save_show_event,
    save_show_results,
    mark_results_parsed,
    process_pending_results,
    process_all_pending_results,
    recalculate_all_ratings, get_shows_needing_results,
)
from ..services.dog_service import (
    get_missing_zoo_ids,
    extract_zoo_ids_from_results,
)
from ..parsers.zooportal_shows import fetch_show_list, fetch_show_results

logger = get_task_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# СПИСОК МЕРОПРИЯТИЙ ЗА ДАТУ
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name='dogs_module.import_show_list')
def import_show_list_task(self, date_str: str) -> dict:
    """
    Парсит список выставок за дату.
    Для каждой с результатами — диспатчит import_show_results_task.
    """
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
        'status':     'dispatched',
        'date':       date_str,
        'found':      len(shows),
        'dispatched': dispatched,
        'elapsed':    round(time.time() - start, 1),
    }


# ──────────────────────────────────────────────────────────────────────────────
# РЕЗУЛЬТАТЫ ОДНОЙ ВЫСТАВКИ
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name='dogs_module.import_show_results',
             soft_time_limit=3600, time_limit=4200)
def import_show_results_task(self, show_id: str, import_missing_dogs: bool = True) -> dict:
    """
    Парсит результаты выставки.
    Найденных собак — сохраняет через show_service.
    Ненайденных — show_service откладывает в Redis, таск диспатчит их импорт.
    """
    start = time.time()
    from ..models import ShowEvent

    event = ShowEvent.objects.using('dogs_db').filter(zooportal_show_id=show_id).first()
    if not event:
        event, _ = ShowEvent.objects.using('dogs_db').get_or_create(
            zooportal_show_id=show_id,
            defaults={'title': f'Show {show_id}', 'show_type': 'other', 'multiplier': 0},
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
            process_pending_results_task.apply_async(
                args=[show_id],
                countdown=60 * 10,
            )

    return {
        'status':          'success',
        'show_id':         show_id,
        'found':           len(results),
        'saved':           saved,
        'pending':         pending_count,
        'failed':          failed,
        'dogs_dispatched': dogs_dispatched,
        'elapsed':         round(time.time() - start, 1),
    }


# ──────────────────────────────────────────────────────────────────────────────
# ОБРАБОТКА ОЖИДАЮЩИХ РЕЗУЛЬТАТОВ
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name='dogs_module.process_pending_results',
             soft_time_limit=600, time_limit=700)
def process_pending_results_task(self, show_id: str = None) -> dict:
    """
    Берёт ожидающие результаты из Redis, сохраняет тех у кого теперь есть dog.
    Если остались — перепланирует себя через 30 минут.
    """
    start = time.time()

    if show_id:
        result = process_pending_results(show_id)
    else:
        result = process_all_pending_results()

    if result.get('still_pending', 0) > 0:
        process_pending_results_task.apply_async(
            args=[show_id],
            countdown=60 * 30,
        )

    return {
        'status':  'success',
        'show_id': show_id,
        'elapsed': round(time.time() - start, 1),
        **result,
    }


@shared_task(bind=True, name='dogs_module.process_all_pending_results')
def process_all_pending_results_task(self) -> dict:
    """Обработать все ожидающие результаты по всем выставкам."""
    return process_pending_results_task(show_id=None)


# ──────────────────────────────────────────────────────────────────────────────
# ДИАПАЗОН ДАТ
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name='dogs_module.import_show_date_range')
def import_show_date_range_task(
    self,
    date_from: str,
    date_to: str,
    countdown_between: int = 10,
) -> dict:
    """Диспатчит import_show_list_task для каждой даты в диапазоне."""
    try:
        dt_from = datetime.strptime(date_from, '%d.%m.%Y')
        dt_to   = datetime.strptime(date_to,   '%d.%m.%Y')
    except ValueError as e:
        return {'status': 'error', 'error': f'Неверный формат даты: {e}'}

    dispatched = []
    dt  = dt_from
    idx = 0

    while dt <= dt_to:
        date_str = dt.strftime('%d.%m.%Y')
        task = import_show_list_task.apply_async(
            args=[date_str],
            countdown=idx * countdown_between,
        )
        dispatched.append({'date': date_str, 'task_id': task.id})
        dt  += timedelta(days=1)
        idx += 1

    return {
        'status':     'dispatched',
        'date_from':  date_from,
        'date_to':    date_to,
        'days':       len(dispatched),
        'dispatched': dispatched,
    }


# ──────────────────────────────────────────────────────────────────────────────
# РЕЗУЛЬТАТЫ ЗА ПЕРИОД ИЗ БД
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name='dogs_module.import_results_for_date_range',
             soft_time_limit=86400, time_limit=90000)
def import_results_for_date_range_task(
    self,
    date_from: str,
    date_to: str = None,
    only_without_results: bool = True,
    import_missing_dogs: bool = True,
) -> dict:
    """
    Смотрит в БД на show_event за период,
    для каждой без результатов — парсит и сохраняет.
    """
    start = time.time()

    if not date_to:
        date_to = date_from

    try:
        dt_from = datetime.strptime(date_from, '%d.%m.%Y').date()
        dt_to   = datetime.strptime(date_to,   '%d.%m.%Y').date()
    except ValueError as e:
        return {'status': 'error', 'error': f'Неверный формат даты: {e}'}

    from ..models import ShowEvent

    qs = ShowEvent.objects.using('dogs_db').filter(
        event_date__gte=dt_from,
        event_date__lte=dt_to,
    ).order_by('event_date')

    if only_without_results:
        qs = qs.filter(results_parsed_at__isnull=True)

    events = list(qs)

    if not events:
        return {
            'status':  'success',
            'message': f'Нет выставок без результатов за {date_from}–{date_to}',
            'elapsed': round(time.time() - start, 1),
        }

    logger.info(f"📋 {len(events)} выставок за {date_from}–{date_to}")

    processed     = 0
    failed        = 0
    total_saved   = 0
    total_pending = 0
    dogs_dispatched = 0

    for event in events:
        logger.info(
            f"  [{processed + 1}/{len(events)}] "
            f"{event.title[:50]} ({event.zooportal_show_id})"
        )
        try:
            results = fetch_show_results(event.zooportal_show_id)
            if not results:
                processed += 1
                continue

            saved, err, pending_count = save_show_results(event, results)
            mark_results_parsed(event)
            total_saved   += saved
            total_pending += pending_count

            if import_missing_dogs and pending_count > 0:
                dogs_dispatched += _dispatch_missing_dogs(results)

            logger.info(f"    saved={saved}, pending={pending_count}, errors={err}")
            processed += 1

        except Exception as e:
            failed += 1
            logger.error(f"    Ошибка: {e}")

    if total_pending > 0:
        process_pending_results_task.apply_async(args=[None], countdown=60 * 10)

    return {
        'status':           'success',
        'period':           f'{date_from}–{date_to}',
        'events_found':     len(events),
        'events_processed': processed,
        'events_failed':    failed,
        'results_saved':    total_saved,
        'results_pending':  total_pending,
        'dogs_dispatched':  dogs_dispatched,
        'elapsed':          round(time.time() - start, 1),
    }


# ──────────────────────────────────────────────────────────────────────────────
# ПОЛНЫЙ ИМПОРТ
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name='dogs_module.import_shows_full',
             soft_time_limit=86400, time_limit=90000)
def import_shows_full_task(self, date_from: str, date_to: str = None) -> dict:
    """
    Полный импорт за дату/диапазон.
    Шаг 1: парсим список дат → сохраняем ShowEvent
    Шаг 2: берём ВСЕ ShowEvent за период без результатов (из БД, надёжно)
    Шаг 3: для каждого парсим результаты
    Шаг 4: ждём импорта собак
    Шаг 5: обрабатываем ожидающие результаты
    Шаг 6: пересчитываем рейтинг
    """
    start = time.time()

    if not date_to:
        date_to = date_from

    try:
        dt_from = datetime.strptime(date_from, '%d.%m.%Y')
        dt_to = datetime.strptime(date_to, '%d.%m.%Y')
    except ValueError as e:
        return {'status': 'error', 'error': f'Неверный формат даты: {e}'}

    dates_done = 0
    dt = dt_from

    # ── Шаг 1: Парсим список выставок за каждую дату ─────────────────────────
    while dt <= dt_to:
        date_str = dt.strftime('%d.%m.%Y')
        logger.info(f"📅 Парсим выставки за {date_str}...")
        try:
            shows = fetch_show_list(date_str)
            for show_data in shows:
                save_show_event(show_data)
        except Exception as e:
            logger.error(f"Ошибка за {date_str}: {e}")
        dates_done += 1
        dt += timedelta(days=1)

    # ── Шаг 2: Берём все выставки без результатов из БД ──────────────────────
    # show_service знает как это делать — не дублируем логику в таске
    events = get_shows_needing_results(dt_from.date(), dt_to.date())

    if not events:
        return {
            'status': 'success',
            'message': 'Все выставки уже имеют результаты или не найдены',
            'dates': dates_done,
            'elapsed': round(time.time() - start, 1),
        }

    logger.info(f"📋 {len(events)} выставок без результатов")

    # ── Шаг 3: Парсим результаты ─────────────────────────────────────────────
    all_zoo_ids = []

    for event in events:
        try:
            results = fetch_show_results(event.zooportal_show_id)
            if results:
                save_show_results(event, results)
                mark_results_parsed(event)
                all_zoo_ids.extend(extract_zoo_ids_from_results(results))
                logger.info(f"  ✅ {event.title[:50]}: {len(results)} результатов")
            else:
                logger.info(f"  ⏭️  {event.title[:50]}: результатов нет (выставка без хаски)")
        except Exception as e:
            logger.error(f"  ❌ {event.title[:50]}: {e}")

    # ── Шаг 4: Импорт отсутствующих собак — ждём ─────────────────────────────
    missing_ids = get_missing_zoo_ids(all_zoo_ids)

    if missing_ids:
        from ..tasks.tasks_zooportal import import_zooportal_dog_task
        tasks = [
            import_zooportal_dog_task.apply_async(args=[zid], countdown=i * 3)
            for i, zid in enumerate(missing_ids)
        ]
        logger.info(f"🚀 Ожидаем {len(tasks)} собак...")

        deadline = time.time() + len(tasks) * 300
        pending_t = list(tasks)
        while pending_t and time.time() < deadline:
            time.sleep(10)
            pending_t = [t for t in pending_t if not t.ready()]
            if pending_t:
                logger.info(f"  ⏳ Осталось {len(pending_t)} собак...")

    # ── Шаг 5: Ожидающие результаты ──────────────────────────────────────────
    logger.info("🔗 Обрабатываем ожидающие результаты...")
    pending_result = process_all_pending_results()

    # ── Шаг 6: Рейтинг ───────────────────────────────────────────────────────
    logger.info("📊 Пересчитываем рейтинги...")
    rating_result = recalculate_all_ratings()

    return {
        'status': 'success',
        'dates_processed': dates_done,
        'shows_processed': len(events),
        'dogs_imported': len(missing_ids),
        'results_pending': pending_result.get('still_pending', 0),
        'rating_updated': rating_result['updated'],
        'elapsed': round(time.time() - start, 1),
    }


# ──────────────────────────────────────────────────────────────────────────────
# РЕЙТИНГ
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, name='dogs_module.recalculate_show_ratings')
def recalculate_ratings_task(self, year: int = None) -> dict:
    result = recalculate_all_ratings(rating_year=year)
    return {'status': 'success', **result}


# диспатч задач

def _dispatch_missing_dogs(results: list) -> int:
    """
    Определяет каких собак нет в БД (через dog_service),
    диспатчит их импорт. Возвращает количество запущенных задач.
    """
    from ..tasks.tasks_zooportal import import_zooportal_dog_task

    zoo_ids = extract_zoo_ids_from_results(results)
    missing_ids = get_missing_zoo_ids(zoo_ids)

    for idx, zoo_id in enumerate(missing_ids):
        import_zooportal_dog_task.apply_async(
            args=[zoo_id],
            countdown=idx * 3,
        )

    if missing_ids:
        logger.info(f"Диспатчен импорт {len(missing_ids)} отсутствующих собак")

    return len(missing_ids)