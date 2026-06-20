"""
Типы выставок.
"""
class ShowType:
    PK = 'pk'  # Национальный клуб породы, монопородная
    KCHK = 'kchk'  # Ранга КЧК
    SPECIALITY = 'speciality'  # Специализированная
    SPORT = 'sport'  # Соревнования / испытания
    WORLD = 'world'  # World Dog Show, Euro Dog Show
    OTHER = 'other'  # Всё остальное (очки не начисляются)

    ALL = (PK, KCHK, SPECIALITY, SPORT, WORLD, OTHER)
