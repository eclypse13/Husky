# dogs_module/domain/recommendation.py
"""
Правила итоговой рекомендации по вязке.

Учитываются только реально прогнозируемые ML факторы (в данный момент на 05.2026):
COI потомства, риск дисплазии бёдер и патологии глаз.
Остальные болезни идут информационно и на рекомендацию не влияют.
"""

from .coi_interpretation import get_coi_comment

# Пороги COI потомства, %
COI_NOT_RECOMMENDED = 12.5
COI_CAUTION = 6.25

# Пороги ML-рисков, доля 0..1
HIP_RISK_NOT_RECOMMENDED = 0.35
HIP_RISK_CAUTION = 0.20
EYE_RISK_CAUTION = 0.30


def get_breeding_recommendation(result: dict, offspring_coi: float | None) -> dict:
    """Дополняет result итоговой рекомендацией. Мутирует и возвращает result."""
    result["coi_info"] = get_coi_comment(offspring_coi)

    # COI — главный приоритет
    if offspring_coi is not None and offspring_coi > COI_NOT_RECOMMENDED:
        result["recommendation"] = "not_recommended"
        return result

    if offspring_coi is not None and offspring_coi > COI_CAUTION:
        if result.get("recommendation") == "recommended":
            result["recommendation"] = "caution"

    # ML бёдра/глаза — только если прогноз основан на модели
    hip = result.get("hip_dysplasia", {})
    eye = result.get("eye_disease", {})
    hip_risk = hip.get("risk", 0) if hip.get("basis") == "ml" else None
    eye_risk = eye.get("risk", 0) if eye.get("basis") == "ml" else None

    if hip_risk is not None and hip_risk > HIP_RISK_NOT_RECOMMENDED:
        result["recommendation"] = "not_recommended"
    elif hip_risk is not None and hip_risk > HIP_RISK_CAUTION:
        if result.get("recommendation") == "recommended":
            result["recommendation"] = "caution"
    elif eye_risk is not None and eye_risk > EYE_RISK_CAUTION:
        if result.get("recommendation") == "recommended":
            result["recommendation"] = "caution"

    return result
