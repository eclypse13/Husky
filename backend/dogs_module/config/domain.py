"""
Доменная конфигурация породы Сибирский Хаски.
"""

from ..constants.show_types import ShowType

# Фильтры выставок Zooportal (что именно тянем)
ZOOPORTAL_SHOW_THEMES = 1209  # выставки
ZOOPORTAL_SHOW_FCI_5_GROUP_ID = 32499  # FCI Группа 5
ZOOPORTAL_SHOW_SH_BREED_ID = 6551  # Сибирский Хаски

# Рейтинговые очки за титулы.
TITLE_POINTS = {
    'ПК': 15,  # титул, полученный на монопородной выставке ранга ПК
    'КЧК': 10,  # кандидат в чемпионы НКП
    'ЮКЧК': 10,  # кандидат в юные чемпионы клуба
    'ВКЧК': 10,  # кандидат в ветераны-чемпионы клуба
    'CW': 12,  # чемпион НКП (класс ЧНКП)
    'СС': 4,  # сертификат соответствия
    'ЮСС': 4,  # сертификат соответствия, класс юниоров
    'ВСС': 4,  # сертификат соответствия, класс ветеранов
    'ЮПК': 15,  # титул юниора на выставке ранга ПК
    'ВПК': 15,  # титул ветерана на выставке ранга ПК
    'ЛПП': 20,  # лучший представитель породы
    'BOB': 20,  # синоним ЛПП (лат., Best of Breed)
    'ВОВ': 20,  # синоним ЛПП, используется в документе наравне с ЛПП/BOB

    'ЧЕМПИОН РОССИИ': 25,
    'ПОБЕДИТЕЛЬ КУБКА РОССИИ': 20,
    'ЧЕМПИОН РКФ': 15,
    'CACT': 10,
    'CACTBR': 5,
    'ВРЕМЕННЫЙ СЕРТИФИКАТ': 2,

    'JWW': 25,
    'WW': 25,
    'VWW': 25,
    'JEW': 20,
    'EW': 20,
    'VEW': 20,
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
SPORT_TITLES = {
    'ЧЕМПИОН РОССИИ', 'ПОБЕДИТЕЛЬ КУБКА РОССИИ', 'ЧЕМПИОН РКФ',
    'CACT', 'CACTBR', 'ВРЕМЕННЫЙ СЕРТИФИКАТ',
}

ALLOWED_TITLES_BY_SHOW_TYPE = {
    ShowType.KCHK: {'ЮКЧК', 'ЮСС', 'ВКЧК', 'ВСС', 'КЧК', 'CW', 'СС', 'ЛПП', 'BOB', 'ВОВ'},
    ShowType.SPECIALITY: {'ЮКЧК', 'ЮСС', 'ВКЧК', 'ВСС', 'КЧК', 'СС', 'ЛПП', 'BOB', 'ВОВ'},
    ShowType.PK: {'ПК', 'ЮПК', 'ВПК', 'КЧК', 'ЮКЧК', 'ВКЧК', 'CW', 'СС', 'ЮСС', 'ВСС', 'ЛПП', 'BOB', 'ВОВ'},
    ShowType.SPORT: {'ЧЕМПИОН РОССИИ', 'ПОБЕДИТЕЛЬ КУБКА РОССИИ', 'ЧЕМПИОН РКФ', 'CACT', 'CACTBR',
                     'ВРЕМЕННЫЙ СЕРТИФИКАТ'},
    ShowType.WORLD: {'JWW', 'WW', 'VWW', 'JEW', 'EW', 'VEW'},
}

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
