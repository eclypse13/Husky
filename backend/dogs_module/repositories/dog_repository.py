"""
Доступ к данным Dog.
"""

import logging
from typing import Optional
from django.db.models import F, Value
from django.db.models.functions import Replace

logger = logging.getLogger(__name__)


def get_by_id(dog_id: int) -> Optional["Dog"]:
    from ..models import Dog
    try:
        return Dog.objects.using('dogs_db').get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_repository: dog_id={dog_id} не найдена")
        return None


# Одним запросом получаем breeders / owners / titles / medical_records / bestrussian_ratings
def get_detail(dog_id) -> "Dog | None":
    from ..models import Dog
    try:
        return (
            Dog.objects.using('dogs_db')
            .select_related('dam', 'sire')
            .prefetch_related('breeders', 'owners', 'titles', 'medical_records', 'bestrussian_ratings')
            .get(pk=dog_id)
        )
    except Dog.DoesNotExist:
        return None


def iter_id_registered_names():
    from ..models import Dog
    return (
        Dog.objects.using('dogs_db')
        .exclude(registered_name__isnull=True)
        .exclude(registered_name='')
        .values_list('id', 'registered_name')
        .iterator()
    )

# Из списка zooportal_id возвращает те, которых нет в БД
def get_missing_zoo_ids(zoo_ids: list) -> list:
    if not zoo_ids:
        return []
    existing = get_existing_zooportal_ids(zoo_ids)
    return [zid for zid in zoo_ids if zid not in existing]


def get_by_zooportal_id(zooportal_id: str) -> Optional["Dog"]:
    from ..models import Dog
    if not zooportal_id:
        return None
    return Dog.objects.using('dogs_db').filter(
        zooportal_id=str(zooportal_id)
    ).first()


def get_by_uuid(uuid: str) -> Optional["Dog"]:
    from ..models import Dog
    if not uuid:
        return None
    return Dog.objects.using('dogs_db').filter(uuid=uuid).first()


