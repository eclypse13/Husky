from pydantic import BaseModel, ConfigDict
from typing import Optional


class DogHealthData(BaseModel):
    """Данные здоровья одной собаки."""

    dog_id: int

    # Бёдра: 0=Excellent, 1=Good, 2=Fair, 3=Borderline, 4=Mild, 5=Moderate, 6=Severe
    hips_score: Optional[int] = None

    # Глаза: 0=Normal, 1=Affected
    eyes_score: Optional[int] = None

    # Локти: 0=Normal, 1=Grade1, 2=Grade2, 3=Grade3
    elbows_score: Optional[int] = None

    # Коэффициент инбридинга (0.0 - 1.0)
    coi: Optional[float] = None


class BreedingPredictRequest(BaseModel):
    """Запрос предсказания для пары."""

    sire: DogHealthData   # кобель
    dam: DogHealthData    # сука

    # COI ожидаемого потомства — считается в Django
    expected_coi: Optional[float] = None

    # Число общих предков пары
    common_ancestors_count: Optional[int] = None

    # Доля предков с дисплазией за 4 поколения (0.0 - 1.0)
    hip_dysplasia_ratio_4gen: Optional[float] = None


class BreedingPredictResponse(BaseModel):
    """Ответ ML сервиса."""

    model_config = ConfigDict(protected_namespaces=())

    # Риски (вероятность 0.0 - 1.0)
    hip_dysplasia_risk: float
    eye_problem_risk: float

    # Уровень риска: low / medium / high
    hip_risk_level: str
    eye_risk_level: str

    # Уверенность: high / medium / low
    confidence: str

    # Какие поля были использованы
    features_used: list[str]

    # Итоговая рекомендация
    recommendation: str  # recommended / caution / not_recommended

    # Какой алгоритм дал результат
    model_used: str  # random_forest / logistic_regression / rule_based
