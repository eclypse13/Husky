# dogs_module/tasks/tasks_ofa.py
"""
OFA таски — только оркестрация.

Никакой работы с БД напрямую. Никакого парсинга.

Парсинг → parsers/ofa.py
БД      → services/dog_service.py + services/ofa_service.py
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="dogs_module.fetch_ofa_dog_task")
def fetch_ofa_dog_task(
    self,
    dog_id: int = None,
    registered_name: str = None,
    registration_number: str = None,
    ofa_number: str = None,
) -> dict:
    """
    Загружает OFA-данные для одной собаки.

    Если передан только dog_id — параметры поиска и пол берутся из БД.
    Пол используется для фильтрации при нескольких результатах поиска.

    Возвращает:
      {'dog_id', 'appnum', 'saved', 'failed', 'dog_info', 'medical_records'}
    """
    from ..parsers.ofa import fetch_ofa_data
    from ..services.dog_service import get_dog_search_params, update_dog_fields
    from ..services.ofa_service import save_ofa_records

    expected_sex = None

    # Если поисковые параметры не переданы — берём из БД
    if dog_id and not any([registered_name, registration_number, ofa_number]):
        params = get_dog_search_params(dog_id)
        if params is None:
            return {"error": f"Dog {dog_id} not found"}
        registered_name     = params["registered_name"]
        registration_number = params["registration_number"]
        expected_sex        = params["sex"]

    if not any([registered_name, registration_number, ofa_number]):
        return {"error": "Нужен хотя бы один параметр поиска"}

    logger.info(
        f"🔬 OFA: dog_id={dog_id} | "
        f"name={registered_name!r} | reg={registration_number!r} | "
        f"sex={expected_sex}"
    )

    result = fetch_ofa_data(
        registered_name=registered_name,
        registration_number=registration_number,
        ofa_number=ofa_number,
        expected_sex=expected_sex,
    )

    if not result:
        logger.info(f"OFA: не найдена на сайте (dog_id={dog_id})")
        return {
            "dog_id":  dog_id,
            "appnum":  None,
            "saved":   0,
            "failed":  0,
            "message": "Собака не найдена в базе OFA",
        }

    saved = failed = 0
    if dog_id:
        update_dog_fields(dog_id, {
            "registration_number": result["dog_info"].get("registration_number"),
            "date_of_birth":       result["dog_info"].get("date_of_birth"),
        })
        saved, failed = save_ofa_records(dog_id, result["medical_records"])

    return {
        "dog_id":          dog_id,
        "appnum":          result["appnum"],
        "dog_info":        result["dog_info"],
        "saved":           saved,
        "failed":          failed,
        "medical_records": result["medical_records"],
    }


@shared_task(bind=True, name="dogs_module.fetch_ofa_bulk_by_reg_task")
def fetch_ofa_bulk_by_reg_task(
    self,
    id_from: int = 1,
    id_to: int = None,
    limit: int = 100,
    delay: float = 1.5,
    only_without_ofa: bool = True,
) -> dict:
    """
    Bulk OFA-импорт по registration_number.

    Параметры:
      id_from          — нижняя граница Dog.id
      id_to            — верхняя граница Dog.id (None = без ограничения)
      limit            — макс. число собак
      delay            — пауза между задачами (секунды)
      only_without_ofa — пропустить собак с уже существующими OFA-записями

    Возвращает: {'dispatched', 'task_ids'}
    """
    from ..services.dog_service import get_dogs_by_reg_number

    logger.info(
        f"🔬 OFA bulk (reg): id={id_from}–{id_to}, "
        f"limit={limit}, delay={delay}"
    )

    dogs = get_dogs_by_reg_number(
        id_from=id_from,
        id_to=id_to,
        limit=limit,
        only_without_ofa=only_without_ofa,
    )

    if not dogs:
        logger.info("OFA bulk (reg): нет собак для обработки")
        return {"dispatched": 0, "task_ids": []}

    task_ids = []
    for i, dog in enumerate(dogs):
        task = fetch_ofa_dog_task.apply_async(
            kwargs={
                "dog_id":              dog["id"],
                "registered_name":     dog["registered_name"],
                "registration_number": dog["registration_number"],
            },
            countdown=int(i * delay),
        )
        task_ids.append(task.id)

    logger.info(f"OFA bulk (reg): диспатчено={len(task_ids)}")
    return {"dispatched": len(task_ids), "task_ids": task_ids}


@shared_task(bind=True, name="dogs_module.fetch_ofa_bulk_by_name_task")
def fetch_ofa_bulk_by_name_task(
    self,
    id_from: int = 1,
    id_to: int = None,
    limit: int = 100,
    delay: float = 1.5,
    only_without_ofa: bool = True,
) -> dict:
    """
    Bulk OFA-импорт по registered_name.

    Параметры:
      id_from          — нижняя граница Dog.id
      id_to            — верхняя граница Dog.id (None = без ограничения)
      limit            — макс. число собак
      delay            — пауза между задачами (секунды)
      only_without_ofa — пропустить собак с уже существующими OFA-записями

    Возвращает: {'dispatched', 'task_ids'}
    """
    from ..services.dog_service import get_dogs_by_name

    logger.info(
        f"🔬 OFA bulk (name): id={id_from}–{id_to}, "
        f"limit={limit}, delay={delay}"
    )

    dogs = get_dogs_by_name(
        id_from=id_from,
        id_to=id_to,
        limit=limit,
        only_without_ofa=only_without_ofa,
    )

    if not dogs:
        logger.info("OFA bulk (name): нет собак для обработки")
        return {"dispatched": 0, "task_ids": []}

    task_ids = []
    for i, dog in enumerate(dogs):
        task = fetch_ofa_dog_task.apply_async(
            kwargs={
                "dog_id":              dog["id"],
                "registered_name":     dog["registered_name"],
                "registration_number": dog["registration_number"],
            },
            countdown=int(i * delay),
        )
        task_ids.append(task.id)

    logger.info(f"OFA bulk (name): диспатчено={len(task_ids)}")
    return {"dispatched": len(task_ids), "task_ids": task_ids}