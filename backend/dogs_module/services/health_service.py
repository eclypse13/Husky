# dogs_module/services/health_service.py
"""
Архив OFA медицинских тестов всех собак.
Показать все записи → отфильтровать по имени собаки / типу теста / результату.
"""

import logging
from django.core.cache import cache
from ..domain.health_codes import classify_registry, score_conclusion
from ..repositories import dog_repository as dog_repo

logger = logging.getLogger(__name__)

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100

_STATS_CACHE_KEY = "health:stats:v1"
_REGISTRIES_CACHE_KEY = "health:registries:v1"
_CACHE_TTL = 1 * 1 * 3600  # 1 час


def search_health_records(
        q: str = "",
        registry: str = "",
        conclusion: str = "",
        page: int = 1,
        per_page: int = DEFAULT_PER_PAGE,
) -> dict:
    """
    Все OFA-записи с фильтрами и пагинацией.
    q — поиск по имени собаки
    registry — тип теста (HIPS, EYES, ...)
    conclusion — результат (EXCELLENT, NORMAL, ...)
    """
    from ..models import MedicalRecord

    per_page = min(max(1, per_page), MAX_PER_PAGE)
    page = max(1, page)
    offset = (page - 1) * per_page

    qs = MedicalRecord.objects.using('dogs_db').filter(source='ofa')

    if registry:
        qs = qs.filter(registry__iexact=registry)

    if conclusion:
        qs = qs.filter(conclusion__icontains=conclusion)

    if q:
        dog_ids = dog_repo.search_ids_by_name(q, limit=500)
        if not dog_ids:
            return {"results": [], "total": 0, "page": page, "per_page": per_page, "pages": 0}
        qs = qs.filter(dog_id__in=dog_ids)

    qs = qs.select_related('dog').order_by('-test_date')
    total = qs.count()
    rows = qs[offset: offset + per_page]

    results = []
    for rec in rows:
        dog = rec.dog
        group = classify_registry(rec.registry)
        results.append({
            "id": rec.id,
            "dog_id": rec.dog_id,
            "dog_name": dog.registered_name if dog else None,
            "dog_photo": (dog.photo_yadisk_url or dog.photo_url) if dog else None,
            "ofa_number": rec.ofa_number,
            "registry": rec.registry,
            "group": group,
            "conclusion": rec.conclusion,
            "score": score_conclusion(group, rec.conclusion) if group else None,
            "test_date": rec.test_date,
            "age_in_months": rec.age_in_months,
        })

    return {
        "results": results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
    }


def get_available_registries() -> list:
    """Какие типы тестов есть в БД — для фильтра."""
    cached = cache.get(_REGISTRIES_CACHE_KEY)
    if cached:
        return cached

    from ..models import MedicalRecord
    from django.db.models import Count

    rows = (
        MedicalRecord.objects.using('dogs_db')
        .filter(source='ofa')
        .values('registry')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    result = [r['registry'] for r in rows if r['registry']]

    cache.set(_REGISTRIES_CACHE_KEY, result, _CACHE_TTL)
    return result


def get_health_stats() -> dict:
    """Сводная статистика: сколько тестов, сколько собак, процент нормальных по каждому тесту."""
    cached = cache.get(_STATS_CACHE_KEY)
    if cached:
        return cached

    from ..models import MedicalRecord
    from django.db.models import Count

    rows = (
        MedicalRecord.objects.using('dogs_db')
        .filter(source='ofa')
        .values('registry', 'conclusion')
        .annotate(count=Count('id'))
    )

    total_records = 0
    by_group: dict = {}

    for row in rows:
        count = row['count']
        total_records += count
        group = classify_registry(row['registry'])
        if not group:
            continue
        if group not in by_group:
            by_group[group] = {'total': 0, 'normal': 0}
        by_group[group]['total'] += count
        if score_conclusion(group, row['conclusion']) == 0:
            by_group[group]['normal'] += count

    for data in by_group.values():
        t = data['total']
        data['pct_normal'] = round(data['normal'] / t * 100, 1) if t else 0.0

    dogs_tested = (
        MedicalRecord.objects.using('dogs_db')
        .filter(source='ofa').values('dog_id').distinct().count()
    )

    result = {"total_records": total_records, "dogs_tested": dogs_tested, "by_group": by_group}
    cache.set(_STATS_CACHE_KEY, result, _CACHE_TTL)
    return result


def get_dog_health_records(dog_id) -> dict:
    """Все тесты одной собаки."""
    from ..models import MedicalRecord

    try:
        dog_id = int(dog_id)
    except (ValueError, TypeError):
        raise ValueError(f"Неверный dog_id: {dog_id!r}")

    qs = (
        MedicalRecord.objects.using('dogs_db')
        .filter(dog_id=dog_id, source='ofa')
        .order_by('-test_date', '-report_date')
    )

    records = []
    for rec in qs:
        group = classify_registry(rec.registry)
        records.append({
            "id": rec.id,
            "ofa_number": rec.ofa_number,
            "registry": rec.registry,
            "group": group,
            "conclusion": rec.conclusion,
            "score": score_conclusion(group, rec.conclusion) if group else None,
            "test_date": rec.test_date,
            "report_date": getattr(rec, 'report_date', None),
            "age_in_months": rec.age_in_months,
        })

    return {"dog_id": dog_id, "records": records}
