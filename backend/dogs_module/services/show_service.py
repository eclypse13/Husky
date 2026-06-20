# dogs_module/services/show_service.py
"""
Сервис для работы с выставочными данными.
"""

import re
import logging
from datetime import datetime, date

from ..repositories import dog_repository as dog_repo  # get_by_zooportal_id, set_rating, reset_ratings_except
from . import pending_results_cache as pending_cache
from ..constants.show_types import ShowType
from ..repositories import show_repository as show_repo
from ..repositories import dog_repository as dog_repo
from ..config import TITLE_POINTS, SHOW_MULTIPLIERS, BOB_TITLES

logger = logging.getLogger(__name__)

# алиас для обратной совместимости
SHOW_TYPE_OTHER = ShowType.OTHER

# Типы выставок
_PK_KEYWORDS = ['ранга пк', 'нкп', 'национальн', 'монопородн', 'племенной смотр']
_SPECIALITY_KEYWORDS = ['специализирован', 'speciality', 'specialty']
_KCHK_KEYWORDS = ['ранга кчк', 'кчк в каждом']
_SPORT_KEYWORDS = ['соревнован', 'испытан', 'кубок', 'чемпионат']
_WORLD_KEYWORDS = ['world dog show', 'euro dog show']
_EXCLUDE_RANKS = ['cac', 'сас', 'cacib', 'сасиб']

HERO_FALLBACK_NAME = "Chudni Medvezhonok Gold Sensation"

def detect_show_type(title: str, rank: str = '') -> str:
    text = (title + ' ' + (rank or '')).lower()
    for kw in _WORLD_KEYWORDS:
        if kw in text: return ShowType.WORLD
    for kw in _PK_KEYWORDS:
        if kw in text: return ShowType.PK
    for kw in _SPECIALITY_KEYWORDS:
        if kw in text: return ShowType.SPECIALITY
    for kw in _KCHK_KEYWORDS:
        if kw in text: return ShowType.KCHK
    for kw in _SPORT_KEYWORDS:
        if kw in text: return ShowType.SPORT
    for ex in _EXCLUDE_RANKS:
        if ex in text: return ShowType.OTHER
    return ShowType.OTHER


# Подсчёт очков
def calc_base_points(titles_won: str) -> tuple[int, bool]:
    if not titles_won:
        return 0, False
    total = 0
    is_bob = False
    for part in re.split(r'[,;/]', titles_won):
        key = part.strip().upper()
        pts = TITLE_POINTS.get(key, 0)
        if pts:
            total += pts
            if key in BOB_TITLES:
                is_bob = True
    return total, is_bob


def calc_result_points(
        titles_won: str,
        show_type: str,
        catalog_count: int = 0,
        bonus_points: int = 0,
) -> int:
    if show_type == ShowType.OTHER:
        return 0
    multiplier = SHOW_MULTIPLIERS.get(show_type, 1.0)
    base_pts, is_bob = calc_base_points(titles_won)
    total = int(base_pts * multiplier)
    total += catalog_count if is_bob else 0
    total += bonus_points
    return total


def detect_nomination(show_class: str, titles_won: str = '') -> str:
    combined = ((show_class or '') + ' ' + (titles_won or '')).lower()
    if any(w in combined for w in ['юниор', 'junior', 'юкчк', 'юсс', 'юпк']):
        return 'junior'
    if any(w in combined for w in ['ветеран', 'veteran', 'вкчк', 'всс', 'впк']):
        return 'veteran'
    if any(w in combined for w in ['рабочий', 'working', 'cact']):
        return 'working'
    return 'main'


# Расчётный год
def get_rating_year(for_date: date = None) -> int:
    d = for_date or date.today()
    return d.year + 1 if d.month == 12 else d.year


def get_rating_period(rating_year: int) -> tuple[date, date]:
    return date(rating_year - 1, 12, 1), date(rating_year, 11, 30)


