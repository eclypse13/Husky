# dogs_module/tasks/tasks_ofa.py
"""
OFA таски.
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
    from ..parsers.ofa import fetch_ofa_data
    from ..services.dog_service import get_dog_search_params, update_dog_from_ofa
    from ..services.ofa_service import save_ofa_records, verify_dog_identity

    expected_sex  = None
    expected_year = None

    if dog_id:
        params = get_dog_search_params(dog_id)
        if params is None:
            return {"error": f"Dog {dog_id} not found"}

        expected_sex  = params["sex"]
        expected_year = params["expected_year"]

        # Имя всегда берём из сервиса — там уже обрезан апостроф
        # Рег.номер берём из переданного если есть, иначе из БД
        registered_name = params["registered_name"]
        if not registration_number and not ofa_number:
            registration_number = params["registration_number"]

    if not any([registered_name, registration_number, ofa_number]):
        return {"error": "Нужен хотя бы один параметр поиска"}

    logger.info(
        f"🔬 OFA: dog_id={dog_id} | "
        f"name={registered_name!r} | reg={registration_number!r} | "
        f"sex={expected_sex} | year={expected_year}"
    )

    result = fetch_ofa_data(
        registered_name=registered_name,
        registration_number=registration_number,
        ofa_number=ofa_number,
        expected_sex=expected_sex,
        expected_year=expected_year,
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
        is_match, reason = verify_dog_identity(dog_id, result["dog_info"])

        if not is_match:
            logger.warning(
                f"OFA: найдена не та собака для dog_id={dog_id} — {reason}"
            )
            return {
                "dog_id":  dog_id,
                "appnum":  result["appnum"],
                "saved":   0,
                "failed":  0,
                "message": f"Найдена не та собака: {reason}",
            }

        update_dog_from_ofa(dog_id, result["dog_info"])
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
    from ..services.dog_service import get_dogs_by_reg_number

    logger.info(f"🔬 OFA bulk (reg): id={id_from}–{id_to}, limit={limit}")

    dogs = get_dogs_by_reg_number(
        id_from=id_from, id_to=id_to,
        limit=limit, only_without_ofa=only_without_ofa,
    )

    if not dogs:
        return {"dispatched": 0, "task_ids": []}

    task_ids = []
    for i, dog in enumerate(dogs):
        task = fetch_ofa_dog_task.apply_async(
            kwargs={
                "dog_id":              dog["id"],
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
    from ..services.dog_service import get_dogs_by_name

    logger.info(f"🔬 OFA bulk (name): id={id_from}–{id_to}, limit={limit}")

    dogs = get_dogs_by_name(
        id_from=id_from, id_to=id_to,
        limit=limit, only_without_ofa=only_without_ofa,
    )

    if not dogs:
        return {"dispatched": 0, "task_ids": []}

    task_ids = []
    for i, dog in enumerate(dogs):
        task = fetch_ofa_dog_task.apply_async(
            kwargs={
                "dog_id": dog["id"],
            },
            countdown=int(i * delay),
        )
        task_ids.append(task.id)

    logger.info(f"OFA bulk (name): диспатчено={len(task_ids)}")
    return {"dispatched": len(task_ids), "task_ids": task_ids}

@shared_task(bind=True, name="dogs_module.refresh_ofa_sh_breed_stats")
def refresh_ofa_sh_breed_stats(self) -> dict:
    """
    Обновляет кэш статистики OFA в Redis.
    """
    from ..services.ofa_service import get_breed_ofa_stats, invalidate_stats_cache
    invalidate_stats_cache()
    stats = get_breed_ofa_stats()
    return {"updated": bool(stats), "tests": len(stats) if stats else 0}