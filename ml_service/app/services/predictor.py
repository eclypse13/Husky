# ml_service/app/services/predictor.py
"""
Предсказание рисков для пары.


Три метода:
  "ml"       — CatBoost модель (если обучена)
  "rules"    — ветеринарные правила OFA
  "genetics" — законы Менделя (DM, PRA, PLL, LPP)
"""

import logging
import pandas as pd
from typing import Optional

from .model_store import load_model
from ..schemas.breeding import (
    BreedingPredictRequest,
    BreedingPredictResponse,
    DiseaseRisk,
)
from ..config import settings, FEATURE_COLS

logger = logging.getLogger(__name__)

# Ветеринарные правила OFA
HIP_RISK     = {0: 0.05, 1: 0.10, 2: 0.18, 3: 0.30, 4: 0.45, 5: 0.60, 6: 0.75}
ELBOW_RISK   = {0: 0.05, 1: 0.20, 2: 0.40, 3: 0.65}
EYE_RISK     = {0: 0.05, 1: 0.50}
CARDIAC_RISK = {0: 0.03, 1: 0.40}
THYROID_RISK = {0: 0.03, 1: 0.30}
PATELLA_RISK = {0: 0.05, 1: 0.35}


def _build_features(req: BreedingPredictRequest) -> pd.DataFrame:
    """
    Строит DataFrame из запроса.
    NaN остаются NaN — CatBoost обрабатывает их нативно.
    """
    s, d = req.sire, req.dam
    avg_hip = None
    if s.hips_score is not None and d.hips_score is not None:
        avg_hip = (s.hips_score + d.hips_score) / 2

    return pd.DataFrame([{
        "sire_hips":       s.hips_score,
        "sire_eyes":       s.eyes_score,
        "sire_elbows":     s.elbows_score,
        "sire_dm":         s.dm_score,
        "sire_pra":        s.pra_score,
        "sire_coi":        s.coi,
        "dam_hips":        d.hips_score,
        "dam_eyes":        d.eyes_score,
        "dam_elbows":      d.elbows_score,
        "dam_dm":          d.dm_score,
        "dam_pra":         d.pra_score,
        "dam_coi":         d.coi,
        "pair_coi":        req.expected_coi,
        "hip_ratio_4gen":  req.hip_dysplasia_ratio_4gen,
        "avg_hip_score":   avg_hip,
    }])


def _ml_predict(name: str, features: pd.DataFrame) -> Optional[float]:
    """Предсказывает через CatBoost. None если модель не обучена."""
    model = load_model(name)
    if model is None:
        return None
    try:
        proba = model.predict_proba(features)
        return float(proba[0][1])
    except Exception as e:
        logger.warning(f"predictor: CatBoost predict failed '{name}': {e}")
        return None


def _rule(sire, dam, table: dict, default: float, mult: float) -> float:
    """Rule-based риск — среднее риска родителей × поправка на COI."""
    r = (table.get(sire, default) + table.get(dam, default)) / 2
    return round(min(r * mult, 0.99), 3)


def _genetics(sire: Optional[int], dam: Optional[int]) -> float:
    """
    Законы Менделя — аутосомно-рецессивное наследование.
    0=Clear, 1=Carrier, 2=Affected

    Carrier × Carrier → 25% больных потомков
    """
    s = min(sire if sire is not None else 0, 2)
    d = min(dam  if dam  is not None else 0, 2)

    affected = {
        (0,0): 0.00, (0,1): 0.00, (0,2): 0.00,
        (1,0): 0.00, (1,1): 0.25, (1,2): 0.50,
        (2,0): 0.00, (2,1): 0.50, (2,2): 1.00,
    }
    carrier = {
        (0,0): 0.00, (0,1): 0.50, (0,2): 1.00,
        (1,0): 0.50, (1,1): 0.50, (1,2): 0.50,
        (2,0): 1.00, (2,1): 0.50, (2,2): 0.00,
    }
    # Риск болезни + 10% от риска носительства
    return round(affected[(s,d)] + 0.1 * carrier[(s,d)], 3)


def _coi_multiplier(coi: Optional[float]) -> float:
    """Высокий COI увеличивает риск рецессивных болезней."""
    if not coi:   return 1.0
    if coi > 0.125:  return 1.4
    if coi > 0.0625: return 1.2
    if coi > 0.03:   return 1.1
    return 1.0


