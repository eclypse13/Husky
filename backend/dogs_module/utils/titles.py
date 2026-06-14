# dogs_module/utils/titles.py
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# СТРАНЫ

_COUNTRY_CODES: Dict[str, str] = {
    'RU': 'RUS', 'RUS': 'RUS', 'RF': 'RUS', 'РФ': 'RUS',
    'RKF': 'RKF',
    'UA': 'UA', 'UKR': 'UA',
    'BY': 'BY', 'BLR': 'BY',
    'KZ': 'KZ', 'KAZ': 'KZ',
    'AZ': 'AZ', 'AZE': 'AZ',
    'CY': 'CY', 'CYP': 'CY',
    'ME': 'ME', 'MNE': 'ME',
    'MD': 'MD', 'MDA': 'MD',
    'GE': 'GE', 'GEO': 'GE',
    'AM': 'AM', 'ARM': 'AM',
    'PL': 'PL', 'POL': 'PL',
    'CZ': 'CZ', 'CZE': 'CZ',
    'SK': 'SK', 'SVK': 'SK',
    'LV': 'LV', 'LVA': 'LV',
    'LT': 'LT', 'LTU': 'LT',
    'EE': 'EE', 'EST': 'EE',
    'FI': 'FIN', 'FIN': 'FIN',
    'SE': 'SWE', 'SWE': 'SWE',
    'NO': 'NOR', 'NOR': 'NOR',
    'DK': 'DNK', 'DNK': 'DNK',
    'DE': 'DEU', 'DEU': 'DEU', 'GER': 'DEU',
    'FR': 'FRA', 'FRA': 'FRA',
    'IT': 'ITA', 'ITA': 'ITA',
    'ES': 'ESP', 'ESP': 'ESP',
    'PT': 'PRT', 'PRT': 'PRT',
    'NL': 'NLD', 'NLD': 'NLD',
    'BE': 'BEL', 'BEL': 'BEL',
    'CH': 'CHE', 'CHE': 'CHE', 'SWI': 'CHE',
    'AT': 'AUT', 'AUT': 'AUT',
    'HU': 'HUN', 'HUN': 'HUN',
    'RO': 'ROU', 'ROU': 'ROU',
    'BG': 'BGR', 'BGR': 'BGR',
    'GR': 'GRC', 'GRC': 'GRC',
    'TR': 'TUR', 'TUR': 'TUR',
    'IL': 'ISR', 'ISR': 'ISR',
    'US': 'USA', 'USA': 'USA',
    'CA': 'CAN', 'CAN': 'CAN',
    'AU': 'AUS', 'AUS': 'AUS',
    'NZ': 'NZL', 'NZL': 'NZL',
    'JP': 'JPN', 'JPN': 'JPN',
    'KR': 'KOR', 'KOR': 'KOR',
    'CN': 'CHN', 'CHN': 'CHN',
    'IN': 'IND', 'IND': 'IND',
    'BR': 'BRA', 'BRA': 'BRA',
    'AR': 'ARG', 'ARG': 'ARG',
    'MX': 'MEX', 'MEX': 'MEX',
    'ZA': 'ZAF', 'ZAF': 'ZAF',
}

_COUNTRY_NAMES: Dict[str, str] = {
    'RUS': 'России', 'RKF': 'РКФ',
    'UA': 'Украины', 'BY': 'Беларуси', 'KZ': 'Казахстана',
    'AZ': 'Азербайджана', 'CY': 'Кипра', 'ME': 'Черногории',
    'MD': 'Молдовы', 'GE': 'Грузии', 'AM': 'Армении',
    'PL': 'Польши', 'CZ': 'Чехии', 'SK': 'Словакии',
    'LV': 'Латвии', 'LT': 'Литвы', 'EE': 'Эстонии',
    'FIN': 'Финляндии', 'SWE': 'Швеции', 'NOR': 'Норвегии',
    'DNK': 'Дании', 'DEU': 'Германии', 'FRA': 'Франции',
    'ITA': 'Италии', 'ESP': 'Испании', 'PRT': 'Португалии',
    'NLD': 'Нидерландов', 'BEL': 'Бельгии', 'CHE': 'Швейцарии',
    'AUT': 'Австрии', 'HUN': 'Венгрии', 'ROU': 'Румынии',
    'BGR': 'Болгарии', 'GRC': 'Греции', 'TUR': 'Турции',
    'ISR': 'Израиля', 'USA': 'США', 'CAN': 'Канады',
    'AUS': 'Австралии', 'NZL': 'Новой Зеландии', 'JPN': 'Японии',
    'KOR': 'Кореи', 'CHN': 'Китая', 'IND': 'Индии',
    'BRA': 'Бразилии', 'ARG': 'Аргентины', 'MEX': 'Мексики',
    'ZAF': 'ЮАР',
}

