# dogs_module/services/photo_service.py
"""
Бизнес-логика работы с фотографиями собак и Яндекс.Диском.

Связь собака ↔ файл на ЯД:
    Файл: disk:/dogs/photos/{dog.id}.jpg
    dog.id — PostgreSQL primary key (Dog.id)

Поля модели Dog:
    photo_url          — оригинальная ссылка (Zooportal / BreedArchive), сохраняем всегда
    photo_yadisk_path  — путь файла на ЯД: 'dogs/photos/12345.jpg'

Сравнение «это ли фото»:
    HEAD к photo_url → Content-Length (байты источника)
    GET метаданных ЯД → size (байты на диске)
    Равны → пропускаем. Отличаются → перекачиваем.
"""

import logging
import os
from io import BytesIO
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# ── Константы ─────────────────────────────────────────────────────────────────

YADISK_API       = "https://cloud-api.yandex.net/v1/disk/resources"
YADISK_FOLDER    = "dogs/photos"
DOWNLOAD_TIMEOUT = 30
MAX_FILE_SIZE    = 10 * 1024 * 1024  # 10 МБ
CHUNK_SIZE       = 16 * 1024

SOURCE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
    "Accept": "image/*,*/*;q=0.8",
}


# ── Утилиты ───────────────────────────────────────────────────────────────────

def _token() -> str:
    from decouple import config
    token = config("YANDEX_DISK_TOKEN", default="")
    if not token:
        raise ValueError("YANDEX_DISK_TOKEN не задан в .env")
    return token


def _yd_headers() -> dict:
    return {"Authorization": f"OAuth {_token()}"}


def _disk(path: str) -> str:
    """'dogs/photos/1.jpg'  →  'disk:/dogs/photos/1.jpg'"""
    return path if path.startswith("disk:/") else f"disk:/{path}"


def _ext(url: str) -> str:
    ext = os.path.splitext(urlparse(url).path)[-1].lower()
    return ext if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp") else ".jpg"


def yadisk_path_for(dog_id: int, photo_url: str) -> str:
    """Канонический путь файла на ЯД для данной собаки."""
    return f"{YADISK_FOLDER}/{dog_id}{_ext(photo_url)}"


# ── Яндекс.Диск ───────────────────────────────────────────────────────────────

def yadisk_ensure_folder() -> None:
    """Создаёт папки dogs/ и dogs/photos/ на ЯД если их нет."""
    for folder in ["dogs", YADISK_FOLDER]:
        r = requests.get(f"{YADISK_API}?path={_disk(folder)}", headers=_yd_headers(), timeout=10)
        if r.status_code == 404:
            r2 = requests.put(f"{YADISK_API}?path={_disk(folder)}", headers=_yd_headers(), timeout=10)
            if r2.status_code not in (200, 201):
                logger.warning(f"ЯД: не удалось создать папку '{folder}': HTTP {r2.status_code}")


def yadisk_get_size(yadisk_path: str) -> Optional[int]:
    """Размер файла на ЯД в байтах. None если файла нет или ошибка."""
    try:
        r = requests.get(
            f"{YADISK_API}?path={_disk(yadisk_path)}&fields=size",
            headers=_yd_headers(), timeout=10,
        )
        return r.json().get("size") if r.status_code == 200 else None
    except Exception as e:
        logger.debug(f"yadisk_get_size '{yadisk_path}': {e}")
        return None


def yadisk_upload(data: bytes, yadisk_path: str) -> bool:
    """Загружает bytes на ЯД по указанному пути. True = успех."""
    try:
        r = requests.get(
            f"{YADISK_API}/upload?path={_disk(yadisk_path)}&overwrite=true",
            headers=_yd_headers(), timeout=15,
        )
        if r.status_code != 200:
            logger.warning(f"ЯД upload URL: HTTP {r.status_code}")
            return False
        href = r.json().get("href")
        if not href:
            return False
        r2 = requests.put(href, data=data, timeout=60)
        return r2.status_code in (200, 201)
    except Exception as e:
        logger.error(f"yadisk_upload error: {e}", exc_info=True)
        return False


