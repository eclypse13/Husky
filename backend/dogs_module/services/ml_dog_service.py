# dogs_module/services/ml_dog_service.py
"""
Сервис подготовки данных собаки для ML сервиса.
"""

import logging

logger = logging.getLogger(__name__)

HIP_MAP = {
    "EXCELLENT": 0, "GOOD": 1, "FAIR": 2,
    "BORDERLINE": 3, "MILD": 4, "MODERATE": 5, "SEVERE": 6,
}
EYE_MAP     = {"NORMAL": 0, "NORMAL W/BO": 0, "AFFECTED": 1}
ELBOW_MAP   = {"NORMAL": 0, "GRADE I": 1, "GRADE II": 2, "GRADE III": 3}
GENETIC_MAP = {
    "CLEAR/NORMAL": 0, "CLEAR": 0, "NORMAL/CLEAR": 0,
    "CARRIER": 1, "AFFECTED": 2,
}
CARDIAC_REGISTRIES = {"BASIC CARDIAC", "ADVANCED CARDIAC", "CONGENITAL CARDIAC"}
EYE_REGISTRIES     = {"EYES", "CERF", "SIBERIAN HUSKY OPTH. REGISTRY"}
PRA_REGISTRIES     = {
    "PROGRESSIVE RETINAL ATROPHY",
    "PRA - CONE ROD DYSTROPHY 3",
    "EARLY ONSET PRA",
}
LPP_REGISTRIES = {
    "JUVENILE LARYNGEAL PARALYSIS & POLYNEUROPATHY (LPP)",
    "POLYNEUROPATHY",
}


def get_dog_health_data(dog_id: int) -> dict:
    """
    Достаёт из БД данные здоровья собаки и маппит в формат для ML сервиса.

    Возвращает dict готовый для передачи в predict_breeding().
    """
    from ..models import Dog, MedicalRecord

    try:
        dog = Dog.objects.using("dogs_db").get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"ml_dog_service: dog_id={dog_id} не найдена")
        return {"dog_id": dog_id}

    records = list(
        MedicalRecord.objects.using("dogs_db")
        .filter(dog_id=dog_id, source="ofa")
        .values("registry", "conclusion")
    )

    data = {
        "dog_id": dog_id,
        "coi": float(dog.coi) if dog.coi else None,
    }

    for rec in records:
        reg = rec["registry"].upper().strip()
        con = (rec["conclusion"] or "").upper().strip()

        if reg == "HIPS":
            data["hips_score"] = HIP_MAP.get(con)

        elif reg in EYE_REGISTRIES:
            data["eyes_score"] = EYE_MAP.get(con)

        elif reg == "ELBOW":
            data["elbows_score"] = ELBOW_MAP.get(con)

        elif reg == "DEGENERATIVE MYELOPATHY":
            data["dm_score"] = GENETIC_MAP.get(con)

        elif reg in PRA_REGISTRIES:
            data["pra_score"] = GENETIC_MAP.get(con)

        elif reg == "PRIMARY LENS LUXATION":
            data["pll_score"] = GENETIC_MAP.get(con)

        elif reg in LPP_REGISTRIES:
            data["lpp_score"] = GENETIC_MAP.get(con)

        elif reg in CARDIAC_REGISTRIES:
            data["cardiac_score"] = 0 if "NORMAL" in con else 1

        elif reg == "THYROID":
            data["thyroid_score"] = 0 if "NORMAL" in con else 1

        elif reg == "PATELLA":
            data["patella_score"] = 0 if "NORMAL" in con else 1

    return data

def get_pair_data(sire_id: int, dam_id: int) -> dict:
    """Формирует данные пары для ML сервиса."""
    from .pedigree_service import get_pair_pedigree_data, calc_offspring_coi

    pedigree = get_pair_pedigree_data(sire_id, dam_id)
    offspring_coi = calc_offspring_coi(sire_id, dam_id)

    return {
        "expected_coi":             offspring_coi / 100 if offspring_coi else None,
        "hip_dysplasia_ratio_4gen": pedigree["pair_hip_ratio"],
    }


def get_breeding_recommendation(result: dict, offspring_coi: float | None) -> dict:
    """
    Рекомендация основана ТОЛЬКО на том что реально прогнозируется ML:
      - COI потомства (главный приоритет — генетика)
      - ML бёдра (ROC-AUC 0.642, обучена на реальных OFA данных)
      - ML глаза (ROC-AUC 0.842, обучена на реальных OFA данных)

    Остальные 8 болезней показываются информационно,
    НЕ влияют на итоговую рекомендацию.
    """
    from .pedigree_service import get_coi_comment

    # COI — главный приоритет
    coi_info = get_coi_comment(offspring_coi)
    result["coi_info"] = coi_info

    if offspring_coi is not None and offspring_coi > 12.5:
        result["recommendation"] = "not_recommended"
        return result

    if offspring_coi is not None and offspring_coi > 6.25:
        if result.get("recommendation") == "recommended":
            result["recommendation"] = "caution"

    # ML бёдра и глаза — только если basis==ml
    hip = result.get("hip_dysplasia", {})
    eye = result.get("eye_disease", {})

    hip_risk = hip.get("risk", 0) if hip.get("basis") == "ml" else None
    eye_risk = eye.get("risk", 0) if eye.get("basis") == "ml" else None

    if hip_risk is not None and hip_risk > 0.35:
        result["recommendation"] = "not_recommended"
    elif hip_risk is not None and hip_risk > 0.20:
        if result.get("recommendation") == "recommended":
            result["recommendation"] = "caution"
    elif eye_risk is not None and eye_risk > 0.30:
        if result.get("recommendation") == "recommended":
            result["recommendation"] = "caution"

    return result
