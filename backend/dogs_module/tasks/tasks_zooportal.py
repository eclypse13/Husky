# dogs_module/tasks/tasks_zooportal.py
"""
Celery задачи для импорта собак из Zooportal.
"""

import logging
import time
from typing import Dict, List, Optional, Set

from celery import shared_task, Task
from celery.utils.log import get_task_logger

from ..services.integration import (
    parse_dog_data,
    parse_dog_data_recursive,
    save_dog_with_ancestors,
    process_dog_from_zooportal,
    mark_recursively_done,
    is_recursively_done,
)
from ..parsers.zooportal import BrowserManager, zooportal_parser

logger = get_task_logger(__name__)


class BaseImportTask(Task):
    autoretry_for = (ConnectionError, TimeoutError, RuntimeError)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True


# ЗАДАЧА 1: ИМПОРТ ОДНОЙ СОБАКИ (с рекурсивными предками)
def _save_parsed_dogs(
        parsed_list: list,
        generations: int = 3,
        main_ids: set = None,
) -> tuple:
    """
    Сохраняет список распарсенных собак в БД и помечает как обработанные.
    Возвращает (dog_ids, imported_count, failed_count).
    """
    dog_ids = []
    imported = save_failed = 0

    for idx, parsed in enumerate(parsed_list, 1):
        zid = parsed['zooportal_id']
        is_main = main_ids is None or zid in main_ids
        prefix = "🐕" if is_main else "  👤"
        try:
            dog = save_dog_with_ancestors(parsed)
            mark_recursively_done(zid, generations)
            imported += 1
            dog_ids.append(dog.id)
            logger.info(f"  [{idx}/{len(parsed_list)}] {prefix} Сохранена: {dog.registered_name}")
        except Exception as e:
            save_failed += 1
            logger.error(f"  [{idx}/{len(parsed_list)}] ❌ Ошибка сохранения {zid}: {e}")

    return dog_ids, imported, save_failed


