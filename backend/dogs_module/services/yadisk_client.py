# dogs_module/services/yadisk_client.py
"""
HTTP-клиент для Яндекс.Диск API.
Использует httpx вместо requests — нет SSLZeroReturnError при загрузке файлов.
"""

import logging
import time
from typing import Dict, List, Optional

import ssl
import httpx

from ..config.yadisk import (
    YADISK_API,
    YADISK_FOLDER,
    YANDEX_DISK_TOKEN,
    YADISK_TIMEOUT,
    YADISK_UPLOAD_TIMEOUT,
    YADISK_PUT_TIMEOUT,
)

logger = logging.getLogger(__name__)


# Утилиты
def _token() -> str:
    if not YANDEX_DISK_TOKEN:
        raise ValueError("YANDEX_DISK_TOKEN не задан в .env")
    return YANDEX_DISK_TOKEN


def _headers() -> dict:
    return {"Authorization": f"OAuth {_token()}"}


def _disk(path: str) -> str:
    """'dogs/photos/1.jpg'  →  'disk:/dogs/photos/1.jpg'"""
    return path if path.startswith("disk:/") else f"disk:/{path}"


def _ssl_ctx() -> ssl.SSLContext:
    """SSL контекст который игнорирует отсутствие TLS close_notify."""
    ctx = ssl.create_default_context()
    try:
        # Python 3.11+
        ctx.options |= ssl.OP_IGNORE_UNEXPECTED_EOF
    except AttributeError:
        # Python 3.10: числовое значение флага из OpenSSL
        ctx.options |= 0x00000080
    return ctx


def _client(timeout: float = None) -> httpx.Client:
    return httpx.Client(
        headers=_headers(),
        timeout=timeout or YADISK_TIMEOUT,
        follow_redirects=True,
        verify=_ssl_ctx(),
    )

# ── Операции с папками ────────────────────────────────────────────────────────

def ensure_folder(path: str) -> None:
    """Создаёт папку на ЯД если её нет. Тихо пропускает если уже существует."""
    try:
        with _client() as c:
            r = c.get(f"{YADISK_API}?path={_disk(path)}")
            if r.status_code == 404:
                r2 = c.put(f"{YADISK_API}?path={_disk(path)}")
                if r2.status_code not in (200, 201):
                    logger.warning(f"ЯД: не удалось создать папку '{path}': HTTP {r2.status_code}")
    except Exception as e:
        logger.warning(f"yadisk ensure_folder '{path}': {e}")


def ensure_photos_folder() -> None:
    """Создаёт dogs/ и dogs/photos/ если их нет."""
    ensure_folder("dogs")
    ensure_folder(YADISK_FOLDER)


# ── Операции с файлами ────────────────────────────────────────────────────────

def get_file_size(yadisk_path: str) -> Optional[int]:
    """Размер файла на ЯД в байтах. None если файла нет или ошибка."""
    try:
        with _client() as c:
            r = c.get(f"{YADISK_API}?path={_disk(yadisk_path)}&fields=size")
            return r.json().get("size") if r.status_code == 200 else None
    except Exception as e:
        logger.debug(f"yadisk get_file_size '{yadisk_path}': {e}")
        return None


def upload(data: bytes, yadisk_path: str) -> bool:
    """
    Загружает bytes на ЯД. True = успех.
    Retry 3 раза — каждый раз получает новый upload URL
    (href одноразовый и быстро истекает).
    """
    for attempt in range(3):
        try:
            with _client(timeout=YADISK_UPLOAD_TIMEOUT) as c:
                # Шаг 1: получить одноразовый upload URL
                r = c.get(
                    f"{YADISK_API}/upload?path={_disk(yadisk_path)}&overwrite=true",
                )
                if r.status_code != 200:
                    logger.warning(f"ЯД: не получили upload URL: HTTP {r.status_code}")
                    return False

                href = r.json().get("href")
                if not href:
                    return False

                # Шаг 2: загрузить файл по одноразовому URL
                # content= вместо data= — разница между httpx и requests
                r2 = c.put(href, content=data, timeout=YADISK_PUT_TIMEOUT)
                return r2.status_code in (200, 201)

        except Exception as e:
            if attempt < 2:
                wait = 2 ** (attempt + 1)  # 2с, 4с
                logger.warning(
                    f"ЯД upload попытка {attempt + 1}/3: {type(e).__name__}, "
                    f"повтор через {wait}с"
                )
                time.sleep(wait)
            else:
                logger.error(f"yadisk upload error: {e}", exc_info=True)
                return False

    return False


