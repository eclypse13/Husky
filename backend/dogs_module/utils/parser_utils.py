# dogs_module/utils/parser_utils.py
"""
Утилиты для парсинга данных
"""

from datetime import datetime, date
from typing import Optional, Union
import logging

from django.utils.timezone import is_aware, make_aware

logger = logging.getLogger(__name__)


def parse_date(date_str: Union[str, date, datetime, None]) -> Optional[datetime]:
    """
    Парсит дату из разных форматов.
    Всегда возвращает timezone-aware datetime (или None) —
    это требование Django DateTimeField при USE_TZ=True.

    ПРИМЕРЫ:
    - "08.02.2025" → datetime(2025, 2, 8, 0, 0, tzinfo=UTC)
    - "2025-02-08" → datetime(2025, 2, 8, 0, 0, tzinfo=UTC)
    - "2025"       → datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
    - aware dt     → возвращается как есть
    - naive dt     → делается aware через make_aware()
    """
    if not date_str:
        return None

    # Уже aware datetime — возвращаем как есть
    if isinstance(date_str, datetime):
        return date_str if is_aware(date_str) else make_aware(date_str)

    # date объект — конвертируем в aware datetime
    if isinstance(date_str, date):
        return make_aware(datetime(date_str.year, date_str.month, date_str.day))

    if not isinstance(date_str, str):
        return None

    date_str = date_str.strip()

    formats = [
        '%d.%m.%Y',  # 08.02.2025
        '%Y-%m-%d',  # 2025-02-08
        '%d/%m/%Y',  # 08/02/2025
        '%Y/%m/%d',  # 2025/02/08
        '%d-%m-%Y',  # 08-02-2025
        '%Y.%m.%d',  # 2025.02.08
        '%d %B %Y',  # 08 February 2025
        '%B %d, %Y',  # February 08, 2025
    ]

    for fmt in formats:
        try:
            naive = datetime.strptime(date_str, fmt)
            return make_aware(naive)
        except ValueError:
            continue

    # Только год ("2025")
    if date_str.isdigit() and len(date_str) == 4:
        try:
            return make_aware(datetime(int(date_str), 1, 1))
        except ValueError:
            pass

    logger.warning(f"Не удалось распарсить дату: {date_str}")
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


