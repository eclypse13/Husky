# dogs_module/utils/cache.py
"""
Утилиты кеширования для парсеров.
"""
import hashlib
import logging
from functools import wraps
from typing import Any, Optional

from django.core.cache import caches

logger = logging.getLogger(__name__)


def _cache(alias: str = 'parsers'):
    return caches[alias]


def cache_get(key: str, alias: str = 'parsers', default: Any = None) -> Any:
    try:
        value = _cache(alias).get(key, default)
        if value is not None and value != default:
            logger.debug(f"CACHE HIT [{alias}]: {key}")
        return value
    except Exception as e:
        logger.error(f"cache_get [{alias}] {key}: {e}")
        return default


def cache_set(key: str, value: Any, ttl: Optional[int] = None, alias: str = 'parsers') -> None:
    try:
        _cache(alias).set(key, value, timeout=ttl)
        logger.debug(f"CACHE SET [{alias}]: {key}")
    except Exception as e:
        logger.error(f"cache_set [{alias}] {key}: {e}")


def cache_delete(key: str, alias: str = 'parsers') -> None:
    try:
        _cache(alias).delete(key)
    except Exception as e:
        logger.error(f"cache_delete [{alias}] {key}: {e}")


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """Генерирует ключ кеша. Если длиннее 200 — усекает через MD5."""
    parts = [prefix] + [str(a).lower().strip() for a in args]
    parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
    key = ":".join(parts)
    if len(key) > 200:
        hash_part = hashlib.md5(key.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_part}"
    return key


def cached(ttl: Optional[int] = None, alias: str = 'parsers', key_prefix: str = ""):
    """Декоратор кеширования результатов функции."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            prefix = key_prefix or func.__name__
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            cached_v = cache_get(cache_key, alias=alias)
            if cached_v is not None:
                return cached_v
            result = func(*args, **kwargs)
            cache_set(cache_key, result, ttl=ttl, alias=alias)
            return result

        return wrapper

    return decorator


# Обратная совместимость: старый класс RedisCache как тонкая обёртка ───────

class RedisCache:
    """
    Обёртка для обратной совместимости.
    """

    def __init__(self, cache_alias: str = 'parsers'):
        self.cache_alias = cache_alias

    def get(self, key: str, default: Any = None) -> Any:
        return cache_get(key, alias=self.cache_alias, default=default)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        cache_set(key, value, ttl=ttl, alias=self.cache_alias)

    def delete(self, key: str) -> None:
        cache_delete(key, alias=self.cache_alias)

    def clear(self) -> None:
        try:
            _cache(self.cache_alias).clear()
        except Exception as e:
            logger.error(f"cache clear [{self.cache_alias}]: {e}")


# Глобальные инстансы для обратной совместимости
parser_cache = RedisCache('parsers')
default_cache = RedisCache('default')
