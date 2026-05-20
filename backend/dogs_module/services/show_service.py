# dogs_module/services/show_service.py
"""
Сервис для работы с выставочными данными.

Архитектурный принцип:
  ShowResult сохраняется ТОЛЬКО если dog найден в БД.
  Для отсутствующих собак — данные временно хранятся в Redis.
  После импорта собаки — задача link_pending_results достаёт данные из Redis и сохраняет.
"""

import re
import json
import logging
from datetime import datetime, date
from typing import Optional

from .dog_service import get_dog_by_zooportal_id, set_dog_rating, reset_ratings_except
from ..config import TITLE_POINTS, SHOW_MULTIPLIERS, SHOW_TYPE_OTHER, BOB_TITLES

logger = logging.getLogger(__name__)

# Redis ключ для ожидающих результатов: pending_show_results:{show_id}
_PENDING_KEY_PREFIX = "pending_show_results"
_PENDING_TTL        = 60 * 60 * 24 * 7  # 7 дней


def _pending_cache():
    from django.core.cache import caches
    return caches['parsers']


def _pending_key(show_id: str) -> str:
    return f"{_PENDING_KEY_PREFIX}:{show_id}"


# ──────────────────────────────────────────────────────────────────────────────
# ОПРЕДЕЛЕНИЕ ТИПА ВЫСТАВКИ
# ──────────────────────────────────────────────────────────────────────────────

SHOW_TYPE_PK         = 'pk'
SHOW_TYPE_KCHK       = 'kchk'
SHOW_TYPE_SPECIALITY = 'speciality'
SHOW_TYPE_SPORT      = 'sport'
SHOW_TYPE_WORLD      = 'world'

_PK_KEYWORDS         = ['ранга пк', 'нкп', 'национальн', 'монопородн', 'племенной смотр']
_SPECIALITY_KEYWORDS = ['специализирован', 'speciality', 'specialty']
_KCHK_KEYWORDS       = ['ранга кчк', 'кчк в каждом']
_SPORT_KEYWORDS      = ['соревнован', 'испытан', 'кубок', 'чемпионат']
_WORLD_KEYWORDS      = ['world dog show', 'euro dog show']
_EXCLUDE_RANKS       = ['cac', 'сас', 'cacib', 'сасиб']


def detect_show_type(title: str, rank: str = '') -> str:
    text = (title + ' ' + (rank or '')).lower()
    for kw in _WORLD_KEYWORDS:
        if kw in text: return SHOW_TYPE_WORLD
    for kw in _PK_KEYWORDS:
        if kw in text: return SHOW_TYPE_PK
    for kw in _SPECIALITY_KEYWORDS:
        if kw in text: return SHOW_TYPE_SPECIALITY
    for kw in _KCHK_KEYWORDS:
        if kw in text: return SHOW_TYPE_KCHK
    for kw in _SPORT_KEYWORDS:
        if kw in text: return SHOW_TYPE_SPORT
    for ex in _EXCLUDE_RANKS:
        if ex in text: return SHOW_TYPE_OTHER
    return SHOW_TYPE_OTHER


# ──────────────────────────────────────────────────────────────────────────────
# ПОДСЧЁТ ОЧКОВ
# ──────────────────────────────────────────────────────────────────────────────

def calc_base_points(titles_won: str) -> tuple[int, bool]:
    if not titles_won:
        return 0, False
    total  = 0
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
    if show_type == SHOW_TYPE_OTHER:
        return 0
    multiplier       = SHOW_MULTIPLIERS.get(show_type, 1.0)
    base_pts, is_bob = calc_base_points(titles_won)
    total  = int(base_pts * multiplier)
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


# ──────────────────────────────────────────────────────────────────────────────
# РАСЧЁТНЫЙ ГОД
# ──────────────────────────────────────────────────────────────────────────────

def get_rating_year(for_date: date = None) -> int:
    d = for_date or date.today()
    return d.year + 1 if d.month == 12 else d.year


def get_rating_period(rating_year: int) -> tuple[date, date]:
    return date(rating_year - 1, 12, 1), date(rating_year, 11, 30)


