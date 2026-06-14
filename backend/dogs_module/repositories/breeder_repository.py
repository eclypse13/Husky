# dogs_module/repositories/breeder_repository.py
"""
Доступ к данным Breeder и связующей таблице Dogbreederlink.
"""

import logging

logger = logging.getLogger(__name__)


def upsert_breeder(
        name: str,
        uuid: str = None,
        kennel: str = None,
        is_breeder: bool = True,
        breeder_url: str = None,
        kennel_url: str = None,
):
    """
    Находит или создаёт Breeder.
    Поиск: по uuid (если есть), иначе по name.
    Если kennel пустой у существующей записи — дозаписывает.
    Возвращает (breeder, created).
    """
    from ..models import Breeder

    defaults = {
        'name': name,
        'kennel': kennel,
        'is_breeder': is_breeder,
    }
    if breeder_url:
        defaults['breeder_url'] = breeder_url
    if kennel_url:
        defaults['kennel_url'] = kennel_url

    if uuid:
        try:
            breeder, created = Breeder.objects.using('dogs_db').get_or_create(
                uuid=uuid,
                defaults=defaults,
            )
        except Exception:
            # race condition — кто-то создал между exists и create
            breeder = Breeder.objects.using('dogs_db').filter(uuid=uuid).first()
            if not breeder:
                raise
            created = False
    else:
        # Без uuid ищем по имени
        try:
            breeder, created = Breeder.objects.using('dogs_db').get_or_create(
                name=name,
                defaults={k: v for k, v in defaults.items() if k != 'name'},
            )
        except Exception:
            breeder = Breeder.objects.using('dogs_db').filter(name=name).first()
            if not breeder:
                raise
            created = False

    # Дозаписываем kennel если он появился
    if not created and kennel and not breeder.kennel:
        Breeder.objects.using('dogs_db').filter(pk=breeder.pk).update(kennel=kennel)
        breeder.kennel = kennel

    return breeder, created


def link_to_dog(dog, breeder) -> None:
    """Создаёт связь Dog ↔ Breeder если её ещё нет."""
    from ..models import Dogbreederlink
    Dogbreederlink.objects.using('dogs_db').get_or_create(dog=dog, breeder=breeder)


def dog_has_breeders(dog) -> bool:
    """True если у собаки уже есть хотя бы один заводчик."""
    return dog.breeders.using('dogs_db').exists()
