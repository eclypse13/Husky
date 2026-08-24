"""
Сервис интеграции Zoo/BA.
"""
import logging
import time
from typing import Dict, List, Optional, Set, Tuple

from ..models import Dog
from ..parsers.zooportal import BrowserManager, zooportal_parser
from ..parsers.breedarchive import (
    search_breedarchive_by_name,
    fetch_breedarchive_dog,
    collect_leaf_uuids as collect_ba_leaf_uuids,
    invalidate_dog_cache,
)
from ..utils.text import normalize_dog_name
from ..utils.parser_utils import parse_date, parse_color
from ..services.title_service import save_dog_titles
from ..services.dog_merger import (
    normalize_ba_data,
    build_zoo_dog_fields,
    merge_zoo_ba_data,
    build_zoo_patch,
    build_ba_patch,
    SOURCE_ZOO as _SOURCE_ZOO,
    SOURCE_BA as _SOURCE_BA,
)
from ..repositories import breeder_repository as breeder_repo
from ..repositories import owner_repository as owner_repo
from ..repositories import litter_repository as litter_repo
from ..repositories import dog_repository as dog_repo
from ..repositories import title_repository as title_repo

from .parse_cache import (
    is_recursively_done,
    mark_recursively_done,
    invalidate_parse_cache,
    get_parse_result,
    set_parse_result,
    is_ba_fully_parsed as _is_ba_fully_parsed,
    mark_ba_fully_parsed as _mark_ba_fully_parsed,
    invalidate_ba_fully_parsed as _invalidate_ba_fully_parsed,
)

logger = logging.getLogger(__name__)

# Задержка между запросами к BA при обходе граничных листьев дерева предков
_BA_LEAF_DELAY = 0.3  # секунды


# СОХРАНЕНИЕ BA-ДЕРЕВА ПРЕДКОВ
def process_ba_dog_tree(
        data: Dict,
        visited: Optional[Set[str]] = None,
        saved: Optional[Dict[str, Dog]] = None,
) -> Optional[Dog]:
    """Рекурсивно сохраняет собаку и всех её предков из BA-данных."""
    if visited is None:
        visited = set()
    if saved is None:
        saved = {}

    uuid = data.get('uuid')
    if not uuid:
        return None

    if uuid in saved:
        return saved[uuid]

    if uuid in visited:
        return dog_repo.get_by_uuid(uuid)

    visited.add(uuid)

    dam = process_ba_dog_tree(data['dam'], visited, saved) if data.get('dam') and data['dam'].get('uuid') else None
    sire = process_ba_dog_tree(data['sire'], visited, saved) if data.get('sire') and data['sire'].get('uuid') else None

    try:
        dog = _save_ba_dog(data, dam, sire)
        saved[uuid] = dog
        _save_ba_relations(dog, data)
        _schedule_photo_upload(dog)
        # Фото диспатчится только для корневой собаки в process_ba_dog_tree caller
        return dog
    except Exception as e:
        logger.error(f"  Ошибка сохранения предка uuid={uuid}: {e}", exc_info=True)
        existing = dog_repo.get_by_uuid(uuid)
        if existing:
            fk_update = {}
            if dam is not None:
                fk_update['dam_id'] = dam.pk
            if sire is not None:
                fk_update['sire_id'] = sire.pk
            if fk_update:
                try:
                    dog_repo.update_by_pk(existing.pk, fk_update)
                    for k, v in fk_update.items():
                        setattr(existing, k, v)
                    logger.info(f"  ♻️ FK восстановлен для uuid={uuid}: {fk_update}")
                except Exception as fk_err:
                    logger.error(f"  FK fallback uuid={uuid}: {fk_err}")
            saved[uuid] = existing
        return existing


