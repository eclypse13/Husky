# ml_service/app/schemas/breeding.py
from pydantic import BaseModel, ConfigDict
from typing import Optional


class DogHealthData(BaseModel):
    """Данные здоровья одной собаки."""
    dog_id: int

    # Клинические тесты
    hips_score: Optional[int] = None  # 0=Excellent..6=Severe
    eyes_score: Optional[int] = None  # 0=Normal, 1=Affected
    elbows_score: Optional[int] = None  # 0=Normal..3=Grade III
    patella_score: Optional[int] = None  # 0=Normal, 1=Abnormal
    cardiac_score: Optional[int] = None  # 0=Normal, 1=Abnormal
    thyroid_score: Optional[int] = None  # 0=Normal, 1=Abnormal

    # Генетические тесты (0=Clear, 1=Carrier, 2=Affected)
    dm_score: Optional[int] = None  # Degenerative Myelopathy
    pra_score: Optional[int] = None  # Progressive Retinal Atrophy
    pll_score: Optional[int] = None  # Primary Lens Luxation
    lpp_score: Optional[int] = None  # Laryngeal Paralysis & Polyneuropathy

    coi: Optional[float] = None  # коэффициент инбридинга 0.0-1.0


class BreedingPredictRequest(BaseModel):
    """Запрос предсказания для пары. Django отправляет — ML отвечает."""
    sire: DogHealthData
    dam:  DogHealthData

    expected_coi: Optional[float] = None
    common_ancestors_count: Optional[int] = None
    hip_dysplasia_ratio_4gen: Optional[float] = None


class DiseaseRisk(BaseModel):
    """Риск по одной болезни."""
    risk: float  # вероятность 0.0 - 1.0
    level: str    # low / medium / high
    basis: str    # ml / rules / genetics


class BreedingPredictResponse(BaseModel):
    """Ответ ML сервиса — риски по всем болезням."""
    model_config = ConfigDict(protected_namespaces=())

    # Клинические
    hip_dysplasia: DiseaseRisk
    elbow_dysplasia: DiseaseRisk
    patella: DiseaseRisk
    eye_disease: DiseaseRisk
    cardiac: DiseaseRisk
    thyroid: DiseaseRisk

    # Генетические (законы Менделя)
    degenerative_myelopathy: DiseaseRisk
    pra: DiseaseRisk
    pll: DiseaseRisk
    polyneuropathy: DiseaseRisk

    # Итог
    confidence: str         # high / medium / low
    recommendation: str         # recommended / caution / not_recommended
    model_used: str         # random_forest / logistic_regression / rules_and_genetics
    features_used: list[str]
    top_risks: list[dict]  # топ-5 наиболее вероятных