# ──────────────────────────────────────────────────────────────────────────────
# СОХРАНЕНИЕ МЕРОПРИЯТИЯ
# ──────────────────────────────────────────────────────────────────────────────

def save_show_event(event_data: dict):
    from ..models import ShowEvent

    show_id = event_data.get('zooportal_show_id')
    if not show_id:
        logger.error('save_show_event: нет zooportal_show_id')
        return None

    title      = event_data.get('title') or ''
    rank       = event_data.get('rank') or ''
    show_type  = detect_show_type(title, rank)
    multiplier = SHOW_MULTIPLIERS.get(show_type, 0.0)

    event_date = None
    raw_date   = event_data.get('event_date')
    if raw_date:
        try:
            event_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            pass

    obj, created = ShowEvent.objects.using('dogs_db').update_or_create(
        zooportal_show_id=show_id,
        defaults={
            'title':      title[:1000],
            'event_date': event_date,
            'organizer':  (event_data.get('organizer') or '')[:500],
            'rank':       rank[:255],
            'show_type':  show_type,
            'multiplier': multiplier,
            'city':       (event_data.get('city') or '')[:255],
            'address':    (event_data.get('address') or '')[:1000],
            'judges':     (event_data.get('judges') or '')[:2000],
            'status':     (event_data.get('status') or '')[:100],
        }
    )
    logger.info(
        f"ShowEvent {'создан' if created else 'обновлён'}: "
        f"id={show_id} type={show_type} ×{multiplier} — {title[:60]}"
    )
    return obj


# ──────────────────────────────────────────────────────────────────────────────
# СОХРАНЕНИЕ РЕЗУЛЬТАТОВ
# Главное правило: ShowResult сохраняется только если dog найден.
# Для остальных — данные идут в Redis.
# ──────────────────────────────────────────────────────────────────────────────

def save_show_results(event, results: list) -> tuple[int, int, int]:
    """
    Сохраняет результаты выставки.

    Возвращает (saved, failed, pending):
      saved   — сохранено с dog FK
      failed  — ошибки
      pending — отложено в Redis (собака не найдена)
    """
    from ..models import ShowResult

    saved   = 0
    failed  = 0
    pending = []

    for rec in results:
        zoo_id = rec.get('zooportal_dog_id')
        if not zoo_id:
            failed += 1
            continue

        dog = get_dog_by_zooportal_id(zoo_id)

        if dog is None:
            # Собаки нет в БД — откладываем в Redis
            pending.append(rec)
            continue

        try:
            saved_ok = _save_single_result(event, dog, rec)
            if saved_ok:
                saved += 1
                _refresh_dog_rating(dog.id)
        except Exception as e:
            failed += 1
            logger.warning(f"save_show_results: ошибка для zoo_id={zoo_id}: {e}")

    # Сохраняем ожидающие в Redis
    if pending:
        _store_pending(event.zooportal_show_id, pending)
        logger.info(
            f"ShowResults event={event.zooportal_show_id}: "
            f"saved={saved}, pending={len(pending)}, failed={failed}"
        )
    else:
        logger.info(f"ShowResults event={event.zooportal_show_id}: saved={saved}, failed={failed}")

    return saved, failed, len(pending)


def _save_single_result(event, dog, rec: dict) -> bool:
    """Сохраняет одну запись ShowResult. dog обязан быть не None."""
    from ..models import ShowResult

    titles_won    = rec.get('titles_won', '') or ''
    show_class    = rec.get('show_class', '') or ''
    catalog_count = rec.get('catalog_count') or 0
    bonus_points  = rec.get('bonus_points') or 0
    points        = calc_result_points(titles_won, event.show_type, catalog_count, bonus_points)
    nomination    = detect_nomination(show_class, titles_won)

    place = rec.get('place')
    if place is not None:
        try:
            place = int(place)
        except (ValueError, TypeError):
            place = None

    # Уникальный ключ: (event, dog) — один результат на собаку на выставке
    ShowResult.objects.using('dogs_db').update_or_create(
        event=event,
        dog=dog,
        defaults={
            'catalog_number': rec.get('catalog_number'),
            'show_class':    show_class[:100],
            'grade':         (rec.get('grade') or '')[:50],
            'place':         place,
            'titles_won':    titles_won[:500],
            'catalog_count': catalog_count,
            'bonus_points':  bonus_points,
            'rating_points': points,
            'nomination':    nomination,
        },
    )
    return True


