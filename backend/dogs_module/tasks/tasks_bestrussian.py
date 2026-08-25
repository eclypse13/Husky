from celery import shared_task, Task


class BaseBestrussianTask(Task):
    autoretry_for = (ConnectionError, TimeoutError)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True


@shared_task(
    base=BaseBestrussianTask,
    name='dogs_module.sync_bestrussian_rating',
    bind=True,
    soft_time_limit=120,
    time_limit=180,
)
def sync_bestrussian_rating_task(self, year: int = None) -> dict:
    from datetime import date
    from ..services.bestrussian_service import sync_husky_rating

    y = year or date.today().year
    return sync_husky_rating(y)