def yadisk_list_files(limit: int = 10000) -> List[Dict]:
    """
    Список файлов в папке YADISK_FOLDER.
    Возвращает [{"name": "12345.jpg", "size": 54321, "path": "disk:/..."}, ...]
    """
    try:
        url = (
            f"{YADISK_API}?path={_disk(YADISK_FOLDER)}"
            f"&fields=_embedded.items.name,_embedded.items.size,_embedded.items.path"
            f"&limit={limit}"
        )
        r = requests.get(url, headers=_yd_headers(), timeout=15)
        if r.status_code == 200:
            return r.json().get("_embedded", {}).get("items", [])
        return []
    except Exception as e:
        logger.error(f"yadisk_list_files: {e}")
        return []

def yadisk_publish_and_get_url(yadisk_path: str) -> Optional[str]:
    """
    Публикует файл на ЯД и возвращает ПРЯМУЮ ссылку на картинку
    (не yadi.sk/i/... страницу просмотра, а реальный URL файла).

    Алгоритм:
      1. PUT publish — делаем файл публичным
      2. GET метаданных с &fields=public_url,file — берём поле 'file'
         ('file' = прямая ссылка на скачивание, работает в <img src=...>)
      3. Если 'file' недоступен — fallback на download URL через отдельный запрос

    Сохраняем в Dog.photo_yadisk_url — постоянная, не истекает.
    """
    try:
        # Шаг 1: публикуем
        requests.put(
            f"{YADISK_API}/publish?path={_disk(yadisk_path)}",
            headers=_yd_headers(), timeout=10,
        )

        # Шаг 2: получаем метаданные — нас интересует поле 'file'
        # 'file' — прямая ссылка на файл, работает как <img src=...>
        # 'public_url' — страница просмотра (yadi.sk/i/...), НЕ подходит для img
        r = requests.get(
            f"{YADISK_API}?path={_disk(yadisk_path)}&fields=file,public_url,sizes",
            headers=_yd_headers(), timeout=10,
        )
        if r.status_code != 200:
            logger.warning(f"yadisk_publish_and_get_url: HTTP {r.status_code} для '{yadisk_path}'")
            return None

        data = r.json()

        # 'file' — прямая ссылка (лучший вариант)
        direct_url = data.get("file")
        if direct_url:
            logger.debug(f"ЯД: прямая ссылка получена для '{yadisk_path}'")
            return direct_url

        # Fallback: preview (thumbnail, но работает в браузере)
        sizes = data.get("sizes", [])
        if sizes:
            # берём наибольший размер
            biggest = max(sizes, key=lambda s: s.get("name", ""), default=None)
            if biggest and biggest.get("url"):
                logger.debug(f"ЯД: preview URL для '{yadisk_path}'")
                return biggest["url"]

        # Последний fallback: download URL (истекает через 30 мин — плохо, но хоть что-то)
        r2 = requests.get(
            f"{YADISK_API}/download?path={_disk(yadisk_path)}",
            headers=_yd_headers(), timeout=10,
        )
        if r2.status_code == 200:
            href = r2.json().get("href")
            if href:
                logger.warning(f"ЯД: используем временный download URL для '{yadisk_path}' — истечёт через 30 мин")
                return href

        logger.error(f"ЯД: не удалось получить прямую ссылку для '{yadisk_path}'")
        return None

    except Exception as e:
        logger.error(f"yadisk_publish_and_get_url '{yadisk_path}': {e}")
        return None


# ── Источник ──────────────────────────────────────────────────────────────────

def source_content_length(url: str) -> Optional[int]:
    """HEAD-запрос к источнику → Content-Length в байтах."""
    try:
        r = requests.head(url, headers=SOURCE_HEADERS, timeout=10, allow_redirects=True)
        cl = r.headers.get("Content-Length")
        return int(cl) if cl else None
    except Exception as e:
        logger.debug(f"HEAD {url}: {e}")
        return None


