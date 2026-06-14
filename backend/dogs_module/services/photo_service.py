# dogs_module/services/photo_service.py
"""
Бизнес-логика работы с фотографиями собак и Яндекс.Диском.
"""
import hashlib
import logging
import os
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse

from ..config.yadisk import (
    YADISK_FOLDER, YADISK_PUBLIC_DOWNLOADER,
    DOWNLOAD_TIMEOUT, HEAD_TIMEOUT,
    MAX_FILE_SIZE, CHUNK_SIZE, ALLOWED_PHOTO_EXT, SOURCE_HEADERS,
    DEFAULT_PHOTO_HASHES, PLACEHOLDER_URL_PATTERNS,
)
from . import yadisk_client as yd

logger = logging.getLogger(__name__)

# in-memory кеш public_key папки (не меняется во время работы сервиса)
_PUBLIC_KEY_CACHE: dict = {}


# Утилиты
def _ext(url: str) -> str:
    ext = os.path.splitext(urlparse(url).path)[-1].lower()
    return ext if ext in ALLOWED_PHOTO_EXT else ".jpg"


def yadisk_path_for(dog_id: int, photo_url: str) -> str:
    """Канонический путь файла на ЯД для данной собаки."""
    return f"{YADISK_FOLDER}/{dog_id}{_ext(photo_url)}"


# Публичный реэкспорт для обратной совместимости
# tasks_photos.py и integration.py зовут yadisk_ensure_folder напрямую
def yadisk_ensure_folder() -> None:
    """Создаёт dogs/ и dogs/photos/ на ЯД если их нет."""
    yd.ensure_photos_folder()


# Скачивание с источника
def _download_with_ba_cookies(url: str) -> Optional[bytes]:
    """Скачивает BA фото через httpx с retry."""
    import ssl
    import httpx

    def _ssl_ctx():
        ctx = ssl.create_default_context()
        try:
            ctx.options |= ssl.OP_IGNORE_UNEXPECTED_EOF
        except AttributeError:
            ctx.options |= 0x00000080
        return ctx

    try:
        from ..utils.cookie_refresher import get_ba_cookies
        cookies = get_ba_cookies()
        if not cookies:
            logger.warning("BA куки недоступны")
            return None

        with httpx.Client(
                cookies=cookies,
                headers=SOURCE_HEADERS,
                timeout=DOWNLOAD_TIMEOUT,
                follow_redirects=True,
                verify=_ssl_ctx(),
        ) as client:
            for attempt in range(3):
                try:
                    r = client.get(url)
                    r.raise_for_status()

                    if "text/html" in r.headers.get("content-type", ""):
                        logger.warning(f"BA: HTML вместо изображения: {url}")
                        return None

                    data = r.content
                    if len(data) > MAX_FILE_SIZE:
                        logger.warning(f"BA: файл >10МБ, пропуск: {url}")
                        return None

                    if data:
                        logger.info(f"BA: фото скачано с куками ({len(data)}b)")
                    return data or None

                except Exception as e:
                    if attempt < 2:
                        logger.warning(f"BA download попытка {attempt + 1}/3 {url}: {e}")
                        time.sleep(2)
                        continue
                    logger.warning(f"BA fallback download failed {url}: {e}")
                    return None

    except Exception as e:
        logger.warning(f"BA fallback download failed {url}: {e}")
        return None


def _download_with_zoo_cookies(url: str) -> Optional[bytes]:
    """Fallback: скачивает Zoo фото с авторизацией + Referer."""
    try:
        import httpx
        from ..utils.cookie_refresher import get_zoo_cookies
        from ..config.scraping import ZOOPORTAL_PHOTO_HEADERS

        cookies = get_zoo_cookies()
        if not cookies:
            logger.warning("Zoo куки недоступны")
            return None

        headers = {**SOURCE_HEADERS, **ZOOPORTAL_PHOTO_HEADERS}
        with httpx.Client(
                cookies=cookies,
                headers=headers,
                timeout=DOWNLOAD_TIMEOUT,
                follow_redirects=True,
        ) as client:
            r = client.get(url)
            r.raise_for_status()

            if "text/html" in r.headers.get("content-type", ""):
                logger.warning(f"Zoo: всё ещё HTML даже с куками для {url}")
                return None

            data = r.content
            if len(data) > MAX_FILE_SIZE:
                return None
            if data:
                logger.info(f"Zoo: фото скачано с куками ({len(data)}b)")
            return data or None

    except Exception as e:
        logger.warning(f"Zoo fallback download failed {url}: {e}")
        return None


