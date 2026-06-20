"""
Загрузка и сохранение моделей.
"""

import logging
from pathlib import Path

from ..config import settings, TARGETS

logger = logging.getLogger(__name__)

# Кэш загруженных моделей
_cache: dict = {}


# Возвращает путь к файлу модели
def model_path(name: str) -> Path:
    return settings.models_dir / f"catboost_{name}.cbm"


# Сохраняет модель на диск и обновляет кэш
def save_model(model, name: str) -> None:
    path = model_path(name)
    model.save_model(str(path))
    _cache[name] = model
    logger.info(f"model_store: сохранена модель '{name}' → {path}")


# Загружает модель из кэша или с диска
def load_model(name: str):
    if name in _cache:
        return _cache[name]

    path = model_path(name)
    if not path.exists():
        logger.debug(f"model_store: модель '{name}' не найдена")
        return None

    try:
        from catboost import CatBoostClassifier
        model = CatBoostClassifier()
        model.load_model(str(path))
        _cache[name] = model
        logger.info(f"model_store: загружена модель '{name}'")
        return model
    except Exception as e:
        logger.error(f"model_store: ошибка загрузки '{name}': {e}")
        return None


# Сбрасывает кэш — нужно после переобучения
def invalidate_cache(name: str = None) -> None:
    if name:
        _cache.pop(name, None)
    else:
        _cache.clear()
    logger.info(f"model_store: кэш сброшен ({name or 'все'})")


# Возвращает список обучаемых моделей и их статус
def list_trained_models() -> dict:
    return {
        name: "trained" if model_path(name).exists() else "not_trained"
        for name in TARGETS
    }
