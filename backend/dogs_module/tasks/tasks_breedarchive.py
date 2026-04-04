# dogs_module/tasks/tasks_breedarchive.py
"""Celery задачи для синхронизации данных из BreedArchive."""

import logging
import time
from typing import Dict

from celery import shared_task, Task
from celery.utils.log import get_task_logger

from ..services.integration import process_ba_dog_tree, process_ba_full_pedigree
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
    """Загружает собаку из BA по UUID — только 5 поколений предков (быстро)."""
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
    name='dogs_module.fetch_full_pedigree',
    bind=True,
    soft_time_limit=7200,
    time_limit=7500,
)
def fetch_full_pedigree_task(self, uuid: str, force_update: bool = False) -> Dict:
    """
    Загружает ПОЛНОЕ дерево предков собаки из BA без ограничения в 5 поколений.
    Рекурсивно обходит всё дерево вплоть до самых ранних предков в BA.
    """
    start_time = time.time()

    if force_update:
        invalidate_dog_cache(uuid)

    try:
        dog = process_ba_full_pedigree(uuid=uuid)
        if not dog:
            return {
                'status': 'error',
                'error': f'Не удалось обработать uuid={uuid}',
                'processing_time': time.time() - start_time,
            }
        return {
            'status': 'success',
            'dog_id': dog.id,
            'uuid': uuid,
            'name': dog.registered_name,
            'processing_time': time.time() - start_time,
        }
    except Exception as e:
        logger.error(f"❌ fetch_full_pedigree_task: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'processing_time': time.time() - start_time,
        }


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
    raw_list = fetch_recent_dogs(
        pages_count=pages_count, start_page=start_page, is_full_sync=is_full_sync
    )
    if not raw_list:
        return {'status': 'success', 'fetched': 0, 'dispatched': 0,
                'processing_time': time.time() - start_time}
    dispatched = 0
    for idx, brief in enumerate(raw_list):
        if brief.get('uuid'):
            fetch_breedarchive_dog_task.apply_async(
                args=[brief['uuid']], countdown=idx * 2
            )
            dispatched += 1
    return {'status': 'dispatched', 'fetched': len(raw_list), 'dispatched': dispatched,
            'processing_time': time.time() - start_time}


@shared_task(
    base=BaseBATask,
    name='dogs_module.sync_breedarchive_browse',
    bind=True,
    soft_time_limit=3600,
    time_limit=4200,
)
def sync_breedarchive_browse_task(self, recent_days: int = 1) -> Dict:
    """
    Парсит browse-страницу BA через Playwright.
    Для каждой найденной собаки запускает fetch_full_pedigree_task —
    все поколения предков, а не только 5.
    """
    start_time = time.time()
    result = parse_browse_page(recent_days=recent_days)

    if result['status'] == 'error':
        return {'status': 'error', 'error': result.get('error'),
                'processing_time': time.time() - start_time}

    dogs_data = result.get('dogs', [])
    dispatched = 0

    for idx, full_data in enumerate(dogs_data):
        uuid = full_data.get('uuid')
        if uuid:
            fetch_full_pedigree_task.apply_async(
                args=[uuid],
                countdown=idx * 3,
            )
            dispatched += 1

    return {
        'status': 'dispatched',
        'found': len(dogs_data),
        'dispatched': dispatched,
        'pages_processed': result.get('pages_processed', 0),
        'processing_time': time.time() - start_time,
    }


@shared_task(
    base=BaseBATask,
    name='dogs_module.import_hybrid_full_dog',
    bind=True,
    soft_time_limit=7200,
    time_limit=7500,
)
def import_hybrid_full_dog_task(
        self,
        zooportal_id: str,
        generations: int = 3,
        force_update: bool = False,
        _enrich_ancestors: bool = True,
) -> Dict:
    """
    Гибридный импорт одной собаки: Zoo данные + BA полное дерево предков.
    """
    start_time = time.time()
    from ..services.integration import process_hybrid_full_pedigree

    try:
        dog = process_hybrid_full_pedigree(
            zooportal_id=zooportal_id,
            generations=generations,
            force_update=force_update,
            _enrich_ancestors=_enrich_ancestors
        )
        if not dog:
            return {
                'status': 'error',
                'error': f'Не удалось обработать zooportal_id={zooportal_id}',
                'processing_time': time.time() - start_time,
            }
        return {
            'status': 'success',
            'dog_id': dog.id,
            'zooportal_id': zooportal_id,
            'name': dog.registered_name,
            'processing_time': time.time() - start_time,
        }
    except Exception as e:
        logger.error(f"❌ import_hybrid_full_dog_task: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'processing_time': time.time() - start_time,
        }


@shared_task(
    base=BaseBATask,
    name='dogs_module.import_hybrid_full_page',
    bind=True,
    soft_time_limit=7200,
    time_limit=7500,
)
def import_hybrid_full_page_task(
        self,
        page_num: int,
        max_dogs: int = 11,
        generations: int = 5,
        delay: float = 2.0,
) -> Dict:
    """
    Гибридный импорт страницы Zoo: для каждой собаки запускает
    Zoo → BA полное дерево предков (все поколения) → Zoo патч.
    """
    start_time = time.time()
    from ..services.integration import process_hybrid_full_pedigree_page

    try:
        result = process_hybrid_full_pedigree_page(
            page_num=page_num,
            max_dogs=max_dogs,
            generations=generations,
            delay=delay,
        )
        result['status'] = 'success'
        result['page'] = page_num
        result['processing_time'] = time.time() - start_time
        return result
    except Exception as e:
        logger.error(f"❌ import_hybrid_full_page_task: {e}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
            'processing_time': time.time() - start_time,
        }


@shared_task(
    base=BaseBATask,
    name='dogs_module.import_hybrid_full_range',
    bind=True,
    soft_time_limit=300,
    time_limit=360,
)
def import_hybrid_full_range_task(
        self,
        start_page: int,
        end_page: int,
        max_dogs_per_page: int = 11,
        generations: int = 5,
        delay: float = 2.0,
        countdown_between_pages: int = 30,
) -> Dict:
    """
    Диспатчит import_hybrid_full_page_task для каждой страницы в диапазоне.
    Возвращает список task_id.
    """
    start_time = time.time()
    dispatched_tasks = []

    for page_num in range(start_page, end_page + 1):
        countdown = (page_num - start_page) * countdown_between_pages
        task = import_hybrid_full_page_task.apply_async(
            kwargs={
                'page_num': page_num,
                'max_dogs': max_dogs_per_page,
                'generations': generations,
                'delay': delay,
            },
            countdown=countdown,
        )
        dispatched_tasks.append({'page': page_num, 'task_id': task.id})
        logger.info(f"  📄 Страница {page_num} → task {task.id} (countdown={countdown}с)")

    return {
        'status': 'dispatched',
        'pages': end_page - start_page + 1,
        'dispatched': dispatched_tasks,
        'processing_time': time.time() - start_time,
    }


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