# Параметры для поиска собаки на OFA
def get_search_params(dog_id: int) -> Optional[dict]:
    from ..models import Dog
    try:
        dog = Dog.objects.using('dogs_db').only(
            'id', 'registered_name', 'registration_number',
            'sex', 'year_of_birth', 'date_of_birth',
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_repository: dog_id={dog_id} не найдена")
        return None

    year = dog.year_of_birth if (dog.year_of_birth and dog.year_of_birth > 0) else None
    if not year and dog.date_of_birth:
        year = dog.date_of_birth.year

    name = dog.registered_name or ''
    for apostrophe in ["'", '\u2019', '\u2018']:
        if apostrophe in name:
            name = name.replace(apostrophe, '').strip()
            break

    return {
        'registered_name': name,
        'registration_number': dog.registration_number,
        'sex': dog.sex,
        'expected_year': year,
    }


# Лёгкая выборка для сверки личности собаки с OFA
def get_identity_fields(dog_id: int) -> Optional["Dog"]:
    from ..models import Dog
    try:
        return Dog.objects.using('dogs_db').only(
            'id', 'sex', 'year_of_birth', 'date_of_birth'
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        return None


def get_coi_map(dog_ids) -> dict:
    from ..models import Dog
    if not dog_ids:
        return {}
    return dict(
        Dog.objects.using('dogs_db')
        .filter(id__in=dog_ids)
        .values_list('id', 'coi')
    )


def get_by_ids(dog_ids) -> list:
    from ..models import Dog
    if not dog_ids:
        return []
    return list(Dog.objects.using('dogs_db').filter(id__in=dog_ids))


def get_siblings(dog) -> list:
    from ..models import Dog
    return list(
        Dog.objects.using('dogs_db')
        .filter(dam=dog.dam, sire=dog.sire)
        .exclude(id=dog.id)
    )


# Потомки собаки (по полу)
def get_offspring(dog) -> list:
    from ..models import Dog
    if dog.sex == 1:
        return list(Dog.objects.using('dogs_db').filter(sire=dog))
    if dog.sex == 2:
        return list(Dog.objects.using('dogs_db').filter(dam=dog))
    return []


def search_by_name(query: str, limit: int = 20) -> list:
    from ..models import Dog
    if not query:
        return []
    return list(
        Dog.objects.using('dogs_db')
        .filter(registered_name__icontains=query)[:limit]
    )


def get_overview_counts() -> dict:
    from ..models import Dog, Breeder
    dogs = Dog.objects.using('dogs_db')
    return {
        'total': dogs.count(),
        'males': dogs.filter(sex=1).count(),
        'females': dogs.filter(sex=2).count(),
        'breeders': Breeder.objects.using('dogs_db').count(),
        'with_zooportal_id': dogs.filter(zooportal_id__isnull=False).count(),
        'with_uuid': dogs.filter(uuid__isnull=False).count(),
    }


# Алиас: было два варианта с разными именами, оставляем оба имени
get_overview_stats = get_overview_counts


# id собак, чьё registered_name содержит query
def search_ids_by_name(query: str, limit: int = 500) -> list:
    from ..models import Dog
    if not query:
        return []
    return list(
        Dog.objects.using('dogs_db')
        .filter(registered_name__icontains=query)
        .values_list('id', flat=True)[:limit]
    )


# Потомки с известными обоими родителями
def get_offspring_with_parents_values() -> list:
    from ..models import Dog
    return list(
        Dog.objects.using('dogs_db')
        .filter(sire_id__isnull=False, dam_id__isnull=False)
        .values('id', 'sire_id', 'dam_id', 'coi')
    )


def count_offspring_with_parents() -> int:
    from ..models import Dog
    return Dog.objects.using('dogs_db').filter(
        sire_id__isnull=False, dam_id__isnull=False
    ).count()


# Предки с батчем
def get_parents_batch_values(dog_ids) -> list:
    from ..models import Dog
    if not dog_ids:
        return []
    return list(
        Dog.objects.using('dogs_db')
        .filter(id__in=dog_ids)
        .values('id', 'sire_id', 'dam_id')
    )


# для предков с непустым COI
def get_coi_for_ancestors(ancestor_ids) -> dict:
    from ..models import Dog
    if not ancestor_ids:
        return {}
    return {
        row['id']: row['coi']
        for row in Dog.objects.using('dogs_db')
        .filter(id__in=ancestor_ids, coi__isnull=False)
        .values('id', 'coi')
    }


# QuerySet собак с обоими родителями для массового пересчёта COI
def iter_dogs_for_coi_recalc(only_missing: bool = True):
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(sire_id__isnull=False, dam_id__isnull=False)
        .only('id', 'registered_name', 'sire_id', 'dam_id', 'coi')
    )
    if only_missing:
        qs = qs.filter(coi__isnull=True)
    return qs


def count_dogs_for_coi_recalc(only_missing: bool = True) -> int:
    return iter_dogs_for_coi_recalc(only_missing).count()


# Сохраняет coi + coi_updated_on у объекта Dog
def save_coi(dog, coi_value, updated_at) -> None:
    dog.coi = coi_value
    dog.coi_updated_on = updated_at
    dog.save(using='dogs_db', update_fields=['coi', 'coi_updated_on'])


def get_by_zooportal_ids_bulk(zoo_ids) -> dict:
    from ..models import Dog
    if not zoo_ids:
        return {}
    return {
        d.zooportal_id: d
        for d in Dog.objects.using('dogs_db').filter(zooportal_id__in=zoo_ids)
        if d.zooportal_id
    }


def get_by_zoo_hashes_bulk(hashes) -> dict:
    from ..models import Dog
    if not hashes:
        return {}
    return {
        d.zoo_hash: d
        for d in Dog.objects.using('dogs_db').filter(zoo_hash__in=hashes)
        if d.zoo_hash
    }


def update_by_pk(pk: int, fields: dict) -> None:
    from ..models import Dog
    if fields:
        Dog.objects.using('dogs_db').filter(pk=pk).update(**fields)


# Переключает всех потомков с old_pk на new_pk как dam/sire
def reparent_children(old_pk: int, new_pk: int) -> None:
    from ..models import Dog
    Dog.objects.using('dogs_db').filter(dam_id=old_pk).update(dam_id=new_pk)
    Dog.objects.using('dogs_db').filter(sire_id=old_pk).update(sire_id=new_pk)


# стаб-предка по zooportal_id, если не найден то создаёт минимальную запись
def stub_or_get_by_zooportal_id(zoo_id: str, name: str, sex: int) -> "Dog":
    from ..models import Dog
    dog, _ = Dog.objects.using('dogs_db').get_or_create(
        zooportal_id=zoo_id,
        defaults={
            'registered_name': name,
            'sex': sex,
            'zoo_hash': Dog.compute_zoo_hash(name, sex),
        },
    )
    return dog


# стаб-предка по имени+полу (когда нет zooportal_id).
def stub_or_get_by_name(name: str, sex: int) -> "Dog":
    from ..models import Dog
    dog, _ = Dog.objects.using('dogs_db').get_or_create(
        registered_name=name,
        sex=sex,
        defaults={'zoo_hash': Dog.compute_zoo_hash(name, sex)},
    )
    return dog


def merge_zoo_stub_into_ba(ba_dog_pk: int, zoo_hash: str, ba_dog_fields: dict) -> dict:
    from ..models import Dog
    from django.db import transaction

    if not zoo_hash:
        return {}

    merge_update = {}
    with transaction.atomic(using='dogs_db'):
        zoo_twin = (
            Dog.objects
            .using('dogs_db')
            .select_for_update(nowait=False)
            .filter(zoo_hash=zoo_hash, uuid__isnull=True)
            .exclude(pk=ba_dog_pk)
            .first()
        )
        if not zoo_twin:
            return {}

        if zoo_twin.zooportal_id and not ba_dog_fields.get('zooportal_id'):
            merge_update['zooportal_id'] = zoo_twin.zooportal_id
        if zoo_twin.zoo_hash and not ba_dog_fields.get('zoo_hash'):
            merge_update['zoo_hash'] = zoo_twin.zoo_hash

        for field in (
                'brand_chip', 'kennel', 'eyes_color', 'club',
                'size', 'weight', 'sports', 'locked', 'removed',
                'frozen_semen', 'approved_for_breeding',
        ):
            zoo_val = getattr(zoo_twin, field, None)
            if zoo_val is not None and ba_dog_fields.get(field) is None:
                merge_update[field] = zoo_val

        if merge_update:
            Dog.objects.using('dogs_db').filter(pk=ba_dog_pk).update(**merge_update)

        Dog.objects.using('dogs_db').filter(dam_id=zoo_twin.pk).update(dam_id=ba_dog_pk)
        Dog.objects.using('dogs_db').filter(sire_id=zoo_twin.pk).update(sire_id=ba_dog_pk)

        zoo_twin.delete(using='dogs_db')

    return merge_update


def get_dog_for_update_by_uuid(uuid: str):
    from ..models import Dog
    return Dog.objects.using('dogs_db').select_for_update(nowait=False).filter(uuid=uuid).first()


def get_stub_candidates_for_update(sex: int, year_of_birth: int = None, year_window: int = 1, limit: int = 200):
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .select_for_update(nowait=False)
        .filter(sex=sex, uuid__isnull=True)
    )
    if year_of_birth:
        qs = qs.filter(
            year_of_birth__gte=year_of_birth - year_window,
            year_of_birth__lte=year_of_birth + year_window,
        )
    return list(qs[:limit])

