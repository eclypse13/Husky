# dogs_module/utils/parser_utils.py
"""
Утилиты для парсинга данных
"""

import logging

logger = logging.getLogger(__name__)

import re
from datetime import datetime, date
from typing import Optional, Union
import logging
from ..config import BREEDARCHIVE_BASE_URL
from django.utils.timezone import is_aware, make_aware

logger = logging.getLogger(__name__)

# Словарь английских названий месяцев (полных и сокращённых)
_EN_MONTHS = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5, 'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12,
}


def _parse_english_month_date(date_str: str) -> Optional[datetime]:
    """
    Парсит даты вида 'Apr 23 1980', 'April 23, 1980', '23 Apr 1980'.
    Возвращает naive datetime или None.
    """
    # Нормализуем пробелы и удаляем запятые
    s = re.sub(r'\s+', ' ', date_str.strip()).replace(',', '')
    parts = s.split()
    if len(parts) != 3:
        return None

    # Определяем, где месяц, где день, где год
    # Вариант 1: месяц буквами, потом число, потом год
    # Вариант 2: число, месяц буквами, год
    month_num = None
    day = None
    year = None

    # Ищем часть, которая может быть месяцем
    for i, p in enumerate(parts):
        p_lower = p.lower()
        if p_lower in _EN_MONTHS:
            month_num = _EN_MONTHS[p_lower]
            # Остальные две части – день и год
            other = [parts[j] for j in range(3) if j != i]
            if len(other) == 2:
                # День должен быть числом до 31, год – 4 цифры
                try:
                    day_candidate = int(other[0])
                    year_candidate = int(other[1])
                    if 1 <= day_candidate <= 31 and 1900 <= year_candidate <= 2100:
                        day, year = day_candidate, year_candidate
                    else:
                        # Попробуем поменять местами
                        day_candidate, year_candidate = year_candidate, day_candidate
                        if 1 <= day_candidate <= 31 and 1900 <= year_candidate <= 2100:
                            day, year = day_candidate, year_candidate
                except ValueError:
                    pass
            break

    if month_num and day and year:
        try:
            return datetime(year, month_num, day)
        except ValueError:
            pass
    return None


def parse_date(date_str: Union[str, date, datetime, None]) -> Optional[datetime]:
    """
    Парсит дату из разных форматов.
    Всегда возвращает timezone-aware datetime (или None).

    ПОДДЕРЖИВАЕТ:
    - ISO: 2025-02-08
    - DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY, YYYY.MM.DD
    - DD Month YYYY (полное или сокращённое название месяца на английском)
    - Month DD, YYYY
    - Четырёхзначный год
    """
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str if is_aware(date_str) else make_aware(date_str)

    if isinstance(date_str, date):
        return make_aware(datetime(date_str.year, date_str.month, date_str.day))

    if not isinstance(date_str, str):
        return None

    # Нормализуем: убираем лишние пробелы, табуляции, переносы
    s = re.sub(r'\s+', ' ', date_str.strip())

    # Сначала пробуем форматы с числами (не зависят от локали)
    numeric_formats = [
        '%d.%m.%Y',  # 08.02.2025
        '%Y-%m-%d',  # 2025-02-08
        '%d/%m/%Y',  # 08/02/2025
        '%Y/%m/%d',  # 2025/02/08
        '%d-%m-%Y',  # 08-02-2025
        '%Y.%m.%d',  # 2025.02.08
    ]
    for fmt in numeric_formats:
        try:
            naive = datetime.strptime(s, fmt)
            return make_aware(naive)
        except ValueError:
            continue

    # Пробуем парсить даты с английскими названиями месяцев
    # покрывает "Apr 23 1980", "April 23, 1980", "23 Apr 1980", "23 April 1980"
    naive = _parse_english_month_date(s)
    if naive:
        return make_aware(naive)

    # Форматы с полным названием месяца (на случай, если локаль английская)
    locale_formats = [
        '%d %B %Y',  # 08 February 2025
        '%B %d, %Y',  # February 08, 2025
        '%b %d %Y',  # Feb 08 2025 (short month)
        '%d %b %Y',  # 08 Feb 2025
    ]
    for fmt in locale_formats:
        try:
            naive = datetime.strptime(s, fmt)
            return make_aware(naive)
        except ValueError:
            continue

    # Год (только цифры)
    if s.isdigit() and len(s) == 4:
        try:
            return make_aware(datetime(int(s), 1, 1))
        except ValueError:
            pass

    logger.warning(f"Не удалось распарсить дату: {date_str!r}")
    return None


def parse_int(value: Union[str, int, float, None], default: int = 0) -> int:
    """
    Безопасный парсинг целого числа.

    ПРИМЕРЫ:
    - "123"    → 123
    - "123.45" → 123
    - "abc"    → 0 (default)
    - None     → 0 (default)
    """
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip().replace(',', '').replace(' ', '')))
        except (ValueError, TypeError):
            pass
    return default