# Загружает и сохраняет полное дерево предков собаки из BA
def process_ba_full_pedigree(
        uuid: str,
        api_dispatched: Optional[Set[str]] = None,
        depth: int = 0,
        max_depth: int = 1024,
        _completed: Optional[Set[str]] = None,
) -> Optional[Dog]:
    if api_dispatched is None:
        api_dispatched = set()
    if _completed is None:
        _completed = set()  # uuid'ы, чьё поддерево в этом прогоне собрано полностью

    indent = "  " * depth
    is_root = (depth == 0)

    if uuid in api_dispatched:
        return dog_repo.get_by_uuid(uuid)

    if not is_root and _is_ba_fully_parsed(uuid):
        existing = dog_repo.get_by_uuid(uuid)
        if existing:
            api_dispatched.add(uuid)
            _completed.add(uuid)
            logger.debug(f"{indent}⚡ Redis HIT: {existing.registered_name} (uuid={uuid})")
            return existing
        _invalidate_ba_fully_parsed(uuid)

    if depth > max_depth:
        logger.warning(f"{indent}⚠️ max_depth={max_depth} uuid={uuid}")
        return dog_repo.get_by_uuid(uuid)  # глубже не идём → поддерево неполное

    logger.info(f"{indent}🔍 BA full pedigree [depth={depth}]: uuid={uuid}")

    data = fetch_breedarchive_dog(uuid)
    if not data:
        logger.error(f"{indent}❌ Нет данных для uuid={uuid}")
        # Не корень: не помечаем fully и не кладём в api_dispatched →
        # ветка незавершённая, будущий прогон попробует снова. Корень → None (retry в таске).
        return None if is_root else dog_repo.get_by_uuid(uuid)

    api_dispatched.add(uuid)  # обработан в этом прогоне — только после успешного fetch

    try:
        dog = process_ba_dog_tree(data, visited=None, saved=None)
    except Exception as e:
        logger.error(f"{indent}❌ save uuid={uuid}: {e}", exc_info=True)
        dog = None
    if not dog:
        # узел не сохранился, но обрывать ветку нельзя — предки достижимы
        logger.warning(f"{indent}⚠️ узел не сохранён, продолжаю обход предков uuid={uuid}")
    leaves: Set[str] = set()
    collect_ba_leaf_uuids(data, leaves)
    leaves.discard(uuid)

    logger.info(f"{indent}  Граничных: {len(leaves)}, api_dispatched: {len(api_dispatched)}")

    complete = True
    for leaf_uuid in leaves:
        if leaf_uuid in _completed or _is_ba_fully_parsed(leaf_uuid):
            continue  # точно готов
        if leaf_uuid in api_dispatched:
            complete = False  # пытались, но не довели → неполное
            continue
        time.sleep(_BA_LEAF_DELAY)
        process_ba_full_pedigree(
            uuid=leaf_uuid,
            api_dispatched=api_dispatched,
            depth=depth + 1,
            max_depth=max_depth,
            _completed=_completed,
        )
        if leaf_uuid not in _completed:
            complete = False  # ветка не завершилась

    if complete:
        _completed.add(uuid)
        if not is_root:
            _mark_ba_fully_parsed(uuid)

    tail = "завершено" if complete else "ЧАСТИЧНО (достроится в след. прогоне)"
    logger.info(f"{indent}✅ BA full pedigree [depth={depth}]: {tail} uuid={uuid}")
    return dog


# Диспатчит import_hybrid_full_dog_task для каждого Zoo-предка
def _dispatch_ancestor_enrichment(
        zoo_raw: Dict, root_zoo_id: str, enrich_ancestors: bool = False
) -> None:
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
                'generations': 3,
                'force_update': False,
                '_enrich_ancestors': enrich_ancestors,
            },
            countdown=30 * (dispatched + 1),
        )
        dispatched += 1

    if dispatched:
        logger.info(
            f"  📬 Диспатч Zoo-патча для {dispatched} предков "
            f"(root zoo_id={root_zoo_id})"
        )


# Парсинг страницы Zoo-собаки
def _parse_zoo_page_with_retry(browser, zoo_id: str, generations: int) -> Dict:
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

    return zoo_raw


# Гибридный импорт одной собаки (Zoo данные и BA полное дерево предков)
def process_hybrid_full_pedigree(
        zooportal_id: str,
        generations: int = 5,
        force_update: bool = False,
        _enrich_ancestors: bool = True,
) -> Optional[Dog]:
    logger.info(f"🔀 Hybrid full pedigree: zooportal_id={zooportal_id}")

    zoo_raw: Dict = {}
    with BrowserManager() as browser:
        zoo_raw = _parse_zoo_page_with_retry(browser, zooportal_id, generations)

    if not zoo_raw:
        logger.warning(f"  Zoo не вернул данные для {zooportal_id}")
        return dog_repo.get_by_zooportal_id(zooportal_id)

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

    if _enrich_ancestors and dog:
        _dispatch_ancestor_enrichment(zoo_raw, zooportal_id)

    return dog


