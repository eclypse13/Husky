# dogs_module/services/integration.py
"""Сервис интеграции: парсинг + слияние Zoo/BA данных + сохранение в БД."""
import hashlib
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from django.core.cache import caches
from django.utils import timezone
from django.db import transaction

from ..models import (
    Dog, Breeder, Owner, Title, Litter,
    Dogbreederlink, Dogownerlink, Dogsiblinglink,
)
from ..parsers.zooportal import BrowserManager, zooportal_parser
from ..parsers.breedarchive import (
    search_breedarchive_by_name,
    fetch_breedarchive_dog, _collect_leaf_uuids, invalidate_dog_cache,
)
from ..utils.text import parse_sex, normalize_dog_name
from ..utils.parser_utils import parse_date, parse_color
from ..utils.dog_matcher import detect_dict_conflicts
from ..utils.titles import save_dog_titles

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# КЕШ
# ══════════════════════════════════════════════════════════════════════════════

_TTL_PARSE_RESULT   = 1 * 24 * 3600 # 24 часа — результат парсинга Zoo страницы
_TTL_RECURSIVE_DONE = 2 * 24 * 3600 # 2 дня  — Zoo собака уже обработана рекурсивно

_TTL_BA_FULLY_PARSED = 3 * 24 * 3600  # 3 дня - собака обработана полностью
_KEY_BA_FULLY_PARSED = "ba:fully_parsed:{uuid}"

def _cache():
    return caches['parsers']


def _key_parse_result(zooportal_id: str, generations: int) -> str:
    return f"parse:result:{zooportal_id}:{generations}"


def _key_recursive_done(zooportal_id: str, generations: int) -> str:
    return f"parse:recursive_done:{zooportal_id}:{generations}"


def is_parse_cached(zooportal_id: str, generations: int = 3) -> bool:
    return _cache().get(_key_parse_result(zooportal_id, generations)) is not None


def is_recursively_done(zooportal_id: str, generations: int = 3) -> bool:
    return _cache().get(_key_recursive_done(zooportal_id, generations)) is not None


def mark_recursively_done(zooportal_id: str, generations: int = 3) -> None:
    _cache().set(_key_recursive_done(zooportal_id, generations), 1, timeout=_TTL_RECURSIVE_DONE)


def invalidate_parse_cache(zooportal_id: str, generations: int = 3) -> None:
    c = _cache()
    c.delete(_key_parse_result(zooportal_id, generations))
    c.delete(_key_recursive_done(zooportal_id, generations))
    logger.info(f"🗑️ Кеш сброшен для {zooportal_id}")


def _is_ba_fully_parsed(uuid: str) -> bool:
    try:
        return bool(_cache().get(_KEY_BA_FULLY_PARSED.format(uuid=uuid)))
    except Exception:
        return False


def _mark_ba_fully_parsed(uuid: str) -> None:
    try:
        _cache().set(
            _KEY_BA_FULLY_PARSED.format(uuid=uuid),
            1,
            timeout=_TTL_BA_FULLY_PARSED,
        )
    except Exception:
        pass


def _invalidate_ba_fully_parsed(uuid: str) -> None:
    try:
        _cache().delete(_KEY_BA_FULLY_PARSED.format(uuid=uuid))
    except Exception:
        pass


def _compute_zoo_hash(name: str, sex: int) -> Optional[str]:
    """
    Вычисляет zoo_hash по имени и полу — ключ для слияния Zoo и BA записей.
    Логика идентична Dog.generate_zoo_hash() в models.py.
    """
    if not name or not sex:
        return None
    normalized = name.strip().lower()
    sex_str = 'male' if sex == 1 else 'female' if sex == 2 else None
    if not sex_str:
        return None
    return hashlib.sha256(f"{normalized}|{sex_str}".encode()).hexdigest()

# ══════════════════════════════════════════════════════════════════════════════
# СОХРАНЕНИЕ BA-ДЕРЕВА ПРЕДКОВ
# ══════════════════════════════════════════════════════════════════════════════

def process_ba_dog_tree(
    data: Dict,
    visited: Optional[Set[str]] = None,
    saved: Optional[Dict[str, Dog]] = None,
) -> Optional[Dog]:
    """Рекурсивно сохраняет собаку и всех её предков из BA-данных.

    visited — uuid которые уже начали обрабатываться (защита от циклов).
    saved   — uuid которые успешно сохранены в этом прогоне (для получения ссылки).
    Исключение одного узла не ломает весь обход — дерево продолжает строиться.
    """
    if visited is None:
        visited = set()
    if saved is None:
        saved = {}

    uuid = data.get('uuid')
    if not uuid:
        return None

    # Уже успешно сохранён в этом прогоне
    if uuid in saved:
        return saved[uuid]

    # Уже начали обрабатывать (возможен цикл) — берём из БД
    if uuid in visited:
        return Dog.objects.using('dogs_db').filter(uuid=uuid).first()

    visited.add(uuid)

    dam  = process_ba_dog_tree(data['dam'],  visited, saved) if data.get('dam')  and data['dam'].get('uuid')  else None
    sire = process_ba_dog_tree(data['sire'], visited, saved) if data.get('sire') and data['sire'].get('uuid') else None

    try:
        dog = _save_ba_dog(data, dam, sire)
        saved[uuid] = dog
        _save_ba_relations(dog, data)
        return dog
    except Exception as e:
        logger.error(f"  Ошибка сохранения предка uuid={uuid}: {e}", exc_info=True)
        # Пытаемся найти собаку в БД (могла быть создана до ошибки)
        existing = Dog.objects.using('dogs_db').filter(uuid=uuid).first()
        if existing:
            # Даже при ошибке применяем FK-связи если они есть
            fk_update = {}
            if dam is not None:
                fk_update['dam_id'] = dam.pk
            if sire is not None:
                fk_update['sire_id'] = sire.pk
            if fk_update:
                try:
                    Dog.objects.using('dogs_db').filter(pk=existing.pk).update(**fk_update)
                    for k, v in fk_update.items():
                        setattr(existing, k, v)
                    logger.info(f"  ♻️ FK восстановлен для uuid={uuid}: {fk_update}")
                except Exception as fk_err:
                    logger.error(f"  FK fallback uuid={uuid}: {fk_err}")
            saved[uuid] = existing
        return existing


def process_ba_full_pedigree(
    uuid: str,
    api_dispatched: Optional[Set[str]] = None,
    depth: int = 0,
    max_depth: int = 30,
) -> Optional["Dog"]:
    """
    Рекурсивно загружает и сохраняет ПОЛНОЕ дерево предков собаки из BA.
    """
    if api_dispatched is None:
        api_dispatched = set()

    # ── Уровень 1: уже запустили в этом прогоне ──────────────────────────────
    if uuid in api_dispatched:
        return Dog.objects.using('dogs_db').filter(uuid=uuid).first()

    # ── Уровень 2: Redis — только для предков (depth > 0) ────────────────────
    # Корневую собаку (depth == 0) всегда обновляем.
    if depth > 0 and _is_ba_fully_parsed(uuid):
        existing = Dog.objects.using('dogs_db').filter(uuid=uuid).first()
        if existing:
            api_dispatched.add(uuid)
            logger.debug(
                f"{'  ' * depth}⚡ Redis HIT: {existing.registered_name} (uuid={uuid})"
            )
            return existing
        # В Redis есть но в БД нет — сбрасываем флаг, обрабатываем заново
        _invalidate_ba_fully_parsed(uuid)

    # ── Защита от слишком глубокой рекурсии ──────────────────────────────────
    if depth > max_depth:
        logger.warning(f"{'  ' * depth}⚠️ max_depth={max_depth} uuid={uuid}")
        return Dog.objects.using('dogs_db').filter(uuid=uuid).first()

    api_dispatched.add(uuid)
    indent = "  " * depth
    logger.info(f"{indent}🔍 BA full pedigree [depth={depth}]: uuid={uuid}")

    # ── Шаг 1: загрузка 5 поколений из API ───────────────────────────────────
    data = fetch_breedarchive_dog(uuid)
    if not data:
        logger.error(f"{indent}❌ Нет данных для uuid={uuid}")
        return None

    # ── Шаг 2: сохраняем дерево в БД ─────────────────────────────────────────
    try:
        dog = process_ba_dog_tree(data, visited=None, saved=None)
    except Exception as e:
        logger.error(f"{indent}❌ process_ba_dog_tree: {e}", exc_info=True)
        return None

    if not dog:
        logger.error(f"{indent}❌ process_ba_dog_tree вернул None uuid={uuid}")
        return None

    # ── Шаг 3: ищем граничные листья ─────────────────────────────────────────
    # Граничный лист: sire/dam = null, но sireId/damId > 0
    leaves: Set[str] = set()
    _collect_leaf_uuids(data, leaves)

    # Фильтруем только по api_dispatched и Redis.
    # db_saved НЕ используем — листья там как стабы без предков.
    new_leaves = {
        leaf for leaf in leaves
        if leaf not in api_dispatched
        and not _is_ba_fully_parsed(leaf)
    }

    logger.info(
        f"{indent}  Граничных: {len(leaves)}, новых: {len(new_leaves)}, "
        f"api_dispatched: {len(api_dispatched)}"
    )

    # ── Шаг 4: рекурсия по граничным листьям ─────────────────────────────────
    for leaf_uuid in new_leaves:
        time.sleep(0.3)
        process_ba_full_pedigree(
            uuid=leaf_uuid,
            api_dispatched=api_dispatched,
            depth=depth + 1,
            max_depth=max_depth,
        )

    # ── Помечаем как полностью обработанного ─────────────────────────────────
    # Ставим ПОСЛЕ рекурсии — значит все предки уже загружены.
    if depth > 0:
        _mark_ba_fully_parsed(uuid)

    logger.info(f"{indent}✅ BA full pedigree [depth={depth}]: завершено uuid={uuid}")
    return dog


