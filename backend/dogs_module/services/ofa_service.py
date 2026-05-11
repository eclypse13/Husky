# dogs_module/services/ofa_service.py
"""
OFA-специфичный сервис
"""

import logging

logger = logging.getLogger(__name__)

STATS_CACHE_KEY = "ofa_breed_stats_sh"
STATS_CACHE_TTL = 3600 * 24  # 24 час

def verify_dog_identity(dog_id: int, dog_info: dict) -> tuple[bool, str]:
    """
    Проверяет что найденная на OFA собака соответствует нашей собаке в БД.

    Возвращает (is_match, причина отказа).
    """
    from ..models import Dog

    if not dog_info:
        return False, "dog_info пустой"

    try:
        dog = Dog.objects.using("dogs_db").only(
            "id", "sex", "year_of_birth", "date_of_birth"
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        return False, f"dog_id={dog_id} не найдена в БД"

    ofa_dob = dog_info.get("date_of_birth")
    ofa_sex_raw = (dog_info.get("sex_raw") or "").upper()

    # ── 1. Проверка пола ──────────────────────────────────────────────────────
    if dog.sex and ofa_sex_raw:
        ofa_sex_int = 1 if ofa_sex_raw == "M" else 2 if ofa_sex_raw == "F" else None
        if ofa_sex_int and dog.sex != ofa_sex_int:
            return False, (
                f"Пол не совпадает: наш={dog.sex}, OFA={ofa_sex_raw}"
            )

    # ── 2. Проверка по year_of_birth ──────────────────────────────────────────
    if dog.year_of_birth and dog.year_of_birth > 0:
        if not ofa_dob:
            return False, (
                f"year_of_birth={dog.year_of_birth} есть в БД, "
                f"но OFA не вернул дату рождения — нельзя подтвердить"
            )
        ofa_year = ofa_dob.year
        if abs(dog.year_of_birth - ofa_year) > 1:
            return False, (
                f"Год рождения не совпадает: "
                f"наш={dog.year_of_birth}, OFA={ofa_year}"
            )
        logger.debug(
            f"OFA verify dog_id={dog_id}: год совпадает ({dog.year_of_birth})"
        )
        return True, ""

    # ── 3. Нет year_of_birth — проверяем по date_of_birth ────────────────────
    if dog.date_of_birth:
        if not ofa_dob:
            return False, (
                f"date_of_birth есть в БД, "
                f"но OFA не вернул дату рождения — нельзя подтвердить"
            )
        our_year = dog.date_of_birth.year
        ofa_year = ofa_dob.year
        if abs(our_year - ofa_year) > 1:
            return False, (
                f"Год в date_of_birth не совпадает: "
                f"наш={our_year}, OFA={ofa_year}"
            )
        logger.debug(
            f"OFA verify dog_id={dog_id}: date_of_birth год совпадает ({our_year})"
        )
        return True, ""

    # ── 4. Нет данных для сравнения — не сохраняем ───────────────────────────
    return False, (
        "Нет year_of_birth и date_of_birth в БД — "
        "невозможно подтвердить что это та же собака"
    )


def should_save_date_of_birth(dog_id: int) -> bool:
    """
    Возвращает True если date_of_birth сейчас пустое — можно записать из OFA.
    """
    from ..models import Dog
    try:
        dog = Dog.objects.using("dogs_db").only("id", "date_of_birth").get(pk=dog_id)
        return dog.date_of_birth is None
    except Dog.DoesNotExist:
        return False


def save_ofa_records(dog_id: int, records: list) -> tuple:
    """
    Сохраняет медицинские записи OFA для собаки.
    Возвращает (saved_count, failed_count).
    """
    from ..models import Dog, MedicalRecord

    try:
        dog = Dog.objects.using("dogs_db").get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"ofa_service: dog_id={dog_id} не найдена")
        return 0, len(records)

    saved = failed = 0
    for rec in records:
        ofa_num = (rec.get("ofa_number") or "").strip()
        if not ofa_num:
            failed += 1
            continue

        try:
            _, created = MedicalRecord.objects.using("dogs_db").update_or_create(
                dog=dog,
                ofa_number=ofa_num,
                defaults={
                    "registry":      rec.get("registry", ""),
                    "test_date":     rec.get("test_date"),
                    "report_date":   rec.get("report_date"),
                    "age_in_months": rec.get("age_in_months"),
                    "conclusion":    rec.get("conclusion", ""),
                    "source":        "ofa",
                },
            )
            saved += 1
            logger.debug(
                f"ofa_service: {ofa_num} — "
                f"{'создана' if created else 'обновлена'}"
            )
        except Exception as e:
            failed += 1
            logger.warning(
                f"ofa_service: ошибка сохранения {ofa_num} "
                f"для dog_id={dog_id}: {e}"
            )

    logger.info(
        f"ofa_service: dog_id={dog_id} — сохранено={saved}, ошибок={failed}"
    )
    return saved, failed


def get_breed_ofa_stats() -> dict:
    """
    Возвращает статистику OFA для Siberian Husky.
    Кэширует в Redis на 24 часа.

    Возвращает dict вида:
      {"HIPS": {"total": 22568, "normal": 21963, "pct_normal": 97.3}, ...}
    """
    from django.core.cache import cache
    from ..parsers.ofa import fetch_ofa_breed_stats

    cached = cache.get(STATS_CACHE_KEY)
    if cached:
        logger.debug("OFA stats: из кэша Redis")
        return cached

    logger.info("OFA stats: запрос к OFA сайту...")
    stats = fetch_ofa_breed_stats()

    if not stats:
        logger.warning("OFA stats: не получены — используем fallback")
        stats = _fallback_stats()

    cache.set(STATS_CACHE_KEY, stats, STATS_CACHE_TTL)
    logger.info("OFA stats: сохранено в Redis")
    return stats


def invalidate_stats_cache() -> None:
    """Сбрасывает кэш статистики."""
    from django.core.cache import cache
    cache.delete(STATS_CACHE_KEY)
    logger.info("OFA stats: кэш сброшен")


def _fallback_stats() -> dict:
    """
    Захардкоженная статистика OFA как fallback если сайт недоступен.
    Источник: OFA public statistics 2023, Siberian Husky.
    """
    return {
        "HIPS": {"total": 22568, "normal": 21963, "pct_normal": 97.3},
        "EYES": {"total": 15178, "normal": 14005, "pct_normal": 92.3},
        "ELBOW": {"total": 1690, "normal": 1687, "pct_normal": 99.8},
        "CARDIAC": {"total": 2897, "normal": 2815, "pct_normal": 97.2},
        "PATELLA": {"total": 1543, "normal": 1529, "pct_normal": 99.1},
        "THYROID": {"total": 892, "normal": 855, "pct_normal": 95.8},
        "DEGENERATIVE MYELOPATHY": {
            "total": 287, "normal": 279, "pct_normal": 97.2
        },
    }