# Гибридный импорт одной страницы (Zoo данные и BA полное дерево предков для каждой собаки)
def process_hybrid_full_pedigree_page(
        page_num: Optional[int] = None,
        max_dogs: int = 11,
        generations: int = 5,
        delay: float = 2.0,
        deadline: Optional[float] = None,
        zooportal_ids: Optional[List[str]] = None,
) -> Dict:
    start_time = time.time()
    imported, failed, dog_ids = 0, 0, []

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
                zoo_raw = _parse_zoo_page_with_retry(browser, zoo_id, generations)

                collected.append({'zoo_id': zoo_id, 'zoo_raw': zoo_raw})
            except Exception as e:
                failed += 1
                logger.error(f"  [{idx}] Zoo парсинг {zoo_id}: {e}")

            if idx < len(ids_to_process):
                time.sleep(delay)

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


# Атомарный слив Zoo-стаб с BA-записью
def _merge_zoo_twin(dog: Dog, zoo_hash: str, defaults: Dict) -> None:
    try:
        merged = dog_repo.merge_zoo_stub_into_ba(dog.pk, zoo_hash, defaults)
        if merged:
            for k, v in merged.items():
                setattr(dog, k, v)
            logger.info(f"  🔗 Слияние Zoo→BA: '{dog.registered_name}' — перенесено {list(merged.keys())}")
    except Exception as e:
        logger.warning(f"  ⚠️ Слияние Zoo→BA пропущено: {e}")

def _save_ba_dog(data: Dict, dam: Optional[Dog], sire: Optional[Dog]) -> Dog:
    uuid = data.get('uuid')
    if not uuid:
        raise ValueError("UUID обязателен")

    from ..config.breedarchive import BASE_URL as _ba_base_url

    defaults = build_ba_patch(data, _ba_base_url)
    dog, created = _find_or_create_ba_dog(uuid, defaults)

    fk_update: Dict = {}
    if dam is not None and dam.pk:
        fk_update['dam_id'] = dam.pk
    if sire is not None and sire.pk:
        fk_update['sire_id'] = sire.pk
    if fk_update:
        dog_repo.update_by_pk(dog.pk, fk_update)
        for k, v in fk_update.items():
            setattr(dog, k, v)

    logger.info(f"  {'✅ Создана' if created else '🔄 Обновлена'}: {dog.registered_name} (uuid={uuid})")
    return dog

# Сохраняет заводчиков, владельцев, титулы, сиблингов и помёты из BA
def _save_ba_relations(dog: Dog, data: Dict) -> None:
    # Заводчики
    ba_breeders = data.get('breeders', [])
    if not ba_breeders and data.get('kennel'):
        kennel_name = (data['kennel'] or '').strip()
        if kennel_name:
            ba_breeders = [{'name': kennel_name, 'kennel': kennel_name, 'is_breeder': True}]

    for b in ba_breeders:
        if not isinstance(b, dict) or not b.get('name'):
            continue
        try:
            breeder, _ = breeder_repo.upsert_breeder(
                name=b['name'],
                uuid=(b.get('uuid') or '').strip() or None,
                kennel=(b.get('kennel') or b.get('name') or '').strip() or None,
                is_breeder=b.get('is_breeder', True),
            )
            breeder_repo.link_to_dog(dog, breeder)
        except Exception as e:
            logger.error(f"  Заводчик '{b.get('name')}': {e}")

    # Владельцы
    for o in data.get('owners', []):
        if not isinstance(o, dict) or not o.get('name'):
            continue
        try:
            owner, _ = owner_repo.upsert_owner(
                name=o['name'],
                uuid=(o.get('uuid') or '').strip() or None,
                is_main_owner=o.get('is_main_owner', False),
            )
            owner_repo.link_to_dog(dog, owner)
        except Exception as e:
            logger.error(f"  Владелец '{o.get('name')}': {e}")

    # Титулы
    _prefix = data.get('prefix_titles') or data.get('prefixTitles') or ''
    _suffix = data.get('suffix_titles') or data.get('suffixTitles') or ''
    if _prefix or _suffix:
        try:
            save_dog_titles(dog, _prefix or None, _suffix or None, _SOURCE_BA)
        except Exception as e:
            logger.error(f"  Титулы для {dog.registered_name} (uuid={data.get('uuid')}): {e}")

    # BA может вернуть структурированный массив titles
    for t in data.get('titles', []):
        if not isinstance(t, dict) or not t.get('short_name'):
            continue
        try:
            country = (t.get('country') or '').strip().lower() or None
            short_name = (t.get('short_name') or '').strip().lower()
            if not short_name:
                continue
            title_repo.upsert_title(
                dog=dog,
                short_name=short_name,
                country=country,
                fields={
                    'long_name': t.get('long_name') or '',
                    'is_prefix': t.get('is_prefix', False),
                    'has_winner_year': t.get('has_winner_year', False),
                    'winner_year': t.get('winner_year'),
                },
            )
        except Exception as e:
            logger.error(f"  Титул '{t.get('short_name')}': {e}")

    # Сиблинги
    for sib in data.get('siblings', []):
        if not isinstance(sib, dict) or not sib.get('uuid'):
            continue
        try:
            litter_repo.upsert_sibling(
                dog=dog,
                sibling_uuid=sib['uuid'],
                name=sib.get('registered_name') or sib.get('registeredName') or '',
                sex=sib.get('sex', 0),
            )
        except Exception as e:
            logger.error(f"  Сиблинг '{sib.get('uuid')}': {e}")

    # Помёты (BA не возвращает по практическому опыту)
    # for lit in data.get('litters', []):
    #     if not isinstance(lit, dict):
    #         continue
    #     try:
    #         dam_uuid = lit.get('dam', {}).get('uuid')
    #         sire_uuid = lit.get('sire', {}).get('uuid')
    #         dam = dog_repo.get_by_uuid(dam_uuid) if dam_uuid else None
    #         sire = dog_repo.get_by_uuid(sire_uuid) if sire_uuid else None
    #         litter_repo.upsert_litter(
    #             dam=dam, sire=sire,
    #             date_of_birth=parse_date(lit.get('date_of_birth')),
    #             fields={
    #                 'litter_male_count': lit.get('litter_male_count'),
    #                 'litter_female_count': lit.get('litter_female_count'),
    #                 'litter_undef_count': lit.get('litter_undef_count'),
    #                 'dam': dam,
    #                 'sire': sire,
    #             },
    #         )
    #     except Exception as e:
    #         logger.error(f"  Помёт: {e}")


