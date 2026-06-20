"""
Утилиты для работы с текстом
"""

import re
import unicodedata
from typing import List


# Нормализует имя собаки в title
def normalize_dog_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(name.split()).title()


def normalize_yo(s: str) -> str:
    return s.replace('ё', 'е').replace('Ё', 'Е')


# Приводит имя к Title Case для поиска в BreedArchive
def normalize_name_title_case(name: str) -> str:
    if not name:
        return ""
    return " ".join(w.capitalize() for w in name.strip().split())


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


# Удаляет титульные приставки из имени собаки
def remove_titles_from_name(name: str) -> str:
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
    return ''.join(_RU_TO_EN.get(c.lower(), c) for c in text)


def transliterate_en_to_ru(text: str) -> str:
    result = text.lower()
    for en, ru in _EN_TO_RU:
        result = result.replace(en, ru)
    return result


# Жёсткая нормализация ТОЛЬКО для нечёткого сравнения имён
def normalize_for_similarity(name: str) -> str:
    if not name:
        return ""
    s = remove_titles_from_name(name)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    for ch in ("'", "\u2019", "\u2018", "`", "\u02bc", "\u00b4", '"', "\u201c", "\u201d"):
        s = s.replace(ch, "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())