def _dispatch_ancestor_enrichment(zoo_raw: Dict, root_zoo_id: str, enrich_ancestors: bool = False) -> None:
    """
    Диспатчит import_hybrid_full_dog_task для каждого Zoo-предка
    у которого есть zooportal_id.
    """
    from ..tasks.tasks_breedarchive import import_hybrid_full_dog_task

    ancestors = zoo_raw.get('pedigree', {}).get('ancestors', {})
    if not ancestors:
        return

    dispatched = 0
    seen_zoo_ids: Set[str] = set()

    for ancestor in ancestors.values():
        zoo_id = ancestor.get('zooportal_id')
        if not zoo_id or zoo_id == root_zoo_id:
            continue
        if zoo_id in seen_zoo_ids:
            continue
        seen_zoo_ids.add(zoo_id)

        import_hybrid_full_dog_task.apply_async(
            kwargs={
                'zooportal_id': zoo_id,
                'generations': 3,  # для предков достаточно
                'force_update': False,
                '_enrich_ancestors': enrich_ancestors,  # предки предков не диспатчим
            },
            countdown=30 * (dispatched + 1),  # 30с, 60с, 90с...
        )
        dispatched += 1

    if dispatched:
        logger.info(
            f"  📬 Диспатч Zoo-патча для {dispatched} предков "
            f"(root zoo_id={root_zoo_id})"
        )


def process_hybrid_full_pedigree(
        zooportal_id: str,
        generations: int = 5,
        force_update: bool = False,
        _enrich_ancestors: bool = True,
) -> Optional[Dog]:
    """
    Гибридный импорт одной собаки: Zoo данные + BA полное дерево предков.

    ПАРАМЕТРЫ:
      zooportal_id      — ID собаки на zooportal.pro
      generations       — глубина Zoo pedigree (для fallback)
      force_update      — сбросить BA-кеш и загрузить заново
      _enrich_ancestors — диспатчить задачи для Zoo-предков
    """
    logger.info(f"🔀 Hybrid full pedigree: zooportal_id={zooportal_id}")

    # ── Фаза 1: Zoo парсинг — только в браузере ───────────────────────────────
    zoo_raw: Dict = {}
    with BrowserManager() as browser:
        zoo_raw = zooportal_parser.parse_dog_page_with_browser(
            browser, zooportal_id, generations
        ) or {}

        if not zoo_raw.get('registered_name'):
            # Признак истёкшей сессии — обновляем куки и пробуем снова
            from ..utils.cookie_refresher import on_zoo_session_expired
            on_zoo_session_expired()
            browser._recreate_context()
            zoo_raw = zooportal_parser.parse_dog_page_with_browser(
                browser, zooportal_id, generations
            ) or {}
    # Браузер закрыт — теперь можно делать DB операции

    # ── Фаза 2: BA + DB — вне браузера ───────────────────────────────────────
    if not zoo_raw:
        logger.warning(f"  Zoo не вернул данные для {zooportal_id}")
        return Dog.objects.using('dogs_db').filter(zooportal_id=zooportal_id).first()

    zoo_name = (zoo_raw.get('registered_name') or '').strip()
    logger.info(f"  Zoo: '{zoo_name}' (zoo_id={zooportal_id})")

    ba_uuid: Optional[str] = None
    if zoo_name:
        try:
            ba_uuid = search_breedarchive_by_name(zoo_name)
            if ba_uuid:
                logger.info(f"  BA найден: uuid={ba_uuid}")
            else:
                logger.info(f"  ⚠️ BA не найден для '{zoo_name}'")
        except Exception as e:
            logger.error(f"  BA поиск '{zoo_name}': {e}")

    dog: Optional[Dog] = None

    if ba_uuid:
        if force_update:
            invalidate_dog_cache(ba_uuid)
        try:
            dog = process_ba_full_pedigree(uuid=ba_uuid)
            if dog:
                _patch_zoo_onto_ba_dog(dog, zoo_raw, zooportal_id)
                logger.info(
                    f"  ✅ Hybrid full: {dog.registered_name} "
                    f"(zoo_id={zooportal_id}, ba_uuid={ba_uuid})"
                )
        except Exception as e:
            logger.error(f"  BA full pedigree ({ba_uuid}): {e}", exc_info=True)
            dog = None

    if not dog:
        logger.info(f"  🦴 Zoo fallback для {zooportal_id}")
        dog = _save_zoo_fallback(zooportal_id, zoo_raw)

    # ── Фаза 3: диспатч Zoo-патча для предков ────────────────────────────────
    if _enrich_ancestors and dog:
        _dispatch_ancestor_enrichment(zoo_raw, zooportal_id)

    return dog


def process_hybrid_full_pedigree_page(
        page_num: Optional[int] = None,
        max_dogs: int = 11,
        generations: int = 5,
        delay: float = 2.0,
        deadline: Optional[float] = None,
        zooportal_ids: Optional[List[str]] = None,
) -> Dict:
    """
    Гибридный импорт страницы: Zoo страница + BA полное дерево для каждой собаки.
    """
    start_time = time.time()
    imported, failed, dog_ids = 0, 0, []

    # ── Фаза 1: Zoo парсинг всех собак страницы — один браузер ───────────────
    collected: List[Dict] = []
    with BrowserManager() as browser:
        if zooportal_ids:
            ids_to_process = zooportal_ids[:max_dogs]
        else:
            dogs_list = zooportal_parser.parse_search_page_with_browser(browser, page_num)
            ids_to_process = [
                                 d['zooportal_id'] for d in (dogs_list or []) if d.get('zooportal_id')
                             ][:max_dogs]

        if not ids_to_process:
            logger.warning(f"⚠️ Страница {page_num}: собак не найдено")
            return {'imported': 0, 'failed': 0, 'dog_ids': []}

        logger.info(f"📄 Hybrid full page {page_num}: {len(ids_to_process)} собак")

        for idx, zoo_id in enumerate(ids_to_process, 1):
            if deadline and time.time() > deadline:
                logger.warning(f"  ⏱️ Дедлайн на [{idx}] {zoo_id}")
                break
            try:
                zoo_raw = zooportal_parser.parse_dog_page_with_browser(
                    browser, zoo_id, generations
                ) or {}

                if not zoo_raw.get('registered_name'):
                    from ..utils.cookie_refresher import on_zoo_session_expired
                    on_zoo_session_expired()
                    browser._recreate_context()
                    zoo_raw = zooportal_parser.parse_dog_page_with_browser(
                        browser, zoo_id, generations
                    ) or {}

                collected.append({'zoo_id': zoo_id, 'zoo_raw': zoo_raw})
            except Exception as e:
                failed += 1
                logger.error(f"  [{idx}] Zoo парсинг {zoo_id}: {e}")

            if idx < len(ids_to_process):
                time.sleep(delay)
    # Браузер закрыт — теперь DB операции

    # ── Фаза 2: BA + DB для каждой собаки — вне браузера ─────────────────────
    for item in collected:
        zoo_id = item['zoo_id']
        zoo_raw = item['zoo_raw']

        if deadline and time.time() > deadline:
            break

        try:
            zoo_name = (zoo_raw.get('registered_name') or '').strip()
            ba_uuid = search_breedarchive_by_name(zoo_name) if zoo_name else None

            dog: Optional[Dog] = None

            if ba_uuid:
                dog = process_ba_full_pedigree(uuid=ba_uuid)
                if dog:
                    _patch_zoo_onto_ba_dog(dog, zoo_raw, zoo_id)
                    # Диспатчим обогащение Zoo-предков
                    _dispatch_ancestor_enrichment(zoo_raw, zoo_id)
                    imported += 1
                    dog_ids.append(dog.id)
                    continue

            dog = _save_zoo_fallback(zoo_id, zoo_raw)
            if dog:
                imported += 1
                dog_ids.append(dog.id)
                _dispatch_ancestor_enrichment(zoo_raw, zoo_id)
            else:
                failed += 1

        except Exception as e:
            failed += 1
            logger.error(f"  {zoo_id}: {e}", exc_info=True)

    processing_time = time.time() - start_time
    logger.info(
        f"✅ Hybrid full page {page_num}: "
        f"{imported} импортировано, {failed} ошибок, {processing_time:.1f}с"
    )
    return {
        'imported': imported,
        'failed': failed,
        'dog_ids': dog_ids,
        'processing_time': processing_time,
    }


