# dogs_module/repositories/litter_repository.py
"""
Доступ к данным Litter и Dogsiblinglink.
"""

import logging

logger = logging.getLogger(__name__)


def upsert_litter(dam, sire, date_of_birth, fields: dict) -> None:
    """
    update_or_create помёта по уникальному ключу (dam, sire, date_of_birth).
    fields — дополнительные поля (litter_male_count и т.д.), None-значения отбрасываются.
    """
    from ..models import Litter

    clean = {k: v for k, v in fields.items() if v is not None}
    Litter.objects.using('dogs_db').update_or_create(
        dam=dam,
        sire=sire,
        date_of_birth=date_of_birth,
        defaults=clean,
    )


def upsert_sibling(dog, sibling_uuid: str, name: str, sex: int) -> None:
    """
    Находит или создаёт собаку-сиблинга по uuid и линкует её к dog.
    Если Dog с таким uuid уже есть — просто линкует, не перезаписывает поля.
    """
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
