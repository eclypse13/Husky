# dogs_module/repositories/title_repository.py
"""
Доступ к данным Title (DB).
"""

import logging

logger = logging.getLogger(__name__)


def upsert_title(dog, short_name: str, country, fields: dict) -> bool:
    """
    get_or_create титула по (dog, short_name, country); при существовании — обновляет.
    Возвращает created (True/False).
    """
    from ..models import Title

    _, created = Title.objects.using('dogs_db').get_or_create(
        dog=dog,
        short_name=short_name,
        country=country,
        defaults=fields,
    )
    if not created:
        Title.objects.using('dogs_db').filter(
            dog=dog, short_name=short_name, country=country
        ).update(**fields)
    return created