# Сохранение мероприятия
def save_show_event(event_data: dict):
    show_id = event_data.get('zooportal_show_id')
    if not show_id:
        logger.error('save_show_event: нет zooportal_show_id')
        return None

    title = event_data.get('title') or ''
    rank = event_data.get('rank') or ''
    show_type = detect_show_type(title, rank)
    multiplier = SHOW_MULTIPLIERS.get(show_type, 0.0)

    event_date = None
    raw_date = event_data.get('event_date')
    if raw_date:
        try:
            event_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            pass

    obj, created = show_repo.upsert_event(show_id, {
        'title': title[:1000],
        'event_date': event_date,
        'organizer': (event_data.get('organizer') or '')[:500],
        'rank': rank[:255],
        'show_type': show_type,
        'multiplier': multiplier,
        'city': (event_data.get('city') or '')[:255],
        'address': (event_data.get('address') or '')[:1000],
        'judges': (event_data.get('judges') or '')[:2000],
        'status': (event_data.get('status') or '')[:100],
    })
    logger.info(
        f"ShowEvent {'создан' if created else 'обновлён'}: "
        f"id={show_id} type={show_type} ×{multiplier} — {title[:60]}"
    )
    return obj


# Сохранение результатов
def save_show_results(event, results: list) -> tuple[int, int, int]:
    saved = 0
    failed = 0
    to_pend = []

    for rec in results:
        zoo_id = rec.get('zooportal_dog_id')
        if not zoo_id:
            failed += 1
            continue

        dog = dog_repo.get_by_zooportal_id(zoo_id)

        if dog is None:
            to_pend.append(rec)
            continue

        try:
            _save_single_result(event, dog, rec)
            saved += 1
            _refresh_dog_rating(dog.id)
        except Exception as e:
            failed += 1
            logger.warning(f"save_show_results: ошибка zoo_id={zoo_id}: {e}")

    if to_pend:
        pending_cache.store(event.zooportal_show_id, to_pend)

    logger.info(
        f"ShowResults event={event.zooportal_show_id}: "
        f"saved={saved}, pending={len(to_pend)}, failed={failed}"
    )
    return saved, failed, len(to_pend)


def _save_single_result(event, dog, rec: dict) -> None:
    """Сохраняет одну запись ShowResult. dog обязан быть не None."""
    titles_won = rec.get('titles_won', '') or ''
    show_class = rec.get('show_class', '') or ''
    catalog_count = rec.get('catalog_count') or 0
    bonus_points = rec.get('bonus_points') or 0
    points = calc_result_points(titles_won, event.show_type, catalog_count, bonus_points)
    nomination = detect_nomination(show_class, titles_won)

    place = rec.get('place')
    if place is not None:
        try:
            place = int(place)
        except (ValueError, TypeError):
            place = None

    show_repo.upsert_result(event, dog, {
        'catalog_number': rec.get('catalog_number'),
        'show_class': show_class[:100],
        'grade': (rec.get('grade') or '')[:50],
        'place': place,
        'titles_won': titles_won[:500],
        'catalog_count': catalog_count,
        'bonus_points': bonus_points,
        'rating_points': points,
        'nomination': nomination,
    })


# Ожидающие результаты
def get_all_pending_show_ids() -> list:
    """Все show_id у которых есть ожидающие результаты в Redis."""
    return pending_cache.all_show_ids()


# Пытается залинковать ожидающие результаты для одной выставки.
def process_pending_results(show_id: str) -> dict:
    pending = pending_cache.retrieve(show_id)
    if not pending:
        return {'saved': 0, 'still_pending': 0}

    event = show_repo.get_event_by_show_id(show_id)
    if not event:
        logger.warning(f"process_pending_results: выставка {show_id} не найдена")
        return {'saved': 0, 'still_pending': len(pending)}

    saved = 0
    still_pending = []

    for rec in pending:
        zoo_id = rec.get('zooportal_dog_id')
        dog = dog_repo.get_by_zooportal_id(zoo_id) if zoo_id else None

        if dog is None:
            still_pending.append(rec)
            continue

        try:
            _save_single_result(event, dog, rec)
            saved += 1
            _refresh_dog_rating(dog.id)
        except Exception as e:
            logger.warning(f"process_pending_results: ошибка zoo_id={zoo_id}: {e}")
            still_pending.append(rec)

    if still_pending:
        pending_cache.save(show_id, still_pending)
    else:
        pending_cache.clear(show_id)

    logger.info(
        f"process_pending_results show_id={show_id}: "
        f"saved={saved}, still_pending={len(still_pending)}"
    )
    return {'saved': saved, 'still_pending': len(still_pending)}


# Обрабатывает ожидающие результаты для всех выставок.
def process_all_pending_results() -> dict:
    show_ids = pending_cache.all_show_ids()
    total_saved = 0
    total_left = 0

    for show_id in show_ids:
        result = process_pending_results(show_id)
        total_saved += result['saved']
        total_left += result['still_pending']

    return {
        'saved': total_saved,
        'still_pending': total_left,
        'shows_processed': len(show_ids),
    }