def create_dog(fields: dict) -> "Dog":
    from ..models import Dog
    return Dog.objects.using('dogs_db').create(**fields)


# def upsert_ba_dog(uuid: str, defaults: dict) -> tuple:
#     from ..models import Dog
#     try:
#         return Dog.objects.using('dogs_db').update_or_create(
#             uuid=uuid, defaults=defaults
#         )
#     except Dog.MultipleObjectsReturned:
#         dog = Dog.objects.using('dogs_db').filter(uuid=uuid).order_by('id').first()
#         for k, v in defaults.items():
#             setattr(dog, k, v)
#         dog.save(using='dogs_db')
#         return dog, False
#

def upsert_zoo_fallback(zooportal_id: str, defaults: dict) -> "Dog":
    from ..models import Dog
    dog, _ = Dog.objects.using('dogs_db').update_or_create(
        zooportal_id=zooportal_id,
        defaults=defaults,
    )
    return dog


# Выборка полей фото одной собаки
def get_photo_fields(dog_id: int, with_zooportal: bool = False):
    from ..models import Dog
    fields = ['id', 'photo_url', 'photo_yadisk_path', 'photo_yadisk_url', 'photo_hash']
    if with_zooportal:
        fields.append('zooportal_id')
    try:
        return Dog.objects.using('dogs_db').only(*fields).get(pk=dog_id)
    except Dog.DoesNotExist:
        return None


# Записывает photo_yadisk_path , photo_yadisk_url
def update_photo_paths(dog_id: int, updates: dict) -> None:
    from ..models import Dog
    if updates:
        Dog.objects.using('dogs_db').filter(pk=dog_id).update(**updates)