# Слова, которые не являются кодами стран
_NOT_COUNTRY = {'CH', 'CL', 'CAC', 'CACIB', 'INT', 'EU', 'WORLD'}


def get_country_display_name(code: str) -> str:
    return _COUNTRY_NAMES.get(code.upper(), code) if code else ''


def extract_country_code(raw_title: str) -> Optional[str]:
    """Извлекает нормализованный код страны из строки титула."""
    upper = raw_title.upper()

    # Формат "GrCH.RUS", "CH.RKF"
    m = re.search(r'\.([A-Z]{2,4})\b', upper)
    if m and m.group(1) not in _NOT_COUNTRY:
        return _COUNTRY_CODES.get(m.group(1), m.group(1))

    # Русские названия
    if 'России' in upper or 'РФ' in upper:
        return 'RUS'
    if 'РКФ' in upper or 'RKF' in upper:
        return 'RKF'
    if 'БЕЛАРУСИ' in upper:
        return 'BY'
    if 'УКРАИНЫ' in upper:
        return 'UA'
    if 'КАЗАХСТАНА' in upper:
        return 'KZ'

    # В скобках
    m = re.search(r'\(([A-Z]{2,4})\)', upper)
    if m:
        return _COUNTRY_CODES.get(m.group(1), m.group(1))

    return None



# ПАРСИНГ ОДНОГО ТИТУЛА

_ZP_PATTERNS = {
    'grch': ('GrCH', 'Гранд Чемпион', True),
    'grand champion': ('GrCH', 'Гранд Чемпион', True),
    'гранд чемпион': ('GrCH', 'Гранд Чемпион', True),
    'ch.cl': ('CH.CL', 'Чемпион Национального клуба породы', True),
    'нкп': ('CH.CL', 'Чемпион Национального клуба породы', True),
    'jch': ('JCH', 'Юниор Чемпион', True),
    'юниор': ('JCH', 'Юниор Чемпион', True),
    'junior': ('JCH', 'Юниор Чемпион', True),
    'vch': ('VCH', 'Ветеран Чемпион', True),
    'ветеран': ('VCH', 'Ветеран Чемпион', True),
    'int': ('INT', 'Интернациональный Чемпион', True),
    'интер': ('INT', 'Интернациональный Чемпион', True),
    'eu': ('EU', 'Европейский Чемпион', True),
    'world': ('WORLD', 'Чемпион Мира', True),
    'мир': ('WORLD', 'Чемпион Мира', True),
    'bch': ('BCH', 'Чемпион породы', True),
    'cacib': ('CACIB', 'Сертификат международной выставки', False),
    'cac': ('CAC', 'Сертификат соответствия породе', False),
    'чк': ('ЧК', 'Чемпион клуба', False),
    'кчк': ('КЧК', 'Кандидат в чемпионы клуба', False),
    'ch': ('CH', 'Чемпион', True),
    'чемпион': ('CH', 'Чемпион', True),
    'champion': ('CH', 'Чемпион', True),
}


def _extract_winner_year(text: str) -> Tuple[Optional[int], bool]:
    m = re.search(r'\b(19|20)\d{2}\b', text)
    if m:
        return int(m.group()), True
    return None, False


# Типы BA-титулов: keyword → (short_name, long_name, is_prefix)
# Вынесено на уровень модуля — не создаётся заново при каждом вызове.
_BA_TITLE_TYPES = {
    'CH': ('CH', 'Чемпион', True),
    'JCH': ('JCH', 'Юниор Чемпион', True),
    'J.CH': ('JCH', 'Юниор Чемпион', True),
    'GRCH': ('GrCH', 'Гранд Чемпион', True),
    'GR.CH': ('GrCH', 'Гранд Чемпион', True),
    'VCH': ('VCH', 'Ветеран Чемпион', True),
    'V.CH': ('VCH', 'Ветеран Чемпион', True),
}