# ПАРСИНГ ОДНОЙ СОБАКИ (Zoo + BA поиск)
def parse_dog_data(browser: BrowserManager, zooportal_id: str, generations: int = 3) -> Dict:
    """Парсит одну собаку: Zoo страница + BA базовые данные → merged_data + pedigree."""
    logger.info(f"🔍 parse_dog_data: zooportal_id={zooportal_id}")

    cached = get_parse_result(zooportal_id, generations)
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
        'merged_data': _merge_dog_data(dog_raw, breedarchive_data),
        'pedigree': pedigree,
    }
    set_parse_result(zooportal_id, generations, result)
    return result


# Рекурсивно парсит собаку и всех её предков у которых есть zooportal_id
def parse_dog_data_recursive(
        browser: BrowserManager,
        zooportal_id: str,
        generations: int = 3,
        visited: Optional[Set[str]] = None,
        deadline: Optional[float] = None,
        _depth: int = 0,
) -> List[Dict]:
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


# СЛИЯНИЕ Zoo + BA (совместимость)
def _merge_dog_data(zooportal_data: Dict, breedarchive_data: Optional[Dict] = None) -> Dict:
    return merge_zoo_ba_data(zooportal_data, breedarchive_data)


# СОХРАНЕНИЕ В БД (Zoo-путь, сохр собаку, заводчика, владельца, титулы и связи родословной)
def save_dog_with_ancestors(parsed: Dict) -> Dog:
    merged_data = parsed['merged_data']
    pedigree = parsed['pedigree']
    zooportal_id = parsed['zooportal_id']

    dog = _save_dog(merged_data)
    _schedule_photo_upload(dog, photo_bytes=merged_data.get('photo_bytes'))
    _save_dog_relations(dog, merged_data)

    if pedigree.get('ancestors'):
        logger.info(f"👨‍👩‍👧‍👦 Обработка {len(pedigree['ancestors'])} предков...")
        dog_map = _save_ancestors(pedigree)
        _apply_relationships(pedigree, dog_map, zooportal_id, dog)

    return dog