def _download_with_zoo_cookies(url: str) -> Optional[bytes]:
    """
    Fallback: скачивает Zoo фото с авторизацией + Referer.
    Zoo проверяет что запрос идёт со страницы сайта.
    """
    try:
        from ..utils.cookie_refresher import get_zoo_cookies
        from ..config import ZOOPORTAL_BASE_URL
        cookies = get_zoo_cookies()
        if not cookies:
            logger.warning("Zoo куки недоступны")
            return None

        headers = {
            **SOURCE_HEADERS,
            "Referer":        f"{ZOOPORTAL_BASE_URL}/pedigree/",
            "Origin":         ZOOPORTAL_BASE_URL,
            "Accept":         "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Sec-Fetch-Dest": "image",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-origin",
        }

        r = requests.get(
            url, headers=headers, cookies=cookies,
            timeout=DOWNLOAD_TIMEOUT, stream=True, allow_redirects=True,
        )
        r.raise_for_status()

        content_type = r.headers.get("Content-Type", "")
        if "text/html" in content_type:
            logger.warning(f"Zoo: всё ещё HTML даже с куками и Referer для {url}")
            return None

        buf = BytesIO()
        size = 0
        for chunk in r.iter_content(CHUNK_SIZE):
            if chunk:
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    return None
                buf.write(chunk)
        result = buf.getvalue() if size > 0 else None
        if result:
            logger.info(f"Zoo: фото скачано с куками ({size}b)")
        return result
    except Exception as e:
        logger.warning(f"Zoo fallback download failed {url}: {e}")
        return None


def download_from_source(url: str) -> Optional[bytes]:
    """
    Скачивает фото с источника.
    Если обычный запрос заблокирован (Zoo антибот) — пробует с куками.
    """
    try:
        r = requests.get(
            url, headers=SOURCE_HEADERS,
            timeout=DOWNLOAD_TIMEOUT, stream=True, allow_redirects=True,
        )
        r.raise_for_status()

        if "text/html" in r.headers.get("Content-Type", ""):
            logger.debug(f"Источник вернул HTML вместо изображения: {url}")
            # Zooportal блокирует без авторизации — пробуем с куками
            if "zooportal" in url:
                logger.info(f"Zoo: пробуем с куками для {url}")
                return _download_with_zoo_cookies(url)
            return None

        buf = BytesIO()
        size = 0
        for chunk in r.iter_content(CHUNK_SIZE):
            if chunk:
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    logger.warning(f"Файл >10МБ, пропуск: {url}")
                    return None
                buf.write(chunk)

        return buf.getvalue() if size > 0 else None

    except requests.HTTPError as e:
        logger.warning(f"HTTP {e.response.status_code} скачивание {url}")
        return None
    except Exception as e:
        logger.warning(f"Ошибка скачивания {url}: {e}")
        return None


# ── Основная логика ───────────────────────────────────────────────────────────

def sync_photo_to_yadisk(dog_id: int, photo_url: str, current_yadisk_path: Optional[str]) -> Dict:
    """
    Скачивает фото с источника и загружает на ЯД.

    Алгоритм:
      1. Определяем целевой путь на ЯД (текущий или новый по dog_id)
      2. HEAD к источнику → source_size
      3. GET метаданных ЯД → yadisk_size
      4. source_size == yadisk_size → пропускаем (фото то же самое)
      5. Иначе → скачиваем → загружаем → возвращаем путь

    Возвращает dict:
        status: "skipped" | "uploaded" | "error"
        path:   путь на ЯД (при uploaded и skipped)
        reason: причина (для логов)
    """
    yadisk_path = current_yadisk_path or yadisk_path_for(dog_id, photo_url)

    source_size = source_content_length(photo_url)
    yadisk_size = yadisk_get_size(yadisk_path)

    # Байты совпадают — файл уже на ЯД и не изменился.
    # Но публичный URL всё равно получаем — вдруг он ещё не сохранён в БД.
    if source_size and yadisk_size and source_size == yadisk_size:
        logger.debug(f"dog {dog_id}: фото не изменилось ({source_size}b), пропуск")
        yadisk_url = yadisk_publish_and_get_url(yadisk_path)
        return {
            "status":     "skipped",
            "path":       yadisk_path,
            "yadisk_url": yadisk_url,
            "reason":     f"байты совпадают ({source_size}b)",
        }

    if yadisk_size is None:
        reason = "нет на ЯД — первая загрузка"
    elif source_size and source_size != yadisk_size:
        reason = f"фото изменилось: {yadisk_size}b → {source_size}b"
    else:
        reason = "Content-Length недоступен у источника"

    logger.info(f"📷 dog {dog_id}: {reason}")

    data = download_from_source(photo_url)
    if data is None:
        return {"status": "error", "error": "не удалось скачать с источника"}

    ok = yadisk_upload(data, yadisk_path)
    if not ok:
        return {"status": "error", "error": "ошибка загрузки на ЯД"}

    # Публикуем файл и получаем постоянный URL для хранения в БД
    yadisk_url = yadisk_publish_and_get_url(yadisk_path)

    return {
        "status":     "uploaded",
        "path":       yadisk_path,
        "yadisk_url": yadisk_url,
        "size":       len(data),
        "reason":     reason,
    }