def list_files(folder: str = None, limit: int = 10000) -> List[Dict]:
    """
    Список файлов в папке.
    Возвращает [{"name": "12345.jpg", "size": 54321, "path": "disk:/..."}, ...]
    """
    target = folder or YADISK_FOLDER
    try:
        url = (
            f"{YADISK_API}?path={_disk(target)}"
            f"&fields=_embedded.items.name,_embedded.items.size,_embedded.items.path"
            f"&limit={limit}"
        )
        with _client(timeout=YADISK_UPLOAD_TIMEOUT) as c:
            r = c.get(url)
            if r.status_code == 200:
                return r.json().get("_embedded", {}).get("items", [])
            return []
    except Exception as e:
        logger.error(f"yadisk list_files: {e}")
        return []


def count_files(folder: str = None) -> Optional[int]:
    """Количество файлов в папке (без листинга)."""
    target = folder or YADISK_FOLDER
    try:
        with _client() as c:
            r = c.get(f"{YADISK_API}?path={_disk(target)}&fields=_embedded.total")
            if r.status_code == 200:
                return r.json().get("_embedded", {}).get("total")
            if r.status_code == 404:
                return 0
            return None
    except Exception as e:
        logger.error(f"yadisk count_files: {e}")
        return None


def publish_and_get_url(yadisk_path: str) -> Optional[str]:
    for attempt in range(3):
        try:
            with _client() as c:
                c.put(f"{YADISK_API}/publish?path={_disk(yadisk_path)}")
                r = c.get(
                    f"{YADISK_API}?path={_disk(yadisk_path)}&fields=file,public_url,sizes"
                )
                if r.status_code != 200:
                    logger.warning(f"yadisk publish_and_get_url: HTTP {r.status_code}")
                    return None
                data = r.json()
                direct_url = data.get("file")
                if direct_url:
                    return direct_url
                sizes = data.get("sizes", [])
                if sizes:
                    biggest = max(sizes, key=lambda s: s.get("name", ""), default=None)
                    if biggest and biggest.get("url"):
                        return biggest["url"]
        except Exception as e:
            if attempt < 2:
                logger.warning(f"yadisk publish_and_get_url попытка {attempt + 1}/3: {e}")
                time.sleep(2 ** attempt)
            else:
                logger.error(f"yadisk publish_and_get_url '{yadisk_path}': {e}")
                return None
    return None


def get_public_key(folder: str = None) -> Optional[str]:
    """Возвращает public_key опубликованной папки. При необходимости публикует."""
    target = folder or YADISK_FOLDER
    try:
        with _client() as c:
            r = c.get(f"{YADISK_API}?path={_disk(target)}&fields=public_key")
            if r.status_code == 200:
                key = r.json().get("public_key")
                if key:
                    return key

            c.put(f"{YADISK_API}/publish?path={_disk(target)}")
            r2 = c.get(f"{YADISK_API}?path={_disk(target)}&fields=public_key")
            if r2.status_code == 200:
                return r2.json().get("public_key")

    except Exception as e:
        logger.error(f"yadisk get_public_key: {e}")

    return None


def download(yadisk_path: str) -> Optional[bytes]:
    """Скачивает файл с ЯД (для backfill хэшей существующих фото)."""
    try:
        with _client(timeout=YADISK_UPLOAD_TIMEOUT) as c:
            r = c.get(f"{YADISK_API}/download?path={_disk(yadisk_path)}")
            if r.status_code != 200:
                return None
            href = r.json().get("href")
            if not href:
                return None
            r2 = c.get(href, timeout=YADISK_PUT_TIMEOUT)
            return r2.content if r2.status_code == 200 else None
    except Exception as e:
        logger.error(f"yadisk download '{yadisk_path}': {e}")
        return None


def delete(yadisk_path: str, permanently: bool = True) -> bool:
    """Удаляет файл с ЯД."""
    try:
        with _client() as c:
            r = c.delete(
                f"{YADISK_API}?path={_disk(yadisk_path)}"
                f"&permanently={str(permanently).lower()}"
            )
            return r.status_code in (200, 202, 204)
    except Exception as e:
        logger.error(f"yadisk delete '{yadisk_path}': {e}")
        return False