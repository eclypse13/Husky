# dogs_module/tasks/tasks_ml.py
"""
Celery задачи для ML.

train_ml_model_task  — собирает датасет и отправляет в ML сервис на обучение
predict_breeding_task — предсказывает риски для пары
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="dogs_module.train_ml_model_task")
def train_ml_model_task(self) -> dict:
    """
    Собирает датасет из БД и обучает ML модели.

    Запускать:
      - вручную через Swagger
      - по расписанию раз в неделю через Celery Beat
      - после массового импорта OFA данных
    """
    from ..services.dataset_builder import build_dataset
    from ..services.ml_client import train_models

    logger.info("Запуск обучения ML модели...")

    dataset = build_dataset()
    if not dataset:
        return {"error": "Датасет пустой — нет потомков с OFA тестами"}

    logger.info(f"Датасет собран: {len(dataset)} записей, отправляем в ML сервис...")

    # Убираем мета-поля перед отправкой
    clean_dataset = [
        {k: v for k, v in row.items() if not k.startswith("_")}
        for row in dataset
    ]

    result = train_models(clean_dataset)
    logger.info(f"Обучение завершено: {result}")
    return result


@shared_task(bind=True, name="dogs_module.predict_breeding_task")
def predict_breeding_task(self, sire_id: int, dam_id: int) -> dict:
    """
    Предсказывает риски для пары через ML сервис.
    Собирает данные из БД и отправляет запрос.
    """
    from ..models import Dog, MedicalRecord
    from ..services.ml_client import predict_breeding
    from ..utils.coi_calculator import calculate_coi

    def get_dog_data(dog_id: int) -> dict:
        try:
            dog = Dog.objects.using("dogs_db").get(pk=dog_id)
        except Dog.DoesNotExist:
            return {"dog_id": dog_id}

        records = list(
            MedicalRecord.objects.using("dogs_db")
            .filter(dog_id=dog_id, source="ofa")
            .values("registry", "conclusion")
        )

        hips_score = None
        eyes_score = None
        hip_map = {"EXCELLENT": 0, "GOOD": 1, "FAIR": 2,
                   "BORDERLINE": 3, "MILD": 4, "MODERATE": 5, "SEVERE": 6}
        eye_map = {"NORMAL": 0, "AFFECTED": 1}

        for r in records:
            reg = r["registry"].upper()
            conclusion = (r["conclusion"] or "").upper().strip()
            if reg == "HIPS":
                hips_score = hip_map.get(conclusion)
            if "EYE" in reg or "OPTH" in reg:
                eyes_score = eye_map.get(conclusion)

        return {
            "dog_id":    dog_id,
            "hips_score": hips_score,
            "eyes_score":  eyes_score,
            "coi":        float(dog.coi) if dog.coi else None,
        }

    sire_data = get_dog_data(sire_id)
    dam_data = get_dog_data(dam_id)

    # COI потомства считаем через существующий калькулятор
    try:
        sire_dog = Dog.objects.using("dogs_db").get(pk=sire_id)
        expected_coi = None  # TODO: calculate_coi для пары
    except Exception:
        expected_coi = None

    pair_data = {
        "expected_coi": expected_coi,
        "common_ancestors_count": None,
        "hip_dysplasia_ratio_4gen": None,
    }

    result = predict_breeding(sire_data, dam_data, pair_data)
    logger.info(f"Прогноз для пары {sire_id}×{dam_id}: {result}")
    return result
