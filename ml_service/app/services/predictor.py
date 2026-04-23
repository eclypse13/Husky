import logging
import numpy as np
import joblib
from pathlib import Path
from typing import Optional

from ..schemas.breeding import BreedingPredictRequest, BreedingPredictResponse

logger = logging.getLogger(__name__)

MODELS_DIR = Path("/app/data/models")
RF_MODEL_PATH = MODELS_DIR / "random_forest.joblib"
LR_MODEL_PATH = MODELS_DIR / "logistic_regression.joblib"

# Риск дисплазии по OFA score родителя (ветеринарные правила)
HIP_RISK_BY_SCORE = {
    0: 0.05,   # Excellent
    1: 0.10,   # Good
    2: 0.18,   # Fair
    3: 0.30,   # Borderline
    4: 0.45,   # Mild
    5: 0.60,   # Moderate
    6: 0.75,   # Severe
}

EYE_RISK_BY_SCORE = {0: 0.05, 1: 0.50}


def extract_features(req: BreedingPredictRequest):
    """
    Преобразует запрос в вектор признаков для ML.
    Отсутствующие данные заполняем медианами.
    Возвращает (массив признаков, список использованных полей).
    """
    features = {}
    used = []

    # Кобель
    features["sire_hips"] = req.sire.hips_score if req.sire.hips_score is not None else 1.5
    if req.sire.hips_score is not None:
        used.append("sire_hips")

    features["sire_eyes"] = req.sire.eyes_score if req.sire.eyes_score is not None else 0.1
    if req.sire.eyes_score is not None:
        used.append("sire_eyes")

    features["sire_coi"] = req.sire.coi if req.sire.coi is not None else 0.03
    if req.sire.coi is not None:
        used.append("sire_coi")

    # Сука
    features["dam_hips"] = req.dam.hips_score if req.dam.hips_score is not None else 1.5
    if req.dam.hips_score is not None:
        used.append("dam_hips")

    features["dam_eyes"] = req.dam.eyes_score if req.dam.eyes_score is not None else 0.1
    if req.dam.eyes_score is not None:
        used.append("dam_eyes")

    features["dam_coi"] = req.dam.coi if req.dam.coi is not None else 0.03
    if req.dam.coi is not None:
        used.append("dam_coi")

    # Пара
    features["pair_coi"] = req.expected_coi if req.expected_coi is not None else 0.04
    if req.expected_coi is not None:
        used.append("pair_coi")

    features["hip_ratio_4gen"] = req.hip_dysplasia_ratio_4gen if req.hip_dysplasia_ratio_4gen is not None else 0.15
    if req.hip_dysplasia_ratio_4gen is not None:
        used.append("hip_dysplasia_ratio_4gen")

    features["avg_hip_score"] = (features["sire_hips"] + features["dam_hips"]) / 2

    arr = np.array([
        features["sire_hips"], features["sire_eyes"], features["sire_coi"],
        features["dam_hips"], features["dam_eyes"], features["dam_coi"],
        features["pair_coi"], features["hip_ratio_4gen"], features["avg_hip_score"],
    ]).reshape(1, -1)

    return arr, used


def rule_based_predict(req: BreedingPredictRequest):
    """
    Ветеринарные правила — работает всегда даже без обученной модели.
    Используется как fallback.
    """
    sire_hip = HIP_RISK_BY_SCORE.get(req.sire.hips_score, 0.20)
    dam_hip = HIP_RISK_BY_SCORE.get(req.dam.hips_score, 0.20)
    hip_risk = (sire_hip + dam_hip) / 2

    if req.hip_dysplasia_ratio_4gen is not None:
        hip_risk = hip_risk * 0.7 + req.hip_dysplasia_ratio_4gen * 0.3

    if req.expected_coi is not None:
        if req.expected_coi > 0.125:
            hip_risk = min(hip_risk * 1.3, 0.95)
        elif req.expected_coi > 0.0625:
            hip_risk = min(hip_risk * 1.1, 0.95)

    sire_eye = EYE_RISK_BY_SCORE.get(req.sire.eyes_score, 0.08)
    dam_eye = EYE_RISK_BY_SCORE.get(req.dam.eyes_score, 0.08)
    eye_risk = (sire_eye + dam_eye) / 2

    return round(hip_risk, 3), round(eye_risk, 3)


def get_confidence(features_used):
    key = {"sire_hips", "dam_hips", "pair_coi"}
    has = len(key & set(features_used))
    if has == 3 and len(features_used) >= 5:
        return "high"
    elif has >= 2:
        return "medium"
    return "low"


def get_risk_level(risk: float) -> str:
    if risk < 0.15:
        return "low"
    elif risk < 0.35:
        return "medium"
    return "high"


def get_recommendation(hip_risk: float, eye_risk: float, coi: Optional[float]) -> str:
    if hip_risk > 0.40 or eye_risk > 0.35:
        return "not_recommended"
    if hip_risk > 0.25 or eye_risk > 0.20:
        return "caution"
    if coi and coi > 0.125:
        return "caution"
    return "recommended"


def predict(req: BreedingPredictRequest) -> BreedingPredictResponse:
    """
    Главная функция предсказания.
    Порядок: Random Forest → Logistic Regression → Rule-based
    """
    features, used = extract_features(req)
    model_used = "rule_based"
    hip_risk = None

    # Пробуем Random Forest
    if RF_MODEL_PATH.exists():
        try:
            rf = joblib.load(RF_MODEL_PATH)
            proba = rf.predict_proba(features)
            hip_risk = float(proba[0][1])
            model_used = "random_forest"
        except Exception as e:
            logger.warning(f"RF failed: {e}")

    # Fallback: Logistic Regression
    if hip_risk is None and LR_MODEL_PATH.exists():
        try:
            lr = joblib.load(LR_MODEL_PATH)
            proba = lr.predict_proba(features)
            hip_risk = float(proba[0][1])
            model_used = "logistic_regression"
        except Exception as e:
            logger.warning(f"LR failed: {e}")

    # Fallback: правила
    if hip_risk is None:
        hip_risk, eye_risk = rule_based_predict(req)
    else:
        _, eye_risk = rule_based_predict(req)

    confidence = get_confidence(used)

    return BreedingPredictResponse(
        hip_dysplasia_risk=hip_risk,
        eye_problem_risk=eye_risk,
        hip_risk_level=get_risk_level(hip_risk),
        eye_risk_level=get_risk_level(eye_risk),
        confidence=confidence,
        features_used=used,
        recommendation=get_recommendation(hip_risk, eye_risk, req.expected_coi),
        model_used=model_used,
    )
