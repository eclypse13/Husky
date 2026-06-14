# dogs_module/repositories/show_repository.py
"""
Доступ к данным ShowEvent и ShowResult.
"""

import logging

logger = logging.getLogger(__name__)


# ShowEvent

def search_events(
        year: str = None,
        city: str = None,
        show_type: str = None,
        has_results: bool = False,
):
    """
    QuerySet ShowEvent с опциональными фильтрами.
    Используется ShowEventViewSet.get_queryset.
    """
    from ..models import ShowEvent
    qs = ShowEvent.objects.using('dogs_db').order_by('-event_date')
    if year:
        qs = qs.filter(event_date__year=year)
    if city:
        qs = qs.filter(city__icontains=city)
    if show_type:
        qs = qs.filter(show_type=show_type)
    if has_results:
        qs = qs.filter(results_parsed_at__isnull=False)
    return qs


def get_event_by_show_id(show_id: str):
    """ShowEvent по zooportal_show_id или None."""
    from ..models import ShowEvent
    return ShowEvent.objects.using('dogs_db').filter(zooportal_show_id=show_id).first()


def get_or_create_event(show_id: str, defaults: dict):
    """get_or_create ShowEvent по zooportal_show_id. → (event, created)."""
    from ..models import ShowEvent
    return ShowEvent.objects.using('dogs_db').get_or_create(
        zooportal_show_id=show_id,
        defaults=defaults,
    )


def upsert_event(show_id: str, defaults: dict):
    """update_or_create ShowEvent. → (event, created)."""
    from ..models import ShowEvent
    return ShowEvent.objects.using('dogs_db').update_or_create(
        zooportal_show_id=show_id,
        defaults=defaults,
    )


def mark_event_parsed(event_pk, parsed_at) -> None:
    from ..models import ShowEvent
    ShowEvent.objects.using('dogs_db').filter(pk=event_pk).update(
        results_parsed_at=parsed_at
    )


def get_events_in_range(date_from, date_to, only_without_results: bool = False) -> list:
    """ShowEvent за период; опционально только без распарсенных результатов."""
    from ..models import ShowEvent
    qs = (
        ShowEvent.objects.using('dogs_db')
        .filter(event_date__gte=date_from, event_date__lte=date_to)
        .order_by('event_date')
    )
    if only_without_results:
        qs = qs.filter(results_parsed_at__isnull=True)
    return list(qs)


# ShowResult

def upsert_result(event, dog, defaults: dict) -> None:
    """update_or_create ShowResult по (event, dog) — один результат на собаку."""
    from ..models import ShowResult
    ShowResult.objects.using('dogs_db').update_or_create(
        event=event,
        dog=dog,
        defaults=defaults,
    )


def sum_points_for_dog(dog_id: int, date_from, date_to) -> int:
    """Сумма rating_points собаки за период."""
    from ..models import ShowResult
    from django.db.models import Sum
    return (
            ShowResult.objects.using('dogs_db')
            .filter(
                dog_id=dog_id,
                event__event_date__gte=date_from,
                event__event_date__lte=date_to,
            )
            .aggregate(total=Sum('rating_points'))['total'] or 0
    )


def get_results_for_dog(dog_id: int, date_from=None, date_to=None):
    """ShowResult queryset для одной собаки с опциональным фильтром по дате."""
    from ..models import ShowResult
    qs = (
        ShowResult.objects.using('dogs_db')
        .filter(dog_id=dog_id)
        .select_related('event')
    )
    if date_from:
        qs = qs.filter(event__event_date__gte=date_from)
    if date_to:
        qs = qs.filter(event__event_date__lte=date_to)
    return qs.order_by('-event__event_date')


def get_results_for_event(event):
    """Все ShowResult для выставки с prefetch Dog."""
    from ..models import ShowResult
    return (
        ShowResult.objects.using('dogs_db')
        .filter(event=event)
        .select_related('dog')
    )


def sum_points_grouped(date_from, date_to, nomination: str = None, limit: int = None) -> list:
    """[{dog_id, total}] — суммы очков по собакам за период (опц. по номинации)."""
    from ..models import ShowResult
    from django.db.models import Sum
    qs = (
        ShowResult.objects.using('dogs_db')
        .filter(
            dog__isnull=False,
            event__event_date__gte=date_from,
            event__event_date__lte=date_to,
        )
    )
    if nomination is not None:
        qs = qs.filter(nomination=nomination)

    qs = qs.values('dog_id').annotate(total=Sum('rating_points'))
    if nomination is not None:
        qs = qs.filter(total__gt=0).order_by('-total')
    if limit is not None:
        qs = qs[:limit]
    return list(qs)



def upsert_yearly_rating(dog_id: int, year: int, nomination: str, points: int) -> None:
    """Сохраняет или обновляет рейтинг собаки за год/номинацию."""
    from ..models import ShowYearlyRating
    ShowYearlyRating.objects.using('dogs_db').update_or_create(
        dog_id=dog_id,
        year=year,
        nomination=nomination,
        defaults={'points': points},
    )

def get_yearly_leaderboard(
        year: int,
        nomination: str = 'main',
        limit: int = 50,
) -> list:
    """
    Быстрый leaderboard из денормализованной таблицы.
    Возвращает [{'dog_id': int, 'points': int}].
    """
    from ..models import ShowYearlyRating
    return list(
        ShowYearlyRating.objects.using('dogs_db')
        .filter(year=year, nomination=nomination, points__gt=0)
        .order_by('-points')
        .values('dog_id', 'points')[:limit]
    )


def reset_yearly_ratings_except(year: int, nomination: str, dog_ids: list) -> None:
    """Обнуляет рейтинг за год для тех кто не участвовал."""
    from ..models import ShowYearlyRating
    ShowYearlyRating.objects.using('dogs_db').filter(
        year=year, nomination=nomination
    ).exclude(dog_id__in=dog_ids).update(points=0)