# ──────────────────────────────────────────────────────────────────────────────
# REDIS — ОЖИДАЮЩИЕ РЕЗУЛЬТАТЫ
# ──────────────────────────────────────────────────────────────────────────────

def _store_pending(show_id: str, results: list) -> None:
    """Сохраняет ожидающие результаты в Redis."""
    try:
        key      = _pending_key(show_id)
        existing = _get_pending(show_id)

        # Мержим — не дублируем по zooportal_dog_id
        existing_ids = {r.get('zooportal_dog_id') for r in existing}
        new_items    = [r for r in results if r.get('zooportal_dog_id') not in existing_ids]

        all_pending = existing + new_items
        _pending_cache().set(key, json.dumps(all_pending, default=str), timeout=_PENDING_TTL)
        logger.debug(f"Pending stored: show_id={show_id}, count={len(all_pending)}")
    except Exception as e:
        logger.error(f"_store_pending show_id={show_id}: {e}")


def _get_pending(show_id: str) -> list:
    """Достаёт ожидающие результаты из Redis."""
    try:
        key  = _pending_key(show_id)
        data = _pending_cache().get(key)
        return json.loads(data) if data else []
    except Exception:
        return []


def _clear_pending(show_id: str) -> None:
    """Удаляет ожидающие результаты из Redis."""
    try:
        _pending_cache().delete(_pending_key(show_id))
    except Exception:
        pass


def get_all_pending_show_ids() -> list[str]:
    """Возвращает все show_id у которых есть ожидающие результаты."""
    try:
        keys = _pending_cache().keys(f"{_PENDING_KEY_PREFIX}:*")
        return [k.replace(f"parsers:{_PENDING_KEY_PREFIX}:", "").replace(f"{_PENDING_KEY_PREFIX}:", "") for k in (keys or [])]
    except Exception:
        return []


def process_pending_results(show_id: str) -> dict:
    """
    Обрабатывает ожидающие результаты для выставки.
    Вызывается после импорта собаки или по расписанию.

    Возвращает {'saved': N, 'still_pending': M}.
    """
    from ..models import ShowEvent

    pending = _get_pending(show_id)
    if not pending:
        return {'saved': 0, 'still_pending': 0}

    event = ShowEvent.objects.using('dogs_db').filter(zooportal_show_id=show_id).first()
    if not event:
        logger.warning(f"process_pending_results: выставка {show_id} не найдена")
        return {'saved': 0, 'still_pending': len(pending)}

    saved          = 0
    still_pending  = []

    for rec in pending:
        zoo_id = rec.get('zooportal_dog_id')
        dog    = get_dog_by_zooportal_id(zoo_id) if zoo_id else None

        if dog is None:
            still_pending.append(rec)
            continue

        try:
            _save_single_result(event, dog, rec)
            saved += 1
            _refresh_dog_rating(dog.id)
        except Exception as e:
            logger.warning(f"process_pending_results: ошибка для zoo_id={zoo_id}: {e}")
            still_pending.append(rec)

    # Обновляем Redis
    if still_pending:
        _pending_cache().set(
            _pending_key(show_id),
            json.dumps(still_pending, default=str),
            timeout=_PENDING_TTL,
        )
    else:
        _clear_pending(show_id)

    logger.info(
        f"process_pending_results show_id={show_id}: "
        f"saved={saved}, still_pending={len(still_pending)}"
    )
    return {'saved': saved, 'still_pending': len(still_pending)}


def process_all_pending_results() -> dict:
    """Обрабатывает ожидающие результаты для всех выставок."""
    show_ids    = get_all_pending_show_ids()
    total_saved = 0
    total_left  = 0

    for show_id in show_ids:
        result      = process_pending_results(show_id)
        total_saved += result['saved']
        total_left  += result['still_pending']

    return {'saved': total_saved, 'still_pending': total_left, 'shows_processed': len(show_ids)}


