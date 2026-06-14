# dogs_module/config/domain.py
"""
Доменная конфигурация породы Сибирский Хаски:
очки за титулы, множители выставок, релевантные тесты OFA, фильтры выставок.
"""

from ..constants.show_types import ShowType

# Фильтры выставок Zooportal (что именно тянем)
ZOOPORTAL_SHOW_THEMES = 1209  # выставки
ZOOPORTAL_SHOW_FCI_5_GROUP_ID = 32499  # FCI Группа 5
ZOOPORTAL_SHOW_SH_BREED_ID = 6551  # Сибирский Хаски

# Рейтинговые очки за титулы
TITLE_POINTS = {
    # Международные
    'BIS': 20,
    'BOB': 10,
    'CACIB': 8,
    'RCACIB': 5,
    # Национальные
    'CAC': 5,
    'RCAC': 3,
    'CW': 3,
    'ЧФ': 5,  # Чемпион ФЦИ
    'СС': 3,  # Сертификат соответствия
    'БОП': 10,  # Лучший из породы (русск.)
    # Юниорские
    'JCAC': 4,
    'R.JCAC': 2,
    'ЮКЧК': 3,
    'ЮЧРКФ': 5,
    'ЮСС': 2,
    'BOB JUNIOR': 8,
    'ЛЮ': 5,  # Лучший юниор
    # Ветеранские
    'BOV': 8,  # Лучший ветеран
    # Классные
    'ОТЛ': 1,  # Отлично (без места)
}

SHOW_MULTIPLIERS = {
    ShowType.PK: 2.0,
    ShowType.KCHK: 1.0,
    ShowType.SPECIALITY: 0.5,
    ShowType.SPORT: 1.0,
    ShowType.WORLD: 1.0,
    ShowType.OTHER: 0.0,
}

# Алиас: используется в show_service для явной проверки
SHOW_TYPE_OTHER = ShowType.OTHER

BOB_TITLES = {'ЛПП', 'BOB', 'ВОВ'}

# Релевантные тесты OFA для породы
HUSKY_REGISTRIES = [
    "HIPS",
    "ELBOW",
    "EYES",
    "CERF",
    "SIBERIAN HUSKY OPTH. REGISTRY",
    "DEGENERATIVE MYELOPATHY",
    "PROGRESSIVE RETINAL ATROPHY",
    "PRA - CONE ROD DYSTROPHY 3",
    "EARLY ONSET PRA",
    "PRIMARY LENS LUXATION",
    "JUVENILE LARYNGEAL PARALYSIS & POLYNEUROPATHY (LPP)",
    "BASIC CARDIAC",
    "ADVANCED CARDIAC",
    "CONGENITAL CARDIAC",
    "THYROID",
    "PATELLA",
    "CANINE HEALTH",
    "SIBERIAN HUSKY POLYNEUROPATHY",
    "SIBERIAN HUSKY SHAKING PUPPY SYNDROME",
]
