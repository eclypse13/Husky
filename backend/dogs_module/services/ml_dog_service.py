"""
Сервис подготовки данных собаки для ML сервиса.
"""

import logging

from ..domain.health_codes import extract_scores
from ..repositories import dog_repository as dog_repo
from ..repositories import medical_record_repository as med_repo

logger = logging.getLogger(__name__)

# логическая группа теста
_GROUP_TO_FIELD = {
    "hips": "hips_score",
    "eyes": "eyes_score",
    "elbows": "elbows_score",
    "dm": "dm_score",
    "pra": "pra_score",
    "pll": "pll_score",
    "lpp": "lpp_score",
    "cardiac": "cardiac_score",
    "thyroid": "thyroid_score",
    "patella": "patella_score",
}


# Достаёт здоровье собаки из БД и маппит в формат DogHealthData
def get_dog_health_data(dog_id: int) -> dict:
    dog = dog_repo.get_by_id(dog_id)
    if dog is None:
        logger.error(f"ml_dog_service: dog_id={dog_id} не найдена")
        return {"dog_id": dog_id}

    records = med_repo.get_ofa_records_for_dog_values(dog_id)
    scores = extract_scores(records)  # {group: score}

    data = {
        "dog_id": dog_id,
        "coi": float(dog.coi) if dog.coi else None,  # проценты
    }
    for group, field in _GROUP_TO_FIELD.items():
        if group in scores:
            data[field] = scores[group]

    return data


# Формирует данные пары для ML сервиса
def get_pair_data(sire_id: int, dam_id: int) -> dict:
    from .pedigree_service import calc_offspring_coi
    from .feature_builder import build_feature_row
    from .ancestor_features import collect_ancestor_ids, ANCESTOR_DEPTH

    offspring_coi = calc_offspring_coi(sire_id, dam_id)  # проценты

    # Предки обеих сторон + сами родители, нужны их баллы для агрегатов.
    need_ids = (
            collect_ancestor_ids(sire_id, ANCESTOR_DEPTH)
            | collect_ancestor_ids(dam_id, ANCESTOR_DEPTH)
            | {sire_id, dam_id}
    )
    records_raw = med_repo.get_ofa_records_for_dogs_values(need_ids)
    records_by_dog: dict[int, list] = {}
    for rec in records_raw:
        records_by_dog.setdefault(rec["dog_id"], []).append(rec)
    scores_by_dog = {i: extract_scores(r) for i, r in records_by_dog.items()}

    coi_map = dog_repo.get_coi_map({sire_id, dam_id})

    features = build_feature_row(
        sire_scores=scores_by_dog.get(sire_id, {}),
        dam_scores=scores_by_dog.get(dam_id, {}),
        sire_coi=float(coi_map.get(sire_id)) if coi_map.get(sire_id) else None,
        dam_coi=float(coi_map.get(dam_id)) if coi_map.get(dam_id) else None,
        pair_coi=offspring_coi,
        sire_id=sire_id,
        dam_id=dam_id,
        scores_by_dog=scores_by_dog,
        parent_map=None,  # для одной пары тянем предков из БД
    )

    return {
        "expected_coi": offspring_coi,  # проценты
        "features": features,
    }


def predict_pair(sire_id: int, dam_id: int) -> dict:
    from .ml_client import predict_breeding
    from .pedigree_service import calc_offspring_coi
    from ..domain.recommendation import get_breeding_recommendation

    result = predict_breeding(
        get_dog_health_data(sire_id),
        get_dog_health_data(dam_id),
        get_pair_data(sire_id, dam_id),
    )
    if "error" in result:
        return result

    offspring_coi = calc_offspring_coi(sire_id, dam_id)
    result["offspring_coi"] = offspring_coi
    return get_breeding_recommendation(result, offspring_coi)