def _save_ba_dog(data: Dict, dam: Optional[Dog], sire: Optional[Dog]) -> Dog:
    """
    Создаёт или обновляет Dog из BA-данных с готовыми ссылками на родителей.
    """
    uuid = data.get('uuid')
    if not uuid:
        raise ValueError("UUID обязателен")

    reg_num = data.get('registration_number') or data.get('registrationNumber')
    if reg_num:
        reg_num = re.sub(r'\s+', '', str(reg_num))

    photo_url = data.get('photo_url')
    if not photo_url or not str(photo_url).startswith('http'):
        path = data.get('primary_photo_path') or data.get('primaryPhotoPath')
        if path:
            base = 'https://siberianhusky.breedarchive.com/resource'
            photo_url = f"{base}/{path.lstrip('/')}"

    coi = data.get('coi')
    try:
        coi = float(coi) if coi is not None else None
    except (ValueError, TypeError):
        coi = None

    dob = parse_date(data.get('date_of_birth') or _assemble_date(data, 'birth'))
    dod = parse_date(data.get('date_of_death') or _assemble_date(data, 'death'))

    defaults = {
        'registered_name': data.get('registered_name') or data.get('registeredName'),
        'call_name': data.get('call_name') or data.get('callName'),
        'link_name': data.get('link_name') or data.get('linkName'),
        'sex': data.get('sex', 0),
        'date_of_birth': dob,
        'date_of_death': dod,
        'year_of_birth': _to_int(data.get('year_of_birth') or data.get('yearOfBirth')),
        'year_of_death': _to_int(data.get('yearOfDeath') or data.get('year_of_death')) or None,
        'color': parse_color(data.get('color') or '') or None,
        'color_marking': data.get('color_marking') or data.get('colorMarking') or None,
        'variety': data.get('variety') or None,
        'land_of_birth': data.get('land_of_birth') or data.get('landOfBirth') or None,
        'land_of_birth_code': data.get('land_of_birth_code') or data.get('landOfBirthCode') or None,
        'land_of_standing': data.get('land_of_standing') or data.get('landOfStanding') or None,
        'registration_number': reg_num or None,
        'registration_status': data.get('registration_status') or data.get('registrationStatus'),
        'prefix_titles': data.get('prefix_titles') or data.get('prefixTitles') or None,
        'suffix_titles': data.get('suffix_titles') or data.get('suffixTitles') or None,
        'photo_url': photo_url or None,
        'coi': coi,
        'neutered': data.get('neutered', False),
        'incomplete_pedigree': data.get('incomplete_pedigree') or data.get('incompletePedigree', False),
        'source': 'breedarchive.com',
        'dam': dam,
        'sire': sire,
        'dam_uuid': data.get('dam_uuid') or (data.get('dam', {}) or {}).get('uuid') or None,
        'sire_uuid': data.get('sire_uuid') or (data.get('sire', {}) or {}).get('uuid') or None,
        'dam_name': (data.get('dam') or {}).get('registeredName') or None,
        'dam_link_name': (data.get('dam') or {}).get('linkName') or None,
        'sire_name': (data.get('sire') or {}).get('registeredName') or None,
        'sire_link_name': (data.get('sire') or {}).get('linkName') or None,
        'health_info_general': data.get('health_info_general') or data.get('healthInfoGeneral'),
        'health_info_genetic': data.get('health_info_genetic') or data.get('healthInfoGenetic'),
        'has_conflicts': data.get('has_conflicts', False),
        'conflicts': data.get('conflicts'),
        'notes': data.get('private_note') or data.get('privateNote') or None,
    }
    defaults = {k: v for k, v in defaults.items() if v is not None and v != ''}

    # ── Поиск 1: по uuid ──────────────────────────────────────────────────────
    try:
        dog, created = Dog.objects.using('dogs_db').update_or_create(
            uuid=uuid, defaults=defaults
        )
    except Dog.MultipleObjectsReturned:
        dog = Dog.objects.using('dogs_db').filter(uuid=uuid).order_by('id').first()
        for k, v in defaults.items():
            setattr(dog, k, v)
        dog.save(using='dogs_db')
        created = False

    # ── Поиск 2: слияние с Zoo-записью по zoo_hash ────────────────────────────
    if created:
        name = defaults.get('registered_name', '')
        sex = defaults.get('sex', 0)
        zoo_hash = _compute_zoo_hash(name, sex)

        if zoo_hash:
            try:
                with transaction.atomic(using='dogs_db'):
                    zoo_twin = (
                        Dog.objects
                        .using('dogs_db')
                        .select_for_update(nowait=False)
                        .filter(zoo_hash=zoo_hash, uuid__isnull=True)
                        .exclude(pk=dog.pk)
                        .first()
                    )

                    if zoo_twin:
                        logger.info(
                            f"  🔗 Слияние Zoo→BA: '{name}' "
                            f"(zoo pk={zoo_twin.pk} → ba pk={dog.pk})"
                        )
                        merge_update: Dict = {}
                        if zoo_twin.zooportal_id and not dog.zooportal_id:
                            merge_update['zooportal_id'] = zoo_twin.zooportal_id
                        if zoo_twin.zoo_hash and not dog.zoo_hash:
                            merge_update['zoo_hash'] = zoo_twin.zoo_hash

                        for field in ('brand_chip', 'kennel', 'eyes_color', 'club',
                                      'size', 'weight', 'sports', 'locked', 'removed',
                                      'frozen_semen', 'approved_for_breeding'):
                            zoo_val = getattr(zoo_twin, field, None)
                            ba_val = getattr(dog, field, None)
                            if zoo_val is not None and ba_val is None:
                                merge_update[field] = zoo_val

                        if merge_update:
                            Dog.objects.using('dogs_db').filter(pk=dog.pk).update(**merge_update)
                            for k, v in merge_update.items():
                                setattr(dog, k, v)

                        Dog.objects.using('dogs_db').filter(dam_id=zoo_twin.pk).update(dam_id=dog.pk)
                        Dog.objects.using('dogs_db').filter(sire_id=zoo_twin.pk).update(sire_id=dog.pk)
                        zoo_twin.delete(using='dogs_db')

            except Exception as e:
                logger.warning(f"  ⚠️ Слияние Zoo→BA пропущено: {e}")

    # ── FK dam/sire ───────────────────────────────────────────────────────────
    fk_update: Dict = {}
    if dam is not None and dam.pk:
        fk_update['dam_id'] = dam.pk
    if sire is not None and sire.pk:
        fk_update['sire_id'] = sire.pk
    if fk_update:
        Dog.objects.using('dogs_db').filter(pk=dog.pk).update(**fk_update)
        for k, v in fk_update.items():
            setattr(dog, k, v)

    logger.info(
        f"  {'✅ Создана' if created else '🔄 Обновлена'}: "
        f"{dog.registered_name} (uuid={uuid})"
    )
    _schedule_photo_upload(dog)
    return dog


