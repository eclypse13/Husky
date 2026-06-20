"""
Сервис популяционной аналитики.
"""

from __future__ import annotations
import logging
from django.core.cache import cache

from ..repositories import stats_repository as repo

logger = logging.getLogger(__name__)

CACHE_TTL = 3600 * 6  # 6 часов
CACHE_KEY = "stats:population:v1"

# Диапазон лет для распределения по году рождения
YEAR_FROM = 1960


def _current_year() -> int:
    from datetime import date
    return date.today().year


def _year_to() -> int:
    return _current_year()


# Все статистики одним словарём
def get_population_stats() -> dict:
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    result = {
        "overview": _get_overview(),
        "by_sex": _get_by_sex(),
        "by_year": _get_by_year(),
        "by_country": _get_by_country(),
        "by_color": _get_by_color(),
        "top_kennels": _get_top_kennels(),
        "top_producers": _get_top_producers(),
        "coi_stats": _get_coi_stats(),
        "coverage": _get_coverage(),
    }

    cache.set(CACHE_KEY, result, CACHE_TTL)
    return result


def invalidate_stats_cache() -> None:
    cache.delete(CACHE_KEY)


# Интерпретация сырых данных репозитория
def _get_overview() -> dict:
    return repo.get_overview_counts()


def _get_by_sex() -> list:
    labels = {0: "Не указан", 1: "Кобели", 2: "Суки"}
    rows = repo.count_grouped_by('sex', exclude_empty=False)
    return [
        {"label": labels[r['sex']], "value": r['count']}
        for r in rows if r['sex'] in labels
    ]


def _get_by_year() -> list:
    rows = repo.count_by_year_range(YEAR_FROM, _year_to())
    return [{"year": r['year_of_birth'], "count": r['count']} for r in rows]


def _get_by_country(limit: int = 15) -> list:
    rows = repo.count_grouped_by('land_of_birth', limit=limit)
    return [{"country": r['land_of_birth'], "count": r['count']} for r in rows]


def _get_by_color(limit: int = 12) -> list:
    rows = repo.count_grouped_by('color', limit=limit)
    return [{"color": r['color'], "count": r['count']} for r in rows]


def _get_top_kennels(limit: int = 10) -> list:
    rows = repo.count_grouped_by('kennel', limit=limit)
    return [{"kennel": r['kennel'], "count": r['count']} for r in rows]


def _get_top_producers(limit: int = 10) -> list:
    rows = repo.get_top_producers(limit)
    return [
        {"id": r['id'], "name": r['registered_name'], "count": r['offspring']}
        for r in rows
    ]


def _get_coi_stats() -> dict:
    agg = repo.get_coi_aggregates()

    buckets = [
        {"label": "0%", "range": (0, 0.001)},
        {"label": "0–2%", "range": (0.001, 2)},
        {"label": "2–5%", "range": (2, 5)},
        {"label": "5–10%", "range": (5, 10)},
        {"label": "10–20%", "range": (10, 20)},
        {"label": ">20%", "range": (20, 100)},
    ]

    distribution = repo.get_coi_distribution(buckets)
    for b in buckets:
        b['count'] = distribution.get(b['label'], 0)

    return {
        "avg": round(agg['avg'] or 0, 2),
        "min": round(agg['min'] or 0, 2),
        "max": round(agg['max'] or 0, 2),
        "total": agg['total'],
        "buckets": buckets,
    }


def _get_coverage() -> dict:
    total = repo.count_total()
    if total == 0:
        return {}

    counts = repo.get_coverage_counts()

    def pct(n):
        return round(n / total * 100, 1)

    return {
        key: {"count": n, "pct": pct(n)}
        for key, n in counts.items()
    }