# Zoo-собаки с photo_url но без фото на ЯД
def get_zoo_dogs_without_yadisk_photo(
        id_from: int = 1, id_to: int = None, limit: int = 100
) -> list:
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(
            photo_url__icontains='zooportal',
            photo_yadisk_url__isnull=True,
            zooportal_id__isnull=False,
            id__gte=id_from,
        )
        .exclude(photo_url='')
        .exclude(zooportal_id='')
        .only('id')
        .order_by('id')
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)
    return list(qs.values('id')[:limit])


def get_dogs_with_yadisk_without_hash(
        limit: int = 1000,
        id_from: int = 1,
        id_to: int = None,
):
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(
            photo_yadisk_path__isnull=False,
            photo_hash__isnull=True,
            id__gte=id_from,
        )
        .exclude(photo_yadisk_path='')
        .only('id', 'photo_url', 'photo_yadisk_path', 'zooportal_id', 'source')
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)
    return list(qs[:limit])


def get_dogs_with_photo_url(
        id_from: int = 1, id_to: int = None,
        limit: int = 500, only_without_yadisk: bool = True,
) -> list:
    """Собаки с photo_url для bulk-синхронизации фото на ЯД."""
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(photo_url__isnull=False, id__gte=id_from)
        .exclude(photo_url='')
        .only('id')
        .order_by('id')
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)
    if only_without_yadisk:
        qs = qs.filter(photo_yadisk_path__isnull=True)
    return list(qs.values('id')[:limit])


def get_dogs_with_url_without_hash(
        limit: int = 1000,
        id_from: int = 1,
        id_to: int = None,
):
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(
            photo_url__isnull=False,
            photo_hash__isnull=True,
            id__gte=id_from,
        )
        .exclude(photo_url='')
        .values('id', 'photo_url', 'source')
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)
    return list(qs[:limit])


# photo_yadisk_path одной собаки
def get_yadisk_path(dog_id: int):
    from ..models import Dog
    try:
        return Dog.objects.using('dogs_db').only('id', 'photo_yadisk_path').get(pk=dog_id)
    except Dog.DoesNotExist:
        return None


# Счётчики статистики фото
def get_photo_coverage_counts() -> dict:
    from ..models import Dog
    qs = Dog.objects.using('dogs_db')
    return {
        "total": qs.count(),
        "with_url": qs.exclude(photo_url__isnull=True).exclude(photo_url='').count(),
        "with_yadisk": qs.exclude(photo_yadisk_path__isnull=True).exclude(photo_yadisk_path='').count(),
    }


def exists_by_zooportal_id(zooportal_id: str) -> bool:
    from ..models import Dog
    if not zooportal_id:
        return False
    return Dog.objects.using('dogs_db').filter(zooportal_id=zooportal_id).exists()


def get_existing_zooportal_ids(zoo_ids: list) -> set:
    from ..models import Dog
    if not zoo_ids:
        return set()
    return set(
        Dog.objects.using('dogs_db')
        .filter(zooportal_id__in=zoo_ids)
        .values_list('zooportal_id', flat=True)
    )


# Собаки с непустым registration_number
def get_dogs_with_reg_number(
        id_from: int = 1, id_to: int = None, limit: int = 100,
) -> list:
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(registration_number__isnull=False, id__gte=id_from)
        .exclude(registration_number='')
    )
    if id_to is not None:
        qs = qs.filter(id__lte=id_to)
    return list(
        qs.order_by('id')[:limit]
        .values('id', 'registered_name', 'registration_number', 'sex')
    )


def get_dogs_with_uuid(
        id_from: int = 1, id_to: int = None, limit: int = 1000,
) -> list:
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(uuid__isnull=False, id__gte=id_from)
        .exclude(uuid='')
    )
    if id_to is not None:
        qs = qs.filter(id__lte=id_to)
    return list(
        qs.order_by('id')[:limit]
        .values('id', 'uuid', 'registered_name')
    )


# Собаки с непустым registered_name
def get_dogs_with_name(
        id_from: int = 1, id_to: int = None, limit: int = 100,
) -> list:
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(registered_name__isnull=False, id__gte=id_from)
        .exclude(registered_name='')
    )
    if id_to is not None:
        qs = qs.filter(id__lte=id_to)
    return list(
        qs.order_by('id')[:limit]
        .values('id', 'registered_name', 'registration_number', 'sex')
    )


