"""
Сервис расчёта генетических коэффициентов из родословной.
"""

import logging
from typing import Optional

from ..domain.health_codes import score_conclusion, HIP_DYSPLASIA_THRESHOLD
from ..repositories import dog_repository as dog_repo
from ..repositories import medical_record_repository as med_repo

logger = logging.getLogger(__name__)

GENERATION_WEIGHTS = {
    1: 1.000,  # родители
    2: 0.500,  # деды
    3: 0.250,  # прадеды
    4: 0.125,  # пра-прадеды
}


# Балл теста бёдер из последнего по дате HIPS-теста
def _get_hip_score(dog_id: int, records_by_dog: dict) -> Optional[int]:
    records = records_by_dog.get(dog_id, [])
    hip_records = [r for r in records if (r["registry"] or "").upper() == "HIPS"]
    if not hip_records:
        return None
    latest = max(hip_records, key=lambda r: r["test_date"] or "")
    return score_conclusion("hips", latest["conclusion"])


# Рекурсивный обход родословной → список
def _get_ancestors(
        dog_id: int,
        generation: int,
        max_generation: int,
        parents_by_dog: dict,
        visited: set,
) -> list:
    if generation > max_generation or dog_id in visited:
        return []

    visited.add(dog_id)
    result = [(dog_id, generation)]

    sire_id, dam_id = parents_by_dog.get(dog_id, (None, None))
    if sire_id:
        result += _get_ancestors(sire_id, generation + 1, max_generation, parents_by_dog, visited)
    if dam_id:
        result += _get_ancestors(dam_id, generation + 1, max_generation, parents_by_dog, visited)
    return result


# Взвешенная доля предков с дисплазией бёдер
def calc_hip_dysplasia_ratio(dog_id: int, max_generations: int = 4) -> Optional[float]:
    all_ids = {dog_id}
    queue = [dog_id]
    parents_by_dog = {}

    for _ in range(max_generations):
        if not queue:
            break

        dogs = dog_repo.get_parents_batch_values(queue)

        next_queue = []
        for dog in dogs:
            sire_id = dog["sire_id"]
            dam_id = dog["dam_id"]
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

    records_raw = med_repo.get_ofa_hips_for_dogs_values(all_ids)

    records_by_dog = {}
    for rec in records_raw:
        records_by_dog.setdefault(rec["dog_id"], []).append(rec)

    ancestors = _get_ancestors(
        dog_id=dog_id,
        generation=0,  # сама собака
        max_generation=max_generations,
        parents_by_dog=parents_by_dog,
        visited=set(),
    )
    ancestors = [(did, gen) for did, gen in ancestors if gen > 0]

    total_weight = 0.0
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
        logger.debug(f"pedigree: dog_id={dog_id} нет предков с тестом бёдер")
        return None

    ratio = round(dysplasia_weight / total_weight, 4)
    logger.info(
        f"pedigree: dog_id={dog_id} hip_dysplasia_ratio={ratio:.3f} "
        f"(вес с дисплазией={dysplasia_weight:.2f} из {total_weight:.2f})"
    )
    return ratio


# Данные родословной пары для передачи в ML сервис
def get_pair_pedigree_data(sire_id: int, dam_id: int) -> dict:
    sire_ratio = calc_hip_dysplasia_ratio(sire_id)
    dam_ratio = calc_hip_dysplasia_ratio(dam_id)

    pair_ratio = None
    if sire_ratio is not None and dam_ratio is not None:
        pair_ratio = round((sire_ratio + dam_ratio) / 2, 4)
    elif sire_ratio is not None:
        pair_ratio = sire_ratio
    elif dam_ratio is not None:
        pair_ratio = dam_ratio

    return {
        "sire_hip_ratio": sire_ratio,
        "dam_hip_ratio": dam_ratio,
        "pair_hip_ratio": pair_ratio,
    }


# Ожидаемый COI потомства для пары
def calc_offspring_coi(sire_id: int, dam_id: int) -> float | None:
    from ..utils.coi_calculator import calculate_coi_for_pair
    result = calculate_coi_for_pair(sire_id, dam_id, generations=10)
    return round(result.coi, 4) if result.is_valid else None
