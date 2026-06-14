# dogs_module/repositories/owner_repository.py
"""
Доступ к данным Owner и связующей таблице Dogownerlink.
"""

import logging

logger = logging.getLogger(__name__)


def upsert_owner(
        name: str,
        uuid: str = None,
        is_main_owner: bool = True,
        kennel: str = None,
        owner_url: str = None,
        kennel_url: str = None,
):
    """
    Находит или создаёт Owner.
    Поиск: по uuid (если есть), иначе по name.
    Возвращает (owner, created).
    """
    from ..models import Owner

    defaults = {
        'name': name,
        'is_main_owner': is_main_owner,
        'kennel': kennel,
        'owner_url': owner_url,
        'kennel_url': kennel_url,
    }
    # Убираем None-значения чтобы не перезаписывать существующие поля
    defaults = {k: v for k, v in defaults.items() if v is not None}

    if uuid:
        try:
            owner, created = Owner.objects.using('dogs_db').get_or_create(
                uuid=uuid,
                defaults=defaults,
            )
        except Exception:
            owner = Owner.objects.using('dogs_db').filter(uuid=uuid).first()
            if not owner:
                raise
            created = False
    else:
        try:
            owner, created = Owner.objects.using('dogs_db').get_or_create(
                name=name,
                defaults={k: v for k, v in defaults.items() if k != 'name'},
            )
        except Exception:
            owner = Owner.objects.using('dogs_db').filter(name=name).first()
            if not owner:
                raise
            created = False

    return owner, created


def link_to_dog(dog, owner) -> None:
    """Создаёт связь Dog ↔ Owner если её ещё нет."""
    from ..models import Dogownerlink
    Dogownerlink.objects.using('dogs_db').get_or_create(dog=dog, owner=owner)


def dog_has_owners(dog) -> bool:
    """True если у собаки уже есть хотя бы один владелец."""
    return dog.owners.using('dogs_db').exists()
