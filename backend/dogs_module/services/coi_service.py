# dogs_module/services/coi_service.py
"""
Массовый пересчёт COI.
"""

import time
import logging
from typing import Callable, Optional

from ..repositories import dog_repository as dog_repo
from ..utils.coi_calculator import calculate_coi, save_coi

logger = logging.getLogger(__name__)


def recalculate_all(
        generations: int = 5,
        batch_size: int = 100,
        only_missing: bool = True,
        use_ancestor_coi: bool = False,
        progress_cb: Optional[Callable[[dict], None]] = None,
) -> dict:
    """
    Пересчитывает COI для всех собак с обоими родителями.

    progress_cb — необязательный колбэк, вызывается после каждого батча
    со словарём прогресса (таска передаёт сюда self.update_state).
    """
    start = time.time()

    qs = dog_repo.iter_dogs_for_coi_recalc(only_missing=only_missing)
    total = dog_repo.count_dogs_for_coi_recalc(only_missing=only_missing)

    updated = skipped = errors = 0
    offset = 0

    logger.info(f"🔄 COI пересчёт: {total} собак | gen={generations}")
    _emit(progress_cb, total=total, processed=0, updated=0, skipped=0, errors=0)

    while offset < total:
        batch = list(qs[offset: offset + batch_size])
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
        _emit(
            progress_cb, total=total, processed=processed,
            updated=updated, skipped=skipped, errors=errors,
            percent=round(processed / total * 100, 1) if total else 100,
        )

    duration = round(time.time() - start, 2)
    logger.info(f"✅ COI готово: обновлено={updated}, пропущено={skipped}, ошибок={errors}")

    return {
        'status': 'success',
        'total': total,
        'updated': updated,
        'skipped': skipped,
        'errors': errors,
        'duration_sec': duration,
    }


def _emit(cb: Optional[Callable[[dict], None]], **meta) -> None:
    if cb is not None:
        cb(meta)