def download_from_source(url: str) -> Optional[bytes]:
    """
    BA  → httpx через _download_with_ba_cookies
    Zoo → httpx, при блокировке — с куками
    """
    try:
        if "breedarchive" in url:
            return _download_with_ba_cookies(url)

        import httpx
        with httpx.Client(
                headers=SOURCE_HEADERS,
                timeout=DOWNLOAD_TIMEOUT,
                follow_redirects=True,
        ) as client:
            r = client.get(url)
            r.raise_for_status()

            if "text/html" in r.headers.get("content-type", ""):
                if "zooportal" in url:
                    logger.info(f"Zoo: пробуем с куками для {url}")
                    return _download_with_zoo_cookies(url)
                logger.warning(f"Получили HTML вместо изображения: {url}")
                return None

            data = r.content
            if len(data) > MAX_FILE_SIZE:
                logger.warning(f"Файл >10МБ, пропуск: {url}")
                return None
            return data or None

    except Exception as e:
        logger.warning(f"Ошибка скачивания {url}: {e}")
        return None


# Основная логика
def sync_photo_to_yadisk(
        dog_id: int,
        photo_url: str,
        current_yadisk_path: Optional[str],
        current_hash: Optional[str] = None,
) -> Dict:
    """Скачивает фото и грузит на ЯД только если оно реально изменилось (по хэшу)."""
    yadisk_path = current_yadisk_path or yadisk_path_for(dog_id, photo_url)

    # Дешёвый префильтр: явная заглушка по URL — не тратим трафик
    if _is_placeholder_url(photo_url):
        logger.info(f"dog {dog_id}: URL-заглушка, пропуск ({photo_url})")
        return {"status": "skipped_placeholder", "reason": "url-заглушка"}

    data = download_from_source(photo_url)
    if data is None:
        return {"status": "error", "error": "не удалось скачать с источника"}

    return _store_or_skip(dog_id, yadisk_path, data, current_hash)


