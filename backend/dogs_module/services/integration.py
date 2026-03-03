# dogs_module/services/integration.py
"""Сервис интеграции: парсинг + слияние Zoo/BA данных + сохранение в БД."""

import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from django.core.cache import caches
from django.utils import timezone

from ..models import (
    Dog, Breeder, Owner, Title, Litter,
    Dogbreederlink, Dogownerlink, Dogsiblinglink,
)
from ..parsers.zooportal import BrowserManager, zooportal_parser
from ..parsers.breedarchive import (
    search_breedarchive_by_name,
    fetch_breedarchive_dog,
)
from ..utils.text import parse_sex, normalize_dog_name
from ..utils.parser_utils import parse_date, parse_color
from ..utils.dog_matcher import detect_dict_conflicts
from ..utils.titles import save_dog_titles

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# КЕШ
# ══════════════════════════════════════════════════════════════════════════════

_TTL_PARSE_RESULT   = 18 * 3600
_TTL_RECURSIVE_DONE = 18 * 24 * 3600


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


def _save_ba_dog(data: Dict, dam: Optional[Dog], sire: Optional[Dog]) -> Dog:
    """Создаёт или обновляет Dog из BA-данных с готовыми ссылками на родителей."""
    uuid = data.get('uuid')
    if not uuid:
        raise ValueError("UUID обязателен")

    reg_num = data.get('registration_number')
    if reg_num:
        reg_num = re.sub(r'\s+', '', str(reg_num))

    # Строим photo_url с правильным путём /resource/
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
        'registered_name':     data.get('registered_name'),
        'call_name':           data.get('call_name'),
        'link_name':           data.get('link_name'),
        'sex':                 data.get('sex', 0),
        'date_of_birth':       dob,
        'date_of_death':       dod,
        'year_of_birth':       _to_int(data.get('year_of_birth')),
        'year_of_death':       _to_int(data.get('year_of_death')),
        'color':               parse_color(data.get('color') or '') or None,
        'color_marking':       data.get('color_marking') or None,
        'variety':             data.get('variety') or None,
        'land_of_birth':       data.get('land_of_birth') or None,
        'land_of_birth_code':  data.get('land_of_birth_code') or None,
        'land_of_standing':    data.get('land_of_standing') or None,
        'registration_number': reg_num or None,
        'registration_status': data.get('registration_status'),
        'prefix_titles':       data.get('prefix_titles') or None,
        'suffix_titles':       data.get('suffix_titles') or None,
        'photo_url':           photo_url or None,
        'coi':                 coi,
        'neutered':            data.get('neutered', False),
        'incomplete_pedigree': data.get('incomplete_pedigree', False),
        'source':              'breedarchive.com',
        'dam':                 dam,
        'sire':                sire,
        # Денормализованные uuid родителей (для обратной совместимости)
        'dam_uuid':            data.get('dam_uuid') or (data.get('dam', {}) or {}).get('uuid') or None,
        'sire_uuid':           data.get('sire_uuid') or (data.get('sire', {}) or {}).get('uuid') or None,
        'health_info_general': data.get('health_info_general'),
        'health_info_genetic': data.get('health_info_genetic'),
        'has_conflicts':       data.get('has_conflicts', False),
        'conflicts':           data.get('conflicts'),
    }
    # Фильтруем None И пустые строки — не перезаписываем существующие данные пустотой
    defaults = {k: v for k, v in defaults.items() if v is not None and v != ''}

    try:
        dog, created = Dog.objects.using('dogs_db').update_or_create(uuid=uuid, defaults=defaults)
    except Dog.MultipleObjectsReturned:
        # uuid не уникален — берём первую запись, обновляем её
        dog = Dog.objects.using('dogs_db').filter(uuid=uuid).order_by('id').first()
        for k, v in defaults.items():
            setattr(dog, k, v)
        dog.save(using='dogs_db')
        created = False

    # Явно применяем dam_id/sire_id через queryset.update() — самый надёжный способ.
    # update_or_create иногда не сохраняет FK корректно при обновлении через Django ORM.
    fk_update: Dict = {}
    if dam is not None and dam.pk:
        fk_update['dam_id'] = dam.pk
    if sire is not None and sire.pk:
        fk_update['sire_id'] = sire.pk
    if fk_update:
        Dog.objects.using('dogs_db').filter(pk=dog.pk).update(**fk_update)
        # Синхронизируем атрибуты в памяти
        for k, v in fk_update.items():
            setattr(dog, k, v)
        logger.debug(f"  FK set for {dog.registered_name} (uuid={uuid}): {fk_update}")

    logger.info(f"  {'✅ Создана' if created else '🔄 Обновлена'}: {dog.registered_name} (uuid={uuid})")
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
                breeder, _ = Breeder.objects.using('dogs_db').get_or_create(
                    uuid=b_uuid,
                    defaults={
                        'name':       b['name'],
                        'kennel':     b_kennel,
                        'is_breeder': b.get('is_breeder', True),
                    },
                )
            else:
                breeder, _ = Breeder.objects.using('dogs_db').get_or_create(
                    name=b['name'],
                    defaults={
                        'kennel':     b_kennel,
                        'is_breeder': b.get('is_breeder', True),
                    },
                )
            # Обновляем kennel если раньше не был заполнен
            if not breeder.kennel and b_kennel:
                Breeder.objects.using('dogs_db').filter(pk=breeder.pk).update(kennel=b_kennel)
            Dogbreederlink.objects.using('dogs_db').get_or_create(dog=dog, breeder=breeder)
        except Exception as e:
            logger.error(f"  Заводчик '{b.get('name')}': {e}")

    for o in data.get('owners', []):
        if not isinstance(o, dict) or not o.get('name'):
            continue
        try:
            owner, _ = Owner.objects.using('dogs_db').get_or_create(
                name=o['name'],
                defaults={'is_main_owner': o.get('is_main_owner', False), 'uuid': o.get('uuid', '')},
            )
            Dogownerlink.objects.using('dogs_db').get_or_create(dog=dog, owner=owner)
        except Exception as e:
            logger.error(f"  Владелец '{o.get('name')}': {e}")

    # BA возвращает титулы как текстовые строки prefix_titles/suffix_titles,
    # а не массив titles. Парсим их через save_dog_titles из utils/titles.py.
    _prefix = data.get('prefix_titles') or ''
    _suffix = data.get('suffix_titles') or ''
    if _prefix or _suffix:
        try:
            save_dog_titles(dog, _prefix or None, _suffix or None, 'breedarchive')
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
                    'registered_name': sib.get('registered_name', ''),
                    'sex':             sib.get('sex', 0),
                    'source':          'breedarchive.com',
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
    """Собирает строку даты из year/month/day полей для parse_date."""
    y = _to_int(data.get(f'year_of_{kind}'))
    m = _to_int(data.get(f'month_of_{kind}'))
    d = _to_int(data.get(f'day_of_{kind}'))
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