def _save_ba_relations(dog: Dog, data: Dict) -> None:
    """Сохраняет заводчиков, владельцев, титулы, сиблингов и помёты из BA."""
    ba_breeders = data.get('breeders', [])

    # Если массив breeders пустой — создаём заводчика из поля kennel
    if not ba_breeders and data.get('kennel'):
        kennel_name = (data['kennel'] or '').strip()
        if kennel_name:
            ba_breeders = [{'name': kennel_name, 'kennel': kennel_name, 'is_breeder': True}]

    for b in ba_breeders:
        if not isinstance(b, dict) or not b.get('name'):
            continue
        try:
            b_uuid = (b.get('uuid') or '').strip() or None
            b_kennel = (b.get('kennel') or b.get('name') or '').strip() or None
            if b_uuid:
                try:
                    breeder, _ = Breeder.objects.using('dogs_db').get_or_create(
                        uuid=b_uuid,
                        defaults={'name': b['name'], 'kennel': b_kennel, 'is_breeder': b.get('is_breeder', True)},
                    )
                except Exception:
                    breeder = Breeder.objects.using('dogs_db').filter(uuid=b_uuid).first()
                    if not breeder:
                        continue
            else:
                try:
                    breeder, _ = Breeder.objects.using('dogs_db').get_or_create(
                        name=b['name'],
                        defaults={'kennel': b_kennel, 'is_breeder': b.get('is_breeder', True)},
                    )
                except Exception:
                    breeder = Breeder.objects.using('dogs_db').filter(name=b['name']).first()
                    if not breeder:
                        continue
            if not breeder.kennel and b_kennel:
                Breeder.objects.using('dogs_db').filter(pk=breeder.pk).update(kennel=b_kennel)
            Dogbreederlink.objects.using('dogs_db').get_or_create(dog=dog, breeder=breeder)
        except Exception as e:
            logger.error(f"  Заводчик '{b.get('name')}': {e}")

    for o in data.get('owners', []):
        if not isinstance(o, dict) or not o.get('name'):
            continue
        try:
            try:
                owner, _ = Owner.objects.using('dogs_db').get_or_create(
                    name=o['name'],
                    defaults={'is_main_owner': o.get('is_main_owner', False), 'uuid': o.get('uuid', '')},
                )
            except Exception:
                owner = Owner.objects.using('dogs_db').filter(name=o['name']).first()
                if not owner:
                    continue
            Dogownerlink.objects.using('dogs_db').get_or_create(dog=dog, owner=owner)
        except Exception as e:
            logger.error(f"  Владелец '{o.get('name')}': {e}")

    # BA возвращает титулы как текстовые строки prefix_titles/suffix_titles,
    # а не массив titles. Парсим их через save_dog_titles из utils/titles.py.
    _prefix = data.get('prefix_titles') or data.get('prefixTitles') or ''
    _suffix = data.get('suffix_titles') or data.get('suffixTitles') or ''
    if _prefix or _suffix:
        try:
            save_dog_titles(dog, _prefix or None, _suffix or None, 'breedarchive.com')
        except Exception as e:
            logger.error(f"  Титулы для {dog.registered_name} (uuid={data.get('uuid')}): {e}")

    # На случай если BA когда-то начнёт отдавать структурированный массив titles
    for t in data.get('titles', []):
        if not isinstance(t, dict) or not t.get('short_name'):
            continue
        try:
            # Нормализуем country: пустая строка → None, чтобы не создавать дубли
            country = (t.get('country') or '').strip().lower() or None
            short_name = (t.get('short_name') or '').strip().lower()
            if not short_name:
                continue
            Title.objects.using('dogs_db').update_or_create(
                dog=dog,
                short_name=short_name,
                country=country,
                defaults={
                    'long_name':       t.get('long_name') or '',
                    'is_prefix':       t.get('is_prefix', False),
                    'has_winner_year': t.get('has_winner_year', False),
                    'winner_year':     t.get('winner_year'),
                },
            )
        except Exception as e:
            logger.error(f"  Титул '{t.get('short_name')}': {e}")

    for sib in data.get('siblings', []):
        if not isinstance(sib, dict) or not sib.get('uuid'):
            continue
        try:
            sibling, _ = Dog.objects.using('dogs_db').get_or_create(
                uuid=sib['uuid'],
                defaults={
                    'registered_name': sib.get('registered_name') or sib.get('registeredName') or '',
                    'sex': sib.get('sex', 0),
                    'source': 'breedarchive.com',
                },
            )
            Dogsiblinglink.objects.using('dogs_db').get_or_create(dog=dog, sibling=sibling)
        except Exception as e:
            logger.error(f"  Сиблинг '{sib.get('uuid')}': {e}")

    for lit in data.get('litters', []):
        if not isinstance(lit, dict):
            continue
        try:
            dam_uuid  = lit.get('dam',  {}).get('uuid')
            sire_uuid = lit.get('sire', {}).get('uuid')
            dam  = Dog.objects.using('dogs_db').filter(uuid=dam_uuid).first()  if dam_uuid  else None
            sire = Dog.objects.using('dogs_db').filter(uuid=sire_uuid).first() if sire_uuid else None
            fields = {
                'date_of_birth':       parse_date(lit.get('date_of_birth')),
                'litter_male_count':   lit.get('litter_male_count'),
                'litter_female_count': lit.get('litter_female_count'),
                'litter_undef_count':  lit.get('litter_undef_count'),
                'dam': dam, 'sire': sire,
            }
            fields = {k: v for k, v in fields.items() if v is not None}
            Litter.objects.using('dogs_db').update_or_create(
                dam=dam, sire=sire,
                date_of_birth=fields.get('date_of_birth'),
                defaults=fields,
            )
        except Exception as e:
            logger.error(f"  Помёт: {e}")