def fetch_zoo_photo_via_playwright(dog_id: int, zooportal_id: str, photo_url: str,
                                   current_hash: Optional[str] = None, ) -> Dict:
    """
    Скачивает Zoo-фото через Playwright (обходит hotlink защиту) и заливает на ЯД.
    """
    from ..parsers.zooportal import BrowserManager
    from ..config import ZOOPORTAL_BASE_URL, ZOOPORTAL_DOG_PATH

    logger.info(f"📷 Zoo Playwright фото: dog_id={dog_id}, zoo_id={zooportal_id}")
    try:
        with BrowserManager() as browser:
            url = f"{ZOOPORTAL_BASE_URL}{ZOOPORTAL_DOG_PATH}/{zooportal_id}/"
            browser.fetch_page(url)
            photo_bytes = browser.download_photo_bytes(photo_url)
    except Exception as e:
        logger.error(f"Zoo Playwright: ошибка для dog_id={dog_id}: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

    if not photo_bytes:
        return {"status": "error", "error": "фото не скачалось через Playwright"}

    return upload_photo_bytes_to_yadisk(dog_id, photo_url, photo_bytes, current_hash)


def upload_photo_bytes_to_yadisk(
        dog_id: int,
        photo_url: str,
        photo_bytes: bytes,
        current_hash: Optional[str] = None,
) -> Dict:
    """Заливает уже скачанные байты (Zoo/Playwright) с дедупом и фильтром заглушек."""
    yadisk_path = yadisk_path_for(dog_id, photo_url)
    return _store_or_skip(dog_id, yadisk_path, photo_bytes, current_hash)


# Оркестраторы

def process_dog_photo(dog_id: int):
    """
    Полный цикл загрузки фото одной собаки на ЯД.
    Zoo-фото перенаправляет на Playwright — возвращает (result, redirect_to_zoo=True).
    """
    from ..repositories import dog_repository as dog_repo

    dog = dog_repo.get_photo_fields(dog_id, with_zooportal=True)
    if dog is None:
        return {"dog_id": dog_id, "status": "not_found"}, False
    if not dog.photo_url:
        return {"dog_id": dog_id, "status": "no_url"}, False

    if "zooportal" in (dog.photo_url or "") and dog.zooportal_id:
        return {"dog_id": dog_id, "status": "redirected_to_playwright"}, True

    result = sync_photo_to_yadisk(
        dog.id, dog.photo_url, dog.photo_yadisk_path, dog.photo_hash
    )
    result["dog_id"] = dog_id

    # Заглушка: на ЯД ничего нет, но запоминаем хэш, чтобы не качать её снова
    if result["status"] == "skipped_placeholder":
        if result.get("hash") and result["hash"] != dog.photo_hash:
            dog_repo.update_photo_paths(dog_id, {"photo_hash": result["hash"]})
        return result, False

    if result["status"] in ("uploaded", "skipped"):
        update = {}
        if result.get("path") and not dog.photo_yadisk_path:
            update["photo_yadisk_path"] = result["path"]
        if result.get("yadisk_url") and not dog.photo_yadisk_url:
            update["photo_yadisk_url"] = result["yadisk_url"]
        if result.get("hash") and result["hash"] != dog.photo_hash:
            update["photo_hash"] = result["hash"]
        if update:
            dog_repo.update_photo_paths(dog_id, update)
            logger.info(f"dog {dog_id}: обновлено в БД {list(update.keys())}")

    return result, False


def process_zoo_dog_photo(dog_id: int) -> Dict:
    """Полный цикл загрузки Zoo-фото через Playwright + запись путей в БД."""
    from ..repositories import dog_repository as dog_repo

    dog = dog_repo.get_photo_fields(dog_id, with_zooportal=True)
    if dog is None:
        return {"dog_id": dog_id, "status": "not_found"}
    if not dog.photo_url:
        return {"dog_id": dog_id, "status": "no_url"}
    if not dog.zooportal_id:
        return {"dog_id": dog_id, "status": "no_zooportal_id"}
    if dog.photo_yadisk_url:
        return {"dog_id": dog_id, "status": "already_on_yadisk", "url": dog.photo_yadisk_url}

    result = fetch_zoo_photo_via_playwright(
        dog.id, dog.zooportal_id, dog.photo_url, dog.photo_hash
    )
    result["dog_id"] = dog_id

    if result["status"] == "skipped_placeholder":
        if result.get("hash") and result["hash"] != dog.photo_hash:
            dog_repo.update_photo_paths(dog_id, {"photo_hash": result["hash"]})
        return result
    if result["status"] in ("uploaded", "skipped"):
        update = {}
        if result.get("path"):       update["photo_yadisk_path"] = result["path"]
        if result.get("yadisk_url"): update["photo_yadisk_url"] = result["yadisk_url"]
        if result.get("hash"):       update["photo_hash"] = result["hash"]
        if update:
            dog_repo.update_photo_paths(dog_id, update)
            logger.info(f"dog {dog_id}: Zoo фото залито на ЯД через Playwright")

    return result


def sync_yadisk_to_db() -> Dict:
    """
    ЯД → БД: сканирует disk:/dogs/photos/, по имени файла
    (12345.jpg → dog_id=12345) обновляет photo_yadisk_path в БД.
    """
    from ..repositories import dog_repository as dog_repo

    files = yd.list_files()
    if not files:
        return {"status": "error", "error": "Папка пуста или не найдена на ЯД"}

    updated = not_found = already_set = 0

    for file in files:
        name = file.get("name", "")
        stem = os.path.splitext(name)[0]
        file_path = file.get("path", "").replace("disk:/", "")

        try:
            dog_id = int(stem)
        except ValueError:
            continue

        dog = dog_repo.get_yadisk_path(dog_id)
        if dog is None:
            not_found += 1
            continue
        if dog.photo_yadisk_path:
            already_set += 1
            continue

        dog_repo.update_photo_paths(dog_id, {"photo_yadisk_path": file_path})
        updated += 1

    return {
        "status": "done",
        "files_on_yadisk": len(files),
        "updated_in_db": updated,
        "already_had_path": already_set,
        "not_found_in_db": not_found,
    }


def get_photo_stats() -> Dict:
    """Статистика по фото: сколько в БД, сколько на ЯД."""
    from ..repositories import dog_repository as dog_repo

    counts = dog_repo.get_photo_coverage_counts()
    total = counts["total"]
    with_url = counts["with_url"]
    with_yadisk = counts["with_yadisk"]

    files_on_disk = yd.count_files()
    yadisk_info = {
        "folder": f"disk:/{YADISK_FOLDER}",
        "files_on_disk": files_on_disk if files_on_disk is not None else "?",
    }
    if files_on_disk == 0:
        yadisk_info["note"] = "папка не создана"

    return {
        "total_dogs": total,
        "dogs_with_photo_url": with_url,
        "dogs_on_yadisk": with_yadisk,
        "missing": with_url - with_yadisk,
        "yadisk": yadisk_info,
    }


def get_dogs_for_bulk_sync(
        id_from: int = 1,
        id_to: Optional[int] = None,
        limit: int = 500,
        only_without_yadisk: bool = True,
) -> List[Dict]:
    """Выбирает собак с photo_url для bulk-синхронизации."""
    from ..repositories import dog_repository as dog_repo
    return dog_repo.get_dogs_with_photo_url(
        id_from=id_from, id_to=id_to, limit=limit,
        only_without_yadisk=only_without_yadisk,
    )


def get_yadisk_public_key() -> Optional[str]:
    """Возвращает public_key папки dogs/photos. Кешируется в памяти."""
    if _PUBLIC_KEY_CACHE.get("key"):
        return _PUBLIC_KEY_CACHE["key"]
    key = yd.get_public_key()
    if key:
        _PUBLIC_KEY_CACHE["key"] = key
        logger.info(f"✅ ЯД: папка опубликована, public_key={key[:20]}...")
    return key


def get_public_photo_url(yadisk_path: str) -> Optional[str]:
    """
    Постоянная публичная ссылка на файл в папке dogs/photos.
    URL = YADISK_PUBLIC_DOWNLOADER/{public_key}/{filename}
    """
    if not yadisk_path:
        return None
    filename = os.path.basename(yadisk_path)
    key = get_yadisk_public_key()
    if not key:
        return None
    return f"{YADISK_PUBLIC_DOWNLOADER}/{key}/{filename}"


# Отпечаток фото (хэш + детекция заглушек)

def photo_hash(data: bytes) -> str:
    """Контентный хэш изображения. Основа сравнения и дедупликации."""
    return hashlib.sha256(data).hexdigest()


def _is_placeholder_url(url: str) -> bool:
    u = (url or "").lower()
    return any(p in u for p in PLACEHOLDER_URL_PATTERNS)


def _is_placeholder_hash(h: str) -> bool:
    return h in DEFAULT_PHOTO_HASHES


def _store_or_skip(
        dog_id: int,
        yadisk_path: str,
        data: bytes,
        current_hash: Optional[str],
) -> Dict:
    """
    Единое ядро решения для уже полученных байт.

    status: uploaded | skipped | skipped_placeholder | error
    """
    new_hash = photo_hash(data)

    # 1. Дефолтная картинка сайта — у сотни собак она одинаковая, не плодим копии
    if _is_placeholder_hash(new_hash):
        logger.info(f"dog {dog_id}: дефолтное фото сайта (hash={new_hash[:12]}), на ЯД не грузим")
        return {"status": "skipped_placeholder", "hash": new_hash,
                "reason": "дефолтное изображение"}

    # 2. Побайтово не изменилось — ничего не делаем (только добираем url если нужно)

    if current_hash and current_hash == new_hash:
        existing_size = yd.get_file_size(yadisk_path)
        if existing_size:
            # файл есть на ЯД — пропускаем
            yadisk_url = yd.publish_and_get_url(yadisk_path)
            return {"status": "skipped", "path": yadisk_path, "yadisk_url": yadisk_url,
                    "hash": new_hash, "reason": "хэш совпадает"}

        # файла нет — перезаливаем несмотря на совпадение хеша
        logger.warning(f"dog {dog_id}: хэш совпадает но файл не найден на ЯД, перезаливаем")

    # 3. Новое/изменённое фото — заливаем
    if not yd.upload(data, yadisk_path):
        return {"status": "error", "error": "ошибка загрузки на ЯД"}

    yadisk_url = yd.publish_and_get_url(yadisk_path)
    logger.info(f"📷 dog {dog_id}: фото залито ({len(data)}b, hash={new_hash[:12]})")
    return {"status": "uploaded", "path": yadisk_path, "yadisk_url": yadisk_url,
            "size": len(data), "hash": new_hash}


# Для тех, у которых есть yandex path
def backfill_photo_hashes(
        limit: int = 1000,
        id_from: int = 1,
        id_to: int = None,
) -> Dict:
    """
    Считает photo_hash для собак с фото на ЯД но без hash.
    Для Zoo-собак скачивает через Playwright (нужен hotlink обход).
    """
    from ..repositories import dog_repository as dog_repo

    dogs = dog_repo.get_dogs_with_yadisk_without_hash(
        limit=limit, id_from=id_from, id_to=id_to
    )
    done = skipped = errors = 0

    for dog in dogs:
        try:
            # Zoo-фото требует Playwright для скачивания
            if 'zooportal' in (dog.photo_url or '') and dog.zooportal_id:
                from ..parsers.zooportal import BrowserManager
                from ..config import ZOOPORTAL_BASE_URL, ZOOPORTAL_DOG_PATH
                with BrowserManager() as browser:
                    browser.fetch_page(
                        f"{ZOOPORTAL_BASE_URL}{ZOOPORTAL_DOG_PATH}/{dog.zooportal_id}/"
                    )
                    data = browser.download_photo_bytes(dog.photo_url)
            else:
                data = download_from_source(dog.photo_url)

            if not data:
                skipped += 1
                continue

            h = photo_hash(data)
            dog_repo.update_photo_paths(dog.id, {'photo_hash': h})
            done += 1
        except Exception as e:
            logger.error(f"backfill_photo_hashes dog_id={dog.id}: {e}")
            errors += 1

    return {'scanned': len(dogs), 'updated': done, 'skipped': skipped, 'errors': errors}


# С обычных ресурсов
def backfill_hashes_from_source(
        limit: int = 1000,
        id_from: int = 1,
        id_to: int = None,
) -> Dict:
    """
    Считает photo_hash из оригинального photo_url (не с ЯД).
    Для BA собак — HTTP, для Zoo — нужен Playwright (пропускаем).
    """
    from ..repositories import dog_repository as dog_repo

    dogs = dog_repo.get_dogs_with_url_without_hash(
        limit=limit, id_from=id_from, id_to=id_to
    )
    done = skipped = 0

    for dog in dogs:
        # Zoo требует Playwright — пропускаем здесь
        if 'zooportal' in (dog.get('photo_url') or ''):
            skipped += 1
            logger.info(f"Processing dog {dog['id']}: {dog.get('photo_url')}")
            continue

        data = download_from_source(dog['photo_url'])
        if not data:
            skipped += 1
            logger.warning(f"Не удалось скачать фото для dog_id={dog['id']}: {dog.get('photo_url')}")
            continue

        h = photo_hash(data)
        dog_repo.update_photo_paths(dog['id'], {'photo_hash': h})
        done += 1

    return {'scanned': len(dogs), 'updated': done, 'skipped': skipped}


def find_placeholder_candidates(min_count: int = 5, top: int = 20) -> List[Dict]:
    """
    Группирует фото по хэшу и возвращает самые частые.
    Дефолтная серая заглушка всплывёт с count в сотни — её хэш переносите в DEFAULT_PHOTO_HASHES.
    """
    from ..repositories import dog_repository as dog_repo
    return dog_repo.count_dogs_by_photo_hash(min_count=min_count, top=top)


def cleanup_placeholder_photos() -> Dict:
    """Удаляет с ЯД уже залитые заглушки (по DEFAULT_PHOTO_HASHES) и чистит поля."""
    from ..repositories import dog_repository as dog_repo
    from ..config.yadisk import DEFAULT_PHOTO_HASHES
    dogs = dog_repo.get_dogs_by_photo_hash(list(DEFAULT_PHOTO_HASHES))  # написать в репо
    deleted = 0
    for dog in dogs:
        if dog.photo_yadisk_path and yd.delete(dog.photo_yadisk_path):
            deleted += 1
        dog_repo.update_photo_paths(dog.id, {
            "photo_yadisk_path": None, "photo_yadisk_url": None,
        })
    return {"status": "done", "cleaned": len(dogs), "deleted_from_yadisk": deleted}


def delete_dog_photo(dog_id: int) -> Dict:
    """Удаляет фото собаки с ЯД и обнуляет photo_yadisk_path/url/hash в БД."""
    from ..repositories import dog_repository as dog_repo

    dog = dog_repo.get_photo_fields(dog_id)
    if dog is None:
        return {"dog_id": dog_id, "status": "not_found"}
    if not dog.photo_yadisk_path:
        return {"dog_id": dog_id, "status": "no_yadisk_photo"}

    deleted = yd.delete(dog.photo_yadisk_path)
    dog_repo.update_photo_paths(dog_id, {
        "photo_yadisk_path": None,
        "photo_yadisk_url": None,
        "photo_hash": None,
    })
    logger.info(f"🗑 dog {dog_id}: фото удалено с ЯД ({'ok' if deleted else 'файла не было'})")
    return {"dog_id": dog_id, "status": "deleted", "removed_from_yadisk": deleted}
