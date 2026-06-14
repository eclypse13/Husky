# dogs_module/tasks/tasks_ml.py
"""
ML таски.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="dogs_module.train_ml_model_task")
def train_ml_model_task(
        self,
        augment: bool = False,
        n_synthetic: int = 1000,
) -> dict:
    """
    Собирает датасет и обучает ML модели.

    Параметры:
      augment — добавить синтетические данные
      n_synthetic — сколько синтетических записей
    """
    from ..services.dataset_builder import build_dataset
    from ..services.ml_client import train_models

    logger.info(f"Запуск обучения ML... augment={augment}, n_synthetic={n_synthetic}")

    dataset = build_dataset(augment=augment, n_synthetic=n_synthetic)
    if not dataset:
        return {"error": "Датасет пустой"}

    clean = [
        {k: v for k, v in row.items() if not k.startswith("_")}
        for row in dataset
    ]

    real_count = sum(1 for r in dataset if not r.get("_synthetic"))
    synthetic_count = sum(1 for r in dataset if r.get("_synthetic"))

    logger.info(
        f"Датасет: {len(clean)} записей "
        f"(реальных={real_count}, синтетических={synthetic_count}), "
        f"отправляем в ML сервис"
    )

    result = train_models(clean)
    logger.info(f"Обучение завершено: {result}")
    return result


@shared_task(bind=True, name="dogs_module.predict_breeding_task")
def predict_breeding_task(self, sire_id: int, dam_id: int) -> dict:
    from ..services.ml_dog_service import predict_pair

    result = predict_pair(sire_id, dam_id)

    if "error" in result:
        logger.error(f"ML predict failed: {result['error']}")
        return result

    logger.info(f"Прогноз {sire_id}×{dam_id}: recommendation={result.get('recommendation')}")
    return result