@shared_task(
    base=BaseImportTask,
    name='dogs_module.import_zooportal_dog',
    bind=True,
    soft_time_limit=3600,  # 1 час — рекурсия может быть глубокой
    time_limit=7200,  # 70 минут жёсткий лимит
    autoretry_for=(ConnectionError, TimeoutError, ValueError, RuntimeError),
    retry_kwargs={'max_retries': 5},
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def import_zooportal_dog_task(self, zooportal_id: str) -> Dict:
    """
    Импортирует одну собаку + рекурсивно всех предков с zooportal_id.
    """
    start_time = time.time()
    # Дедлайн: оставляем 5 минут буфера до soft_time_limit
    deadline = start_time + 3300  # 55 минут

    logger.info(f"🚀 Импорт с рекурсией: zooportal_id={zooportal_id}")

    self.update_state(
        state='PROGRESS',
        meta={'status': 'parsing', 'zooportal_id': zooportal_id}
    )

    try:
        dog = process_dog_from_zooportal(
            zooportal_id=zooportal_id,
            generations=3,
            deadline=deadline,
        )

        processing_time = time.time() - start_time
        # Защита: process_dog_from_zooportal должна всегда возвращать Dog,
        # но на случай непредвиденного None — не падаем с AttributeError
        if dog is None:
            logger.error(f"❌ process_dog_from_zooportal вернул None для {zooportal_id}")
            raise ValueError(f"Не удалось получить объект собаки {zooportal_id}")
        return {
            'status': 'success',
            'dog_id': dog.id,
            'zooportal_id': zooportal_id,
            'name': dog.registered_name,
            'processing_time': processing_time,
        }

    except Exception as e:
        logger.error(f"❌ Ошибка импорта {zooportal_id}: {e}")
        raise


# ЗАДАЧА 2: ИМПОРТ ОДНОЙ СТРАНИЦЫ ПОИСКА (с рекурсивными предками)
@shared_task(
    base=BaseImportTask,
    name='dogs_module.import_zooportal_page',
    bind=True,
    soft_time_limit=3600,  # 1 час — рекурсия существенно увеличивает время
    time_limit=4200,  # 70 минут жёсткий лимит
)
def import_zooportal_page_task(
        self,
        page_num: int,
        max_dogs: int = 10,
        delay: float = 2.0,
        generations: int = 3,
) -> Dict:
    """
    Импортирует одну страницу поиска Zooportal.

    РЕКУРСИВНАЯ ВЕРСИЯ:
      Каждая собака на странице парсится вместе с ПОЛНЫМ деревом предков.
      Один BrowserManager открыт на весь процесс.
      Один visited Set разделяется между всеми собаками страницы
      (предотвращает дублирование общих предков).
    """
    start_time = time.time()
    # Дедлайн для рекурсии: оставляем 5 минут до soft_time_limit
    deadline = start_time + 3300  # 55 минут

    logger.info(
        f"📄 Страница #{page_num} | max_dogs={max_dogs} | "
        f"delay={delay}с | рекурсия включена"
    )

    # Один visited для всей страницы — общие предки парсятся один раз
    visited: Set[str] = set()
    all_parsed: List[Dict] = []
    parse_failed = 0
    total = 0

    # ЭТАП 1+2: Парсинг
    try:
        with BrowserManager() as browser:

            # 1. Список собак со страницы
            self.update_state(
                state='PROGRESS',
                meta={'status': 'loading_search_page', 'page': page_num}
            )

            dogs_list = zooportal_parser.parse_search_page_with_browser(
                browser, page_num
            )

            if not dogs_list:
                logger.warning(f"⚠️ Страница {page_num} пуста")
                return {
                    'status': 'success',
                    'page': page_num,
                    'total': 0,
                    'imported': 0,
                    'failed': 0,
                    'ancestors_parsed': 0,
                    'dog_ids': [],
                    'processing_time': time.time() - start_time,
                }

            dogs_list = dogs_list[:max_dogs]
            total = len(dogs_list)
            logger.info(f"  Найдено {total} собак на странице {page_num}")

            # 2. Рекурсивный парсинг каждой собаки
            for idx, dog_info in enumerate(dogs_list, 1):
                zooportal_id = dog_info.get('zooportal_id')

                if not zooportal_id:
                    logger.warning(f"  [{idx}/{total}] Нет zooportal_id, пропуск")
                    parse_failed += 1
                    continue

                # Если собака уже полностью обработана — пропускаем
                if is_recursively_done(zooportal_id, generations):
                    logger.info(
                        f"  [{idx}/{total}] ⏭️  {zooportal_id} уже в recursive_done"
                    )
                    continue

                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': 'parsing',
                        'page': page_num,
                        'current': idx,
                        'total': total,
                        'zooportal_id': zooportal_id,
                        'visited_count': len(visited),
                        'parsed_count': len(all_parsed),
                    }
                )

                try:
                    results = parse_dog_data_recursive(
                        browser=browser,
                        zooportal_id=zooportal_id,
                        generations=generations,
                        visited=visited,  # ОБЩИЙ visited для всей страницы
                        deadline=deadline,
                    )
                    all_parsed.extend(results)

                    main_name = (
                        results[0]['merged_data'].get('registered_name', '?')
                        if results else '?'
                    )
                    logger.info(
                        f"  [{idx}/{total}] ✅ {main_name} "
                        f"(+{len(results) - 1} предков, "
                        f"visited={len(visited)}, "
                        f"total_parsed={len(all_parsed)})"
                    )

                except Exception as e:
                    parse_failed += 1
                    logger.error(
                        f"  [{idx}/{total}] ❌ Ошибка парсинга {zooportal_id}: {e}"
                    )

                # Задержка только между основными собаками страницы
                # (не между рекурсивными предками — там встроенные 2с)
                if idx < total and deadline and time.time() < deadline:
                    time.sleep(delay)

        # ── BrowserManager.__exit__ → playwright.stop() → ORM свободен ──────
        logger.info(
            f"  Парсинг завершён: {len(all_parsed)} результатов "
            f"({parse_failed} ошибок). Сохраняем в БД..."
        )

    except Exception as e:
        logger.error(f"❌ Критическая ошибка страницы {page_num}: {e}")
        raise

    # ЭТАП 3+4: Дедупликация + Сохранение в БД (Playwright остановлен)
    from ..services.integration import deduplicate_parsed
    unique_parsed = deduplicate_parsed(all_parsed)
    if len(unique_parsed) < len(all_parsed):
        logger.info(f"  Дедупликация: {len(all_parsed)} → {len(unique_parsed)}")
    imported = 0
    save_failed = 0
    dog_ids: List[int] = []
    # Считаем сколько из сохранённых — основные собаки (не рекурсивные предки)
    main_dog_ids_on_page = {d['zooportal_id'] for d in dogs_list if d.get('zooportal_id')}
    ancestors_parsed = sum(
        1 for p in unique_parsed
        if p['zooportal_id'] not in main_dog_ids_on_page
    )

    dog_ids, imported, save_failed = _save_parsed_dogs(
        unique_parsed, generations=generations, main_ids=main_dog_ids_on_page
    )

    processing_time = time.time() - start_time
    failed = parse_failed + save_failed

    logger.info(
        f"✅ Страница {page_num}: {imported}/{total} основных + "
        f"{ancestors_parsed} предков сохранено | "
        f"{failed} ошибок | {processing_time:.1f}с"
    )

    return {
        'status': 'success',
        'page': page_num,
        'total': total,
        'imported': imported,
        'ancestors_parsed': ancestors_parsed,
        'total_saved': imported,
        'failed': failed,
        'dog_ids': dog_ids,
        'processing_time': processing_time,
    }


