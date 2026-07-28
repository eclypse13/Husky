"""
Конфигурация интеграции с Яндекс.Диском.
"""

from decouple import config as _config
from .scraping import USER_AGENT

# Яндекс.Диск API
YADISK_API = "https://cloud-api.yandex.net/v1/disk/resources"
YADISK_PUBLIC_DOWNLOADER = "https://downloader.disk.yandex.ru/public/files"
YADISK_FOLDER = "dogs/photos"
# YANDEX_DISK_TOKEN = _config("YANDEX_DISK_TOKEN", default="")
# для dev и дебага
YANDEX_DISK_TOKEN = _config("", default="")

# Таймауты HTTP, сек
YADISK_TIMEOUT = 30  # обычные API-вызовы ЯД
YADISK_UPLOAD_TIMEOUT = 30  # запрос ссылки на загрузку
YADISK_PUT_TIMEOUT = 60  # сам PUT файла
DOWNLOAD_TIMEOUT = 60  # скачивание фото с источника
HEAD_TIMEOUT = 30  # HEAD-проверка размера источника

# Ограничения файла
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 МБ
CHUNK_SIZE = 16 * 1024
ALLOWED_PHOTO_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")

# Заголовки запроса к источнику фото
SOURCE_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "image/*,*/*;q=0.8",
}
DEFAULT_PHOTO_HASHES = frozenset({
    "7f666ee537b86dcf93c9dbd16935fc2ada5c7551583c14b9b3bca9f2d3ca6ba0",  # серая заглушка zooportal
})

# Префильтр по URL — отсекаем заглушки без скачивания
PLACEHOLDER_URL_PATTERNS = (
    "noimage", "no_photo", "nophoto", "no-photo",
    "placeholder", "default", "dummy", "blank", "stub",
)
