# dogs_module/tasks/tasks_photos.py
"""
Celery таски для фотографий — тонкие обёртки над photo_service.

Вся логика в: dogs_module/services/photo_service.py
"""

from typing import Dict, Optional
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, name="dogs_module.photo_upload_one")
def photo_upload_one(self, dog_id: int) -> Dict:
    """
    Загружает фото одной собаки на ЯД.
    Вызывается автоматически сигналом при сохранении Dog с photo_url,
    а также вручную из API или админки.
    """
    from ..models import Dog
    from ..services.photo_service import sync_photo_to_yadisk

    try:
        dog = Dog.objects.using("dogs_db").only(
            "id", "photo_url", "photo_yadisk_path", "photo_yadisk_url"
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        return {"dog_id": dog_id, "status": "not_found"}

    if not dog.photo_url:
        return {"dog_id": dog_id, "status": "no_url"}

    # Zoo фото нельзя скачать прямым HTTP — нужен Playwright
    # Перенаправляем на специальную таску
    if "zooportal" in (dog.photo_url or "") and dog.zooportal_id:
        logger.info(f"dog {dog_id}: Zoo фото → передаём в Playwright таску")
        photo_fetch_zoo_via_playwright.apply_async(kwargs={"dog_id": dog_id})
        return {"dog_id": dog_id, "status": "redirected_to_playwright"}

    result = sync_photo_to_yadisk(dog.id, dog.photo_url, dog.photo_yadisk_path)
    result["dog_id"] = dog_id

    # Сохраняем path и yadisk_url в БД при uploaded или skipped.
    # При skipped путь уже есть, но yadisk_url мог быть пустым — заполняем.
    if result["status"] in ("uploaded", "skipped"):
        update = {}
        if result.get("path") and not dog.photo_yadisk_path:
            update["photo_yadisk_path"] = result["path"]
        if result.get("yadisk_url") and not dog.photo_yadisk_url:
            update["photo_yadisk_url"] = result["yadisk_url"]
        if update:
            Dog.objects.using("dogs_db").filter(pk=dog_id).update(**update)
            logger.info(f"dog {dog_id}: обновлено в БД {list(update.keys())}")

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
        "task_ids":   task_ids,
        "id_from":    id_from,
        "id_to":      id_to,
        "only_without_yadisk": only_without_yadisk,
    }


@shared_task(bind=True, name="dogs_module.photo_fetch_zoo_via_playwright")
def photo_fetch_zoo_via_playwright(self, dog_id: int) -> Dict:
    """
    Открывает страницу Zoo собаки через Playwright, скачивает фото
    и загружает на ЯД.

    Используй для Zoo собак у которых нет photo_yadisk_url:
      POST /api/dogs/photos/upload/<dog_id>/   ← запустит эту таску если Zoo
      или напрямую через Celery
    """
    from ..models import Dog
    from ..services.photo_service import fetch_zoo_photo_via_playwright

    try:
        dog = Dog.objects.using("dogs_db").only(
            "id", "zooportal_id", "photo_url", "photo_yadisk_path", "photo_yadisk_url"
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        return {"dog_id": dog_id, "status": "not_found"}

    if not dog.photo_url:
        return {"dog_id": dog_id, "status": "no_url"}

    if not dog.zooportal_id:
        return {"dog_id": dog_id, "status": "no_zooportal_id"}

    # Если уже есть на ЯД — не трогаем
    if dog.photo_yadisk_url:
        return {"dog_id": dog_id, "status": "already_on_yadisk", "url": dog.photo_yadisk_url}

    result = fetch_zoo_photo_via_playwright(dog.id, dog.zooportal_id, dog.photo_url)
    result["dog_id"] = dog_id

    if result["status"] == "uploaded":
        update = {}
        if result.get("path"):
            update["photo_yadisk_path"] = result["path"]
        if result.get("yadisk_url"):
            update["photo_yadisk_url"] = result["yadisk_url"]
        if update:
            Dog.objects.using("dogs_db").filter(pk=dog_id).update(**update)
            logger.info(f"dog {dog_id}: Zoo фото залито на ЯД через Playwright")

    return result


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
    from ..models import Dog

    qs = (
        Dog.objects.using("dogs_db")
        .filter(
            photo_url__icontains="zooportal",
            photo_yadisk_url__isnull=True,
            zooportal_id__isnull=False,
            id__gte=id_from,
        )
        .exclude(photo_url="")
        .exclude(zooportal_id="")
        .only("id")
        .order_by("id")
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)

    dogs = list(qs.values("id")[:limit])
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
        "task_ids":   task_ids,
        "id_from":    id_from,
        "id_to":      id_to,
    }


@shared_task(bind=True, name="dogs_module.photo_sync_yadisk_to_db")
def photo_sync_yadisk_to_db(self) -> Dict:
    """
    ЯД → БД: сканирует disk:/dogs/photos/, обновляет photo_yadisk_path в БД.
    Полезно если загружал фото вручную или пути сбросились.
    """
    from ..services.photo_service import sync_yadisk_to_db
    return sync_yadisk_to_db()


@shared_task(bind=True, name="dogs_module.photo_stats")
def photo_stats(self) -> Dict:
    """Статистика: сколько в БД, на ЯД, осталось."""
    from ..services.photo_service import get_photo_stats
    return get_photo_stats()