# Создаёт или обновляет запись Dog из Zoo merged_data
def _save_dog(dog_data: Dict) -> Dog:
    zooportal_id = dog_data.get('zooportal_id')
    if not zooportal_id:
        raise ValueError("zooportal_id обязателен")

    update_fields = {k: v for k, v in build_zoo_dog_fields(dog_data).items() if v is not None}

    update_fields['zooportal_id'] = zooportal_id

    existing = dog_repo.get_by_zooportal_id(zooportal_id)

    if existing:
        fields_to_update = {
            k: v for k, v in update_fields.items()
            if k not in ('uuid', 'source') or not getattr(existing, k, None)
        }
        dog_repo.update_by_pk(existing.pk, fields_to_update)
        for k, v in fields_to_update.items():
            setattr(existing, k, v)
        logger.info(f"  🔄 Обновлена: {existing.registered_name}")
        return existing

    # Фаззи-дедуп перед созданием (заменяет старую проверку по zoo_hash)
    from ..services.duplicate_service import find_duplicate, flag_possible_duplicate

    dup = find_duplicate({
        "registered_name": update_fields.get('registered_name', ''),
        "sex": update_fields.get('sex', 0),
        "year_of_birth": update_fields.get('year_of_birth'),
        "sire_name": update_fields.get('sire_name'),
        "dam_name": update_fields.get('dam_name'),
    })

    if dup and dup["verdict"] == "merge":
        existing = dup["dog"]
        logger.info(f"  🔗 Слияние с dog_id={existing.id} '{existing.registered_name}' "
                    f"(score={dup['score']:.2f}, {dup['reason']})")
        # Применяем Zoo-поля поверх существующих (только пустые)
        merge_patch = {
            k: v for k, v in update_fields.items()
            if not getattr(existing, k, None)
        }
        merge_patch['zooportal_id'] = str(zooportal_id)
        dog_repo.update_by_pk(existing.pk, merge_patch)
        for k, v in merge_patch.items():
            setattr(existing, k, v)
        return existing

    try:
        dog = dog_repo.create_dog(update_fields)
        logger.info(f"  ✅ Создана: {dog.registered_name}")
    except Exception as e:
        logger.warning(f"  ⚠️ create упал ({e}), пробуем get")
        dog = dog_repo.get_by_zooportal_id(zooportal_id)
        if dog:
            return dog
        raise

    if dup is not None and dup["verdict"] == "flag":
        flag_possible_duplicate(dog.pk, dup["dog"].id, dup["score"], dup["reason"])

    return dog


# Сохраняет заводчиков, владельцев и титулы из merged_data (единый поинт входа для Zoo-пути)
def _save_dog_relations(dog: Dog, dog_data: Dict) -> None:
    _save_breeder_zooportal(dog, dog_data)
    _save_breeders_ba(dog, dog_data)
    _save_owner_for_dog(dog, dog_data)
    _save_titles_for_dog(dog, dog_data)


def _save_breeder_zooportal(dog: Dog, dog_data: Dict) -> None:
    name = dog_data.get('breeder_name')
    if not name:
        return
    try:
        breeder, _ = breeder_repo.upsert_breeder(
            name=name,
            kennel=dog_data.get('breeder_kennel'),
            is_breeder=True,
            breeder_url=dog_data.get('breeder_url'),
            kennel_url=dog_data.get('breeder_kennel_url'),
        )
        breeder_repo.link_to_dog(dog, breeder)
    except Exception as e:
        logger.error(f"  Заводчик Zoo '{name}': {e}")


def _save_breeders_ba(dog: Dog, dog_data: Dict) -> None:
    ba_breeders = dog_data.get('breeders') or []
    if not ba_breeders and dog_data.get('kennel'):
        kennel_name = (dog_data['kennel'] or '').strip()
        if kennel_name:
            ba_breeders = [{'name': kennel_name, 'kennel': kennel_name, 'is_breeder': True}]

    for raw in ba_breeders:
        if not isinstance(raw, dict) or not raw.get('name'):
            continue
        try:
            breeder, _ = breeder_repo.upsert_breeder(
                name=raw['name'],
                uuid=(raw.get('uuid') or '').strip() or None,
                kennel=(raw.get('kennel') or raw.get('name') or '').strip() or None,
                is_breeder=raw.get('is_breeder', True),
            )
            breeder_repo.link_to_dog(dog, breeder)
        except Exception as e:
            logger.error(f"  Заводчик BA '{raw.get('name')}': {e}")


def _save_owner_for_dog(dog: Dog, dog_data: Dict) -> None:
    owner_name = dog_data.get('owner_name')
    owner_uuid = None
    ba_owners = dog_data.get('owners') or []
    if not owner_name and ba_owners and isinstance(ba_owners[0], dict):
        owner_name = ba_owners[0].get('name')
        owner_uuid = ba_owners[0].get('uuid')
    if not owner_name:
        return
    try:
        owner, _ = owner_repo.upsert_owner(
            name=owner_name,
            uuid=owner_uuid,
            is_main_owner=True,
            kennel=dog_data.get('owner_kennel'),
            owner_url=dog_data.get('owner_url'),
            kennel_url=dog_data.get('owner_kennel_url'),
        )
        owner_repo.link_to_dog(dog, owner)
    except Exception as e:
        logger.error(f"  Владелец '{owner_name}': {e}")


