# dogs_module/utils/text.py
"""
Утилиты для работы с текстом
"""

import re
import unicodedata
from typing import List


# НОРМАЛИЗАЦИЯ ИМЁН
def normalize_dog_name(name: str) -> str:
    """
    Нормализует имя собаки в title.

    ПРИМЕР:
    "  all about orinoco  " → "All About Orinoco"
    """
    if not name:
        return ""
    return " ".join(name.split()).title()

def normalize_yo(s: str) -> str:
    return s.replace('ё', 'е').replace('Ё', 'Е')

def normalize_name_title_case(name: str) -> str:
    """
    Приводит имя к Title Case для поиска в BreedArchive.

    ПРИМЕРЫ:
    - "LODGEPOLES LIFE" → "Lodgepoles Life"
    - "lodgepoles life" → "Lodgepoles Life"
    """
    if not name:
        return ""
    return " ".join(w.capitalize() for w in name.strip().split())


# РАБОТА С ТИТУЛАМИ В ИМЕНАХ


# Полный список титульных приставок (используется при поиске в BA и нормализации)
TITLE_PREFIXES: List[str] = [
    'MULTI CH', 'GRAND CH', 'INT CH', 'EURO CH', 'WORLD CH',
    'AM CH', 'CAN CH', 'RUS CH', 'FCI CH',
    'BISS', 'BIS', 'BOB', 'CACIB', 'CAC',
    'GCH', 'GRCH', 'JCH', 'CH',
]

_TITLE_RE = re.compile(
    r'\b(' + '|'.join(re.escape(t) for t in TITLE_PREFIXES) + r')\b\.?',
    re.IGNORECASE,
)

# Паттерны для формата "CH.RUS", "JCH.RKF" (российские выставки)
_DOTTED_TITLE_RE = re.compile(
    r'\b(?:CH|JCH|GrCH|VCH|BCH)\.[A-Z]{2,4}\b',
    re.IGNORECASE,
)


def remove_titles_from_name(name: str) -> str:
    """
    Удаляет титульные приставки из имени собаки.

    Обрабатывает оба формата:
    - Пробельный:  "CH Lodgepole..."       → "Lodgepole..."
    - Точечный:    "CH.RUS ALL ABOUT..."   → "ALL ABOUT..."
    - Смешанный:   "JCH.RUS, CH.RKF FOXFIRE" → "FOXFIRE"

    ПРИМЕРЫ:
    - "CH.RUS ALL ABOUT ORINOCO"     → "ALL ABOUT ORINOCO"
    - "JCH.RUS, CH.RKF FOXFIRE"      → "FOXFIRE"
    - "MULTI CH Lodgepoles Life"     → "Lodgepoles Life"
    """
    if not name:
        return ""

    # Убираем точечные форматы (CH.RUS, JCH.RKF и т.д.)
    result = _DOTTED_TITLE_RE.sub('', name)

    # Убираем пробельные форматы из общего списка
    result = _TITLE_RE.sub('', result)

    # Чистим запятые и лишние пробелы
    result = result.replace(',', '').strip()
    return ' '.join(result.split())


# ПОЛ
def parse_sex(text: str) -> int:
    """
    Парсит пол из текста.

    ВОЗВРАЩАЕТ:
    - 1 = кобель (male)
    - 2 = сука (female)
    - 0 = неизвестно
    """
    if not text:
        return 0

    text = text.lower()

    if 'сука' in text or 'female' in text or 'bitch' in text:
        return 2
    if 'кобель' in text or 'male' in text or 'dog' in text:
        return 1

    return 0


