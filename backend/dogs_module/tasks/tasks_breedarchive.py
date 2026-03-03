# dogs_module/tasks/tasks_breedarchive.py
"""Celery задачи для синхронизации данных из BreedArchive."""

import logging
import time
from typing import Dict

from celery import shared_task, Task
from celery.utils.log import get_task_logger

from ..services.integration import process_ba_dog_tree
from ..parsers.breedarchive import (
    fetch_breedarchive_dog,
    fetch_recent_dogs,
    parse_browse_page,
    invalidate_dog_cache,
)

logger = get_task_logger(__name__)


class BaseBATask(Task):
    autoretry_for = (ConnectionError, TimeoutError)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 120
    retry_jitter = True


@shared_task(
    base=BaseBATask,
    name='dogs_module.fetch_breedarchive_dog',
    bind=True,
    soft_time_limit=1800,
    time_limit=2100,
)
def fetch_breedarchive_dog_task(self, uuid: str, force_update: bool = False) -> Dict:
    """Загружает собаку из BA по UUID и рекурсивно сохраняет всех предков."""
    start_time = time.time()
    from ..models import Dog

    if not force_update:
        existing = Dog.objects.using('dogs_db').filter(uuid=uuid).first()
        if existing:
            logger.info(f"♻️ Уже в БД: {existing.registered_name}")
            return {'status': 'exists', 'dog_id': existing.id, 'name': existing.registered_name,
                    'processing_time': time.time() - start_time}

    if force_update:
        invalidate_dog_cache(uuid)

    full_data = fetch_breedarchive_dog(uuid)
    if not full_data:
        return {'status': 'error', 'error': f'BA не вернул данные для uuid={uuid}',
                'processing_time': time.time() - start_time}

    try:
        dog = process_ba_dog_tree(full_data)
        if not dog:
            return {'status': 'error', 'error': 'Ошибка сохранения дерева',
                    'processing_time': time.time() - start_time}
        return {'status': 'success', 'dog_id': dog.id, 'uuid': uuid,
                'name': dog.registered_name, 'processing_time': time.time() - start_time}
    except Exception as e:
        logger.error(f"❌ BA fetch: {e}")
        return {'status': 'error', 'error': str(e), 'processing_time': time.time() - start_time}


@shared_task(
    base=BaseBATask,
    name='dogs_module.sync_breedarchive_recent',
    bind=True,
    soft_time_limit=1800,
    time_limit=2100,
)
def sync_breedarchive_recent_task(
    self, pages_count: int = 1, start_page: int = 0, is_full_sync: bool = False,
) -> Dict:
    """Загружает список последних обновлений из BA и диспатчит задачи на каждую собаку."""
    start_time = time.time()
    raw_list = fetch_recent_dogs(pages_count=pages_count, start_page=start_page, is_full_sync=is_full_sync)
    if not raw_list:
        return {'status': 'success', 'fetched': 0, 'dispatched': 0, 'processing_time': time.time() - start_time}
    dispatched = sum(
        1 for idx, brief in enumerate(raw_list)
        if brief.get('uuid') and not fetch_breedarchive_dog_task.apply_async(
            args=[brief['uuid']], countdown=idx * 2
        ) is None
    )
    return {'status': 'dispatched', 'fetched': len(raw_list), 'dispatched': len(raw_list),
            'processing_time': time.time() - start_time}


@shared_task(
    base=BaseBATask,
    name='dogs_module.sync_breedarchive_browse',
    bind=True,
    soft_time_limit=3600,
    time_limit=4200,
)
def sync_breedarchive_browse_task(self, recent_days: int = 1) -> Dict:
    """Парсит browse-страницу BA через Playwright и диспатчит задачи на каждую собаку."""
    start_time = time.time()
    result = parse_browse_page(recent_days=recent_days)
    if result['status'] == 'error':
        return {'status': 'error', 'error': result.get('error'), 'processing_time': time.time() - start_time}
    dogs_data = result.get('dogs', [])
    dispatched = 0
    for idx, full_data in enumerate(dogs_data):
        uuid = full_data.get('uuid')
        if uuid:
            fetch_breedarchive_dog_task.apply_async(args=[uuid], countdown=idx * 2)
            dispatched += 1
    return {'status': 'dispatched', 'found': len(dogs_data), 'dispatched': dispatched,
            'pages_processed': result.get('pages_processed', 0),
            'processing_time': time.time() - start_time}

@shared_task(
    base=BaseBATask,
    name='dogs_module.refresh_cookies',
    bind=True,
    soft_time_limit=300,
    time_limit=360,
)
def refresh_cookies_task(self) -> Dict:
    """Превентивное обновление куков BA и Zoo. Запускается через beat каждые 20ч."""
    from ..utils.cookie_refresher import _do_ba_login, _do_zoo_login
    results = {}
    ba = _do_ba_login()
    results['ba'] = f"ok ({len(ba)} cookies)" if ba else "failed"
    zoo = _do_zoo_login()
    results['zoo'] = f"ok ({len(zoo)} cookies)" if zoo else "failed"
    logger.info(f"Cookie refresh: {results}")
    return results