# ЗАДАЧА 3: ЗАПУСК ИМПОРТА ДИАПАЗОНА СТРАНИЦ (NON-BLOCKING DISPATCH)
@shared_task(
    name='dogs_module.import_zooportal_range',
    bind=True,
    soft_time_limit=120,
    time_limit=180,
)
def import_zooportal_range_task(
        self,
        start_page: int,
        end_page: int,
        max_dogs_per_page: int = 10,
        delay: float = 2.0,
        generations: int = 3,
        countdown_between_pages: int = 5,
) -> Dict:
    """
    Запускает импорт диапазона страниц через независимые Celery задачи.
    """
    total_pages = end_page - start_page + 1
    logger.info(
        f"📚 Dispatch страниц {start_page}–{end_page} "
        f"({total_pages} стр | countdown={countdown_between_pages}с/стр)"
    )

    dispatched = 0
    failed_dispatch = 0

    for idx, page_num in enumerate(range(start_page, end_page + 1)):
        try:
            countdown = idx * countdown_between_pages

            import_zooportal_page_task.apply_async(
                args=[page_num, max_dogs_per_page, delay, generations],
                countdown=countdown,
                task_id=f"import_page_{page_num}",
            )
            dispatched += 1

            if idx % 100 == 0 and idx > 0:
                logger.info(
                    f"  Отправлено {dispatched}/{total_pages} задач "
                    f"(последняя: стр {page_num})"
                )

        except Exception as e:
            failed_dispatch += 1
            logger.error(f"  ❌ Ошибка dispatch стр {page_num}: {e}")

    logger.info(
        f"✅ Dispatch завершён: {dispatched} задач, "
        f"{failed_dispatch} ошибок"
    )

    return {
        'status': 'dispatched',
        'start_page': start_page,
        'end_page': end_page,
        'total_pages': total_pages,
        'dispatched': dispatched,
        'failed_dispatch': failed_dispatch,
        'message': (
            f"Задачи отправлены. Рекурсия включена — время выполнения "
            f"первого прогона существенно больше чем без рекурсии. "
            f"Повторные прогоны быстрые (кеш)."
        ),
    }