# ОЧИСТКА ТЕКСТА
def clean_text(text: str) -> str:
    """
    Очищает текст от лишних символов.

    ПРИМЕРЫ:
    - "   Text  with\\n\\nnewlines   " → "Text with newlines"
    - "Text\\t\\twith\\ttabs"          → "Text with tabs"
    """
    if not text:
        return ""

    text = re.sub(r'[\n\r\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def color_stem(word: str) -> str:
    word = normalize_yo(word.strip('-').strip())
    if len(word) > 6:
        return word[:-2]
    if len(word) > 4:
        return word[:-1]
    return word

def build_color_filter(qs, color: str):
    from django.db.models import Q, Value, F
    from django.db.models.functions import Replace

    color = color.strip().lstrip('-').strip()
    if not color:
        return qs

    color_norm = normalize_yo(color)

    qs = qs.annotate(
        _color_norm=Replace(
            Replace(F('color'), Value('ё'), Value('е')),
            Value('Ё'), Value('Е'),
        )
    )

    stop_words = {'с', 'и', 'а', 'со'}
    parts = [
        p.strip() for p in re.split(r'[-\s]+', color_norm)
        if p.strip() and p.strip().lower() not in stop_words
    ]

    if len(parts) >= 2:
        stems = [color_stem(p) for p in parts if len(p) >= 3]
        q = Q()
        for stem in stems:
            q &= Q(_color_norm__icontains=stem)
        q |= Q(_color_norm__icontains=color_norm)
    else:
        q = Q(_color_norm__icontains=color_norm)

    return qs.filter(q)

# НОМЕР РОДОСЛОВНОЙ
def extract_registration_number(text: str) -> str:
    """
    Извлекает номер родословной из текста.

    ПРИМЕРЫ:
    - "РКФ 6145419"            → "РКФ 6145419"
    - "RKF 4832047 grey&white" → "RKF 4832047"
    """
    if not text:
        return ""

    match = re.search(r'(РКФ|RKF)\s+(\d+)', text, re.IGNORECASE)
    if match:
        return match.group(0).strip()

    return text.strip()


# ТРАНСЛИТЕРАЦИЯ
_RU_TO_EN: dict = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
    'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
    'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
    'э': 'e', 'ю': 'yu', 'я': 'ya',
}

# Длинные паттерны первыми — порядок важен
_EN_TO_RU: list = [
    ('sch', 'щ'), ('zh', 'ж'), ('ts', 'ц'), ('ch', 'ч'),
    ('sh', 'ш'), ('yu', 'ю'), ('ya', 'я'), ('yo', 'ё'),
    ('a', 'а'), ('b', 'б'), ('v', 'в'), ('g', 'г'),
    ('d', 'д'), ('e', 'е'), ('z', 'з'), ('i', 'и'),
    ('y', 'й'), ('k', 'к'), ('l', 'л'), ('m', 'м'),
    ('n', 'н'), ('o', 'о'), ('p', 'п'), ('r', 'р'),
    ('s', 'с'), ('t', 'т'), ('u', 'у'), ('f', 'ф'),
    ('h', 'х'),
]


def transliterate_ru_to_en(text: str) -> str:
    """
    Транслитерация RU → EN.

    ПРИМЕРЫ:
    - "Сибирский" → "Sibirskiy"
    """
    return ''.join(_RU_TO_EN.get(c.lower(), c) for c in text)


def transliterate_en_to_ru(text: str) -> str:
    """
    Транслитерация EN → RU.

    ПРИМЕРЫ:
    - "Sibirskiy" → "Сибирский"
    """
    result = text.lower()
    for en, ru in _EN_TO_RU:
        result = result.replace(en, ru)
    return result


def normalize_for_similarity(name: str) -> str:
    """
    Жёсткая нормализация ТОЛЬКО для нечёткого сравнения имён (не для хранения).
    Снимает титулы, регистр, апострофы/кавычки, диакритику; схлопывает разделители.
    'CH Pain Babe' / "Pain Babe" / 'Раин Babe' → 'pain babe'
    """
    if not name:
        return ""
    s = remove_titles_from_name(name)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    for ch in ("'", "\u2019", "\u2018", "`", "\u02bc", "\u00b4", '"', "\u201c", "\u201d"):
        s = s.replace(ch, "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())