def _save_titles_for_dog(dog: Dog, dog_data: Dict) -> None:
    source = 'breedarchive' if dog_data.get('uuid') else 'zooportal'  # title_service keys
    save_dog_titles(
        dog,
        dog_data.get('prefix_titles') or dog_data.get('titles_text'),
        dog_data.get('suffix_titles'),
        source,
    )


# Сохраняет предков из Zoo pedigree
def _save_ancestors(pedigree: Dict) -> Dict[str, Dog]:
    ancestors = pedigree.get('ancestors', {})
    if not ancestors:
        return {}

    # Шаг 1: собираем все zoo_ids и вычисляем zoo_hashes
    ancestor_meta: Dict[str, Dict] = {}  # node_key → {name, sex, zoo_id, zoo_hash}
    all_zoo_ids: Set[str] = set()
    all_zoo_hashes: Set[str] = set()

    for node_key, ancestor in ancestors.items():
        name = ancestor.get('name')
        sex = ancestor.get('sex', 0)
        zoo_id = ancestor.get('zooportal_id')
        if not name:
            continue
        zoo_hash = Dog.compute_zoo_hash(name, sex)
        ancestor_meta[node_key] = {
            'name': name, 'sex': sex,
            'zoo_id': zoo_id, 'zoo_hash': zoo_hash,
        }
        if zoo_id:
            all_zoo_ids.add(zoo_id)
        if zoo_hash:
            all_zoo_hashes.add(zoo_hash)

    # Шаг 2: батч-загрузка существующих — 2 SQL на все предки
    by_zoo_id = dog_repo.get_by_zooportal_ids_bulk(all_zoo_ids)
    by_zoo_hash = dog_repo.get_by_zoo_hashes_bulk(all_zoo_hashes)

    # Шаг 3: сопоставляем или создаём стабы
    dog_map: Dict[str, Dog] = {}

    for node_key, meta in ancestor_meta.items():
        name = meta['name']
        sex = meta['sex']
        zoo_id = meta['zoo_id']
        zoo_hash = meta['zoo_hash']
        dog: Optional[Dog] = None

        try:
            # Lookup 1: по zooportal_id (точный)
            if zoo_id:
                dog = by_zoo_id.get(zoo_id)
                if dog:
                    dog_map[node_key] = dog
                    continue

            # Lookup 2: по zoo_hash (нечёткий — Zoo-стаб без zooportal_id)
            if zoo_hash:
                dog = by_zoo_hash.get(zoo_hash)
                if dog:
                    if zoo_id and not dog.zooportal_id:
                        dog_repo.update_by_pk(dog.pk, {'zooportal_id': zoo_id})
                        dog.zooportal_id = zoo_id
                        by_zoo_id[zoo_id] = dog  # кешируем для последующих итераций
                    dog_map[node_key] = dog
                    continue

            # Создаём стаб, собаки нет ни по zoo_id ни по hash
            if zoo_id:
                dog = dog_repo.stub_or_get_by_zooportal_id(zoo_id, name, sex)
                by_zoo_id[zoo_id] = dog
            else:
                dog = dog_repo.stub_or_get_by_name(name, sex)
            if zoo_hash:
                by_zoo_hash[zoo_hash] = dog

            dog_map[node_key] = dog

        except Exception as e:
            logger.error(f"  Предок '{name}' (zoo_id={zoo_id}): {e}")

    logger.info(f"  Предков: {len(dog_map)}")
    return dog_map


# Устанавливает связи sire/dam для всех собак в родословной (zoo-собака)
def _apply_relationships(
        pedigree: Dict, dog_map: Dict[str, Dog], root_zooportal_id: str, root_dog: Dog,
) -> None:
    full_map = {**dog_map, f"{root_zooportal_id}:": root_dog}

    for base_key, base_info in pedigree.get('base_dogs', {}).items():
        if base_key not in full_map:
            bzid = base_info.get('zooportal_id')
            if bzid:
                dog_obj = dog_repo.get_by_zooportal_id(bzid)
                if dog_obj:
                    full_map[base_key] = dog_obj

    for rel in pedigree.get('relationships', []):
        child = full_map.get(rel.get('child_key'))
        parent = full_map.get(rel.get('parent_key'))
        if not child or not parent or not child.id or not parent.id:
            continue
        if rel['relation'] == 'sire' and child.sire_id != parent.id:
            dog_repo.update_by_pk(child.id, {'sire_id': parent.id})
            child.sire_id = parent.id
        elif rel['relation'] == 'dam' and child.dam_id != parent.id:
            dog_repo.update_by_pk(child.id, {'dam_id': parent.id})
            child.dam_id = parent.id