# Рейтинг
def recalculate_dog_rating(dog_id: int, rating_year: int = None) -> int:
    year = rating_year or get_rating_year()
    date_from, date_to = get_rating_period(year)
    total = show_repo.sum_points_for_dog(dog_id, date_from, date_to)
    dog_repo.set_rating(dog_id, total)
    return total


# Пересчитывает рейтинг за год
def recalculate_all_ratings(rating_year: int = None) -> dict:
    year = rating_year or get_rating_year()
    date_from, date_to = get_rating_period(year)

    # Группируем по dog_id + nomination
    from ..repositories import show_repository as show_repo
    from django.db.models import Sum
    from ..models import ShowResult

    rows_by_nomination = {}
    for nomination in ('main', 'junior', 'veteran', 'working'):
        rows = show_repo.sum_points_grouped(date_from, date_to, nomination=nomination)
        rows_by_nomination[nomination] = rows

    # Пишем в DogYearlyRating, история сохраняется
    all_participant_ids = set()
    for nomination, rows in rows_by_nomination.items():
        for row in rows:
            show_repo.upsert_yearly_rating(
                dog_id=row['dog_id'],
                year=year,
                nomination=nomination,
                points=row['total'] or 0,
            )
            all_participant_ids.add(row['dog_id'])

    # Обнуляем тех кто не участвовал в этом году
    for nomination in rows_by_nomination:
        show_repo.reset_yearly_ratings_except(
            year=year,
            nomination=nomination,
            dog_ids=list(all_participant_ids),
        )

    # Dog.rating = кэш суммарных очков за текущий год (для быстрой сортировки)
    main_rows = rows_by_nomination['main']
    participant_ids = [r['dog_id'] for r in main_rows]
    for row in main_rows:
        dog_repo.set_rating(row['dog_id'], row['total'] or 0)
    dog_repo.reset_ratings_except(participant_ids)

    logger.info(f"Рейтинг {year} пересчитан: {len(all_participant_ids)} собак")

    from django.core.cache import cache
    cache.delete('home:hero_dog')

    return {
        'updated': len(all_participant_ids),
        'rating_year': year,
        'date_from': str(date_from),
        'date_to': str(date_to),
    }


def mark_results_parsed(event) -> None:
    from django.utils import timezone
    show_repo.mark_event_parsed(event.pk, timezone.now())


def get_rating_leaderboard_data(
        nomination: str = 'main',
        rating_year: int = None,
        limit: int = 50,
) -> list:
    year = rating_year or get_rating_year()
    rows = show_repo.get_yearly_leaderboard(year, nomination=nomination, limit=limit)
    dog_pts = {r['dog_id']: r['points'] for r in rows}

    if not dog_pts:
        # Fallback: пересчитываем на лету если таблица пустая (первый запуск)
        date_from, date_to = get_rating_period(year)
        live_rows = show_repo.sum_points_grouped(date_from, date_to, nomination=nomination, limit=limit)
        dog_pts = {r['dog_id']: r['total'] for r in live_rows}

    dogs = dog_repo.get_by_ids(list(dog_pts.keys()))
    return [
        {'dog': dog, 'points': dog_pts[dog.id]}
        for dog in sorted(dogs, key=lambda d: dog_pts[d.id], reverse=True)
    ]


# Алиас
def get_rating_leaderboard(nomination: str = 'main', rating_year: int = None, limit: int = 50) -> list:
    return get_rating_leaderboard_data(nomination=nomination, rating_year=rating_year, limit=limit)


def get_shows_needing_results(date_from, date_to) -> list:
    return show_repo.get_events_in_range(date_from, date_to, only_without_results=True)


def _refresh_dog_rating(dog_id: int) -> None:
    try:
        recalculate_dog_rating(dog_id)
    except Exception as e:
        logger.warning(f"_refresh_dog_rating dog_id={dog_id}: {e}")

# Самая рейтинговая собака за текущий год (для Home страницы)
def get_hero_dog(rating_year: int = None):
    year = rating_year or get_rating_year()

    dog_id = show_repo.get_top_dog_id_for_year(year, nomination='main')
    if dog_id:
        dog = dog_repo.get_by_id(dog_id)
        if dog:
            return dog

    fallback = dog_repo.search_by_name(HERO_FALLBACK_NAME)
    return fallback[0] if fallback else None
