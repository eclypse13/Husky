"""
Доступ к данным Title.
"""

import logging

logger = logging.getLogger(__name__)


def upsert_title(dog, short_name: str, country, fields: dict) -> bool:
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