def _to_int(val) -> Optional[int]:
    try:
        return int(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _assemble_date(data: Dict, kind: str) -> Optional[str]:
    # snake = f'year_of_{kind}'
    # camel = f'year{"Of" + kind.capitalize()}'
    if kind == 'birth':
        y = _to_int(data.get('year_of_birth') or data.get('yearOfBirth'))
        m = _to_int(data.get('month_of_birth') or data.get('monthOfBirth'))
        d = _to_int(data.get('day_of_birth') or data.get('dayOfBirth'))
    else:  # death
        y = _to_int(data.get('year_of_death') or (data.get('yearOfDeath') or None))
        m = _to_int(data.get('month_of_death') or data.get('monthOfDeath'))
        d = _to_int(data.get('day_of_death') or data.get('dayOfDeath'))
    if y and m and d:
        return f"{y}-{m:02d}-{d:02d}"
    if y and m:
        return f"{y}-{m:02d}-01"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ПАРСИНГ ОДНОЙ СОБАКИ (Zoo + BA поиск → merged_data)
# ══════════════════════════════════════════════════════════════════════════════

def parse_dog_data(browser: BrowserManager, zooportal_id: str, generations: int = 3) -> Dict:
    """Парсит одну собаку: Zoo страница + BA базовые данные → merged_data + pedigree."""
    logger.info(f"🔍 parse_dog_data: zooportal_id={zooportal_id}")

    c = _cache()
    cache_key = _key_parse_result(zooportal_id, generations)
    cached = c.get(cache_key)
    if cached is not None:
        logger.info(f"🎯 Cache HIT: {zooportal_id} ({cached['merged_data'].get('registered_name', '?')})")
        return cached

    dog_raw = zooportal_parser.parse_dog_page_with_browser(browser, zooportal_id, generations)
    if not dog_raw:
        raise ValueError(f"Zooportal не вернул данные для {zooportal_id}")
    if not dog_raw.get('registered_name'):
        raise ValueError(f"Нет имени у собаки {zooportal_id}")

    pedigree = dog_raw.get('pedigree', {
        'parents': {'dam': None, 'sire': None},
        'ancestors': {}, 'relationships': [], 'base_dogs': {},
    })

    breedarchive_data = None
    try:
        ba_uuid = search_breedarchive_by_name(dog_raw['registered_name'])
        if ba_uuid:
            breedarchive_data = fetch_breedarchive_dog(ba_uuid)
            logger.info(f"✅ BA найден: {ba_uuid}")
        else:
            logger.info(f"⚠️ BA не найден: {dog_raw['registered_name']}")
    except Exception as e:
        logger.error(f"❌ BA ошибка для {dog_raw['registered_name']}: {e}")

    result = {
        'zooportal_id': zooportal_id,
        'merged_data':  _merge_dog_data(dog_raw, breedarchive_data),
        'pedigree':     pedigree,
    }
    c.set(cache_key, result, timeout=_TTL_PARSE_RESULT)
    return result


def parse_dog_data_recursive(
    browser: BrowserManager,
    zooportal_id: str,
    generations: int = 3,
    visited: Optional[Set[str]] = None,
    deadline: Optional[float] = None,
    _depth: int = 0,
) -> List[Dict]:
    """Рекурсивно парсит собаку и всех её предков у которых есть zooportal_id."""
    if visited is None:
        visited = set()
    indent = "  " * _depth

    if deadline and time.time() > deadline:
        logger.warning(f"{indent}⏱️ Дедлайн истёк, пропуск {zooportal_id}")
        return []
    if zooportal_id in visited:
        return []
    visited.add(zooportal_id)
    if is_recursively_done(zooportal_id, generations):
        logger.info(f"{indent}⏭️ {zooportal_id} уже обработан")
        return []

    try:
        result = parse_dog_data(browser, zooportal_id, generations)
    except Exception as e:
        logger.error(f"{indent}❌ Ошибка парсинга {zooportal_id}: {e}")
        return []

    all_results = [result]
    ancestors = result['pedigree'].get('ancestors', {})
    seen: Set[str] = set()
    to_recurse: List[str] = []

    for ancestor in ancestors.values():
        aid = ancestor.get('zooportal_id')
        if aid and aid not in visited and aid not in seen and not is_recursively_done(aid, generations):
            seen.add(aid)
            to_recurse.append(aid)

    for aid in to_recurse:
        if deadline and time.time() > deadline:
            logger.warning(f"{indent}⏱️ Дедлайн при обходе предков {zooportal_id}")
            break
        all_results.extend(parse_dog_data_recursive(
            browser=browser, zooportal_id=aid, generations=generations,
            visited=visited, deadline=deadline, _depth=_depth + 1,
        ))

    return all_results


# ══════════════════════════════════════════════════════════════════════════════
# СЛИЯНИЕ Zoo + BA
# ══════════════════════════════════════════════════════════════════════════════

def _merge_dog_data(zooportal_data: Dict, breedarchive_data: Optional[Dict] = None) -> Dict:
    """Объединяет Zoo и BA данные: Zoo приоритет для имени, BA для всего остального."""
    merged: Dict = {}
    merged['zooportal_id']   = zooportal_data.get('zooportal_id')
    merged['zoo_hash']       = zooportal_data.get('zoo_hash')
    merged['registered_name'] = zooportal_data.get('registered_name')

    _ZP_FIELDS = (
        'call_name', 'sex', 'date_of_birth', 'year_of_birth',
        'color', 'land_of_birth', 'registration_number', 'brand_chip',
        'photo_url', 'titles_text', 'prefix_titles',
        'breeder_name', 'breeder_url', 'breeder_kennel', 'breeder_kennel_url',
        'owner_name', 'owner_url', 'owner_kennel', 'owner_kennel_url',
        'sire_name', 'dam_name',
    )
    for key in _ZP_FIELDS:
        val = zooportal_data.get(key)
        if val not in (None, ''):
            merged[key] = val

    if breedarchive_data:
        _BA_FILL = (
            'call_name', 'sex', 'date_of_birth', 'year_of_birth',
            'month_of_birth', 'day_of_birth', 'color', 'land_of_birth',
            'registration_number', 'brand_chip', 'photo_url', 'prefix_titles',
        )
        for key in _BA_FILL:
            if not merged.get(key):
                val = breedarchive_data.get(key)
                if val not in (None, ''):
                    merged[key] = val

        _BA_EXCLUSIVE = (
            'uuid', 'link_name', 'color_marking', 'variety',
            'land_of_birth_code', 'land_of_standing', 'registration_status',
            'suffix_titles', 'coi', 'coi_updated_on', 'incomplete_pedigree',
            'neutered', 'kennel', 'breeders', 'owners',
        )
        for key in _BA_EXCLUSIVE:
            val = breedarchive_data.get(key)
            if val not in (None, ''):
                merged[key] = val

        _COMPARE = ('call_name', 'sex', 'date_of_birth', 'color', 'land_of_birth', 'registration_number', 'brand_chip')
        has_conflicts, conflicts = detect_dict_conflicts(
            {k: zooportal_data.get(k) for k in _COMPARE},
            {k: breedarchive_data.get(k) for k in _COMPARE},
            'zooportal.pro', 'breedarchive.com',
        )
        merged['_conflicts']     = conflicts if has_conflicts else {}
        merged['_has_conflicts'] = has_conflicts
    else:
        merged['_conflicts']     = {}
        merged['_has_conflicts'] = False

    if 'date_of_birth' in merged and isinstance(merged['date_of_birth'], str):
        parsed = parse_date(merged['date_of_birth'])
        if parsed:
            merged['date_of_birth'] = parsed
    if 'sex' in merged and isinstance(merged['sex'], str):
        merged['sex'] = parse_sex(merged['sex'])
    if 'color' in merged:
        merged['color'] = parse_color(merged['color'])

    return merged


# ══════════════════════════════════════════════════════════════════════════════
# СОХРАНЕНИЕ В БД (Zoo-путь)
# ══════════════════════════════════════════════════════════════════════════════

def save_dog_with_ancestors(parsed: Dict) -> Dog:
    """Сохраняет собаку, заводчика, владельца, титулы и устанавливает связи родословной."""
    merged_data  = parsed['merged_data']
    pedigree     = parsed['pedigree']
    zooportal_id = parsed['zooportal_id']

    dog = _save_dog(merged_data)
    _save_breeder_zooportal(dog, merged_data)
    _save_breeders_ba(dog, merged_data)
    _save_owner_for_dog(dog, merged_data)
    _save_titles_for_dog(dog, merged_data)

    if pedigree.get('ancestors'):
        logger.info(f"👨‍👩‍👧‍👦 Обработка {len(pedigree['ancestors'])} предков...")
        dog_map = _save_ancestors(pedigree)
        _apply_relationships(pedigree, dog_map, zooportal_id, dog)

    return dog

# zooportal
def _save_dog(dog_data: Dict) -> Dog:
    """
    Создаёт или обновляет запись Dog из Zoo merged_data.
    """
    zooportal_id = dog_data.get('zooportal_id')
    if not zooportal_id:
        raise ValueError("zooportal_id обязателен")

    fields = {
        'registered_name':     dog_data.get('registered_name'),
        'call_name':           dog_data.get('call_name'),
        'link_name':           dog_data.get('link_name'),
        'uuid':                dog_data.get('uuid'),
        'zoo_hash':            dog_data.get('zoo_hash'),
        'sex':                 dog_data.get('sex', 0),
        'date_of_birth':       dog_data.get('date_of_birth'),
        'year_of_birth':       dog_data.get('year_of_birth'),
        'month_of_birth':      dog_data.get('month_of_birth'),
        'day_of_birth':        dog_data.get('day_of_birth'),
        'land_of_birth':       dog_data.get('land_of_birth') or dog_data.get('country'),
        'land_of_birth_code':  dog_data.get('land_of_birth_code'),
        'land_of_standing':    dog_data.get('land_of_standing'),
        'color':               dog_data.get('color'),
        'color_marking':       dog_data.get('color_marking'),
        'variety':             dog_data.get('variety'),
        'registration_number': dog_data.get('registration_number'),
        'registration_status': dog_data.get('registration_status'),
        'brand_chip':          dog_data.get('brand_chip'),
        'coi':                 dog_data.get('coi'),
        'incomplete_pedigree': dog_data.get('incomplete_pedigree'),
        'neutered':            dog_data.get('neutered'),
        'photo_url':           dog_data.get('photo_url'),
        'prefix_titles':       dog_data.get('prefix_titles') or dog_data.get('titles_text'),
        'suffix_titles':       dog_data.get('suffix_titles'),
        'sire_name':           dog_data.get('sire_name'),
        'dam_name':            dog_data.get('dam_name'),
        'kennel':              dog_data.get('kennel') or dog_data.get('breeder_kennel'),
        'source':              'zooportal.pro',
        'has_conflicts':       dog_data.get('_has_conflicts') or None,
        'conflicts':           dog_data.get('_conflicts') or None,
        'modified_at':         timezone.now(),
    }
    update_fields = {k: v for k, v in fields.items() if v is not None}

    # ── Поиск 1: по zooportal_id ──────────────────────────────────────────────
    try:
        existing = Dog.objects.using('dogs_db').filter(
            zooportal_id=zooportal_id
        ).order_by('id').first()
    except Exception:
        existing = None

    if existing:
        # Уже есть — обновляем поля не перезаписывая BA-данные
        for k, v in update_fields.items():
            if k in ('uuid', 'source') and getattr(existing, k, None):
                continue  # не затираем BA uuid и source
            setattr(existing, k, v)
        existing.save(using='dogs_db')
        logger.info(f"  🔄 Обновлена: {existing.registered_name}")
        _schedule_photo_upload(existing, photo_bytes=dog_data.get("photo_bytes"))
        return existing

    # ── Поиск 2: по zoo_hash — ДО создания ───────────────────────────────────
    # Ищем любую запись с тем же именем и полом — BA или Zoo с другим zoo_id
    name = update_fields.get('registered_name', '')
    sex = update_fields.get('sex', 0)
    zoo_hash = _compute_zoo_hash(name, sex)

    if zoo_hash:
        try:
            with transaction.atomic(using='dogs_db'):
                hash_match = (
                    Dog.objects
                    .using('dogs_db')
                    .select_for_update(nowait=False)
                    .filter(zoo_hash=zoo_hash)
                    .first()
                )

                if hash_match:
                    logger.info(
                        f"  🔗 Zoo hash match: '{name}' → pk={hash_match.pk} "
                        f"(старый zooportal_id={hash_match.zooportal_id})"
                    )
                    merge: Dict = {'zooportal_id': zooportal_id}
                    for k, v in update_fields.items():
                        # Не перезаписываем BA-поля если они уже заполнены
                        if k in ('uuid', 'source') and getattr(hash_match, k, None):
                            continue
                        # Не перезаписываем уже заполненные поля из BA
                        current = getattr(hash_match, k, None)
                        if current is not None and k not in (
                            'zooportal_id', 'zoo_hash', 'modified_at',
                            'brand_chip', 'kennel', 'photo_url',
                            'registration_number', 'land_of_birth',
                        ):
                            continue
                        merge[k] = v

                    Dog.objects.using('dogs_db').filter(pk=hash_match.pk).update(**merge)
                    for k, v in merge.items():
                        setattr(hash_match, k, v)
                    logger.info(f"  🔄 Обновлена через zoo_hash: {hash_match.registered_name}")
                    _schedule_photo_upload(hash_match, photo_bytes=dog_data.get("photo_bytes"))
                    return hash_match

        except Exception as e:
            logger.warning(f"  ⚠️ Zoo hash поиск пропущен: {e}")

    # ── Поиск 3: создаём новую запись ────────────────────────────────────────
    try:
        dog = Dog.objects.using('dogs_db').create(**update_fields)
        logger.info(f"  ✅ Создана: {dog.registered_name}")
        _schedule_photo_upload(dog)
        return dog
    except Exception as e:
        # Последний шанс — гонка данных, кто-то создал пока мы проверяли
        logger.warning(f"  ⚠️ create упал ({e}), пробуем get")
        dog = Dog.objects.using('dogs_db').filter(
            zooportal_id=zooportal_id
        ).first()
        if dog:
            _schedule_photo_upload(dog, photo_bytes=dog_data.get("photo_bytes"))
            return dog
        raise

def _save_breeder_zooportal(dog: Dog, dog_data: Dict) -> None:
    name = dog_data.get('breeder_name')
    if not name:
        return
    try:
        try:
            breeder, _ = Breeder.objects.using('dogs_db').get_or_create(
                name=name,
                defaults={
                    'is_breeder':  True,
                    'kennel':      dog_data.get('breeder_kennel'),
                    'breeder_url': dog_data.get('breeder_url'),
                    'kennel_url':  dog_data.get('breeder_kennel_url'),
                },
            )
        except Exception:
            breeder = Breeder.objects.using('dogs_db').filter(name=name).first()
            if not breeder:
                return
        Dogbreederlink.objects.using('dogs_db').get_or_create(dog=dog, breeder=breeder)
    except Exception as e:
        logger.error(f"  Заводчик Zoo '{name}': {e}")


def _save_breeders_ba(dog: Dog, dog_data: Dict) -> None:
    """Сохраняет заводчиков из BA-массива breeders.
    Если breeders пустой — создаёт запись из поля kennel (name=kennel, kennel=kennel).
    """
    ba_breeders = dog_data.get('breeders') or []
    if not ba_breeders and dog_data.get('kennel'):
        kennel_name = (dog_data['kennel'] or '').strip()
        if kennel_name:
            ba_breeders = [{'name': kennel_name, 'kennel': kennel_name, 'is_breeder': True}]
    for raw in ba_breeders:
        if not isinstance(raw, dict) or not raw.get('name'):
            continue
        try:
            b_uuid = (raw.get('uuid') or '').strip() or None
            b_kennel = (raw.get('kennel') or raw.get('name') or '').strip() or None
            if b_uuid:
                breeder, _ = Breeder.objects.using('dogs_db').get_or_create(
                    uuid=b_uuid,
                    defaults={
                        'name':       raw['name'],
                        'kennel':     b_kennel,
                        'is_breeder': raw.get('is_breeder', True),
                    },
                )
            else:
                breeder, _ = Breeder.objects.using('dogs_db').get_or_create(
                    name=raw['name'],
                    defaults={
                        'kennel':     b_kennel,
                        'is_breeder': raw.get('is_breeder', True),
                    },
                )
            if not breeder.kennel and b_kennel:
                Breeder.objects.using('dogs_db').filter(pk=breeder.pk).update(kennel=b_kennel)
            Dogbreederlink.objects.using('dogs_db').get_or_create(dog=dog, breeder=breeder)
        except Exception as e:
            logger.error(f"  Заводчик BA '{raw.get('name')}': {e}")


def _save_owner_for_dog(dog: Dog, dog_data: Dict) -> None:
    """Сохраняет владельца из Zoo или BA данных."""
    owner_name = dog_data.get('owner_name')
    owner_uuid = None
    ba_owners = dog_data.get('owners') or []
    if not owner_name and ba_owners and isinstance(ba_owners[0], dict):
        owner_name = ba_owners[0].get('name')
        owner_uuid = ba_owners[0].get('uuid')
    if not owner_name:
        return
    try:
        if owner_uuid:
            owner, _ = Owner.objects.using('dogs_db').get_or_create(
                uuid=owner_uuid,
                defaults={
                    'name': owner_name, 'is_main_owner': True,
                    'kennel': dog_data.get('owner_kennel'),
                    'owner_url': dog_data.get('owner_url'),
                    'kennel_url': dog_data.get('owner_kennel_url'),
                },
            )
        else:
            owner, _ = Owner.objects.using('dogs_db').get_or_create(
                name=owner_name,
                defaults={
                    'is_main_owner': True,
                    'kennel': dog_data.get('owner_kennel'),
                    'owner_url': dog_data.get('owner_url'),
                    'kennel_url': dog_data.get('owner_kennel_url'),
                },
            )
        Dogownerlink.objects.using('dogs_db').get_or_create(dog=dog, owner=owner)
    except Exception as e:
        logger.error(f"  Владелец '{owner_name}': {e}")


def _save_titles_for_dog(dog: Dog, dog_data: Dict) -> None:
    """Сохраняет структурированные титулы из prefix/suffix строк."""
    source = 'breedarchive' if dog_data.get('uuid') else 'zooportal'
    save_dog_titles(
        dog,
        dog_data.get('prefix_titles') or dog_data.get('titles_text'),
        dog_data.get('suffix_titles'),
        source,
    )

def _save_ancestors(pedigree: Dict) -> Dict[str, Dog]:
    """
    Сохраняет предков из Zoo pedigree.
    """
    dog_map: Dict[str, Dog] = {}
    processed: Set[str] = set()

    for node_key, ancestor in pedigree['ancestors'].items():
        if node_key in processed:
            continue
        processed.add(node_key)

        name = ancestor.get('name')
        sex = ancestor.get('sex', 0)
        zoo_id = ancestor.get('zooportal_id')

        if not name:
            continue

        dog: Optional[Dog] = None

        try:
            # ── 1. Ищем по zooportal_id ───────────────────────────────────
            if zoo_id:
                dog = Dog.objects.using('dogs_db').filter(
                    zooportal_id=zoo_id
                ).first()
                if dog:
                    dog_map[node_key] = dog
                    continue

            # ── 2. Ищем по zoo_hash ───────────────────────────────────────
            zoo_hash = _compute_zoo_hash(name, sex)
            if zoo_hash:
                dog = Dog.objects.using('dogs_db').filter(
                    zoo_hash=zoo_hash
                ).first()
                if dog:
                    # Нашли по хешу — прописываем zooportal_id если его нет
                    if zoo_id and not dog.zooportal_id:
                        Dog.objects.using('dogs_db').filter(pk=dog.pk).update(
                            zooportal_id=zoo_id
                        )
                        dog.zooportal_id = zoo_id
                    dog_map[node_key] = dog
                    continue

            # ── 3. Создаём стаб ───────────────────────────────────────────
            if zoo_id:
                dog, created = Dog.objects.using('dogs_db').get_or_create(
                    zooportal_id=zoo_id,
                    defaults={
                        'registered_name': name,
                        'sex': sex,
                        'zoo_hash': _compute_zoo_hash(name, sex),
                    },
                )
            else:
                # Без zooportal_id и без совпадения по хешу — создаём по имени
                # Используем get_or_create чтобы не плодить дубли по имени
                dog, created = Dog.objects.using('dogs_db').get_or_create(
                    registered_name=name,
                    sex=sex,
                    defaults={
                        'zoo_hash': _compute_zoo_hash(name, sex),
                    },
                )

            dog_map[node_key] = dog

        except Exception as e:
            logger.error(f"  Предок '{name}' (zoo_id={zoo_id}): {e}")

    logger.info(f"  Предков: {len(dog_map)}")
    return dog_map

def _apply_relationships(
    pedigree: Dict, dog_map: Dict[str, Dog], root_zooportal_id: str, root_dog: Dog,
) -> None:
    """Устанавливает связи sire/dam для всех собак в родословной."""
    full_map = {**dog_map, f"{root_zooportal_id}:": root_dog}

    for base_key, base_info in pedigree.get('base_dogs', {}).items():
        if base_key not in full_map:
            bzid = base_info.get('zooportal_id')
            if bzid:
                dog_obj = Dog.objects.using('dogs_db').filter(zooportal_id=bzid).first()
                if dog_obj:
                    full_map[base_key] = dog_obj


    for rel in pedigree.get('relationships', []):
        child = full_map.get(rel.get('child_key'))
        parent = full_map.get(rel.get('parent_key'))
        if not child or not parent or not child.id or not parent.id:
            continue
        if rel['relation'] == 'sire' and child.sire_id != parent.id:
            Dog.objects.using('dogs_db').filter(pk=child.id).update(sire_id=parent.id)
            child.sire_id = parent.id
        elif rel['relation'] == 'dam' and child.dam_id != parent.id:
            Dog.objects.using('dogs_db').filter(pk=child.id).update(dam_id=parent.id)
            child.dam_id = parent.id


# ══════════════════════════════════════════════════════════════════════════════
# ОБЁРТКА ДЛЯ ОДИНОЧНОГО ИМПОРТА
# ══════════════════════════════════════════════════════════════════════════════

def process_dog_from_zooportal(
    zooportal_id: str, generations: int = 3, deadline: Optional[float] = None,
) -> Dog:
    """Полный цикл одиночного импорта одной собаки + все предки рекурсивно."""
    visited: Set[str] = set()

    with BrowserManager() as browser:
        all_parsed = parse_dog_data_recursive(
            browser=browser, zooportal_id=zooportal_id,
            generations=generations, visited=visited, deadline=deadline,
        )

    if not all_parsed:
        existing = Dog.objects.using('dogs_db').filter(zooportal_id=zooportal_id).first()
        if existing:
            logger.info(f"♻️ {zooportal_id} уже в БД: {existing.registered_name}")
            return existing
        invalidate_parse_cache(zooportal_id, generations)
        raise ValueError(f"Не удалось распарсить {zooportal_id}")

    root_dog = None
    for parsed in all_parsed:
        pid = parsed['zooportal_id']
        try:
            dog = save_dog_with_ancestors(parsed)
            mark_recursively_done(pid, generations)
            if pid == zooportal_id:
                root_dog = dog
        except Exception as e:
            logger.error(f"  Ошибка сохранения {pid}: {e}")
            if pid == zooportal_id:
                root_dog = Dog.objects.using('dogs_db').filter(zooportal_id=pid).first()

    if not root_dog:
        root_dog = Dog.objects.using('dogs_db').filter(zooportal_id=zooportal_id).first()
        if not root_dog:
            raise ValueError(f"Не удалось сохранить основную собаку {zooportal_id}")

    logger.info(f"🎉 Импорт завершён: {root_dog.registered_name} + {len(all_parsed) - 1} предков")
    return root_dog


# ══════════════════════════════════════════════════════════════════════════════
# ГИБРИДНЫЙ ИМПОРТ: Zoo список → BA дерево предков (до 5 поколения)
# ══════════════════════════════════════════════════════════════════════════════

def save_hybrid_dog(
    zoo_id: str,
    zoo_raw: Dict,
    ba_uuid: Optional[str],
    visited: Optional[Set[str]] = None,
    saved: Optional[Dict] = None,
) -> Optional[Dog]:
    """Фаза 2 гибридного импорта: BA дерево предков + Zoo патч, или Zoo-fallback."""
    if visited is None:
        visited = set()
    if saved is None:
        saved = {}

    if ba_uuid:
        try:
            ba_data = fetch_breedarchive_dog(ba_uuid)
            if ba_data:
                dog = process_ba_dog_tree(ba_data, visited, saved)
                if dog:
                    _patch_zoo_onto_ba_dog(dog, zoo_raw, zoo_id)
                    logger.info(f"  🔀 BA+Zoo: {dog.registered_name} (zoo_id={zoo_id})")
                    return dog
        except Exception as e:
            logger.error(f"  BA дерево ({zoo_id}): {e}")

    return _save_zoo_fallback(zoo_id, zoo_raw)


def _patch_zoo_onto_ba_dog(dog: Dog, zoo_raw: Dict, zoo_id: str) -> None:
    """Применяет Zoo-данные поверх BA-записи.

    Всегда: zooportal_id + имя в UPPERCASE.
    Для остальных полей: заполняет только если у BA-записи значение пустое.
    Нормализует цвет через parse_color, имя через normalize_dog_name,
    дату через parse_date.
    """
    update: Dict = {'zooportal_id': str(zoo_id)}

    # ── Имя — всегда из Zoo в UPPERCASE ───────────────────────────────────────
    zoo_name = zoo_raw.get('registered_name') or zoo_raw.get('name') or zoo_raw.get('registeredName') or ''
    if zoo_name:
        update['registered_name'] = normalize_dog_name(zoo_name)

    # call_name: если у BA пустое, берём из Zoo
    if not getattr(dog, 'call_name', None):
        call = zoo_raw.get('call_name')
        if call:
            update['call_name'] = call.strip()

    # ── Пол ───────────────────────────────────────────────────────────────────
    if not getattr(dog, 'sex', None):
        zoo_sex = zoo_raw.get('sex')
        if zoo_sex is not None:
            if isinstance(zoo_sex, int):
                update['sex'] = zoo_sex
            elif isinstance(zoo_sex, str):
                update['sex'] = parse_sex(zoo_sex)

    # ── Дата рождения ─────────────────────────────────────────────────────────
    if not getattr(dog, 'date_of_birth', None):
        dob = parse_date(zoo_raw.get('date_of_birth'))
        if dob:
            update['date_of_birth'] = dob
    if not getattr(dog, 'year_of_birth', None):
        yob = zoo_raw.get('year_of_birth')
        if yob:
            update['year_of_birth'] = _to_int(yob)

    # ── Дата смерти ───────────────────────────────────────────────────────────
    if not getattr(dog, 'date_of_death', None):
        dod = parse_date(zoo_raw.get('date_of_death'))
        if dod:
            update['date_of_death'] = dod
    if not getattr(dog, 'year_of_death', None):
        yod = zoo_raw.get('year_of_death')
        if yod:
            update['year_of_death'] = _to_int(yod)

    # ── Простые строковые поля (заполняем если пусто у BA) ────────────────────
    _SIMPLE_FIELDS = (
        'photo_url',
        'land_of_birth',
        'land_of_birth_code',
        'land_of_standing',
        'registration_number',
        'brand_chip',
        'kennel',
        'sire_name',
        'dam_name',
        'variety',
        'eyes_color',
        'distinguishing_features',
        'notes',
        'club',
    )
    for field in _SIMPLE_FIELDS:
        if not getattr(dog, field, None):
            val = zoo_raw.get(field)
            if val:
                update[field] = str(val).strip()

    # ── Цвет — нормализуем через parse_color ──────────────────────────────────
    if not getattr(dog, 'color', None):
        zoo_color = zoo_raw.get('color') or ''
        if zoo_color:
            update['color'] = parse_color(zoo_color)

    # color_marking: не нормализуем, берём как есть
    if not getattr(dog, 'color_marking', None):
        cm = zoo_raw.get('color_marking')
        if cm:
            update['color_marking'] = str(cm).strip()

    # ── Титулы ────────────────────────────────────────────────────────────────
    if not getattr(dog, 'prefix_titles', None):
        pt = zoo_raw.get('prefix_titles') or zoo_raw.get('titles_text')
        if pt:
            update['prefix_titles'] = str(pt).strip()
    if not getattr(dog, 'suffix_titles', None):
        st = zoo_raw.get('suffix_titles')
        if st:
            update['suffix_titles'] = str(st).strip()

    # ── COI ───────────────────────────────────────────────────────────────────
    if getattr(dog, 'coi', None) is None:
        zoo_coi = zoo_raw.get('coi')
        if zoo_coi is not None:
            try:
                update['coi'] = float(zoo_coi)
            except (ValueError, TypeError):
                pass

    # ── Размер / вес ─────────────────────────────────────────────────────────
    if getattr(dog, 'size', None) is None:
        try:
            sz = zoo_raw.get('size')
            if sz is not None:
                update['size'] = float(sz)
        except (ValueError, TypeError):
            pass
    if getattr(dog, 'weight', None) is None:
        try:
            wt = zoo_raw.get('weight')
            if wt is not None:
                update['weight'] = float(wt)
        except (ValueError, TypeError):
            pass

    # ── Применяем ────────────────────────────────────────────────────────────
    if update:
        Dog.objects.using('dogs_db').filter(pk=dog.pk).update(**update)
        for k, v in update.items():
            setattr(dog, k, v)

    # ── Заводчик из Zoo (если нет ни одного BA-заводчика) ────────────────────
    if not dog.breeders.using('dogs_db').exists():
        _save_breeder_zooportal(dog, zoo_raw)

    # ── Владелец из Zoo (если нет ни одного BA-владельца) ────────────────────
    if not dog.owners.using('dogs_db').exists():
        _save_owner_for_dog(dog, zoo_raw)

    # ── Титулы из Zoo (дополнительно, если есть строки) ──────────────────────
    prefix_for_titles = zoo_raw.get('prefix_titles') or zoo_raw.get('titles_text')
    suffix_for_titles = zoo_raw.get('suffix_titles')
    if prefix_for_titles or suffix_for_titles:
        save_dog_titles(dog, prefix_for_titles, suffix_for_titles, 'zooportal')


def _save_zoo_fallback(zoo_id: str, zoo_raw: Dict) -> Optional[Dog]:
    """Сохраняет собаку только из Zoo-данных когда BA не нашёл совпадений."""
    pedigree = zoo_raw.get('pedigree')
    if pedigree and pedigree.get('ancestors'):
        return save_dog_with_ancestors({
            'zooportal_id': zoo_id,
            'merged_data':  _merge_dog_data(zoo_raw, None),
            'pedigree':     pedigree,
        })
    name = zoo_raw.get('registered_name') or zoo_raw.get('name') or ''
    dog, _ = Dog.objects.using('dogs_db').update_or_create(
        zooportal_id=zoo_id,
        defaults={
            'registered_name': normalize_dog_name(name) if name else None,
            'sex':             zoo_raw.get('sex', 0),
            'color':           parse_color(zoo_raw.get('color') or ''),
            'photo_url':       zoo_raw.get('photo_url'),
            'land_of_birth':   zoo_raw.get('land_of_birth'),
            'source':          'zooportal.pro',
        },
    )
    logger.info(f"  🦴 Zoo fallback: {dog.registered_name}")
    return dog

def collect_hybrid_page_data(
    browser: BrowserManager,
    page_num: Optional[int],
    max_dogs: int = 10,
    generations: int = 3,
    delay: float = 2.0,
    deadline: Optional[float] = None,
    zooportal_ids: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Фаза 1 гибридного импорта.
    zooportal_ids — если передан, пропускает парсинг страницы-списка.
    """
    if zooportal_ids:
        dogs_list = [{'zooportal_id': zid} for zid in zooportal_ids]
    else:
        dogs_list = zooportal_parser.parse_search_page_with_browser(browser, page_num)
        if not dogs_list:
            return []

    results = []
    dogs_list = dogs_list[:max_dogs]

    for idx, dog_info in enumerate(dogs_list, 1):
        zoo_id = dog_info.get('zooportal_id')
        if not zoo_id or is_recursively_done(zoo_id, generations):
            continue
        if deadline and time.time() > deadline:
            logger.warning(f"  ⏱️ Дедлайн истёк на [{idx}] {zoo_id}")
            break

        zoo_raw = dog_info
        try:
            zoo_page = zooportal_parser.parse_dog_page_with_browser(browser, zoo_id, generations)
            if zoo_page:
                zoo_raw = zoo_page
        except Exception as e:
            logger.warning(f"  [{idx}] Zoo страница {zoo_id}: {e}")

        ba_uuid = None
        zoo_name = zoo_raw.get('registered_name') or zoo_raw.get('name') or ''
        if zoo_name:
            try:
                ba_uuid = search_breedarchive_by_name(zoo_name)
                status = f"✓ BA: {ba_uuid}" if ba_uuid else "— BA не найден"
                logger.info(f"  [{idx}/{len(dogs_list)}] {status} для '{zoo_name}'")
            except Exception as e:
                logger.warning(f"  [{idx}] BA поиск '{zoo_name}': {e}")

        results.append({'zooportal_id': zoo_id, 'zoo_raw': zoo_raw, 'ba_uuid': ba_uuid})

        if idx < len(dogs_list):
            time.sleep(delay)

    return results


def _schedule_photo_upload(dog, photo_bytes: bytes = None) -> None:
    """
    Загружает фото собаки на Яндекс.Диск.

    Если photo_bytes переданы (скачаны при парсинге Zoo через Playwright) —
    загружаем сразу синхронно, без повторного запроса к источнику.

    Если байт нет — ставим Celery-таску которая скачает сама
    (для BA и других источников где нет защиты hotlink).
    """
    if not dog or not dog.photo_url:
        return

    # Если байты уже есть — загружаем на ЯД прямо сейчас
    if photo_bytes:
        try:
            from ..services.photo_service import upload_photo_bytes_to_yadisk
            from ..models import Dog
            result = upload_photo_bytes_to_yadisk(dog.id, dog.photo_url, photo_bytes)
            if result["status"] == "uploaded":
                update = {"photo_yadisk_path": result["path"]}
                if result.get("yadisk_url"):
                    update["photo_yadisk_url"] = result["yadisk_url"]
                Dog.objects.using("dogs_db").filter(pk=dog.id).update(**update)
                logger.info(f"📷 Фото залито на ЯД синхронно dog_id={dog.id}")
            else:
                logger.warning(f"📷 Ошибка синхронной загрузки dog_id={dog.id}: {result}")
        except Exception as e:
            logger.warning(f"📷 Синхронная загрузка не удалась dog_id={dog.id}: {e}")
        return

    # Байт нет — ставим таску (BA и другие источники)
    try:
        from ..tasks.tasks_photos import photo_upload_one
        photo_upload_one.apply_async(
            kwargs={"dog_id": dog.id},
            countdown=2,
        )
        logger.debug(f"📷 Запланирована загрузка фото dog_id={dog.id}")
    except Exception as e:
        logger.warning(f"📷 Не удалось запланировать фото dog_id={dog.id}: {e}")