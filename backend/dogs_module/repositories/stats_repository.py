"""
Агрегатные выборки для популяционной статистики.
"""

import logging

logger = logging.getLogger(__name__)


def count_total() -> int:
    from ..models import Dog
    return Dog.objects.using('dogs_db').count()


def get_overview_counts() -> dict:
    from ..models import Dog
    qs = Dog.objects.using('dogs_db')
    return {
        "total": qs.count(),
        "males": qs.filter(sex=1).count(),
        "females": qs.filter(sex=2).count(),
        "with_coi": qs.filter(coi__isnull=False).count(),
        "with_photo": qs.filter(photo_url__isnull=False).exclude(photo_url='').count(),
        "with_rating": qs.filter(rating__gt=0).count(),
    }


def count_grouped_by(field: str, limit: int = None, exclude_empty: bool = True) -> list:
    from django.db.models import Count
    from ..models import Dog

    qs = Dog.objects.using('dogs_db')
    if exclude_empty:
        qs = qs.filter(**{f"{field}__isnull": False}).exclude(**{field: ''})

    qs = qs.values(field).annotate(count=Count('id'))
    qs = qs.order_by('-count') if limit else qs.order_by(field)
    if limit:
        qs = qs[:limit]
    return list(qs)


# Регистрации по годам рождения в диапазоне
def count_by_year_range(year_from: int, year_to: int) -> list:
    from django.db.models import Count
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(year_of_birth__gte=year_from, year_of_birth__lte=year_to)
        .values('year_of_birth')
        .annotate(count=Count('id'))
        .order_by('year_of_birth')
    )
    return list(qs)


# Топ кобелей по числу потомков
def get_top_producers(limit: int = 10) -> list:
    from django.db.models import Count
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(sex=1)
        .annotate(offspring=Count('children_as_sire'))
        .filter(offspring__gt=0)
        .values('id', 'registered_name', 'offspring')  # values ДО среза
        .order_by('-offspring')[:limit]
    )
    return list(qs)


# avg/min/max + total по собакам с непустым COI
def get_coi_aggregates() -> dict:
    from django.db.models import Avg, Min, Max
    from ..models import Dog
    qs = Dog.objects.using('dogs_db').filter(coi__isnull=False)
    agg = qs.aggregate(avg=Avg('coi'), min=Min('coi'), max=Max('coi'))
    agg['total'] = qs.count()
    return agg


def count_coi_in_range(lo: float, hi: float) -> int:
    from ..models import Dog
    return (
        Dog.objects.using('dogs_db')
        .filter(coi__isnull=False, coi__gte=lo, coi__lt=hi)
        .count()
    )


# Принимает список бакетов с полем range, возвращает label: count для каждого бакета
def get_coi_distribution(buckets: list) -> dict:
    return {
        b['label']: count_coi_in_range(b['range'][0], b['range'][1])
        for b in buckets
    }


# Сколько собак имеют непустое значение по полю
def get_coverage_counts() -> dict:
    from ..models import Dog
    qs = Dog.objects.using('dogs_db')

    def _non_empty(field: str) -> int:
        return qs.filter(**{f"{field}__isnull": False}).exclude(**{field: ''}).count()

    return {
        "coi": qs.filter(coi__isnull=False).count(),
        "color": _non_empty('color'),
        "origin": _non_empty('land_of_birth'),
        "photo": _non_empty('photo_url'),
        "reg": _non_empty('registration_number'),
    }
