"""
Функции слияния и нормализации данных.
"""

import re
from datetime import datetime
from typing import Dict, Optional
from django.utils.timezone import now
from ..utils.text import parse_sex, normalize_dog_name
from ..utils.parser_utils import (
    parse_date, parse_color, parse_int, assemble_partial_date, build_BA_photo_url,
)
from ..utils.dog_matcher import detect_dict_conflicts

SOURCE_ZOO = 'zooportal.pro'
SOURCE_BA = 'breedarchive.com'


# BA: нормализация сырых данных
def normalize_ba_data(data: Dict, ba_base_url: str) -> Dict:
    reg_num = data.get('registration_number') or data.get('registrationNumber') or ''
    if reg_num:
        reg_num = re.sub(r'\s+', '', str(reg_num))

    photo_url = data.get('photo_url') or ''
    if not photo_url.startswith('http'):
        path = data.get('primary_photo_path') or data.get('primaryPhotoPath') or ''
        if path:
            photo_url = build_BA_photo_url(path)

    coi = data.get('coi')
    try:
        coi = float(coi) if coi is not None else None
    except (ValueError, TypeError):
        coi = None

    dam_raw = data.get('dam') or {}
    sire_raw = data.get('sire') or {}

    return {
        'registered_name': data.get('registered_name') or data.get('registeredName'),
        'call_name': data.get('call_name') or data.get('callName'),
        'link_name': data.get('link_name') or data.get('linkName'),
        'sex': data.get('sex', 0) or None,
        'date_of_birth': parse_date(data.get('date_of_birth') or assemble_partial_date(data, 'birth')),
        'date_of_death': parse_date(data.get('date_of_death') or assemble_partial_date(data, 'death')),
        'year_of_birth': parse_int(data.get('year_of_birth') or data.get('yearOfBirth'), default=None),
        'year_of_death': parse_int(data.get('yearOfDeath') or data.get('year_of_death'), default=None) or None,
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
        'neutered': data.get('neutered') if data.get('neutered') is not None else None,
        'incomplete_pedigree': data.get('incomplete_pedigree') or data.get('incompletePedigree', False),
        'source': SOURCE_BA,

        'dam_uuid': data.get('dam_uuid') or dam_raw.get('uuid') or None,
        'sire_uuid': data.get('sire_uuid') or sire_raw.get('uuid') or None,
        'dam_name': dam_raw.get('registeredName') or None,
        'dam_link_name': dam_raw.get('linkName') or None,
        'sire_name': sire_raw.get('registeredName') or None,
        'sire_link_name': sire_raw.get('linkName') or None,

        'health_info_general': data.get('health_info_general') or data.get('healthInfoGeneral'),
        'health_info_genetic': data.get('health_info_genetic') or data.get('healthInfoGenetic'),

        'has_conflicts': data.get('has_conflicts', False),
        'conflicts': data.get('conflicts'),

        'notes': data.get('private_note') or data.get('privateNote') or None,
        'modified_at': now(),
    }