# ОБЁРТКА ДЛЯ ОДИНОЧНОГО ИМПОРТА
def process_dog_from_zooportal(
        zooportal_id: str, generations: int = 3, deadline: Optional[float] = None,
) -> Dog:
    visited: Set[str] = set()

    with BrowserManager() as browser:
        all_parsed = parse_dog_data_recursive(
            browser=browser, zooportal_id=zooportal_id,
            generations=generations, visited=visited, deadline=deadline,
        )

    if not all_parsed:
        existing = dog_repo.get_by_zooportal_id(zooportal_id)
        if existing:
            logger.info(f"♻️ {zooportal_id} уже в БД: {existing.registered_name}")
            _ensure_photo(existing)
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
                root_dog = dog_repo.get_by_zooportal_id(pid)

    if not root_dog:
        root_dog = dog_repo.get_by_zooportal_id(zooportal_id)
        if not root_dog:
            raise ValueError(f"Не удалось сохранить основную собаку {zooportal_id}")

    logger.info(f"🎉 Импорт завершён: {root_dog.registered_name} + {len(all_parsed) - 1} предков")
    _ensure_photo(root_dog)
    return root_dog


# ГИБРИДНЫЙ ИМПОРТ: Zoo список → BA дерево предков
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
    """
    Применяет Zoo-данные поверх BA-записи.
    Вычисление обновлений — в dog_merger.build_zoo_patch (pure function).
    """
    update = build_zoo_patch(dog, zoo_raw, zoo_id)
    if update:
        dog_repo.update_by_pk(dog.pk, update)
        for k, v in update.items():
            setattr(dog, k, v)

    if not breeder_repo.dog_has_breeders(dog):
        _save_breeder_zooportal(dog, zoo_raw)

    if not owner_repo.dog_has_owners(dog):
        _save_owner_for_dog(dog, zoo_raw)

    prefix_for_titles = zoo_raw.get('prefix_titles') or zoo_raw.get('titles_text')
    suffix_for_titles = zoo_raw.get('suffix_titles')
    if prefix_for_titles or suffix_for_titles:
        save_dog_titles(dog, prefix_for_titles, suffix_for_titles, 'zooportal')  # title_service key


# Сохраняет собаку только из Zoo-данных когда BA не нашёл совпадений
def _save_zoo_fallback(zoo_id: str, zoo_raw: Dict) -> Optional[Dog]:
    from ..services.duplicate_service import find_duplicate, flag_possible_duplicate

    pedigree = zoo_raw.get('pedigree')
    if pedigree and pedigree.get('ancestors'):
        return save_dog_with_ancestors({
            'zooportal_id': zoo_id,
            'merged_data': _merge_dog_data(zoo_raw, None),
            'pedigree': pedigree,
        })

    name = zoo_raw.get('registered_name') or zoo_raw.get('name') or ''
    norm_name = normalize_dog_name(name) if name else None

    dup = None
    if norm_name:
        sire_name, dam_name = _zoo_parent_names(zoo_raw)
        dup = find_duplicate({
            "registered_name": norm_name,
            "sex": zoo_raw.get('sex', 0),
            "year_of_birth": zoo_raw.get('year_of_birth'),
            "sire_name": sire_name,
            "dam_name": dam_name,
        })
        if dup and dup["verdict"] == "merge":
            existing = dup["dog"]
            logger.info(f"  🔗 Слияние с dog_id={existing.id} '{existing.registered_name}' "
                        f"(score={dup['score']:.2f}, {dup['reason']})")
            dog_repo.set_zooportal_id(existing.pk, zoo_id)
            return existing

    dog = dog_repo.upsert_zoo_fallback(zoo_id, {
        'registered_name': norm_name,
        'sex': zoo_raw.get('sex', 0),
        'color': parse_color(zoo_raw.get('color') or ''),
        'photo_url': zoo_raw.get('photo_url'),
        'land_of_birth': zoo_raw.get('land_of_birth'),
        'source': _SOURCE_ZOO,
    })

    if dup is not None and dup["verdict"] == "flag":
        flag_possible_duplicate(dog.pk, dup["dog"].id, dup["score"], dup["reason"])

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

        try:
            zoo_raw = _parse_zoo_page_with_retry(browser, zoo_id, generations) or dog_info
        except Exception as e:
            zoo_raw = dog_info
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


# Дедупликация списка распарсенных собак по zooportal_id
def deduplicate_parsed(parsed_list: list) -> list:
    seen: set = set()
    result = []
    for p in parsed_list:
        zid = p.get('zooportal_id')
        if zid and zid not in seen:
            seen.add(zid)
            result.append(p)
    return result