# ЗАДАЧА 4: ПОЛНЫЙ ИМПОРТ ВСЕХ СТРАНИЦ
@shared_task(
    name='dogs_module.import_all_pages',
    bind=True,
    soft_time_limit=120,
    time_limit=180,
)
def import_all_pages_task(
        self,
        total_pages: int = 1720,
        max_dogs_per_page: int = 10,
        delay: float = 2.0,
        generations: int = 3,
        countdown_between_pages: int = 30,  # Увеличено из-за рекурсии
) -> Dict:
    """
    Запускает импорт ВСЕХ страниц через import_zooportal_range_task.
    """
    logger.info(f"🚀 Полный импорт {total_pages} страниц (с рекурсией)")

    result = import_zooportal_range_task.apply_async(
        args=[1, total_pages, max_dogs_per_page, delay, generations,
              countdown_between_pages]
    )

    return {
        'status': 'dispatched',
        'total_pages': total_pages,
        'range_task_id': result.id,
        'message': (
            f'Импорт {total_pages} страниц запущен с рекурсивным парсингом предков. '
            f'task_id={result.id}'
        ),
    }


# ЗАДАЧА 5: АВТОМАТИЧЕСКИЙ ИМПОРТ НОВЫХ СОБАК (Celery Beat)
@shared_task(
    base=BaseImportTask,
    name='dogs_module.auto_import_new_dogs',
    bind=True,
    soft_time_limit=3600,  # Увеличено из-за рекурсии
    time_limit=4200,
)
def auto_import_new_dogs_task(
        self,
        check_pages: int = 1,
        delay: float = 2.0,
) -> Dict:
    """
    Автоматически импортирует новых собак с первых страниц.

    РЕКУРСИВНАЯ ВЕРСИЯ:
      При импорте новой собаки рекурсивно обрабатываем всех её предков.
      recursive_done гарантирует что уже обработанные предки пропускаются.
    """
    logger.info(f"🔄 Автоимпорт: проверяем {check_pages} стр.")
    start_time = time.time()
    deadline = start_time + 3300

    # ── Фаза 1: Список собак со страниц (Playwright) ──────────────────────────
    all_dogs_from_site: List[Dict] = []
    try:
        with BrowserManager() as browser:
            for page_num in range(1, check_pages + 1):
                self.update_state(
                    state='PROGRESS',
                    meta={'status': 'loading_search', 'page': page_num}
                )
                try:
                    dogs_list = zooportal_parser.parse_search_page_with_browser(
                        browser, page_num
                    )
                    all_dogs_from_site.extend(dogs_list)
                    logger.info(f"  Страница {page_num}: {len(dogs_list)} собак")
                except Exception as e:
                    logger.error(f"  ❌ Ошибка загрузки стр {page_num}: {e}")
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка: {e}")
        raise

    # ── Фаза 2: Фильтрация (ORM — Playwright уже остановлен) ─────────────────
    from ..repositories import dog_repository as dog_repo
    to_import: List[str] = []
    skipped = 0

    for dog_info in all_dogs_from_site:
        zooportal_id = dog_info.get('zooportal_id')
        if not zooportal_id:
            continue

        # Сначала быстрая проверка кеша (без ORM)
        if is_recursively_done(zooportal_id):
            skipped += 1
            continue

        try:
            exists = dog_repo.exists_by_zooportal_id(zooportal_id)
        except Exception as e:
            logger.error(f"  ❌ Ошибка проверки БД: {e}")
            continue

        if exists:
            skipped += 1
        else:
            to_import.append(zooportal_id)

    logger.info(
        f"  Найдено новых: {len(to_import)}, пропущено: {skipped}"
    )

    if not to_import:
        return {
            'status': 'success',
            'imported': 0,
            'skipped': skipped,
            'processing_time': time.time() - start_time,
        }

    # ── Фаза 3: Рекурсивный парсинг новых (Playwright снова открывается) ─────
    all_parsed: List[Dict] = []
    visited: Set[str] = set()

    try:
        with BrowserManager() as browser:
            for idx, zooportal_id in enumerate(to_import, 1):
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'status': 'parsing_new',
                        'current': idx,
                        'total': len(to_import),
                        'zooportal_id': zooportal_id,
                    }
                )

                try:
                    results = parse_dog_data_recursive(
                        browser=browser,
                        zooportal_id=zooportal_id,
                        generations=3,
                        visited=visited,
                        deadline=deadline,
                    )
                    all_parsed.extend(results)
                    logger.info(
                        f"  [{idx}/{len(to_import)}] ✅ "
                        f"{results[0]['merged_data'].get('registered_name', '?') if results else '?'} "
                        f"(+{len(results) - 1} предков)"
                    )
                except Exception as e:
                    logger.error(
                        f"  [{idx}/{len(to_import)}] ❌ {zooportal_id}: {e}"
                    )

                if idx < len(to_import):
                    time.sleep(delay)
    except Exception as e:
        logger.error(f"❌ Ошибка рекурсивного парсинга: {e}")
        raise

    # ── Фаза 4: Сохранение (ORM — Playwright остановлен) ─────────────────────
    from ..services.integration import deduplicate_parsed
    unique_parsed = deduplicate_parsed(all_parsed)

    _, imported, save_failed = _save_parsed_dogs(unique_parsed, generations=3)

    processing_time = time.time() - start_time
    logger.info(
        f"✅ Автоимпорт завершён: новых {len(to_import)}, "
        f"сохранено всего {imported} (вкл. предков), "
        f"пропущено {skipped} (за {processing_time:.1f}с)"
    )

    return {
        'status': 'success',
        'new_dogs_found': len(to_import),
        'total_saved': imported,
        'skipped': skipped,
        'save_failed': save_failed,
        'processing_time': processing_time,
    }


