"""
Конфигурация ML сервиса.
"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Путь к папке с моделями
    models_dir: Path = Path("/app/data/models")

    # Минимум позитивных случаев для обучения
    min_positive_samples: int = 10

    # Параметры CatBoost
    catboost_iterations: int = 500
    catboost_learning_rate: float = 0.05
    catboost_depth: int = 6

    class Config:
        env_prefix = "ML_"


settings = Settings()

# Создание папки для моделей при старте
settings.models_dir.mkdir(parents=True, exist_ok=True)

# FEATURE_COLS — единственный источник правды о наборе/порядке признаков на стороне ML
FEATURE_COLS = [
    # Прямые родители пары
    "sire_hips", "sire_eyes", "sire_elbows", "sire_dm", "sire_pra", "sire_coi",
    "dam_hips", "dam_eyes", "dam_elbows", "dam_dm", "dam_pra", "dam_coi",
    "pair_coi", "avg_hip_score",

    # Агрегаты по предкам (dogs_module/services/ancestor_features.py) ──
    # tested_ratio — доля протестированных предков (показатель полноты данных)
    # mean  — средний балл по известным предкам (NaN если никто не тестирован)
    # affected_ratio — доля больных среди протестированных (NaN если никто не тестирован)
    "sire_anc_hips_tested_ratio", "sire_anc_hips_mean", "sire_anc_hips_affected_ratio",
    "sire_anc_eyes_tested_ratio", "sire_anc_eyes_mean", "sire_anc_eyes_affected_ratio",
    "dam_anc_hips_tested_ratio", "dam_anc_hips_mean", "dam_anc_hips_affected_ratio",
    "dam_anc_eyes_tested_ratio", "dam_anc_eyes_mean", "dam_anc_eyes_affected_ratio",
]

# В ответе elbow_dysplasia
# остаётся (его считает rules-ветка в predictor), схема не меняется.
TARGETS = {
    "hip": "offspring_has_hip_problem",
    "eye": "offspring_has_eye_problem",
}
