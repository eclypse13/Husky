"""
Доступ к данным Dogsiblinglink.
"""

import logging

logger = logging.getLogger(__name__)


def upsert_sibling(dog, sibling_uuid: str, name: str, sex: int) -> None:
    from ..models import Dog, Dogsiblinglink

    sibling, _ = Dog.objects.using('dogs_db').get_or_create(
        uuid=sibling_uuid,
        defaults={
            'registered_name': name,
            'sex': sex,
            'source': 'breedarchive.com',
        },
    )
    Dogsiblinglink.objects.using('dogs_db').get_or_create(dog=dog, sibling=sibling)