def _save_dog(dog_data: Dict) -> Dog:
    """Создаёт или обновляет запись Dog из merged_data."""
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

    dog, created = Dog.objects.using('dogs_db').update_or_create(
        zooportal_id=zooportal_id, defaults=update_fields,
    )
    logger.info(f"  {'✅ Создана' if created else '🔄 Обновлена'}: {dog.registered_name}")
    return dog


def _save_breeder_zooportal(dog: Dog, dog_data: Dict) -> None:
    """Сохраняет заводчика из Zoo-данных."""
    name = dog_data.get('breeder_name')
    if not name:
        return
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
    """Сохраняет предков из pedigree как заглушки (get_or_create — не затираем полные данные)."""
    dog_map: Dict[str, Dog] = {}
    processed: Set[str] = set()

    for node_key, ancestor in pedigree['ancestors'].items():
        if node_key in processed:
            continue
        processed.add(node_key)
        name = ancestor.get('name')
        if not name:
            continue
        zoo_id = ancestor.get('zooportal_id')
        try:
            if zoo_id:
                dog, created = Dog.objects.using('dogs_db').get_or_create(
                    zooportal_id=zoo_id,
                    defaults={'registered_name': name, 'sex': ancestor.get('sex', 0)},
                )
            else:
                dog, created = Dog.objects.using('dogs_db').get_or_create(
                    registered_name=name,
                    defaults={'sex': ancestor.get('sex', 0)},
                )
            dog_map[node_key] = dog
        except Exception as e:
            logger.error(f"  Предок '{name}': {e}")

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

    dogs_by_id = {d.id: d for d in full_map.values() if d and d.id}
    updated: Set[int] = set()

    for rel in pedigree.get('relationships', []):
        child  = full_map.get(rel.get('child_key'))
        parent = full_map.get(rel.get('parent_key'))
        if not child or not parent or not child.id or not parent.id:
            continue
        if rel['relation'] == 'sire' and child.sire_id != parent.id:
            child.sire = parent
            updated.add(child.id)
        elif rel['relation'] == 'dam' and child.dam_id != parent.id:
            child.dam = parent
            updated.add(child.id)

    for dog_id in updated:
        dog_obj = dogs_by_id.get(dog_id)
        if dog_obj:
            try:
                dog_obj.save(using='dogs_db', update_fields=['sire', 'dam'])
            except Exception as e:
                logger.error(f"  Связи для id={dog_id}: {e}")

    if updated:
        logger.info(f"  Связи установлены: {len(updated)} собак")


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
# ГИБРИДНЫЙ ИМПОРТ: Zoo список → BA полное дерево предков
# ══════════════════════════════════════════════════════════════════════════════

def collect_hybrid_page_data(
    browser: BrowserManager,
    page_num: int,
    max_dogs: int = 10,
    generations: int = 3,
    delay: float = 2.0,
    deadline: Optional[float] = None,
) -> List[Dict]:
    """
    Фаза 1 гибридного импорта: Zoo список + Zoo страница + BA поиск по имени.
    Возвращает список {zooportal_id, zoo_raw, ba_uuid} без записи в БД.
    """
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
    zoo_name = zoo_raw.get('registered_name') or zoo_raw.get('name') or ''
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
            'registered_name': name.strip().upper() if name else None,
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