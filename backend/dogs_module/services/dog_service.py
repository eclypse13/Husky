# dogs_module/services/dog_service.py
"""
Работа с БД
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# ЧТЕНИЕ
# ──────────────────────────────────────────────────────────────────────────────

def get_dog_by_id(dog_id: int):
    from ..models import Dog
    try:
        return Dog.objects.using('dogs_db').get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_service: dog_id={dog_id} не найдена")
        return None


def get_dog_by_zooportal_id(zooportal_id: str):
    from ..models import Dog
    if not zooportal_id:
        return None
    return Dog.objects.using('dogs_db').filter(zooportal_id=zooportal_id).first()


def get_dog_search_params(dog_id: int):
    """Параметры для поиска собаки на OFA."""
    from ..models import Dog
    try:
        dog = Dog.objects.using('dogs_db').only(
            'id', 'registered_name', 'registration_number',
            'sex', 'year_of_birth', 'date_of_birth',
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_service: dog_id={dog_id} не найдена")
        return None

    year = dog.year_of_birth if (dog.year_of_birth and dog.year_of_birth > 0) else None
    if not year and dog.date_of_birth:
        year = dog.date_of_birth.year

    name = dog.registered_name or ''
    for apostrophe in ["'", '\u2019', '\u2018']:
        if apostrophe in name:
            name = name.split(apostrophe)[0].strip()
            break

    return {
        'registered_name':     name,
        'registration_number': dog.registration_number,
        'sex':                 dog.sex,
        'expected_year':       year,
    }


def get_existing_zooportal_ids(zoo_ids: list) -> set:
    """
    Принимает список zooportal_id, возвращает те которые уже есть в БД.
    Используется в tasks чтобы определить каких собак нужно импортировать.
    """
    from ..models import Dog
    if not zoo_ids:
        return set()
    return set(
        Dog.objects.using('dogs_db')
        .filter(zooportal_id__in=zoo_ids)
        .values_list('zooportal_id', flat=True)
    )


def get_dogs_by_reg_number(
    id_from: int = 1,
    id_to: int = None,
    limit: int = 100,
    only_without_ofa: bool = True,
) -> list:
    """Выборка собак с registration_number для bulk OFA-импорта."""
    from ..models import Dog, MedicalRecord

    qs = Dog.objects.using('dogs_db').filter(
        registration_number__isnull=False,
        id__gte=id_from,
    ).exclude(registration_number='')

    qs = qs.exclude(registration_number__regex=r'^[а-яёА-ЯЁ]')
    qs = qs.exclude(registration_number__icontains='метрик')
    qs = qs.exclude(registration_number__icontains='РКФ')

    if id_to is not None:
        qs = qs.filter(id__lte=id_to)

    if only_without_ofa:
        dogs_with_ofa = (
            MedicalRecord.objects.using('dogs_db')
            .filter(source='ofa')
            .values_list('dog_id', flat=True)
            .distinct()
        )
        qs = qs.exclude(id__in=dogs_with_ofa)

    return list(
        qs.order_by('id')[:limit]
        .values('id', 'registered_name', 'registration_number', 'sex')
    )


def get_dogs_by_name(
    id_from: int = 1,
    id_to: int = None,
    limit: int = 100,
    only_without_ofa: bool = True,
) -> list:
    """Выборка собак с registered_name для bulk OFA-импорта."""
    from ..models import Dog, MedicalRecord

    qs = Dog.objects.using('dogs_db').filter(
        registered_name__isnull=False,
        id__gte=id_from,
    ).exclude(registered_name='')

    if id_to is not None:
        qs = qs.filter(id__lte=id_to)

    if only_without_ofa:
        dogs_with_ofa = (
            MedicalRecord.objects.using('dogs_db')
            .filter(source='ofa')
            .values_list('dog_id', flat=True)
            .distinct()
        )
        qs = qs.exclude(id__in=dogs_with_ofa)

    return list(
        qs.order_by('id')[:limit]
        .values('id', 'registered_name', 'registration_number', 'sex')
    )


def get_missing_zoo_ids(zoo_ids: list) -> list:
    """
    Принимает список zooportal_id из результатов выставки.
    Возвращает только те которых нет в таблице Dog.
    """
    if not zoo_ids:
        return []
    existing = get_existing_zooportal_ids(zoo_ids)
    return [zid for zid in zoo_ids if zid not in existing]


def extract_zoo_ids_from_results(results: list) -> list:
    """
    Достаёт все zooportal_dog_id из списка результатов выставки.
    Фильтрует пустые значения.
    """
    return [
        r['zooportal_dog_id']
        for r in results
        if r.get('zooportal_dog_id')
    ]


# ──────────────────────────────────────────────────────────────────────────────
# ЗАПИСЬ
# ──────────────────────────────────────────────────────────────────────────────

def update_dog_fields(dog_id: int, updates: dict) -> bool:
    """Обновляет поля собаки только если они сейчас пустые."""
    from ..models import Dog

    if not updates:
        return False

    try:
        dog = Dog.objects.using('dogs_db').only('id', *updates.keys()).get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_service: dog_id={dog_id} не найдена при обновлении")
        return False

    actual_updates = {
        field: value
        for field, value in updates.items()
        if value and not getattr(dog, field, None)
    }

    if not actual_updates:
        return False

    Dog.objects.using('dogs_db').filter(pk=dog_id).update(**actual_updates)
    logger.info(f"dog_service: dog_id={dog_id} — обновлено {list(actual_updates.keys())}")
    return True


def update_dog_from_ofa(dog_id: int, dog_info: dict) -> bool:
    """Обновляет поля собаки данными из OFA. Только пустые поля."""
    updates = {}
    reg_num = (dog_info.get('registration_number') or '').strip()
    if reg_num:
        updates['registration_number'] = reg_num
    dob = dog_info.get('date_of_birth')
    if dob:
        updates['date_of_birth'] = dob
    return update_dog_fields(dog_id, updates)


def set_dog_rating(dog_id: int, rating: int) -> None:
    """Записывает рейтинг в Dog.rating. Вызывается только из show_service."""
    from ..models import Dog
    from django.utils import timezone
    Dog.objects.using('dogs_db').filter(pk=dog_id).update(
        rating=rating,
        rating_updated_at=timezone.now(),
    )
    logger.debug(f"dog_service: dog_id={dog_id} rating={rating}")


def reset_ratings_except(participant_ids: list) -> None:
    """Обнуляет рейтинг у всех собак кроме переданных."""
    from ..models import Dog
    from django.utils import timezone
    Dog.objects.using('dogs_db').exclude(pk__in=participant_ids).filter(
        rating__gt=0
    ).update(rating=0, rating_updated_at=timezone.now())


