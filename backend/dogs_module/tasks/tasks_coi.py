# dogs_module/tasks/tasks_coi.py
"""
Celery-задача для массового пересчёта COI.
Только оркестрация — вся логика в coi_calculator.py.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='dogs_module.recalculate_all_coi',
    max_retries=0,
    time_limit=3600,
    soft_time_limit=3500,
)
def recalculate_all_coi_task(
    self,
    generations: int = 5,
    batch_size: int = 100,
    only_missing: bool = True,
    use_ancestor_coi: bool = False,
) -> dict:
    """
    Массовый пересчёт COI для всех собак в БД.
    Прогресс виден через GET /api/dogs/import/status/{task_id}/
    """
    from ..utils.coi_calculator import calculate_coi, save_coi
    from ..models import Dog
    import time

    start = time.time()

    qs = (
        Dog.objects
        .using('dogs_db')
        .filter(sire_id__isnull=False, dam_id__isnull=False)
        .only('id', 'registered_name', 'sire_id', 'dam_id', 'coi')
    )
    if only_missing:
        qs = qs.filter(coi__isnull=True)

    total   = qs.count()
    updated = skipped = errors = 0
    offset  = 0

    logger.info(f"🔄 COI пересчёт: {total} собак | gen={generations}")

    self.update_state(state='PROGRESS', meta={
        'total': total, 'processed': 0,
        'updated': 0, 'skipped': 0, 'errors': 0,
    })

    while offset < total:
        batch  = list(qs[offset: offset + batch_size])
        offset += batch_size

        for dog in batch:
            try:
                result = calculate_coi(
                    dog,
                    generations=generations,
                    use_ancestor_coi=use_ancestor_coi,
                )
                if not result.is_valid:
                    skipped += 1
                    continue
                save_coi(dog, result)
                updated += 1
            except Exception as exc:
                errors += 1
                logger.error(f"❌ COI ошибка dog.id={dog.id}: {exc}")

        processed = min(offset, total)
        self.update_state(state='PROGRESS', meta={
            'total':     total,
            'processed': processed,
            'updated':   updated,
            'skipped':   skipped,
            'errors':    errors,
            'percent':   round(processed / total * 100, 1) if total else 100,
        })

    duration = round(time.time() - start, 2)
    logger.info(f"✅ COI готово: обновлено={updated}, пропущено={skipped}, ошибок={errors}")

    return {
        'status':       'success',
        'total':        total,
        'updated':      updated,
        'skipped':      skipped,
        'errors':       errors,
        'duration_sec': duration,
    }