# ЗАДАЧА 6: СТАТУС ПРОГРЕССА ИМПОРТА

@shared_task(
    name='dogs_module.check_import_progress',
    bind=True,
)
def check_import_progress_task(
        self,
        start_page: int,
        end_page: int,
) -> Dict:
    """
    Проверяет прогресс пакетного импорта по диапазону страниц.
    """
    from celery.result import AsyncResult

    total = end_page - start_page + 1
    completed = pending = failed = unknown = 0

    for page_num in range(start_page, end_page + 1):
        task_id = f"import_page_{page_num}"
        try:
            result = AsyncResult(task_id)
            state = result.state
            if state == 'SUCCESS':
                completed += 1
            elif state in ('PENDING', 'PROGRESS', 'STARTED', 'RETRY'):
                pending += 1
            elif state == 'FAILURE':
                failed += 1
            else:
                unknown += 1
        except Exception:
            unknown += 1

    return {
        'start_page': start_page,
        'end_page': end_page,
        'total': total,
        'completed': completed,
        'pending': pending,
        'failed': failed,
        'unknown': unknown,
        'progress_pct': round(completed / total * 100, 1) if total else 0,
    }


# ЗАДАЧА 7: ЕЖЕДНЕВНАЯ СИНХРОНИЗАЦИЯ СТРАНИЦ 1-10
@shared_task(
    name='dogs_module.daily_zooportal_sync',
    bind=True,
    soft_time_limit=60,
    time_limit=120,
)
def daily_zooportal_sync_task(
        self,
        start_page: int = 1,
        end_page: int = 10,
        max_dogs_per_page: int = 10,
        generations: int = 3,
        countdown_between_pages: int = 60,
) -> Dict:
    """
    Ежедневная синхронизация страниц Zooportal.
    Запускается Celery Beat каждый день в 4:00 (настраивается в celery.py).
    """
    start_time = time.time()
    total_pages = end_page - start_page + 1

    logger.info(
        f"🔄 Ежедневная синхронизация Zooportal: "
        f"страницы {start_page}–{end_page} "
        f"({total_pages} стр × {max_dogs_per_page} собак, "
        f"generations={generations})"
    )

    self.update_state(
        state='PROGRESS',
        meta={'status': 'dispatching', 'total_pages': total_pages}
    )

    dispatched = 0
    failed_dispatch = 0

    for idx, page_num in enumerate(range(start_page, end_page + 1)):
        try:
            countdown = idx * countdown_between_pages

            import_zooportal_page_task.apply_async(
                kwargs={
                    'page_num': page_num,
                    'max_dogs': max_dogs_per_page,
                    'delay': 2.0,
                    'generations': generations,
                },
                countdown=countdown,
                # ID содержит дату → легко найти задачи конкретного дня в мониторинге
                task_id=f"daily_sync_page_{page_num}_{int(start_time)}",
            )
            dispatched += 1
            logger.info(
                f"  📤 Стр {page_num} → старт через {countdown}с"
            )

        except Exception as e:
            failed_dispatch += 1
            logger.error(f"  ❌ Ошибка dispatch стр {page_num}: {e}")

    processing_time = time.time() - start_time
    logger.info(
        f"✅ Dispatch завершён: {dispatched}/{total_pages} задач отправлено "
        f"| {failed_dispatch} ошибок | {processing_time:.1f}с"
    )

    return {
        'status': 'dispatched',
        'start_page': start_page,
        'end_page': end_page,
        'total_pages': total_pages,
        'dispatched': dispatched,
        'failed_dispatch': failed_dispatch,
        'processing_time': processing_time,
    }