# Zoo: маппинг полей
def build_zoo_dog_fields(dog_data: Dict) -> Dict:
    return {
        'registered_name': dog_data.get('registered_name'),
        'call_name': dog_data.get('call_name'),
        'link_name': dog_data.get('link_name'),
        'uuid': dog_data.get('uuid'),
        'zoo_hash': dog_data.get('zoo_hash'),
        'sex': dog_data.get('sex', 0),
        'date_of_birth': dog_data.get('date_of_birth'),
        'year_of_birth': dog_data.get('year_of_birth'),
        'month_of_birth': dog_data.get('month_of_birth'),
        'day_of_birth': dog_data.get('day_of_birth'),
        'land_of_birth': dog_data.get('land_of_birth') or dog_data.get('country'),
        'land_of_birth_code': dog_data.get('land_of_birth_code'),
        'land_of_standing': dog_data.get('land_of_standing'),
        'color': dog_data.get('color'),
        'color_marking': dog_data.get('color_marking'),
        'variety': dog_data.get('variety'),
        'registration_number': dog_data.get('registration_number'),
        'registration_status': dog_data.get('registration_status'),
        'brand_chip': dog_data.get('brand_chip'),
        'coi': dog_data.get('coi'),
        'incomplete_pedigree': dog_data.get('incomplete_pedigree'),
        'neutered': dog_data.get('neutered'),
        'photo_url': dog_data.get('photo_url'),
        'prefix_titles': dog_data.get('prefix_titles') or dog_data.get('titles_text'),
        'suffix_titles': dog_data.get('suffix_titles'),
        'sire_name': dog_data.get('sire_name'),
        'dam_name': dog_data.get('dam_name'),
        'kennel': dog_data.get('kennel') or dog_data.get('breeder_kennel'),
        'source': SOURCE_ZOO,
        'has_conflicts': dog_data.get('_has_conflicts') or None,
        'conflicts': dog_data.get('_conflicts') or None,
        'modified_at': now(),
    }


# Поля которые Zoo-источник заполняет первым
_ZP_FIELDS = (
    'call_name', 'sex', 'date_of_birth', 'year_of_birth',
    'color', 'land_of_birth', 'registration_number', 'brand_chip',
    'photo_url', 'titles_text', 'prefix_titles',
    'breeder_name', 'breeder_url', 'breeder_kennel', 'breeder_kennel_url',
    'owner_name', 'owner_url', 'owner_kennel', 'owner_kennel_url',
    'sire_name', 'dam_name',
)

# Поля которые BA может заполнить если Zoo пропустил
_BA_FILL_FIELDS = (
    'call_name', 'sex', 'date_of_birth', 'year_of_birth',
    'month_of_birth', 'day_of_birth', 'color', 'land_of_birth',
    'registration_number', 'brand_chip', 'photo_url', 'prefix_titles',
)

# Поля которые есть только в BA
_BA_EXCLUSIVE_FIELDS = (
    'uuid', 'link_name', 'color_marking', 'variety',
    'land_of_birth_code', 'land_of_standing', 'registration_status',
    'suffix_titles', 'coi', 'coi_updated_on', 'incomplete_pedigree',
    'neutered', 'kennel', 'breeders', 'owners',
)

# Поля для сравнения конфликтов между источниками
_CONFLICT_COMPARE_FIELDS = (
    'call_name', 'sex', 'date_of_birth', 'color',
    'land_of_birth', 'registration_number', 'brand_chip',
)


def merge_zoo_ba_data(
        zoo_data: Dict,
        ba_data: Optional[Dict] = None,
) -> Dict:
    merged: Dict = {
        'zooportal_id': zoo_data.get('zooportal_id'),
        'zoo_hash': zoo_data.get('zoo_hash'),
        'registered_name': zoo_data.get('registered_name'),
    }

    for key in _ZP_FIELDS:
        val = zoo_data.get(key)
        if val not in (None, ''):
            merged[key] = val

    if ba_data:
        for key in _BA_FILL_FIELDS:
            if not merged.get(key):
                val = ba_data.get(key)
                if val not in (None, ''):
                    merged[key] = val

        for key in _BA_EXCLUSIVE_FIELDS:
            val = ba_data.get(key)
            if val not in (None, ''):
                merged[key] = val

        has_conflicts, conflicts = detect_dict_conflicts(
            {k: zoo_data.get(k) for k in _CONFLICT_COMPARE_FIELDS},
            {k: ba_data.get(k) for k in _CONFLICT_COMPARE_FIELDS},
            SOURCE_ZOO, SOURCE_BA,
        )
        merged['_conflicts'] = conflicts if has_conflicts else {}
        merged['_has_conflicts'] = has_conflicts
    else:
        merged['_conflicts'] = {}
        merged['_has_conflicts'] = False

    # Финальная нормализация типов
    if 'date_of_birth' in merged and isinstance(merged['date_of_birth'], str):
        parsed = parse_date(merged['date_of_birth'])
        if parsed:
            merged['date_of_birth'] = parsed
    if 'sex' in merged and isinstance(merged['sex'], str):
        merged['sex'] = parse_sex(merged['sex'])
    if 'color' in merged:
        merged['color'] = parse_color(merged['color'])

    return merged


