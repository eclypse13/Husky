# dogs_module/services/parse_cache.py
"""
Redis-кэш состояния парсинга (результат разбора Zoo-страницы и отметки).
"""

import logging
from django.core.cache import caches

logger = logging.getLogger(__name__)

_TTL_PARSE_RESULT = 1 * 24 * 3600  # 24 часа, результат парсинга Zoo страницы
_TTL_RECURSIVE_DONE = 2 * 24 * 3600  # 2 дня, Zoo собака обработана рекурсивно
_TTL_BA_FULLY_PARSED = 3 * 24 * 3600  # 3 дня, B  A-дерево разобрано полностью
_KEY_BA_FULLY_PARSED = "ba:fully_parsed:{uuid}"


def _cache():
    return caches['parsers']


def _key_parse_result(zooportal_id: str, generations: int) -> str:
    return f"parse:result:{zooportal_id}:{generations}"


def _key_recursive_done(zooportal_id: str, generations: int) -> str:
    return f"parse:recursive_done:{zooportal_id}:{generations}"


# Кэшированный результат разбора Zoo-страницы
def get_parse_result(zooportal_id: str, generations: int = 3):
    return _cache().get(_key_parse_result(zooportal_id, generations))


# Сохраняет результат разбора Zoo-страницы
def set_parse_result(zooportal_id: str, generations: int, result) -> None:
    _cache().set(_key_parse_result(zooportal_id, generations), result, timeout=_TTL_PARSE_RESULT)


def is_parse_cached(zooportal_id: str, generations: int = 3) -> bool:
    return _cache().get(_key_parse_result(zooportal_id, generations)) is not None


def is_recursively_done(zooportal_id: str, generations: int = 3) -> bool:
    return _cache().get(_key_recursive_done(zooportal_id, generations)) is not None


def mark_recursively_done(zooportal_id: str, generations: int = 3) -> None:
    _cache().set(_key_recursive_done(zooportal_id, generations), 1, timeout=_TTL_RECURSIVE_DONE)


def invalidate_parse_cache(zooportal_id: str, generations: int = 3) -> None:
    c = _cache()
    c.delete(_key_parse_result(zooportal_id, generations))
    c.delete(_key_recursive_done(zooportal_id, generations))
    logger.info(f"🗑️ Кеш сброшен для {zooportal_id}")


# BA полное дерево
def is_ba_fully_parsed(uuid: str) -> bool:
    try:
        return bool(_cache().get(_KEY_BA_FULLY_PARSED.format(uuid=uuid)))
    except Exception:
        return False


def mark_ba_fully_parsed(uuid: str) -> None:
    try:
        _cache().set(_KEY_BA_FULLY_PARSED.format(uuid=uuid), 1, timeout=_TTL_BA_FULLY_PARSED)
    except Exception:
        pass


def invalidate_ba_fully_parsed(uuid: str) -> None:
    try:
        _cache().delete(_KEY_BA_FULLY_PARSED.format(uuid=uuid))
    except Exception:
        pass