# ЗАДАЧА 8 + 9: ГИБРИДНЫЙ ИМПОРТ Zoo → BA полное дерево предков
from ..services.integration import collect_hybrid_page_data, save_hybrid_dog


@shared_task(
    base=BaseImportTask,
    name='dogs_module.import_hybrid_page',
    bind=True,
    soft_time_limit=3600,
    time_limit=4200,
)
def import_hybrid_page_task(
        self,
        page_num: int,
        max_dogs: int = 10,
        delay: float = 2.0,
        generations: int = 3,
) -> Dict:
    """Гибридный импорт страницы: Zoo список → BA полное дерево предков → Zoo патч."""
    start_time = time.time()
    deadline = start_time + 3300
    logger.info(f"🔀 Гибрид стр.{page_num}, max={max_dogs}, gen={generations}")

    self.update_state(state='PROGRESS', meta={'status': 'parsing', 'page': page_num})
    try:
        with BrowserManager() as browser:
            pending = collect_hybrid_page_data(
                browser=browser, page_num=page_num, max_dogs=max_dogs,
                generations=generations, delay=delay, deadline=deadline,
            )
    except Exception as e:
        logger.error(f"❌ Фаза 1 стр.{page_num}: {e}")
        raise

    if not pending:
        return {'status': 'success', 'page': page_num, 'total': 0, 'imported': 0,
                'failed': 0, 'processing_time': time.time() - start_time}

    visited: Set[str] = set()
    saved: Dict = {}
    imported = ba_count = zoo_count = failed = 0
    dog_ids: List[int] = []

    for idx, item in enumerate(pending, 1):
        zoo_id = item['zooportal_id']
        self.update_state(state='PROGRESS', meta={
            'status': 'saving', 'page': page_num,
            'current': idx, 'total': len(pending), 'imported': imported,
        })
        try:
            dog = save_hybrid_dog(zoo_id, item['zoo_raw'], item['ba_uuid'], visited, saved)
            if dog:
                imported += 1
                dog_ids.append(dog.id)
                if item['ba_uuid']:
                    # BA нашёлся — полные данные, помечаем как завершённое
                    mark_recursively_done(zoo_id, generations)
                    ba_count += 1
                else:
                    # Zoo fallback — минимальные данные, НЕ помечаем done
                    # чтобы при следующем прогоне BA мог найтись
                    zoo_count += 1
        except Exception as e:
            failed += 1
            logger.error(f"  [{idx}] ❌ {zoo_id}: {e}")

    processing_time = time.time() - start_time
    logger.info(
        f"✅ Гибрид стр.{page_num}: {imported}/{len(pending)} "
        f"(BA={ba_count}, Zoo={zoo_count}, err={failed}, {processing_time:.1f}с)"
    )
    return {
        'status': 'success', 'page': page_num,
        'total': len(pending), 'imported': imported,
        'ba_sourced': ba_count, 'zoo_fallback': zoo_count,
        'failed': failed, 'dog_ids': dog_ids,
        'processing_time': processing_time,
    }