# Загружает фото собаки на Яндекс.Диск
def _schedule_photo_upload(dog, photo_bytes: bytes = None) -> None:
    if not dog or not dog.photo_url:
        return

    if photo_bytes:
        try:
            from ..services.photo_service import upload_photo_bytes_to_yadisk
            result = upload_photo_bytes_to_yadisk(
                dog.id, dog.photo_url, photo_bytes, getattr(dog, "photo_hash", None)
            )
            if result["status"] == "skipped_placeholder":
                if result.get("hash"):
                    dog_repo.update_by_pk(dog.id, {"photo_hash": result["hash"]})
                logger.info(f"📷 dog {dog.id}: дефолтное фото — не грузим на ЯД")
            elif result["status"] in ("uploaded", "skipped"):
                update = {}
                if result.get("path"): update["photo_yadisk_path"] = result["path"]
                if result.get("yadisk_url"): update["photo_yadisk_url"] = result["yadisk_url"]
                if result.get("hash"): update["photo_hash"] = result["hash"]
                if update:
                    dog_repo.update_by_pk(dog.id, update)
                logger.info(f"📷 dog {dog.id}: {result['status']} синхронно")
            else:
                logger.warning(f"📷 dog {dog.id}: {result}")
        except Exception as e:
            logger.warning(f"📷 Синхронная загрузка dog_id={dog.id}: {e}")
        return

    try:
        # Lazy import:
        from ..tasks.tasks_photos import photo_upload_one
        photo_upload_one.apply_async(kwargs={"dog_id": dog.id}, countdown=2)
        logger.debug(f"📷 Запланирована загрузка фото dog_id={dog.id}")
    except Exception as e:
        logger.warning(f"📷 Не удалось запланировать фото dog_id={dog.id}: {e}")


def _find_or_create_ba_dog(uuid: str, fields: Dict) -> Tuple[Dog, bool]:
    from django.db import transaction
    from ..utils.dog_matcher import classify_duplicate

    registered_name = fields.get('registered_name', '')
    sex = fields.get('sex', 0)

    with transaction.atomic(using='dogs_db'):
        target = dog_repo.get_dog_for_update_by_uuid(uuid)

        if not target and sex:
            candidates = dog_repo.get_stub_candidates_for_update(
                sex=sex, year_of_birth=fields.get('year_of_birth'),
            )
            new_data = {
                'registered_name': registered_name, 'sex': sex,
                'year_of_birth': fields.get('year_of_birth'),
                'sire_name': fields.get('sire_name'), 'dam_name': fields.get('dam_name'),
            }
            best, best_score, best_reason = None, 0.0, ''
            for cand in candidates:
                cand_data = {
                    'registered_name': cand.registered_name, 'sex': cand.sex,
                    'year_of_birth': cand.year_of_birth,
                    'sire_name': cand.sire_name, 'dam_name': cand.dam_name,
                }
                verdict, score, reason = classify_duplicate(new_data, cand_data)
                if verdict == 'merge' and score > best_score:
                    best, best_score, best_reason = cand, score, reason
            if best:
                target = best
                logger.info(
                    f"  🔗 BA fuzzy-match '{registered_name}' → dog_id={target.pk} "
                    f"({best_reason}, score={best_score:.2f})"
                )

        update_fields = dict(fields)
        update_fields['uuid'] = uuid

        if target:
            dog_repo.update_by_pk(target.pk, update_fields)
            target.refresh_from_db(using='dogs_db')
            return target, False

        dog = dog_repo.create_dog(update_fields)
        return dog, True

# Достаёт (sire_name, dam_name) из распарсенной родословной Zoo
def _zoo_parent_names(zoo_raw: dict) -> tuple:
    parents = (zoo_raw.get('pedigree') or {}).get('parents') or {}
    sire = (parents.get('sire') or {}).get('name')
    dam = (parents.get('dam') or {}).get('name')
    return sire, dam

def _ensure_photo(dog) -> None:
    # дозагрузка фото для собаки, которая вернулась без парсинга (уже была в БД)
    if dog and dog.photo_url and not dog.photo_yadisk_path:
        from ..tasks.tasks_photos import photo_upload_one
        photo_upload_one.apply_async(kwargs={"dog_id": dog.id}, countdown=2)


# Собаки (для breedarhive) из БД (по DB id, не uuid)
def get_dogs_for_ba_refresh(id_from: int, id_to: int = None, limit: int = 1000) -> List[Dict]:
    return dog_repo.get_dogs_with_uuid(id_from=id_from, id_to=id_to, limit=limit)