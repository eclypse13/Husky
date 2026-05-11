# dogs_module/services/pedigree_service.py
"""
Сервис для расчёта генетических коэффициентов из родословной.

Взвешенная доля предков с дисплазией:
  Поколение 1 (родители)  → вес 1.0
  Поколение 2 (деды)      → вес 0.5
  Поколение 3 (прадеды)   → вес 0.25
  Поколение 4             → вес 0.125

Источник весов: доля генов передаваемых от предка к потомку
(каждое поколение = 50% от предыдущего).
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Вес каждого поколения = доля генов которую передаёт предок
GENERATION_WEIGHTS = {
    1: 1.000,   # родители    → 50% генов → нормализован к 1.0
    2: 0.500,   # деды        → 25% генов
    3: 0.250,   # прадеды     → 12.5% генов
    4: 0.125,   # пра-прадеды → 6.25% генов
}

# Порог дисплазии бёдер — FAIR и хуже
HIP_MAP = {
    "EXCELLENT": 0, "GOOD": 1, "FAIR": 2,
    "BORDERLINE": 3, "MILD": 4, "MODERATE": 5, "SEVERE": 6,
}
HIP_DYSPLASIA_THRESHOLD = 2  # FAIR и хуже = проблема


def _get_hip_score(dog_id: int, records_by_dog: dict) -> Optional[int]:
    """Берёт результат теста бёдер из кэша записей."""
    records = records_by_dog.get(dog_id, [])
    hip_records = [r for r in records if r["registry"].upper() == "HIPS"]
    if not hip_records:
        return None
    latest = max(hip_records, key=lambda r: r["test_date"] or "")
    conclusion = (latest["conclusion"] or "").upper().strip()
    return HIP_MAP.get(conclusion)


def _get_ancestors(
    dog_id: int,
    generation: int,
    max_generation: int,
    parents_by_dog: dict,
    visited: set,
) -> list:
    """
    Рекурсивно обходит родословную.
    Возвращает список (dog_id, generation) для всех предков.
    """
    if generation > max_generation or dog_id in visited:
        return []

    visited.add(dog_id)
    result = [(dog_id, generation)]

    sire_id, dam_id = parents_by_dog.get(dog_id, (None, None))
    if sire_id:
        result += _get_ancestors(
            sire_id, generation + 1, max_generation, parents_by_dog, visited
        )
    if dam_id:
        result += _get_ancestors(
            dam_id, generation + 1, max_generation, parents_by_dog, visited
        )
    return result


def calc_hip_dysplasia_ratio(
    dog_id: int,
    max_generations: int = 4,
) -> Optional[float]:
    """
    Рассчитывает взвешенную долю предков с дисплазией бёдер.

    Параметры:
      dog_id         — ID собаки
      max_generations — глубина родословной (по умолчанию 4)

    Возвращает:
      float 0.0-1.0 — взвешенная доля предков с FAIR и хуже
      None          — если нет данных

    Пример:
      Мама: FAIR (вес 1.0) — больная
      Дед:  FAIR (вес 0.5) — больной
      Папа: GOOD (вес 1.0) — здоровый
      → (1.0 + 0.5) / (1.0 + 0.5 + 1.0) = 0.6
    """
    from ..models import Dog, MedicalRecord

    # Собираем всех предков до max_generations поколений
    # Сначала загружаем всю родословную одним запросом

    # Шаг 1 — загружаем иерархию родителей BFS
    all_ids = {dog_id}
    queue = [dog_id]
    parents_by_dog = {}

    for _ in range(max_generations):
        if not queue:
            break

        dogs = list(
            Dog.objects.using("dogs_db")
            .filter(id__in=queue)
            .values("id", "sire_id", "dam_id")
        )

        next_queue = []
        for dog in dogs:
            sire_id = dog["sire_id"]
            dam_id  = dog["dam_id"]
            parents_by_dog[dog["id"]] = (sire_id, dam_id)

            if sire_id and sire_id not in all_ids:
                all_ids.add(sire_id)
                next_queue.append(sire_id)
            if dam_id and dam_id not in all_ids:
                all_ids.add(dam_id)
                next_queue.append(dam_id)

        queue = next_queue

    if len(all_ids) <= 1:
        logger.debug(f"pedigree: dog_id={dog_id} нет предков в родословной")
        return None

    # Шаг 2 — загружаем OFA записи для всех предков одним запросом
    records_raw = list(
        MedicalRecord.objects.using("dogs_db")
        .filter(dog_id__in=all_ids, source="ofa", registry="HIPS")
        .values("dog_id", "registry", "conclusion", "test_date")
    )

    records_by_dog = {}
    for rec in records_raw:
        did = rec["dog_id"]
        if did not in records_by_dog:
            records_by_dog[did] = []
        records_by_dog[did].append(rec)

    # Шаг 3 — обходим родословную и считаем взвешенный коэффициент
    ancestors = _get_ancestors(
        dog_id=dog_id,
        generation=0,        # сама собака = поколение 0
        max_generation=max_generations,
        parents_by_dog=parents_by_dog,
        visited=set(),
    )

    # Убираем саму собаку (generation=0)
    ancestors = [(did, gen) for did, gen in ancestors if gen > 0]

    total_weight    = 0.0
    dysplasia_weight = 0.0

    for ancestor_id, generation in ancestors:
        weight = GENERATION_WEIGHTS.get(generation, 0.0)
        if weight == 0:
            continue

        hip_score = _get_hip_score(ancestor_id, records_by_dog)
        if hip_score is None:
            continue  # нет теста — не учитываем

        total_weight += weight
        if hip_score >= HIP_DYSPLASIA_THRESHOLD:
            dysplasia_weight += weight

    if total_weight == 0:
        logger.debug(
            f"pedigree: dog_id={dog_id} нет предков с тестом бёдер"
        )
        return None

    ratio = round(dysplasia_weight / total_weight, 4)
    logger.info(
        f"pedigree: dog_id={dog_id} "
        f"hip_dysplasia_ratio={ratio:.3f} "
        f"(взвешенный вес с дисплазией={dysplasia_weight:.2f} "
        f"из {total_weight:.2f})"
    )
    return ratio


def get_pair_pedigree_data(sire_id: int, dam_id: int) -> dict:
    """
    Рассчитывает данные родословной для пары.
    Вызывается перед передачей в ML сервис.

    Возвращает:
      {
        "sire_hip_ratio": 0.15,  # доля дисплазии в родословной кобеля
        "dam_hip_ratio":  0.33,  # доля дисплазии в родословной суки
        "pair_hip_ratio": 0.24,  # среднее для пары
      }
    """
    sire_ratio = calc_hip_dysplasia_ratio(sire_id)
    dam_ratio  = calc_hip_dysplasia_ratio(dam_id)

    pair_ratio = None
    if sire_ratio is not None and dam_ratio is not None:
        pair_ratio = round((sire_ratio + dam_ratio) / 2, 4)
    elif sire_ratio is not None:
        pair_ratio = sire_ratio
    elif dam_ratio is not None:
        pair_ratio = dam_ratio

    return {
        "sire_hip_ratio": sire_ratio,
        "dam_hip_ratio":  dam_ratio,
        "pair_hip_ratio": pair_ratio,
    }


def calc_offspring_coi(sire_id: int, dam_id: int) -> float | None:
    """
    Рассчитывает ожидаемый COI потомства для пары.

    Использует существующий calculate_coi через виртуальную собаку.
    check_completeness=False — для вязки нам важен любой результат,
    даже если родословная неполная (иначе сын×мать даст 0 вместо 25%).
    """
    from ..utils.coi_calculator import calculate_coi
    from types import SimpleNamespace

    virtual_dog = SimpleNamespace(
        id=None,
        sire_id=sire_id,
        dam_id=dam_id,
    )

    result = calculate_coi(
        virtual_dog,
        generations=10,  # максимум поколений
        check_completeness=False,  # не блокировать при неполной родословной
    )

    if result.is_valid:
        return round(result.coi, 4)
    return None


def get_coi_comment(coi: float | None) -> dict:
    """
    Объясняет уровень COI потомства понятным языком.
    Возвращает dict с уровнем, заголовком и объяснением.
    """
    if coi is None:
        return {
            "level": "unknown",
            "title": "COI не рассчитан",
            "text": "Недостаточно данных родословной для расчёта.",
        }

    if coi >= 25.0:
        return {
            "level": "critical",
            "title": f"Критический инбридинг — {coi:.2f}%",
            "text": (
                "Эквивалент вязки родитель × потомок или брат × сестра. "
                "Потомки получат одинаковые копии генов от обоих родителей "
                "с вероятностью 1 из 4. Резко возрастает риск всех рецессивных "
                "болезней и иммунодефицита. Вязка недопустима."
            ),
        }
    if coi >= 12.5:
        return {
            "level": "high",
            "title": f"Высокий инбридинг — {coi:.2f}%",
            "text": (
                "Эквивалент вязки дед × внучка или полубрат × полусестра. "
                "Общие предки встречаются в нескольких ветках родословной. "
                "Значительно повышен риск рецессивных заболеваний "
                "характерных для сибирского хаски."
            ),
        }
    if coi >= 6.25:
        return {
            "level": "medium",
            "title": f"Повышенный инбридинг — {coi:.2f}%",
            "text": (
                "Эквивалент вязки двоюродных родственников. "
                "Общие предки присутствуют в родословной обоих родителей. "
                "Рекомендуется проверить наличие генетических тестов "
                "на рецессивные болезни (DM, PRA, LPP) перед вязкой."
            ),
        }
    if coi >= 3.125:
        return {
            "level": "low",
            "title": f"Умеренный инбридинг — {coi:.2f}%",
            "text": (
                "Умеренный уровень родства. Допустимо при наличии "
                "хороших результатов здоровья у обоих родителей."
            ),
        }
    if coi > 0:
        return {
            "level": "minimal",
            "title": f"Низкий инбридинг — {coi:.2f}%",
            "text": (
                "Хорошее разнообразие линий. "
                "Минимальный риск накопления рецессивных болезней."
            ),
        }
    return {
        "level": "zero",
        "title": "Инбридинг не обнаружен — 0%",
        "text": (
            "Общих предков в доступной родословной не найдено. "
            "Вязка несвязанных линий."
        ),
    }