@shared_task(
    name='dogs_module.import_hybrid_range',
    bind=True,
    soft_time_limit=120,
    time_limit=180,
)
def import_hybrid_range_task(
        self,
        start_page: int,
        end_page: int,
        max_dogs_per_page: int = 10,
        delay: float = 2.0,
        generations: int = 3,
        countdown_between_pages: int = 5,
) -> Dict:
    """Диспатчит import_hybrid_page_task для каждой страницы из диапазона."""
    dispatched = 0
    for idx, page_num in enumerate(range(start_page, end_page + 1)):
        try:
            import_hybrid_page_task.apply_async(
                kwargs={
                    'page_num': page_num, 'max_dogs': max_dogs_per_page,
                    'delay': delay, 'generations': generations,
                },
                countdown=idx * countdown_between_pages,
                task_id=f"hybrid_page_{page_num}",
            )
            dispatched += 1
        except Exception as e:
            logger.error(f"  Dispatch стр.{page_num}: {e}")

    total = end_page - start_page + 1
    logger.info(f"✅ Hybrid range: {dispatched}/{total} задач")
    return {
        'status': 'dispatched', 'start_page': start_page,
        'end_page': end_page, 'total_pages': total, 'dispatched': dispatched,
    }


@shared_task(
    base=BaseImportTask,
    name='dogs_module.import_hybrid_dog',
    bind=True,
    soft_time_limit=1800,
    time_limit=2100,
)
def import_hybrid_dog_task(self, zooportal_id: str, generations: int = 3) -> Dict:
    """Гибридный импорт одной собаки: Zoo страница → BA поиск → BA дерево предков → Zoo патч."""
    start_time = time.time()
    logger.info(f"🔀 Гибрид одна собака: zoo_id={zooportal_id}, gen={generations}")

    self.update_state(state='PROGRESS', meta={'status': 'parsing', 'zooportal_id': zooportal_id})

    # Фаза 1: Zoo страница + BA поиск (browser)
    try:
        with BrowserManager() as browser:
            pending = collect_hybrid_page_data(
                browser=browser,
                page_num=None,  # не нужна страница-список
                max_dogs=1,
                generations=generations,
                delay=0,
                deadline=None,
                zooportal_ids=[zooportal_id],  # передаём конкретный id
            )
    except Exception as e:
        logger.error(f"❌ Фаза 1 ({zooportal_id}): {e}")
        raise

    if not pending:
        return {
            'status': 'skipped', 'zooportal_id': zooportal_id,
            'reason': 'already_done_or_parse_failed',
            'processing_time': time.time() - start_time,
        }

    # Фаза 2: сохранение (browser закрыт)
    item = pending[0]
    visited: Set[str] = set()
    saved: Dict = {}
    try:
        dog = save_hybrid_dog(zooportal_id, item['zoo_raw'], item['ba_uuid'], visited, saved)
        if dog and item['ba_uuid']:
            # BA нашёлся — полные данные, помечаем done
            mark_recursively_done(zooportal_id, generations)
        # Zoo fallback — не помечаем, пусть перепроверяется при следующем прогоне
        return {
            'status': 'success',
            'zooportal_id': zooportal_id,
            'dog_id': dog.id if dog else None,
            'name': dog.registered_name if dog else None,
            'ba_sourced': bool(item['ba_uuid']),
            'processing_time': time.time() - start_time,
        }
    except Exception as e:
        logger.error(f"❌ Фаза 2 ({zooportal_id}): {e}")
        return {'status': 'error', 'error': str(e), 'processing_time': time.time() - start_time}