def parse_color(color_str: str) -> str:
    """
    Нормализует название окраса к единому русскому стандарту.

    СТАНДАРТНЫЕ ЗНАЧЕНИЯ:
      серо-белый        — все варианты grey & white
      палево-белый      — все варианты fawn & white
      чёрно-белый       — все варианты black & white
      серебристо-белый  — все варианты silver & white
      медно-белый       — все варианты copper/brown & white
      рыже-белый        — все варианты red & white
      чёрный            — чисто чёрный без белого
      белый             — чисто белый
      рыжий             — чисто рыжий/red без белого
      агути             — agouti / волчий окрас
      пегий             — piebald / splash / пятнистый

    ПРИМЕРЫ:
    - "gray&white"        → "серо-белый"
    - "с-б"               → "серо-белый"
    - "gris y blanco"     → "серо-белый"
    - "пал-бел."          → "палево-белый"
    - "fawn/white"        → "палево-белый"
    - "чер-бел"           → "чёрно-белый"
    - "black&white"       → "чёрно-белый"
    - "copper & white"    → "медно-белый"
    - "red/white"         → "рыже-белый"
    - "agouti"            → "агути"
    - "бел."              → "белый"
    """
    if not color_str:
        return ""

    # Нормализуем входную строку: lowercase, убираем точки/пробелы по краям
    color = color_str.lower().strip().rstrip('.')

    # ── Прямой маппинг известных вариантов ────────────────────────────────────
    _COLOR_MAP = {

        # ── серо-белый ────────────────────────────────────────────────────────
        # русские варианты
        'серо-белый':           'серо-белый',
        'серый с белым':        'серо-белый',
        'бело-серый':           'серо-белый',
        'сер белый':            'серо-белый',
        'сер-белый':            'серо-белый',
        'сер-бел':              'серо-белый',
        'сер.-бел':             'серо-белый',
        'сер-б':                'серо-белый',
        'с-б':                  'серо-белый',
        # английские варианты
        'grey & white':         'серо-белый',
        'grey/white':           'серо-белый',
        'grey&white':           'серо-белый',
        'gray & white':         'серо-белый',
        'gray/white':           'серо-белый',
        'gray&white':           'серо-белый',
        'gray and white':       'серо-белый',
        'grey and white':       'серо-белый',
        'silver grey & white':  'серо-белый',
        # испанский / другие
        'gris y blanco':        'серо-белый',
        'gris & blanco':        'серо-белый',
        'gris/blanco':          'серо-белый',

        # ── палево-белый ──────────────────────────────────────────────────────
        # русские варианты
        'палево-белый':         'палево-белый',
        'пал-белый':            'палево-белый',
        'пал-бел':              'палево-белый',
        'пал.-бел':             'палево-белый',
        'палевый с белым':      'палево-белый',
        'пало-белый':           'палево-белый',
        'пал':                  'палево-белый',
        # английские варианты
        'fawn & white':         'палево-белый',
        'fawn/white':           'палево-белый',
        'fawn&white':           'палево-белый',
        'fawn and white':       'палево-белый',
        'sable & white':        'палево-белый',
        'sable/white':          'палево-белый',
        'sable&white':          'палево-белый',
        'sable and white':      'палево-белый',
        'isabella & white':     'палево-белый',
        # испанский
        'leonado y blanco':     'палево-белый',
        'bayo y blanco':        'палево-белый',

        # ── чёрно-белый ───────────────────────────────────────────────────────
        # русские варианты
        'чёрно-белый':          'чёрно-белый',
        'черно-белый':          'чёрно-белый',
        'чёрный с белым':       'чёрно-белый',
        'черный с белым':       'чёрно-белый',
        'черн-бел':             'чёрно-белый',
        'чер-бел':              'чёрно-белый',
        'ч-б':                  'чёрно-белый',
        'чёр-бел':              'чёрно-белый',
        # английские варианты
        'black & white':        'чёрно-белый',
        'black/white':          'чёрно-белый',
        'black&white':          'чёрно-белый',
        'black and white':      'чёрно-белый',
        # испанский
        'negro y blanco':       'чёрно-белый',
        'negro & blanco':       'чёрно-белый',

        # ── серебристо-белый ──────────────────────────────────────────────────
        # русские варианты
        'серебристо-белый':     'серебристо-белый',
        'серебристый с белым':  'серебристо-белый',
        'сереб-белый':          'серебристо-белый',
        'сер-бел серебр':       'серебристо-белый',
        # английские варианты
        'silver & white':       'серебристо-белый',
        'silver/white':         'серебристо-белый',
        'silver&white':         'серебристо-белый',
        'silver and white':     'серебристо-белый',
        'silver-white':         'серебристо-белый',
        'silver':               'серебристо-белый',

        # ── медно-белый ───────────────────────────────────────────────────────
        # русские варианты
        'медно-белый':          'медно-белый',
        'медный с белым':       'медно-белый',
        'коричнево-белый':      'медно-белый',
        'коричневый с белым':   'медно-белый',
        'кор-бел':              'медно-белый',
        'кор-белый':            'медно-белый',
        # английские варианты
        'copper & white':       'медно-белый',
        'copper/white':         'медно-белый',
        'copper&white':         'медно-белый',
        'copper and white':     'медно-белый',
        'brown & white':        'медно-белый',
        'brown/white':          'медно-белый',
        'brown&white':          'медно-белый',
        'brown and white':      'медно-белый',
        'chocolate & white':    'медно-белый',
        'chocolate/white':      'медно-белый',
        # испанский
        'cobre y blanco':       'медно-белый',

        # ── рыже-белый ────────────────────────────────────────────────────────
        # русские варианты
        'рыже-белый':           'рыже-белый',
        'рыжий с белым':        'рыже-белый',
        'рыж-бел':              'рыже-белый',
        # английские варианты
        'red & white':          'рыже-белый',
        'red/white':            'рыже-белый',
        'red&white':            'рыже-белый',
        'red and white':        'рыже-белый',
        'orange & white':       'рыже-белый',
        'orange/white':         'рыже-белый',
        # испанский
        'rojo y blanco':        'рыже-белый',

        # ── чёрный ────────────────────────────────────────────────────────────
        # русские варианты
        'чёрный':               'чёрный',
        'черный':               'чёрный',
        'чёрн':                 'чёрный',
        'черн':                 'чёрный',
        # английские варианты
        'black':                'чёрный',
        'solid black':          'чёрный',
        # испанский
        'negro':                'чёрный',

        # ── белый ─────────────────────────────────────────────────────────────
        # русские варианты
        'белый':                'белый',
        'бел':                  'белый',
        'белая':                'белый',
        # английские варианты
        'white':                'белый',
        'solid white':          'белый',
        'pure white':           'белый',
        # испанский
        'blanco':               'белый',

        # ── рыжий ─────────────────────────────────────────────────────────────
        # русские варианты
        'рыжий':                'рыжий',
        'рыжая':                'рыжий',
        'рыж':                  'рыжий',
        # английские варианты
        'red':                  'рыжий',
        'solid red':            'рыжий',
        'orange':               'рыжий',
        # испанский
        'rojo':                 'рыжий',

        # ── агути ─────────────────────────────────────────────────────────────
        # русские варианты
        'агути':                'агути',
        'волчий':               'агути',
        'волчий серый':         'агути',
        'зонарный':             'агути',
        # английские варианты
        'agouti':               'агути',
        'agouti & white':       'агути',
        'agouti/white':         'агути',
        'agouti&white':         'агути',
        'wolf grey':            'агути',
        'wolf gray':            'агути',
        'wolf sable':           'агути',

        # ── пегий ─────────────────────────────────────────────────────────────
        # русские варианты
        'пегий':                'пегий',
        'пятнистый':            'пегий',
        'пегая':                'пегий',
        # английские варианты
        'piebald':              'пегий',
        'splash':               'пегий',
        'splash & white':       'пегий',
        'pinto':                'пегий',
    }

    # Убираем точки из ключа для поиска (пал-бел. → пал-бел)
    lookup = color.rstrip('.')
    if lookup in _COLOR_MAP:
        return _COLOR_MAP[lookup]

    # ── Общая нормализация для неизвестных значений (fallback) ───────────────
    # Для совсем новых окрасов приводим к читаемому виду, не теряя смысл
    color = color.replace('gray', 'серый').replace('grey', 'серый')
    color = color.replace('black', 'чёрный').replace('white', 'белый')
    color = color.replace('fawn', 'палевый').replace('red', 'рыжий')
    color = color.replace('silver', 'серебристый').replace('copper', 'медный')
    color = color.replace(' and ', ' с ').replace(' & ', ' с ')
    color = color.replace(' con ', ' с ')
    color = color.replace('/', ' с ').replace('&', ' с ')
    return ' '.join(color.split())


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