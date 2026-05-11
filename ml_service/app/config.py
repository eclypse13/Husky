# ml_service/app/config.py
"""
Конфигурация ML сервиса.
Все настройки в одном месте.
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

# Создаём папку для моделей при старте
settings.models_dir.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "sire_hips", "sire_eyes", "sire_elbows", "sire_dm", "sire_pra", "sire_coi",
    "dam_hips",  "dam_eyes",  "dam_elbows",  "dam_dm",  "dam_pra",  "dam_coi",
    "pair_coi",  "hip_ratio_4gen", "avg_hip_score",
]

TARGETS = {
    "hip":   "offspring_has_hip_problem",
    "eye":   "offspring_has_eye_problem",
    "elbow": "offspring_has_elbow_problem",
}