def _level(risk: float) -> str:
    return "low" if risk < 0.10 else "medium" if risk < 0.30 else "high"


def _make(risk: float, basis: str) -> DiseaseRisk:
    return DiseaseRisk(risk=risk, level=_level(risk), basis=basis)


def predict(req: BreedingPredictRequest) -> BreedingPredictResponse:
    """Предсказывает риски для пары по всем болезням."""
    s, d  = req.sire, req.dam
    coi   = req.expected_coi
    mult  = _coi_multiplier(coi)
    feat  = _build_features(req)
    used_ml = False

    def ml_or_rules(name, sire_score, dam_score, table, default):
        nonlocal used_ml
        risk = _ml_predict(name, feat)
        if risk is not None:
            used_ml = True
            return _make(round(min(risk * mult, 0.99), 3), "ml")
        return _make(_rule(sire_score, dam_score, table, default, mult), "rules")

    # Клинические — ML если обучена, иначе rules
    hip_risk     = ml_or_rules("hip",   s.hips_score,   d.hips_score,   HIP_RISK,    0.15)
    eye_risk     = ml_or_rules("eye",   s.eyes_score,   d.eyes_score,   EYE_RISK,    0.08)
    elbow_risk   = ml_or_rules("elbow", s.elbows_score, d.elbows_score, ELBOW_RISK,  0.05)
    cardiac_risk = _make(_rule(s.cardiac_score, d.cardiac_score, CARDIAC_RISK, 0.05, mult), "rules")
    thyroid_risk = _make(_rule(s.thyroid_score, d.thyroid_score, THYROID_RISK, 0.05, mult), "rules")
    patella_risk = _make(_rule(s.patella_score, d.patella_score, PATELLA_RISK, 0.05, mult), "rules")

    # Генетические — всегда законы Менделя
    dm_risk  = _make(_genetics(s.dm_score,  d.dm_score),  "genetics")
    pra_risk = _make(_genetics(s.pra_score, d.pra_score), "genetics")
    pll_risk = _make(_genetics(s.pll_score, d.pll_score), "genetics")
    lpp_risk = _make(_genetics(s.lpp_score, d.lpp_score), "genetics")

    # Топ-5 рисков
    all_risks = {
        "Дисплазия бёдер":           hip_risk,
        "Дисплазия локтей":          elbow_risk,
        "Болезни глаз":              eye_risk,
        "Патология пателлы":         patella_risk,
        "Болезни сердца":            cardiac_risk,
        "Болезни щитовидки":         thyroid_risk,
        "Дегенеративная миелопатия": dm_risk,
        "PRA (атрофия сетчатки)":    pra_risk,
        "PLL (вывих хрусталика)":    pll_risk,
        "Полинейропатия":            lpp_risk,
    }
    top5 = sorted(
        [{"disease": k, "risk": v.risk, "level": v.level, "basis": v.basis}
         for k, v in all_risks.items()],
        key=lambda x: x["risk"],
        reverse=True,
    )[:5]

    # Уверенность — сколько ключевых полей передано
    filled = sum(1 for v in [
        s.hips_score, s.eyes_score, s.dm_score, s.coi,
        d.hips_score, d.eyes_score, d.dm_score, d.coi, coi,
    ] if v is not None)
    confidence = "high" if filled >= 6 else "medium" if filled >= 3 else "low"

    # Итоговая рекомендация
    high_count = sum(1 for v in all_risks.values() if v.level == "high")
    med_count  = sum(1 for v in all_risks.values() if v.level == "medium")
    if high_count >= 2 or any(v.risk > 0.50 for v in all_risks.values()):
        recommendation = "not_recommended"
    elif high_count >= 1 or med_count >= 3:
        recommendation = "caution"
    else:
        recommendation = "recommended"

    return BreedingPredictResponse(
        hip_dysplasia=hip_risk,
        elbow_dysplasia=elbow_risk,
        patella=patella_risk,
        eye_disease=eye_risk,
        pra=pra_risk,
        pll=pll_risk,
        degenerative_myelopathy=dm_risk,
        polyneuropathy=lpp_risk,
        cardiac=cardiac_risk,
        thyroid=thyroid_risk,
        confidence=confidence,
        recommendation=recommendation,
        model_used="catboost" if used_ml else "rules_and_genetics",
        features_used=FEATURE_COLS,
        top_risks=top5,
    )

