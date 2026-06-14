# dogs_module/tasks/tasks_coi.py
"""
Celery-задача массового пересчёта COI.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='dogs_module.recalculate_all_coi',
    max_retries=0,
    time_limit=3600,
    soft_time_limit=3500,
)
def recalculate_all_coi_task(
        self,
        generations: int = 5,
        batch_size: int = 100,
        only_missing: bool = True,
        use_ancestor_coi: bool = False,
) -> dict:
    """
    Массовый пересчёт COI.
    """
    from ..services.coi_service import recalculate_all

    def _progress(meta: dict) -> None:
        self.update_state(state='PROGRESS', meta=meta)

    return recalculate_all(
        generations=generations,
        batch_size=batch_size,
        only_missing=only_missing,
        use_ancestor_coi=use_ancestor_coi,
        progress_cb=_progress,
    )
