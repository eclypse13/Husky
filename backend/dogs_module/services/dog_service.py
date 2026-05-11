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


# def get_dog_search_params(dog_id: int) -> Optional[dict]:
#     """
#     Возвращает параметры для поиска собаки на внешних сайтах.
#
#     Возвращает:
#       {
#         'registered_name': '...',
#         'registration_number': '...',
#         'sex': 1,  # 1=кобель, 2=сука
#       }
#     или None если собака не найдена.
#     """
#     from ..models import Dog
#
#     try:
#         dog = Dog.objects.using("dogs_db").only(
#             "id", "registered_name", "registration_number", "sex"
#         ).get(pk=dog_id)
#     except Dog.DoesNotExist:
#         logger.error(f"dog_service: dog_id={dog_id} не найдена")
#         return None
#
#     return {
#         "registered_name":     dog.registered_name,
#         "registration_number": dog.registration_number,
#         "sex":                 dog.sex,
#     }

# ofa search
def get_dog_search_params(dog_id: int):
    from ..models import Dog
    try:
        dog = Dog.objects.using("dogs_db").only(
            "id", "registered_name", "registration_number",
            "sex", "year_of_birth", "date_of_birth",
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_service: dog_id={dog_id} не найдена")
        return None

    # Вычисляем год для сравнения с OFA
    # year_of_birth=0 считаем пустым — это мусорное значение из BreedArchive
    year = dog.year_of_birth if (dog.year_of_birth and dog.year_of_birth > 0) else None
    if not year and dog.date_of_birth:
        year = dog.date_of_birth.year

    name = dog.registered_name or ""
    for apostrophe in ["'", "\u2019", "\u2018"]:
        if apostrophe in name:
            name = name.split(apostrophe)[0].strip()
            break

    return {
        "registered_name": name,
        "registration_number": dog.registration_number,
        "sex": dog.sex,
        "expected_year": year,  # None если нет ни года ни даты
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

    # Фильтр мусорных рег.номеров — не AKC номера
    qs = qs.exclude(registration_number__regex=r'^[а-яёА-ЯЁ]')
    qs = qs.exclude(registration_number__icontains='метрик')
    qs = qs.exclude(registration_number__icontains='РКФ')

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

def update_dog_from_ofa(dog_id: int, dog_info: dict) -> bool:
    """
    Обновляет поля собаки данными из OFA.
    Обновляет только пустые поля.
    date_of_birth сохраняет только если сейчас пустое.
    """
    updates = {}

    reg_num = (dog_info.get("registration_number") or "").strip()
    if reg_num:
        updates["registration_number"] = reg_num

    dob = dog_info.get("date_of_birth")
    if dob:
        updates["date_of_birth"] = dob  # update_dog_fields уже проверяет на пустоту

    return update_dog_fields(dog_id, updates)