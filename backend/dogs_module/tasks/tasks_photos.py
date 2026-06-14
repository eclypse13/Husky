# dogs_module/tasks/tasks_photos.py
"""
Celery таски для фотографий — тонкие обёртки над photo_service.
"""

from typing import Dict, Optional
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, name="dogs_module.photo_upload_one")
def photo_upload_one(self, dog_id: int) -> Dict:
    """
    Загружает фото одной собаки на ЯД.
    """
    from ..services.photo_service import process_dog_photo

    result, redirect_to_zoo = process_dog_photo(dog_id)
    if redirect_to_zoo:
        logger.info(f"dog {dog_id}: Zoo фото → передаём в Playwright таску")
        photo_fetch_zoo_via_playwright.apply_async(kwargs={"dog_id": dog_id})
    return result


@shared_task(bind=True, name="dogs_module.photo_upload_bulk")
def photo_upload_bulk(
        self,
        id_from: int = 1,
        id_to: Optional[int] = None,
        limit: int = 500,
        delay: float = 0.5,
        only_without_yadisk: bool = True,
) -> Dict:
    """
    Bulk-загрузка фото всех собак из БД на ЯД.
    Диспатчит photo_upload_one для каждой собаки с photo_url.

    only_without_yadisk=True  → только новые (у кого нет пути на ЯД)
    only_without_yadisk=False → все, сравнивает байты и обновляет изменившиеся
    """
    from ..services.photo_service import yadisk_ensure_folder, get_dogs_for_bulk_sync

    dogs = get_dogs_for_bulk_sync(
        id_from=id_from,
        id_to=id_to,
        limit=min(limit, 2000),
        only_without_yadisk=only_without_yadisk,
    )

    if not dogs:
        return {"dispatched": 0, "message": "Нет собак для обработки"}

    try:
        yadisk_ensure_folder()
    except Exception as e:
        logger.warning(f"yadisk_ensure_folder: {e}")

    task_ids = []
    for i, dog in enumerate(dogs):
        task = photo_upload_one.apply_async(
            kwargs={"dog_id": dog["id"]},
            countdown=int(i * delay),
        )
        task_ids.append(task.id)

    logger.info(f"📷 photo_upload_bulk: диспатчено {len(task_ids)} задач")
    return {
        "dispatched": len(task_ids),
        "task_ids": task_ids,
        "id_from": id_from,
        "id_to": id_to,
        "only_without_yadisk": only_without_yadisk,
    }


@shared_task(bind=True, name="dogs_module.photo_fetch_zoo_via_playwright")
def photo_fetch_zoo_via_playwright(self, dog_id: int) -> Dict:
    """
    Открывает страницу Zoo собаки через Playwright, скачивает фото
    и загружает на ЯД.
    """
    from ..services.photo_service import process_zoo_dog_photo
    return process_zoo_dog_photo(dog_id)


@shared_task(bind=True, name="dogs_module.photo_fetch_zoo_bulk")
def photo_fetch_zoo_bulk(
        self,
        id_from: int = 1,
        id_to: Optional[int] = None,
        limit: int = 100,
        delay: float = 5.0,
) -> Dict:
    """
    Bulk-загрузка Zoo фото через Playwright для собак у которых нет photo_yadisk_url.

    delay=5.0 — Playwright тяжёлый, нужна пауза между задачами.
    limit=100 — не больше 100 за раз (каждая таска запускает браузер).
    """
    from ..repositories import dog_repository as dog_repo

    dogs = dog_repo.get_zoo_dogs_without_yadisk_photo(
        id_from=id_from, id_to=id_to, limit=limit
    )
    if not dogs:
        return {"dispatched": 0, "message": "Нет Zoo собак без фото на ЯД"}

    task_ids = []
    for i, dog in enumerate(dogs):
        task = photo_fetch_zoo_via_playwright.apply_async(
            kwargs={"dog_id": dog["id"]},
            countdown=int(i * delay),
        )
        task_ids.append(task.id)

    logger.info(f"📷 Zoo bulk Playwright: диспатчено {len(task_ids)} задач")
    return {
        "dispatched": len(task_ids),
        "task_ids": task_ids,
        "id_from": id_from,
        "id_to": id_to,
    }


@shared_task(bind=True, name="dogs_module.photo_sync_yadisk_to_db")
def photo_sync_yadisk_to_db(self) -> Dict:
    """
    ЯД → БД: сканирует disk:/dogs/photos/, обновляет photo_yadisk_path в БД.
    """
    from ..services.photo_service import sync_yadisk_to_db
    return sync_yadisk_to_db()


@shared_task(bind=True, name="dogs_module.photo_stats")
def photo_stats(self) -> Dict:
    """Статистика: сколько в БД, на ЯД, осталось."""
    from ..services.photo_service import get_photo_stats
    return get_photo_stats()


@shared_task(bind=True, name="dogs_module.photo_delete_one")
def photo_delete_one(self, dog_id: int) -> Dict:
    """Удаляет фото одной собаки с ЯД и чистит поля photo_yadisk_* в БД."""
    from ..services.photo_service import delete_dog_photo
    return delete_dog_photo(dog_id)


@shared_task(bind=True, name="dogs_module.photo_backfill_hashes")
def photo_backfill_hashes(
    self,
    limit: int = 1000,
    id_from: int = 1,
    id_to: int = None,
) -> Dict:
    from ..services.photo_service import backfill_photo_hashes
    return backfill_photo_hashes(limit=limit, id_from=id_from, id_to=id_to)


@shared_task(bind=True, name="dogs_module.photo_cleanup_placeholders")
def photo_cleanup_placeholders(self) -> Dict:
    """Удаляет с ЯД дефолтные заглушки (по DEFAULT_PHOTO_HASHES) и чистит поля."""
    from ..services.photo_service import cleanup_placeholder_photos
    return cleanup_placeholder_photos()

@shared_task(bind=True, name="dogs_module.photo_backfill_hashes_from_source")
def photo_backfill_hashes_from_source(
    self,
    limit: int = 1000,
    id_from: int = 1,
    id_to: int = None,
) -> dict:
    """
    Считает photo_hash из оригинального photo_url для BA-собак.
    Zoo-собаки пропускаются (нужен Playwright).
    """
    from ..services.photo_service import backfill_hashes_from_source
    return backfill_hashes_from_source(limit=limit, id_from=id_from, id_to=id_to)