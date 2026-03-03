# dogs_module/utils/cache.py
"""
Redis кэш для парсеров.
"""

from django.core.cache import caches
from functools import wraps
import hashlib
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """Обёртка над Django Redis cache"""

    def __init__(self, cache_alias: str = 'parsers'):
        self.cache = caches[cache_alias]
        self.cache_alias = cache_alias

    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение из кэша"""
        try:
            value = self.cache.get(key, default)
            if value is not None and value != default:
                logger.debug(f"CACHE HIT [{self.cache_alias}]: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Сохранить значение в кэш"""
        try:
            self.cache.set(key, value, timeout=ttl)
            logger.debug(f"CACHE SET [{self.cache_alias}]: {key}")
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    def delete(self, key: str):
        """Удалить ключ"""
        try:
            self.cache.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

    def clear(self):
        """Очистить весь кэш"""
        try:
            self.cache.clear()
        except Exception as e:
            logger.error(f"Cache clear error: {e}")


# Глобальные экземпляры
parser_cache = RedisCache('parsers')
default_cache = RedisCache('default')


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Генерация ключа кэша"""
    parts = [prefix]

    for arg in args:
        parts.append(str(arg).lower().strip())

    for k, v in sorted(kwargs.items()):
        parts.append(f"{k}={v}")

    key = ":".join(parts)

    if len(key) > 200:
        hash_part = hashlib.md5(key.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_part}"

    return key


def cached(ttl: Optional[int] = None, cache_alias: str = 'parsers', key_prefix: str = ""):
    """Декоратор для кэширования результатов"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = RedisCache(cache_alias)
            prefix = key_prefix or func.__name__
            cache_key = generate_cache_key(prefix, *args, **kwargs)

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator