# dogs_module/services/ofa_service.py
import re

"""
OFA-специфичный сервис: сверка личности, сохранение записей, статистика породы.
"""

import logging
import unicodedata

from ..repositories import dog_repository as dog_repo
from ..repositories import medical_record_repository as med_repo

logger = logging.getLogger(__name__)

STATS_CACHE_KEY = "ofa_breed_stats_sh"
STATS_CACHE_TTL = 3600 * 24  # 24 часа
MAX_OFA_RECORDS_PER_DOG = 50  # реальная собака не имеет сотен записей; превышение = чужие данные
# Рег. номера на кирилице или содержащие 'метрик'/'РКФ' — не OFA-совместимы
_INVALID_REG_PREFIX = re.compile(r'^[а-яёА-ЯЁ]')
_INVALID_REG_SUBSTRINGS = ('метрик', 'РКФ')

def _normalize_for_match(name: str) -> str:
    """Жёсткая нормализация ТОЛЬКО для сверки имён."""
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    for ch in ("'", "’", "`", "ʼ", "‘", "´", '"', "“", "”"):
        s = s.replace(ch, "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def _ofa_name_matches(our_name: str, ofa_name: str) -> bool:
    a, b = _normalize_for_match(our_name), _normalize_for_match(ofa_name)
    if not a or not b:
        return False
    return a == b or a.replace(" ", "") == b.replace(" ", "")


def verify_dog_identity(dog_id: int, dog_info: dict) -> tuple[bool, str]:
    if not dog_info:
        return False, "dog_info пустой"
    dog = dog_repo.get_identity_fields(dog_id)
    if dog is None:
        return False, f"dog_id={dog_id} не найдена в БД"
    return _identity_matches(dog, dog_info)


def _identity_matches(dog, dog_info: dict) -> tuple[bool, str]:
    ofa_dob = dog_info.get("date_of_birth")
    ofa_sex_raw = (dog_info.get("sex_raw") or "").upper()

    if dog.sex and ofa_sex_raw:
        ofa_sex_int = 1 if ofa_sex_raw == "M" else 2 if ofa_sex_raw == "F" else None
        if ofa_sex_int and dog.sex != ofa_sex_int:
            return False, f"Пол не совпадает: наш={dog.sex}, OFA={ofa_sex_raw}"

    if dog.year_of_birth and dog.year_of_birth > 0:
        if not ofa_dob:
            return False, f"year_of_birth={dog.year_of_birth} есть, OFA без даты — нельзя подтвердить"
        if abs(dog.year_of_birth - ofa_dob.year) > 1:
            return False, f"Год не совпадает: наш={dog.year_of_birth}, OFA={ofa_dob.year}"
        return True, ""

    if dog.date_of_birth:
        if not ofa_dob:
            return False, "date_of_birth есть, OFA без даты — нельзя подтвердить"
        if abs(dog.date_of_birth.year - ofa_dob.year) > 1:
            return False, f"Год date_of_birth не совпадает: наш={dog.date_of_birth.year}, OFA={ofa_dob.year}"
        return True, ""

    return False, "Нет year_of_birth и date_of_birth — невозможно подтвердить идентичность"


def _select_ofa_candidate(dog_id, candidates, expected_name, expected_reg) -> tuple:
    """Из кандидатов выбирает ОДНО однозначно подтверждённое животное → (candidate|None, reason)."""
    if not candidates:
        return None, "OFA ничего не вернул"

    # 1. Точное совпадение имени — режем substring/префиксный мусор OFA
    if expected_name:
        named = [c for c in candidates
                 if _ofa_name_matches(expected_name, c["dog_info"].get("registered_name", ""))]
    else:
        named = list(candidates)
    if not named:
        return None, "нет точного совпадения имени среди результатов"

    # 2. Идентификационная сверка (один запрос identity на всех)
    if dog_id:
        dog = dog_repo.get_identity_fields(dog_id)
        if dog is None:
            return None, f"dog_id={dog_id} не найдена в БД"
        verified = [c for c in named if _identity_matches(dog, c["dog_info"])[0]]
    else:
        verified = named
    if not verified:
        return None, "ни один кандидат не прошёл сверку (пол/год)"

    if len(verified) == 1:
        return verified[0], ""

    # 3. Тай-брейк по точному рег. номеру
    if expected_reg:
        er = expected_reg.strip().lower()
        exact = [c for c in verified if (c.get("registration_number") or "").strip().lower() == er]
        if len(exact) == 1:
            return exact[0], ""

    # 4. Осознанный отказ — для ML лучше пропуск, чем чужие данные
    return None, f"неоднозначно: {len(verified)} собак с этим именем прошли сверку — пропуск"


def should_save_date_of_birth(dog_id: int) -> bool:
    """True если date_of_birth сейчас пустое — можно записать из OFA."""
    dog = dog_repo.get_by_id(dog_id)
    return bool(dog and dog.date_of_birth is None)


def save_ofa_records(dog_id: int, records: list) -> tuple:
    """Сохраняет медицинские записи OFA. → (saved_count, failed_count)."""
    dog = dog_repo.get_by_id(dog_id)
    if dog is None:
        logger.error(f"ofa_service: dog_id={dog_id} не найдена")
        return 0, len(records)

    saved = failed = 0
    for rec in records:
        ofa_num = (rec.get("ofa_number") or "").strip()
        if not ofa_num:
            failed += 1
            continue

        try:
            created = med_repo.upsert_ofa_record(dog, ofa_num, {
                "registry": rec.get("registry", ""),
                "test_date": rec.get("test_date"),
                "report_date": rec.get("report_date"),
                "age_in_months": rec.get("age_in_months"),
                "conclusion": rec.get("conclusion", ""),
                "source": "ofa",
            })
            saved += 1
            logger.debug(f"ofa_service: {ofa_num} — {'создана' if created else 'обновлена'}")
        except Exception as e:
            failed += 1
            logger.warning(f"ofa_service: ошибка сохранения {ofa_num} для dog_id={dog_id}: {e}")

    logger.info(f"ofa_service: dog_id={dog_id} — сохранено={saved}, ошибок={failed}")
    return saved, failed


def get_breed_ofa_stats() -> dict:
    """Статистика OFA для Siberian Husky. Кэш в Redis на 24ч."""
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
    from django.core.cache import cache
    cache.delete(STATS_CACHE_KEY)
    logger.info("OFA stats: кэш сброшен")


def _fallback_stats() -> dict:
    """Статистика OFA из constants."""
    from ..constants.ofa_fallback import OFA_FALLBACK_STATS
    return OFA_FALLBACK_STATS


def _update_dog_from_ofa(dog_id: int, dog_info: dict) -> bool:
    """Обновляет пустые поля Dog из данных OFA."""
    updates = {}
    reg_num = (dog_info.get('registration_number') or '').strip()
    if reg_num:
        updates['registration_number'] = reg_num
    dob = dog_info.get('date_of_birth')
    if dob:
        updates['date_of_birth'] = dob
    if not updates:
        return False
    return dog_repo.update_fields_if_empty(dog_id, updates)


# Публичный алиас — dog_service.py и внешний код могут импортировать напрямую
def update_dog_from_ofa(dog_id: int, dog_info: dict) -> bool:
    return _update_dog_from_ofa(dog_id, dog_info)


def import_ofa_for_dog(
        dog_id: int = None,
        registered_name: str = None,
        registration_number: str = None,
        ofa_number: str = None,
) -> dict:
    """
    Полный цикл OFA-импорта для одной собаки.
    Вынесено из fetch_ofa_dog_task — задача становится тонкой обёрткой.

    Возвращает dict с ключами: dog_id, appnum, saved, failed, message.
    """
    from ..parsers.ofa import fetch_ofa_data

    expected_sex = expected_year = None

    if dog_id:
        params = dog_repo.get_search_params(dog_id)
        if params is None:
            return {"error": f"Dog {dog_id} not found"}
        expected_sex = params["sex"]
        expected_year = params["expected_year"]
        registered_name = params["registered_name"]
        if not registration_number and not ofa_number:
            registration_number = params["registration_number"]

    if not any([registered_name, registration_number, ofa_number]):
        return {"error": "Нужен хотя бы один параметр поиска"}

    result = fetch_ofa_data(
        registered_name=registered_name,
        registration_number=registration_number,
        ofa_number=ofa_number,
        expected_sex=expected_sex,
        expected_year=expected_year,
    )
    candidates = (result or {}).get("candidates", [])
    if not candidates:
        return {"dog_id": dog_id, "appnum": None, "saved": 0, "failed": 0,
                "message": "Собака не найдена в базе OFA"}

    candidate, reason = _select_ofa_candidate(
        dog_id, candidates, expected_name=registered_name, expected_reg=registration_number,
    )
    if candidate is None:
        logger.info(f"OFA dog_id={dog_id}: не сохраняем — {reason}")
        return {"dog_id": dog_id, "appnum": None, "saved": 0, "failed": 0,
                "message": f"Не сохраняем: {reason}"}

    records = candidate["medical_records"]

    # Защита от регрессий: даже у одного животного столько записей быть не должно
    if len(records) > MAX_OFA_RECORDS_PER_DOG:
        logger.error(f"OFA dog_id={dog_id}: {len(records)} записей у appnum={candidate['appnum']} "
                     f"— аномалия, пропуск")
        return {"dog_id": dog_id, "appnum": candidate["appnum"], "saved": 0, "failed": 0,
                "message": f"Аномалия: {len(records)} записей — пропуск"}

    saved = failed = 0
    if dog_id:
        _update_dog_from_ofa(dog_id, candidate["dog_info"])
        saved, failed = save_ofa_records(dog_id, records)

    return {
        "dog_id": dog_id,
        "appnum": candidate["appnum"],
        "dog_info": candidate["dog_info"],
        "saved": saved,
        "failed": failed,
        "medical_records": records,
    }


# ФИЛЬТРАЦИЯ СОБАК ДЛЯ BULK OFA-ИМПОРТА

def is_valid_ofa_reg(reg: str) -> bool:
    """True если рег. номер может быть использован для поиска на OFA."""
    if not reg:
        return False
    if _INVALID_REG_PREFIX.match(reg):
        return False
    if any(s in reg for s in _INVALID_REG_SUBSTRINGS):
        return False
    return True


def get_dogs_eligible_by_reg(
        id_from: int = 1,
        id_to: int = None,
        limit: int = 100,
        only_without_ofa: bool = True,
) -> list:
    """
    Собаки с валидным OFA рег. номером для bulk-импорта.
    Применяет доменные фильтры поверх чистой выборки репозитория.
    """
    dogs = dog_repo.get_dogs_with_reg_number(id_from=id_from, id_to=id_to, limit=limit * 3)
    dogs = [d for d in dogs if is_valid_ofa_reg(d.get('registration_number', ''))]

    if only_without_ofa:
        existing_ids = med_repo.get_dog_ids_with_ofa()
        dogs = [d for d in dogs if d['id'] not in existing_ids]

    return dogs[:limit]


def get_dogs_eligible_by_name(
        id_from: int = 1,
        id_to: int = None,
        limit: int = 100,
        only_without_ofa: bool = True,
) -> list:
    """Собаки с именем для bulk OFA-импорта по имени."""
    dogs = dog_repo.get_dogs_with_name(id_from=id_from, id_to=id_to, limit=limit * 2)

    if only_without_ofa:
        existing_ids = med_repo.get_dog_ids_with_ofa()
        dogs = [d for d in dogs if d['id'] not in existing_ids]

    return dogs[:limit]