def _parse_zooportal_title(raw: str) -> Optional[Dict[str, Any]]:
    """Парсит один Zooportal-титул вида "GrCH.RUS", "CH.RKF 2023"."""
    if not raw:
        return None

    country = extract_country_code(raw)
    lower = raw.lower()
    short_name, long_name, is_prefix = raw, raw, True

    for pattern, (short, long, prefix) in _ZP_PATTERNS.items():
        if pattern not in lower:
            continue
        # "ch" не должен срабатывать внутри grch, jch и т.д.
        if pattern == 'ch' and any(x in lower for x in ('grch', 'jch', 'vch', 'bch', 'ch.cl')):
            continue
        short_name, long_name, is_prefix = short, long, prefix
        if country and 'чемпион' in long.lower():
            long_name = f"{long} {get_country_display_name(country)}"
        break

    winner_year, has_winner_year = _extract_winner_year(raw)
    return {
        'short_name': short_name,
        'long_name': long_name,
        'country': country,
        'is_prefix': is_prefix,
        'has_winner_year': has_winner_year,
        'winner_year': winner_year,
    }


def _parse_breedarchive_title(raw: str) -> Optional[Dict[str, Any]]:
    """Парсит один BA-титул вида "RU CH", "UA JCH", "RU Club CH"."""
    if not raw:
        return None

    upper = raw.upper()
    words = upper.split()

    # "Club CH" без страны
    if upper in ('CLUB CH', 'CLUB.CH'):
        winner_year, has_winner_year = _extract_winner_year(raw)
        return {
            'short_name': 'CH.CL',
            'long_name': 'Чемпион Национального клуба породы',
            'country': None,
            'is_prefix': True,
            'has_winner_year': has_winner_year,
            'winner_year': winner_year,
        }

    if len(words) >= 2:
        cc = _COUNTRY_CODES.get(words[0])
        title_word = words[1]

        # "RU Club CH"
        if cc and title_word == 'CLUB' and len(words) >= 3 and words[2] == 'CH':
            winner_year, has_winner_year = _extract_winner_year(raw)
            return {
                'short_name': 'CH.CL',
                'long_name': f"Чемпион Национального клуба породы {get_country_display_name(cc)}",
                'country': cc,
                'is_prefix': True,
                'has_winner_year': has_winner_year,
                'winner_year': winner_year,
            }

        if cc:
            if title_word in _BA_TITLE_TYPES:
                short, base_long, is_prefix = _BA_TITLE_TYPES[title_word]
                long_name = f"{base_long} {get_country_display_name(cc)}"
                winner_year, has_winner_year = _extract_winner_year(raw)
                return {
                    'short_name': short,
                    'long_name': long_name,
                    'country': cc,
                    'is_prefix': is_prefix,
                    'has_winner_year': has_winner_year,
                    'winner_year': winner_year,
                }

    # Fallback — пробуем общий парсер
    return _parse_zooportal_title(raw)



# ПУБЛИЧНЫЙ ПАРСЕР ТЕКСТОВОЙ СТРОКИ ТИТУЛОВ

def parse_titles_from_text(text: str, source: str = 'zooportal') -> List[Dict[str, Any]]:
    """
    Разбивает строку титулов на структурированные записи.
    source: 'zooportal' | 'breedarchive'
    """
    if not text:
        return []

    normalized = re.sub(r'\s+', ' ', text.strip())
    raw_parts = [p.strip() for p in normalized.split(',') if p.strip()]

    result = []
    for part in raw_parts:
        parsed = (
            _parse_breedarchive_title(part)
            if source == 'breedarchive'
            else _parse_zooportal_title(part)
        )
        if parsed:
            result.append(parsed)
    return result



# СОХРАНЕНИЕ В БД


def build_title_entries(
        prefix_text: Optional[str],
        suffix_text: Optional[str],
        source: str,
) -> List[Dict[str, Any]]:
    """
    Парсит prefix/suffix-строки титулов в нормализованные записи (без БД).
    Пустые short_name отбрасываются. Сохранение — в services/title_service.py.
    """
    raw_entries: List[Dict[str, Any]] = []
    if prefix_text:
        raw_entries.extend(parse_titles_from_text(prefix_text, source))
    if suffix_text:
        raw_entries.extend(parse_titles_from_text(suffix_text, source))

    entries: List[Dict[str, Any]] = []
    for entry in raw_entries:
        short_name = (entry.get('short_name') or '').strip().lower()
        if not short_name:
            continue
        long_name = entry.get('long_name')
        entries.append({
            'short_name': short_name,
            'country': (entry.get('country') or '').lower() or None,
            'long_name': long_name[:500] if long_name else '',
            'is_prefix': entry.get('is_prefix', True),
            'has_winner_year': entry.get('has_winner_year', False),
            'winner_year': entry.get('winner_year'),
        })
    return entries
