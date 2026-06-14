# dogs_module/services/title_service.py
"""
Сохранение титулов собаки.
"""

import logging

from ..utils.titles import build_title_entries
from ..repositories import title_repository as repo

logger = logging.getLogger(__name__)


def save_dog_titles(dog, prefix_text, suffix_text, source: str) -> None:
    """
    Парсит prefix/suffix-строки и сохраняет титулы в БД.
    get_or_create по (dog, short_name, country) — дублей не создаёт.
    """
    if not dog or not dog.pk:
        return

    entries = build_title_entries(prefix_text, suffix_text, source)
    if not entries:
        return

    saved = failed = 0
    for entry in entries:
        short_name = entry.pop('short_name')
        country = entry.pop('country')
        try:
            repo.upsert_title(dog, short_name, country, entry)
            saved += 1
        except Exception as exc:
            failed += 1
            logger.warning(
                f"Ошибка сохранения титула '{short_name}' для dog.id={dog.pk}: {exc}"
            )

    logger.info(f"Титулы dog.id={dog.pk}: сохранено {saved}, ошибок {failed}")
