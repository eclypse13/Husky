"""
OFA таски.
"""

import logging
from typing import Dict, List, Optional

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
    from ..services.ofa_service import import_ofa_for_dog
    logger.info(f"🔬 OFA: dog_id={dog_id}")
    return import_ofa_for_dog(
        dog_id=dog_id,
        registered_name=registered_name,
        registration_number=registration_number,
        ofa_number=ofa_number,
    )


@shared_task(bind=True, name="dogs_module.fetch_ofa_bulk_by_reg_task")
def fetch_ofa_bulk_by_reg_task(
        self,
        id_from: int = 1,
        id_to: int = None,
        limit: int = 100,
        delay: float = 1.5,
        only_without_ofa: bool = True,
) -> dict:
    from ..services.ofa_service import get_dogs_eligible_by_reg as get_dogs_by_reg_number

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
                "dog_id": dog["id"],
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
    from ..services.ofa_service import get_dogs_eligible_by_name as get_dogs_by_name

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


# Обновляет кэш статистики OFA в Redis
@shared_task(bind=True, name="dogs_module.refresh_ofa_sh_breed_stats")
def refresh_ofa_sh_breed_stats(self) -> dict:
    from ..services.ofa_service import get_breed_ofa_stats, invalidate_stats_cache
    invalidate_stats_cache()
    stats = get_breed_ofa_stats()
    return {"updated": bool(stats), "tests": len(stats) if stats else 0}