def fetch_zoo_photo_via_playwright(dog_id: int, zooportal_id: str, photo_url: str) -> Dict:
    """
    Открывает страницу собаки на Zooportal через Playwright,
    скачивает фото через авторизованный контекст и загружает на ЯД.

    Используется для собак у которых photo_url с Zoo но фото ещё не на ЯД.
    Playwright нужен потому что Zoo блокирует прямые HTTP запросы к фото
    (hotlink protection + проверка сессии).

    Вызывается из таски fetch_zoo_photo_task.
    """
    from ..parsers.zooportal import BrowserManager
    from ..config import ZOOPORTAL_BASE_URL, ZOOPORTAL_DOG_PATH

    logger.info(f"📷 Zoo Playwright фото: dog_id={dog_id}, zoo_id={zooportal_id}")

    try:
        with BrowserManager() as browser:
            # Открываем страницу собаки — устанавливает сессию и Referer
            url = f"{ZOOPORTAL_BASE_URL}{ZOOPORTAL_DOG_PATH}/{zooportal_id}/"
            browser.fetch_page(url)

            # Скачиваем фото в том же контексте
            photo_bytes = browser.download_photo_bytes(photo_url)

    except Exception as e:
        logger.error(f"Zoo Playwright: ошибка для dog_id={dog_id}: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}

    if not photo_bytes:
        return {"status": "error", "error": "фото не скачалось через Playwright"}

    return upload_photo_bytes_to_yadisk(dog_id, photo_url, photo_bytes)


def upload_photo_bytes_to_yadisk(dog_id: int, photo_url: str, photo_bytes: bytes) -> Dict:
    """
    Загружает уже скачанные байты фото на ЯД.
    Вызывается из integration когда байты получены при парсинге Zoo.
    Не делает повторный запрос к источнику.
    """
    yadisk_path = yadisk_path_for(dog_id, photo_url)

    ok = yadisk_upload(photo_bytes, yadisk_path)
    if not ok:
        return {"status": "error", "error": "ошибка загрузки на ЯД"}

    yadisk_url = yadisk_publish_and_get_url(yadisk_path)
    logger.info(f"📷 dog {dog_id}: фото залито на ЯД из байт ({len(photo_bytes)}b)")

    return {
        "status":     "uploaded",
        "path":       yadisk_path,
        "yadisk_url": yadisk_url,
        "size":       len(photo_bytes),
    }


def sync_yadisk_to_db() -> Dict:
    """
    ЯД → БД: сканирует disk:/dogs/photos/, по имени файла
    (12345.jpg → dog_id=12345) обновляет photo_yadisk_path в БД
    для собак у которых это поле пустое.

    Используй если:
    - Загружал фото на ЯД вручную
    - photo_yadisk_path в БД сбросился
    - После восстановления данных
    """
    from ..models import Dog

    files = yadisk_list_files()
    if not files:
        return {"status": "error", "error": "Папка пуста или не найдена на ЯД"}

    updated = not_found = already_set = 0

    for file in files:
        name      = file.get("name", "")
        stem      = os.path.splitext(name)[0]
        file_path = file.get("path", "").replace("disk:/", "")

        try:
            dog_id = int(stem)
        except ValueError:
            continue

        try:
            dog = Dog.objects.using("dogs_db").only("id", "photo_yadisk_path").get(pk=dog_id)
        except Dog.DoesNotExist:
            not_found += 1
            continue

        if dog.photo_yadisk_path:
            already_set += 1
            continue

        Dog.objects.using("dogs_db").filter(pk=dog_id).update(photo_yadisk_path=file_path)
        updated += 1

    return {
        "status":         "done",
        "files_on_yadisk": len(files),
        "updated_in_db":  updated,
        "already_had_path": already_set,
        "not_found_in_db": not_found,
    }


def get_photo_stats() -> Dict:
    """Статистика по фото: сколько в БД, сколько на ЯД."""
    from ..models import Dog

    total       = Dog.objects.using("dogs_db").count()
    with_url    = Dog.objects.using("dogs_db").exclude(photo_url__isnull=True).exclude(photo_url="").count()
    with_yadisk = Dog.objects.using("dogs_db").exclude(photo_yadisk_path__isnull=True).exclude(photo_yadisk_path="").count()

    yadisk_info = {}
    try:
        r = requests.get(
            f"{YADISK_API}?path={_disk(YADISK_FOLDER)}&fields=_embedded.total",
            headers=_yd_headers(), timeout=10,
        )
        if r.status_code == 200:
            yadisk_info = {
                "folder": f"disk:/{YADISK_FOLDER}",
                "files_on_disk": r.json().get("_embedded", {}).get("total", "?"),
            }
        elif r.status_code == 404:
            yadisk_info = {"folder": f"disk:/{YADISK_FOLDER}", "files_on_disk": 0, "note": "папка не создана"}
    except Exception as e:
        yadisk_info = {"error": str(e)}

    return {
        "total_dogs":          total,
        "dogs_with_photo_url": with_url,
        "dogs_on_yadisk":      with_yadisk,
        "missing":             with_url - with_yadisk,
        "yadisk":              yadisk_info,
    }


def get_dogs_for_bulk_sync(
    id_from: int = 1,
    id_to: Optional[int] = None,
    limit: int = 500,
    only_without_yadisk: bool = True,
) -> List[Dict]:
    """Выбирает собак с photo_url для bulk-синхронизации."""
    from ..models import Dog

    qs = (
        Dog.objects.using("dogs_db")
        .filter(photo_url__isnull=False, id__gte=id_from)
        .exclude(photo_url="")
        .only("id")
        .order_by("id")
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)
    if only_without_yadisk:
        qs = qs.filter(photo_yadisk_path__isnull=True)

    return list(qs.values("id")[:limit])


_PUBLIC_KEY_CACHE: dict = {}  # простой in-memory кеш для public_key


def get_yadisk_public_key() -> Optional[str]:
    """
    Возвращает public_key папки dogs/photos на ЯД.
    При первом вызове публикует папку и кеширует ключ.
    При повторных — возвращает из кеша (не ходит на ЯД каждый раз).
    """
    if _PUBLIC_KEY_CACHE.get("key"):
        return _PUBLIC_KEY_CACHE["key"]

    try:
        # Сначала проверяем — вдруг папка уже опубликована
        r = requests.get(
            f"{YADISK_API}?path={_disk(YADISK_FOLDER)}&fields=public_key",
            headers=_yd_headers(), timeout=10,
        )
        if r.status_code == 200:
            key = r.json().get("public_key")
            if key:
                _PUBLIC_KEY_CACHE["key"] = key
                return key

        # Публикуем папку
        requests.put(
            f"{YADISK_API}/publish?path={_disk(YADISK_FOLDER)}",
            headers=_yd_headers(), timeout=10,
        )

        # Получаем public_key
        r2 = requests.get(
            f"{YADISK_API}?path={_disk(YADISK_FOLDER)}&fields=public_key",
            headers=_yd_headers(), timeout=10,
        )
        if r2.status_code == 200:
            key = r2.json().get("public_key")
            if key:
                _PUBLIC_KEY_CACHE["key"] = key
                logger.info(f"✅ ЯД: папка опубликована, public_key={key[:20]}...")
                return key

    except Exception as e:
        logger.error(f"get_yadisk_public_key: {e}")

    return None


def get_public_photo_url(yadisk_path: str) -> Optional[str]:
    """
    Возвращает прямую публичную ссылку на файл в папке dogs/photos.

    Как работает:
      yadisk_path = 'dogs/photos/12345.jpg'
      filename    = '12345.jpg'
      URL = https://downloader.disk.yandex.ru/public/files/{public_key}/{filename}

    Эта ссылка постоянная (не истекает как download URL).
    Работает только если папка опубликована через get_yadisk_public_key().
    """
    if not yadisk_path:
        return None

    import os
    filename = os.path.basename(yadisk_path)  # '12345.jpg'

    key = get_yadisk_public_key()
    if not key:
        return None

    # Публичная ссылка на файл внутри публичной папки
    return f"https://downloader.disk.yandex.ru/public/files/{key}/{filename}"