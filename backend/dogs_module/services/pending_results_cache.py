"""
Redis хранилище ожидающих результатов выставки.
"""

import json
import logging
from django.core.cache import caches

logger = logging.getLogger(__name__)

_PREFIX = "pending_show_results"
_TTL = 3600 * 24 * 1  # 1 день


def _cache():
    return caches['parsers']


def _key(show_id: str) -> str:
    return f"{_PREFIX}:{show_id}"


# Сохраняет список результатов в Redis для указанной выставки
def store(show_id: str, results: list) -> None:
    try:
        existing = retrieve(show_id)
        existing_ids = {r.get('zooportal_dog_id') for r in existing}
        new_items = [r for r in results if r.get('zooportal_dog_id') not in existing_ids]
        merged = existing + new_items
        _cache().set(_key(show_id), json.dumps(merged, default=str), timeout=_TTL)
        logger.debug(f"pending_cache: show_id={show_id}, всего={len(merged)}, новых={len(new_items)}")
    except Exception as e:
        logger.error(f"pending_cache.store show_id={show_id}: {e}")


# Достаёт ожидающие результаты из Redis
def retrieve(show_id: str) -> list:
    try:
        data = _cache().get(_key(show_id))
        return json.loads(data) if data else []
    except Exception as e:
        logger.error(f"pending_cache.retrieve show_id={show_id}: {e}")
        return []


# Перезаписывает список целиком
def save(show_id: str, results: list) -> None:
    try:
        _cache().set(_key(show_id), json.dumps(results, default=str), timeout=_TTL)
    except Exception as e:
        logger.error(f"pending_cache.save show_id={show_id}: {e}")


# Удаляет все ожидающие результаты для выставки
def clear(show_id: str) -> None:
    try:
        _cache().delete(_key(show_id))
    except Exception as e:
        logger.error(f"pending_cache.clear show_id={show_id}: {e}")


# Возвращает все show_id у которых есть ожидающие результаты
def all_show_ids() -> list:
    try:
        keys = _cache().keys(f"{_PREFIX}:*") or []
        result = []
        for k in keys:
            # Нормализуем: Django cache может добавлять имя backend как префикс
            if f"{_PREFIX}:" in k:
                result.append(k.split(f"{_PREFIX}:")[-1])
        return result
    except Exception as e:
        logger.error(f"pending_cache.all_show_ids: {e}")
        return []