# ──────────────────────────────────────────────────────────────────────────────
# РЕЙТИНГ
# ──────────────────────────────────────────────────────────────────────────────

def recalculate_dog_rating(dog_id: int, rating_year: int = None) -> int:
    from ..models import ShowResult
    from django.db.models import Sum

    year               = rating_year or get_rating_year()
    date_from, date_to = get_rating_period(year)

    total = (
        ShowResult.objects
        .using('dogs_db')
        .filter(
            dog_id=dog_id,
            event__event_date__gte=date_from,
            event__event_date__lte=date_to,
        )
        .aggregate(total=Sum('rating_points'))['total'] or 0
    )

    set_dog_rating(dog_id, total)
    return total


def recalculate_all_ratings(rating_year: int = None) -> dict:
    from ..models import ShowResult
    from django.db.models import Sum

    year               = rating_year or get_rating_year()
    date_from, date_to = get_rating_period(year)

    rows = (
        ShowResult.objects
        .using('dogs_db')
        .filter(
            dog__isnull=False,
            event__event_date__gte=date_from,
            event__event_date__lte=date_to,
        )
        .values('dog_id')
        .annotate(total=Sum('rating_points'))
    )

    participant_ids = []
    for row in rows:
        set_dog_rating(row['dog_id'], row['total'] or 0)
        participant_ids.append(row['dog_id'])

    reset_ratings_except(participant_ids)

    logger.info(f"Рейтинг {year} пересчитан: {len(participant_ids)} собак")
    return {
        'updated':     len(participant_ids),
        'rating_year': year,
        'date_from':   str(date_from),
        'date_to':     str(date_to),
    }


def mark_results_parsed(event) -> None:
    from django.utils import timezone
    from ..models import ShowEvent
    ShowEvent.objects.using('dogs_db').filter(pk=event.pk).update(
        results_parsed_at=timezone.now()
    )


def get_rating_leaderboard(nomination: str = 'main', rating_year: int = None, limit: int = 50) -> list:
    from ..models import ShowResult
    from django.db.models import Sum

    year = rating_year or get_rating_year()
    date_from, date_to = get_rating_period(year)

    # Собираем dog_id с суммой очков за нужную номинацию
    rows = (
        ShowResult.objects
        .using('dogs_db')
        .filter(
            dog__isnull=False,
            nomination=nomination,
            event__event_date__gte=date_from,
            event__event_date__lte=date_to,
        )
        .values('dog_id')
        .annotate(total=Sum('rating_points'))
        .filter(total__gt=0)
        .order_by('-total')[:limit]
    )

    from ..models import Dog
    from ..serializers import DogListSerializer

    dog_pts = {r['dog_id']: r['total'] for r in rows}
    dogs = Dog.objects.using('dogs_db').filter(id__in=dog_pts.keys())

    result = []
    for dog in sorted(dogs, key=lambda d: dog_pts[d.id], reverse=True):
        data = DogListSerializer(dog).data
        data['points'] = dog_pts[dog.id]
        result.append(data)

    return result


def get_shows_needing_results(date_from, date_to) -> list:
    """
    Возвращает все ShowEvent за период у которых нет результатов.
    Используется в полном импорте вместо проверки статуса из парсера —
    статус из Zooportal ненадёжен (может быть пустым или на другом языке).
    """
    from ..models import ShowEvent
    return list(
        ShowEvent.objects
        .using('dogs_db')
        .filter(
            event_date__gte=date_from,
            event_date__lte=date_to,
            results_parsed_at__isnull=True,
        )
        .order_by('event_date')
    )


# ──────────────────────────────────────────────────────────────────────────────
# ВНУТРЕННИЕ
# ──────────────────────────────────────────────────────────────────────────────

def _refresh_dog_rating(dog_id: int) -> None:
    try:
        recalculate_dog_rating(dog_id)
    except Exception as e:
        logger.warning(f"_refresh_dog_rating dog_id={dog_id}: {e}")