def parse_float(value: Union[str, int, float, None], default: float = 0.0) -> float:
    """
    Безопасный парсинг дробного числа.

    ПРИМЕРЫ:
    - "123.45" → 123.45
    - "123,45" → 123.45
    - "abc"    → 0.0 (default)
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(',', '.').replace(' ', ''))
        except (ValueError, TypeError):
            pass
    return default


def parse_year(value: Union[str, int, date, datetime, None]) -> Optional[int]:
    """
    Извлекает год из разных форматов.

    ПРИМЕРЫ:
    - "2025"            → 2025
    - "08.02.2025"      → 2025
    - date(2025, 2, 8)  → 2025
    """
    if not value:
        return None
    if isinstance(value, int):
        return value if 1900 <= value <= 2100 else None
    if isinstance(value, (date, datetime)):
        return value.year
    if isinstance(value, str):
        parsed_date = parse_date(value)
        if parsed_date:
            return parsed_date.year
        year = parse_int(value, default=0)
        if year and 1900 <= year <= 2100:
            return year
    return None


# Словарь нормализации окраса

_COLOR_MAP: dict = {
    # серо-белый
    'серо-белый': 'серо-белый',
    'серый с белым': 'серо-белый',
    'бело-серый': 'серо-белый',
    'сер белый': 'серо-белый',
    'сер-белый': 'серо-белый',
    'сер-бел': 'серо-белый',
    'сер.-бел': 'серо-белый',
    'сер-б': 'серо-белый',
    'с-б': 'серо-белый',
    'grey & white': 'серо-белый',
    'grey/white': 'серо-белый',
    'grey&white': 'серо-белый',
    'gray & white': 'серо-белый',
    'gray/white': 'серо-белый',
    'gray&white': 'серо-белый',
    'gray and white': 'серо-белый',
    'grey and white': 'серо-белый',
    'silver grey & white': 'серо-белый',
    'gris y blanco': 'серо-белый',
    'gris & blanco': 'серо-белый',
    'gris/blanco': 'серо-белый',

    # палево-белый
    'палево-белый': 'палево-белый',
    'пал-белый': 'палево-белый',
    'пал-бел': 'палево-белый',
    'пал.-бел': 'палево-белый',
    'палевый с белым': 'палево-белый',
    'пало-белый': 'палево-белый',
    'пал': 'палево-белый',
    'fawn & white': 'палево-белый',
    'fawn/white': 'палево-белый',
    'fawn&white': 'палево-белый',
    'fawn and white': 'палево-белый',
    'sable & white': 'палево-белый',
    'sable/white': 'палево-белый',
    'sable&white': 'палево-белый',
    'sable and white': 'палево-белый',
    'isabella & white': 'палево-белый',
    'leonado y blanco': 'палево-белый',
    'bayo y blanco': 'палево-белый',

    # чёрно-белый
    'чёрно-белый': 'чёрно-белый',
    'черно-белый': 'чёрно-белый',
    'чёрный с белым': 'чёрно-белый',
    'черный с белым': 'чёрно-белый',
    'черн-бел': 'чёрно-белый',
    'чер-бел': 'чёрно-белый',
    'ч-б': 'чёрно-белый',
    'чёр-бел': 'чёрно-белый',
    'black & white': 'чёрно-белый',
    'black/white': 'чёрно-белый',
    'black&white': 'чёрно-белый',
    'black and white': 'чёрно-белый',
    'negro y blanco': 'чёрно-белый',
    'negro & blanco': 'чёрно-белый',

    # серебристо-белый
    'серебристо-белый': 'серебристо-белый',
    'серебристый с белым': 'серебристо-белый',
    'сереб-белый': 'серебристо-белый',
    'сер-бел серебр': 'серебристо-белый',
    'silver & white': 'серебристо-белый',
    'silver/white': 'серебристо-белый',
    'silver&white': 'серебристо-белый',
    'silver and white': 'серебристо-белый',
    'silver-white': 'серебристо-белый',
    'silver': 'серебристо-белый',

    # медно-белый
    'медно-белый': 'медно-белый',
    'медный с белым': 'медно-белый',
    'коричнево-белый': 'медно-белый',
    'коричневый с белым': 'медно-белый',
    'кор-бел': 'медно-белый',
    'кор-белый': 'медно-белый',
    'copper & white': 'медно-белый',
    'copper/white': 'медно-белый',
    'copper&white': 'медно-белый',
    'copper and white': 'медно-белый',
    'brown & white': 'медно-белый',
    'brown/white': 'медно-белый',
    'brown&white': 'медно-белый',
    'brown and white': 'медно-белый',
    'chocolate & white': 'медно-белый',
    'chocolate/white': 'медно-белый',
    'cobre y blanco': 'медно-белый',

    # рыже-белый
    'рыже-белый': 'рыже-белый',
    'рыжий с белым': 'рыже-белый',
    'рыж-бел': 'рыже-белый',
    'red & white': 'рыже-белый',
    'red/white': 'рыже-белый',
    'red&white': 'рыже-белый',
    'red and white': 'рыже-белый',
    'orange & white': 'рыже-белый',
    'orange/white': 'рыже-белый',
    'rojo y blanco': 'рыже-белый',

    # чёрный
    'чёрный': 'чёрный',
    'черный': 'чёрный',
    'чёрн': 'чёрный',
    'черн': 'чёрный',
    'black': 'чёрный',
    'solid black': 'чёрный',
    'negro': 'чёрный',

    # белый
    'белый': 'белый',
    'бел': 'белый',
    'белая': 'белый',
    'white': 'белый',
    'solid white': 'белый',
    'pure white': 'белый',
    'blanco': 'белый',

    # рыжий
    'рыжий': 'рыжий',
    'рыжая': 'рыжий',
    'рыж': 'рыжий',
    'red': 'рыжий',
    'solid red': 'рыжий',
    'orange': 'рыжий',
    'rojo': 'рыжий',

    # агути
    'агути': 'агути',
    'волчий': 'агути',
    'волчий серый': 'агути',
    'зонарный': 'агути',
    'agouti': 'агути',
    'agouti & white': 'агути',
    'agouti/white': 'агути',
    'agouti&white': 'агути',
    'wolf grey': 'агути',
    'wolf gray': 'агути',
    'wolf sable': 'агути',

    # пегий
    'пегий': 'пегий',
    'пятнистый': 'пегий',
    'пегая': 'пегий',
    'piebald': 'пегий',
    'splash': 'пегий',
    'splash & white': 'пегий',
    'pinto': 'пегий',
}


def _normalize_unknown_color(color: str) -> str:
    """
    Fallback-нормализация для окрасов которых нет в _COLOR_MAP.
    Переводит английские/испанские слова в русские и унифицирует разделители.
    """
    color = color.replace('gray', 'серый').replace('grey', 'серый')
    color = color.replace('black', 'чёрный').replace('white', 'белый')
    color = color.replace('fawn', 'палевый').replace('red', 'рыжий')
    color = color.replace('silver', 'серебристый').replace('copper', 'медный')
    color = color.replace(' and ', ' с ').replace(' & ', ' с ')
    color = color.replace(' con ', ' с ')
    color = color.replace('/', ' с ').replace('&', ' с ')
    return ' '.join(color.split())


def parse_color(color_str: str) -> str:
    """
    Нормализует название окраса к единому русскому стандарту.

    СТАНДАРТНЫЕ ЗНАЧЕНИЯ:
      серо-белый, палево-белый, чёрно-белый, серебристо-белый,
      медно-белый, рыже-белый, чёрный, белый, рыжий, агути, пегий

    ПРИМЕРЫ:
    - "gray&white"   → "серо-белый"
    - "с-б"          → "серо-белый"
    - "black&white"  → "чёрно-белый"
    - "agouti"       → "агути"
    - "бел."         → "белый"
    """
    if not color_str:
        return ""

    lookup = color_str.lower().strip().rstrip('.')
    result = _COLOR_MAP.get(lookup)
    if result:
        return result

    return _normalize_unknown_color(lookup)


def parse_coi(coi_str: Union[str, float, None]) -> Optional[float]:
    """
    Парсит коэффициент инбридинга (COI), возвращает в процентах.

    ПРИМЕРЫ:
    - "12.5%" → 12.5
    - "0.125" → 12.5
    - 0.125   → 12.5
    """
    if not coi_str:
        return None

    if isinstance(coi_str, float):
        return coi_str * 100 if 0 <= coi_str <= 1 else coi_str

    if isinstance(coi_str, str):
        coi = parse_float(coi_str.replace('%', '').strip(), default=None)
        if coi is not None:
            return coi * 100 if 0 <= coi <= 1 else coi

    return None


def assemble_partial_date(data: dict, kind: str) -> str | None:
    """
    Собирает дату-строку из разрозненных полей year/month/day.
    kind = 'birth' | 'death'
    """

    def _i(v) -> int | None:
        try:
            return int(v) if v is not None else None
        except (ValueError, TypeError):
            return None

    if kind == 'birth':
        y = _i(data.get('year_of_birth') or data.get('yearOfBirth'))
        m = _i(data.get('month_of_birth') or data.get('monthOfBirth'))
        d = _i(data.get('day_of_birth') or data.get('dayOfBirth'))
    else:
        y = _i(data.get('year_of_death') or data.get('yearOfDeath'))
        m = _i(data.get('month_of_death') or data.get('monthOfDeath'))
        d = _i(data.get('day_of_death') or data.get('dayOfDeath'))

    if y and m and d:
        return f"{y}-{m:02d}-{d:02d}"
    if y and m:
        return f"{y}-{m:02d}-01"
    return None


def build_BA_photo_url(photo_path: Optional[str]) -> Optional[str]:
    """Строит полный URL фото из относительного пути BreedArchive."""
    if not photo_path:
        return None
    # Убираем суффикс маленького превью _s
    # "photo.b123ca419507eff9_s.jpg" → "photo.b123ca419507eff9.jpg"
    clean_path = re.sub(r'_s(\.[^.]+)$', r'\1', photo_path)
    return f"https://siberianhusky.breedarchive.com/resource/{clean_path}"