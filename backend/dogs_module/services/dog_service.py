# dogs_module/services/dog_service.py
"""
Общий сервис для работы с таблицей Dog.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_dog_by_id(dog_id: int):
    """
    Достаёт собаку из БД по ID.
    Возвращает объект Dog или None.
    """
    from ..models import Dog

    try:
        return Dog.objects.using("dogs_db").get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_service: dog_id={dog_id} не найдена")
        return None


def get_dog_search_params(dog_id: int) -> Optional[dict]:
    """
    Возвращает параметры для поиска собаки на внешних сайтах.

    Возвращает:
      {
        'registered_name': '...',
        'registration_number': '...',
        'sex': 1,  # 1=кобель, 2=сука
      }
    или None если собака не найдена.
    """
    from ..models import Dog

    try:
        dog = Dog.objects.using("dogs_db").only(
            "id", "registered_name", "registration_number", "sex"
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_service: dog_id={dog_id} не найдена")
        return None

    return {
        "registered_name":     dog.registered_name,
        "registration_number": dog.registration_number,
        "sex":                 dog.sex,
    }


def get_dogs_by_reg_number(
    id_from: int = 1,
    id_to: int = None,
    limit: int = 100,
    only_without_ofa: bool = True,
) -> list:
    """
    Выборка собак с registration_number для bulk OFA-импорта.

    Параметры:
      id_from          — нижняя граница Dog.id (включительно)
      id_to            — верхняя граница Dog.id (включительно), None = без ограничения
      limit            — макс. число собак
      only_without_ofa — исключить собак у которых уже есть OFA-записи

    Возвращает список dict: [{'id', 'registered_name', 'registration_number', 'sex'}]
    """
    from ..models import Dog, MedicalRecord

    qs = Dog.objects.using("dogs_db").filter(
        registration_number__isnull=False,
        id__gte=id_from,
    ).exclude(registration_number="")

    if id_to is not None:
        qs = qs.filter(id__lte=id_to)

    if only_without_ofa:
        dogs_with_ofa = (
            MedicalRecord.objects
            .using("dogs_db")
            .filter(source="ofa")
            .values_list("dog_id", flat=True)
            .distinct()
        )
        qs = qs.exclude(id__in=dogs_with_ofa)

    return list(
        qs.order_by("id")[:limit]
        .values("id", "registered_name", "registration_number", "sex")
    )


def get_dogs_by_name(
    id_from: int = 1,
    id_to: int = None,
    limit: int = 100,
    only_without_ofa: bool = True,
) -> list:
    """
    Выборка собак с registered_name для bulk OFA-импорта по имени.

    Параметры:
      id_from          — нижняя граница Dog.id (включительно)
      id_to            — верхняя граница Dog.id (включительно), None = без ограничения
      limit            — макс. число собак
      only_without_ofa — исключить собак у которых уже есть OFA-записи

    Возвращает список dict: [{'id', 'registered_name', 'registration_number', 'sex'}]
    """
    from ..models import Dog, MedicalRecord

    qs = Dog.objects.using("dogs_db").filter(
        registered_name__isnull=False,
        id__gte=id_from,
    ).exclude(registered_name="")

    if id_to is not None:
        qs = qs.filter(id__lte=id_to)

    if only_without_ofa:
        dogs_with_ofa = (
            MedicalRecord.objects
            .using("dogs_db")
            .filter(source="ofa")
            .values_list("dog_id", flat=True)
            .distinct()
        )
        qs = qs.exclude(id__in=dogs_with_ofa)

    return list(
        qs.order_by("id")[:limit]
        .values("id", "registered_name", "registration_number", "sex")
    )


def update_dog_fields(dog_id: int, updates: dict) -> bool:
    """
    Обновляет поля собаки — только если поле пустое (не перезаписывает).

    updates — словарь {field_name: value}

    Возвращает True если хотя бы одно поле обновилось.
    """
    from ..models import Dog

    if not updates:
        return False

    try:
        dog = Dog.objects.using("dogs_db").only(
            "id", *updates.keys()
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_service: dog_id={dog_id} не найдена при обновлении")
        return False

    # Оставляем только те поля которые сейчас пусты
    actual_updates = {
        field: value
        for field, value in updates.items()
        if value and not getattr(dog, field, None)
    }

    if not actual_updates:
        return False

    Dog.objects.using("dogs_db").filter(pk=dog_id).update(**actual_updates)
    logger.info(f"dog_service: dog_id={dog_id} — обновлено {list(actual_updates.keys())}")
    return True