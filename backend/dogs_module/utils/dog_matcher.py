# dogs_module/utils/dog_matcher.py
from datetime import datetime, date
from typing import Any, Dict, Tuple

from ..models import Dog


# Поля, по которым проверяются конфликты между источниками
_CONFLICT_FIELDS = (
    'call_name', 'sex', 'date_of_birth', 'date_of_death',
    'land_of_birth', 'land_of_standing', 'color', 'color_marking',
    'eyes_color', 'registration_number', 'brand_chip', 'coi',
    'photo_url', 'kennel', 'sire_name', 'dam_name',
)

# Числовые поля, требующие приведения типов перед сравнением
_NUMERIC_FIELDS = ('size', 'weight', 'coi')


def _to_comparable(field: str, value: Any) -> Any:
    """Приводит значение числового поля к float для сравнения."""
    if field in _NUMERIC_FIELDS and isinstance(value, str):
        try:
            return float(value.strip())
        except (ValueError, TypeError):
            pass
    return value


def _serialize(value: Any) -> Any:
    """Конвертирует дату/время в ISO-строку для JSON-сериализации."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def detect_conflicts(
    existing_dog: Dog,
    new_data: Dict[str, Any],
    source: str,
) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
    """
    Сравнивает поля существующей записи Dog с новыми данными.
    Конфликт = оба значения непустые и не совпадают.
    registered_name сравнивается без учёта регистра.
    """
    conflicts: Dict[str, Dict[str, Any]] = {}

    for field in _CONFLICT_FIELDS:
        existing = _to_comparable(field, getattr(existing_dog, field, None))
        incoming = _to_comparable(field, new_data.get(field))

        if incoming in (None, ''):
            continue
        if existing in (None, ''):
            continue

        if field == 'registered_name':
            if str(existing).upper() == str(incoming).upper():
                continue
        elif existing == incoming:
            continue

        existing_source = existing_dog.source or 'unknown'
        conflicts[field] = {
            existing_source: _serialize(existing),
            source: _serialize(incoming),
        }

    return bool(conflicts), conflicts


def detect_dict_conflicts(
    left: Dict[str, Any],
    right: Dict[str, Any],
    left_source: str,
    right_source: str,
) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
    """
    Детектирует конфликты между двумя словарями данных (до сохранения в БД).
    """
    conflicts: Dict[str, Dict[str, Any]] = {}

    for key in set(left) & set(right):
        lv, rv = left.get(key), right.get(key)
        if lv in (None, '') or rv in (None, ''):
            continue
        if lv == rv:
            continue
        # registered_name — без учёта регистра
        if key == 'registered_name':
            if str(lv).upper() == str(rv).upper():
                continue
        conflicts[key] = {
            left_source: _serialize(lv),
            right_source: _serialize(rv),
        }

    return bool(conflicts), conflicts