# Числовые поля с float-конвертацией
_FLOAT_FIELDS = ('coi', 'size', 'weight')

# Простые строковые поля, заполняем только если пустые в BA-записи
_PATCH_SIMPLE_FIELDS = (
    'photo_url', 'land_of_birth', 'land_of_birth_code', 'land_of_standing',
    'registration_number', 'brand_chip', 'kennel', 'sire_name', 'dam_name',
    'variety', 'eyes_color', 'distinguishing_features', 'notes', 'club',
)


# Вычисляет dict обновлений Zoo-данных поверх существующей BA-записи
def build_zoo_patch(dog, zoo_raw: Dict, zoo_id: str) -> Dict:
    update: Dict = {'zooportal_id': str(zoo_id)}

    zoo_name = (
            zoo_raw.get('registered_name') or
            zoo_raw.get('name') or
            zoo_raw.get('registeredName') or ''
    )
    if zoo_name:
        update['registered_name'] = normalize_dog_name(zoo_name)

    if not getattr(dog, 'call_name', None):
        call = zoo_raw.get('call_name')
        if call:
            update['call_name'] = call.strip()

    if not getattr(dog, 'sex', None):
        zoo_sex = zoo_raw.get('sex')
        if zoo_sex is not None:
            update['sex'] = zoo_sex if isinstance(zoo_sex, int) else parse_sex(zoo_sex)

    if not getattr(dog, 'date_of_birth', None):
        dob = parse_date(zoo_raw.get('date_of_birth'))
        if dob:
            update['date_of_birth'] = dob

    if not getattr(dog, 'year_of_birth', None):
        yob = zoo_raw.get('year_of_birth')
        if yob:
            update['year_of_birth'] = parse_int(yob, default=None)

    if not getattr(dog, 'date_of_death', None):
        dod = parse_date(zoo_raw.get('date_of_death'))
        if dod:
            update['date_of_death'] = dod

    if not getattr(dog, 'year_of_death', None):
        yod = zoo_raw.get('year_of_death')
        if yod:
            update['year_of_death'] = parse_int(yod, default=None)

    for field in _PATCH_SIMPLE_FIELDS:
        if not getattr(dog, field, None):
            val = zoo_raw.get(field)
            if val:
                update[field] = str(val).strip()

    if not getattr(dog, 'color', None):
        zoo_color = zoo_raw.get('color') or ''
        if zoo_color:
            update['color'] = parse_color(zoo_color)

    if not getattr(dog, 'color_marking', None):
        cm = zoo_raw.get('color_marking')
        if cm:
            update['color_marking'] = str(cm).strip()

    if not getattr(dog, 'prefix_titles', None):
        pt = zoo_raw.get('prefix_titles') or zoo_raw.get('titles_text')
        if pt:
            update['prefix_titles'] = str(pt).strip()

    if not getattr(dog, 'suffix_titles', None):
        st = zoo_raw.get('suffix_titles')
        if st:
            update['suffix_titles'] = str(st).strip()

    for field in _FLOAT_FIELDS:
        if getattr(dog, field, None) is None:
            raw = zoo_raw.get(field)
            if raw is not None:
                try:
                    update[field] = float(raw)
                except (ValueError, TypeError):
                    pass

    return update

# BA: патч полей с приоритетом BA (перезаписывает даже непустые значения, но не пустотой)
def build_ba_patch(data: Dict, ba_base_url: str) -> Dict:
    normalized = normalize_ba_data(data, ba_base_url)
    return {k: v for k, v in normalized.items() if v not in (None, '')}