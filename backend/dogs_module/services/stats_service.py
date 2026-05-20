# dogs_module/services/stats_service.py
"""
Сервис популяционной аналитики.
Все запросы к БД только здесь — views и tasks не трогают модели напрямую.
"""

from __future__ import annotations
import logging
from django.db.models import Count, Avg, Q
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 60 * 6  # 6 часов
CACHE_KEY  = "stats:population:v1"


def get_population_stats() -> dict:
    """
    Главная функция — возвращает все статистики одним словарём.
    Результат кешируется на 6 часов.
    """
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    result = {
        "overview":      _get_overview(),
        "by_sex":        _get_by_sex(),
        "by_year":       _get_by_year(),
        "by_country":    _get_by_country(),
        "by_color":      _get_by_color(),
        "top_kennels":   _get_top_kennels(),
        "top_producers": _get_top_producers(),
        "coi_stats":     _get_coi_stats(),
        "coverage":      _get_coverage(),
    }

    cache.set(CACHE_KEY, result, CACHE_TTL)
    return result


def invalidate_stats_cache() -> None:
    cache.delete(CACHE_KEY)


# ── Детальные функции ─────────────────────────────────────────────────────────

def _get_overview() -> dict:
    from ..models import Dog
    qs = Dog.objects.using('dogs_db')
    return {
        "total":       qs.count(),
        "males":       qs.filter(sex=1).count(),
        "females":     qs.filter(sex=2).count(),
        "with_coi":    qs.filter(coi__isnull=False).count(),
        "with_photo":  qs.filter(photo_url__isnull=False).exclude(photo_url='').count(),
        "with_rating": qs.filter(rating__gt=0).count(),
    }


def _get_by_sex() -> list:
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .values('sex')
        .annotate(count=Count('id'))
        .order_by('sex')
    )
    labels = {0: "Не указан", 1: "Кобели", 2: "Суки"}
    return [
        {"label": labels.get(r['sex'], str(r['sex'])), "value": r['count']}
        for r in qs if r['sex'] in labels
    ]


def _get_by_year() -> list:
    """Регистрации по годам рождения (последние 30 лет)."""
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(year_of_birth__gte=1995, year_of_birth__lte=2025)
        .values('year_of_birth')
        .annotate(count=Count('id'))
        .order_by('year_of_birth')
    )
    return [{"year": r['year_of_birth'], "count": r['count']} for r in qs]


def _get_by_country(limit: int = 15) -> list:
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(land_of_birth__isnull=False)
        .exclude(land_of_birth='')
        .values('land_of_birth')
        .annotate(count=Count('id'))
        .order_by('-count')[:limit]
    )
    return [{"country": r['land_of_birth'], "count": r['count']} for r in qs]


def _get_by_color(limit: int = 12) -> list:
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(color__isnull=False)
        .exclude(color='')
        .values('color')
        .annotate(count=Count('id'))
        .order_by('-count')[:limit]
    )
    return [{"color": r['color'], "count": r['count']} for r in qs]


def _get_top_kennels(limit: int = 10) -> list:
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(kennel__isnull=False)
        .exclude(kennel='')
        .values('kennel')
        .annotate(count=Count('id'))
        .order_by('-count')[:limit]
    )
    return [{"kennel": r['kennel'], "count": r['count']} for r in qs]


def _get_top_producers(limit: int = 10) -> list:
    from ..models import Dog
    sires = (
        Dog.objects.using('dogs_db')
        .filter(sex=1)
        .annotate(offspring=Count('children_as_sire'))  # ← исправлено
        .filter(offspring__gt=0)
        .order_by('-offspring')[:limit]
        .values('id', 'registered_name', 'offspring')
    )
    return [
        {
            "id":    r['id'],
            "name":  r['registered_name'],
            "count": r['offspring'],
        }
        for r in sires
    ]

def _get_coi_stats() -> dict:
    """Статистика коэффициента инбридинга."""
    from ..models import Dog
    from django.db.models import Min, Max, StdDev
    qs = Dog.objects.using('dogs_db').filter(coi__isnull=False)

    agg = qs.aggregate(
        avg=Avg('coi'),
        min=Min('coi'),
        max=Max('coi'),
    )

    # Распределение по диапазонам
    buckets = [
        {"label": "0%",      "range": (0, 0.001),  "count": 0},
        {"label": "0–2%",    "range": (0.001, 2),   "count": 0},
        {"label": "2–5%",    "range": (2, 5),       "count": 0},
        {"label": "5–10%",   "range": (5, 10),      "count": 0},
        {"label": "10–20%",  "range": (10, 20),     "count": 0},
        {"label": ">20%",    "range": (20, 100),    "count": 0},
    ]
    for b in buckets:
        lo, hi = b['range']
        b['count'] = qs.filter(coi__gte=lo, coi__lt=hi).count()

    return {
        "avg": round(agg['avg'] or 0, 2),
        "min": round(agg['min'] or 0, 2),
        "max": round(agg['max'] or 0, 2),
        "total": qs.count(),
        "buckets": buckets,
    }


def _get_coverage() -> dict:
    """Покрытие данными."""
    from ..models import Dog
    total = Dog.objects.using('dogs_db').count()
    if total == 0:
        return {}

    def pct(n): return round(n / total * 100, 1)

    with_coi = Dog.objects.using('dogs_db').filter(coi__isnull=False).count()
    with_color = Dog.objects.using('dogs_db').exclude(color='').filter(color__isnull=False).count()
    with_origin = Dog.objects.using('dogs_db').exclude(land_of_birth='').filter(land_of_birth__isnull=False).count()
    with_photo = Dog.objects.using('dogs_db').exclude(photo_url='').filter(photo_url__isnull=False).count()
    with_reg = Dog.objects.using('dogs_db').exclude(registration_number='').filter(registration_number__isnull=False).count()

    return {
        "coi":    {"count": with_coi,    "pct": pct(with_coi)},
        "color":  {"count": with_color,  "pct": pct(with_color)},
        "origin": {"count": with_origin, "pct": pct(with_origin)},
        "photo":  {"count": with_photo,  "pct": pct(with_photo)},
        "reg":    {"count": with_reg,    "pct": pct(with_reg)},
    }
