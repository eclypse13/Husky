"""
Сборка строки ML-признаков.
"""

from .ancestor_features import prefixed_side_features, empty_side_features, ANCESTOR_DEPTH


def build_feature_row(
        *,
        sire_scores: dict,
        dam_scores: dict,
        sire_coi: float | None,
        dam_coi: float | None,
        pair_coi: float | None,
        sire_id: int | None,
        dam_id: int | None,
        scores_by_dog: dict,
        parent_map: dict | None = None,
) -> dict:
    """
    sire_scores / dam_scores — {'hips':int,'eyes':int,...} (extract_scores) для самих родителей.
    scores_by_dog — баллы по всем нужным предкам (для агрегатов).
    parent_map — скелет дерева {id:(sire_id,dam_id)} для in-memory обхода (обучение);
                 None → ancestor_features тянет предков из БД (инференс).
    sire_id / dam_id — None означает «родитель неизвестен» → агрегаты «нет данных».
    """
    avg_hip = None
    if sire_scores.get("hips") is not None and dam_scores.get("hips") is not None:
        avg_hip = (sire_scores["hips"] + dam_scores["hips"]) / 2

    row = {
        "sire_hips": sire_scores.get("hips"),
        "sire_eyes": sire_scores.get("eyes"),
        "sire_elbows": sire_scores.get("elbows"),
        "sire_dm": sire_scores.get("dm"),
        "sire_pra": sire_scores.get("pra"),
        "sire_coi": sire_coi,
        "dam_hips": dam_scores.get("hips"),
        "dam_eyes": dam_scores.get("eyes"),
        "dam_elbows": dam_scores.get("elbows"),
        "dam_dm": dam_scores.get("dm"),
        "dam_pra": dam_scores.get("pra"),
        "dam_coi": dam_coi,
        "pair_coi": pair_coi,
        "avg_hip_score": avg_hip,
    }

    # Агрегаты по предкам каждой стороны.
    if sire_id is not None:
        row.update(prefixed_side_features("sire", sire_id, scores_by_dog,
                                          depth=ANCESTOR_DEPTH, parent_map=parent_map))
    else:
        row.update(empty_side_features("sire"))

    if dam_id is not None:
        row.update(prefixed_side_features("dam", dam_id, scores_by_dog,
                                          depth=ANCESTOR_DEPTH, parent_map=parent_map))
    else:
        row.update(empty_side_features("dam"))

    return row