def search_filtered(
        search: str = None,
        sex: int = None,
        year: int = None,
        year_from: int = None,
        year_to: int = None,
        color: str = None,
        kennel: str = None,
        country: str = None,
):
    from ..models import Dog
    from ..utils.text import build_color_filter
    qs = (
        Dog.objects.using('dogs_db')
        .order_by('-id')
        .select_related('dam', 'sire')
        .prefetch_related('breeders')
    )
    if search:
        from ..utils.text import _normalize_yo
        search_norm = _normalize_yo(search)
        qs = qs.annotate(
            _name_norm=Replace(
                Replace(F('registered_name'), Value('ё'), Value('е')),
                Value('Ё'), Value('Е'),
            )
        ).filter(_name_norm__icontains=search_norm)
        # qs = qs.filter(registered_name__icontains=search)
    if sex:
        qs = qs.filter(sex=sex)
    if year:
        qs = qs.filter(year_of_birth=year)
    if year_from:
        qs = qs.filter(year_of_birth__gte=year_from)
    if year_to:
        qs = qs.filter(year_of_birth__lte=year_to)
    if color:
        qs = build_color_filter(qs, color)
    if kennel:
        qs = qs.filter(kennel__icontains=kennel)
    if country:
        qs = qs.filter(land_of_birth__icontains=country)
    return qs


# Обновляет поля собаки только если они сейчас пустые
def update_fields_if_empty(dog_id: int, updates: dict) -> bool:
    from ..models import Dog

    if not updates:
        return False

    try:
        dog = Dog.objects.using('dogs_db').only('id', *updates.keys()).get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_repository: dog_id={dog_id} не найдена при обновлении")
        return False

    actual_updates = {
        field: value
        for field, value in updates.items()
        if value and not getattr(dog, field, None)
    }

    if not actual_updates:
        return False

    Dog.objects.using('dogs_db').filter(pk=dog_id).update(**actual_updates)
    logger.info(f"dog_repository: dog_id={dog_id} — обновлено {list(actual_updates.keys())}")
    return True


def set_rating(dog_id: int, rating: int) -> None:
    from ..models import Dog
    from django.utils import timezone
    Dog.objects.using('dogs_db').filter(pk=dog_id).update(
        rating=rating,
        rating_updated_at=timezone.now(),
    )
    logger.debug(f"dog_repository: dog_id={dog_id} rating={rating}")


def reset_ratings_except(participant_ids: list) -> None:
    from ..models import Dog
    from django.utils import timezone
    Dog.objects.using('dogs_db').exclude(pk__in=participant_ids).filter(
        rating__gt=0
    ).update(rating=0, rating_updated_at=timezone.now())


def get_by_uuid(uuid: str) -> "Dog | None":
    from ..models import Dog
    if not uuid:
        return None
    return Dog.objects.using('dogs_db').filter(uuid=uuid).first()


def set_zooportal_id(dog_pk: int, zooportal_id: str) -> None:
    from ..models import Dog
    Dog.objects.using('dogs_db').filter(pk=dog_pk).update(zooportal_id=zooportal_id)


# Группировка собак по photo_hash
def count_dogs_by_photo_hash(min_count: int = 5, top: int = 20) -> list:
    from django.db.models import Count
    from ..models import Dog
    return list(
        Dog.objects.using('dogs_db')
        .exclude(photo_hash__isnull=True)
        .values('photo_hash')
        .annotate(count=Count('id'))
        .filter(count__gte=min_count)
        .order_by('-count')[:top]
    )


def get_dogs_by_photo_hash(hashes: list) -> list:
    from ..models import Dog
    if not hashes:
        return []
    return list(
        Dog.objects.using('dogs_db')
        .filter(photo_hash__in=list(hashes))
        .only('id', 'photo_yadisk_path', 'photo_yadisk_url')
    )


# Кандидаты на дубль
def get_duplicate_candidates(sex: int, year_of_birth: int = None,
                             year_window: int = 1, exclude_pk: int = None,
                             limit: int = 200) -> list:
    from ..models import Dog
    if not sex:
        return []
    qs = Dog.objects.using('dogs_db').filter(sex=sex)
    if year_of_birth:
        qs = qs.filter(
            year_of_birth__gte=year_of_birth - year_window,
            year_of_birth__lte=year_of_birth + year_window,
        )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return list(
        qs.only('id', 'registered_name', 'sex', 'year_of_birth',
                'sire_name', 'dam_name')[:limit]
    )
