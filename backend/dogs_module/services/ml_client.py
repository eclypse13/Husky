# dogs_module/services/ml_client.py
"""
HTTP клиент для обращения к ML сервису из Django.
Никакой бизнес-логики — только HTTP запросы.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ML_SERVICE_URL = getattr(settings, "ML_SERVICE_URL", "http://ml_service:8001")


def predict_breeding(sire_data: dict, dam_data: dict, pair_data: dict) -> dict:
    """
    Отправляет данные о паре в ML сервис и возвращает предсказание.

    sire_data / dam_data:
      {"dog_id": 123, "hips_score": 1, "eyes_score": 0, "coi": 0.03}

    pair_data:
      {"expected_coi": 0.04, "hip_dysplasia_ratio_4gen": 0.1}
    """
    payload = {
        "sire": sire_data,
        "dam":  dam_data,
        **pair_data,
    }
    try:
        resp = requests.post(
            f"{ML_SERVICE_URL}/breeding/predict",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout:
        logger.error("ML service predict: timeout")
        return {"error": "ML service timeout"}
    except requests.ConnectionError:
        logger.error("ML service predict: недоступен")
        return {"error": "ML service unavailable"}
    except requests.HTTPError as e:
        logger.error(f"ML service predict HTTP error: {e}")
        return {"error": f"HTTP error: {e}"}
    except requests.RequestException as e:
        logger.error(f"ML service predict error: {e}")
        return {"error": str(e)}


def train_models(dataset: list[dict]) -> dict:
    """
    Отправляет датасет в ML сервис для обучения моделей.
    Вызывается из Celery задачи.
    """
    try:
        resp = requests.post(
            f"{ML_SERVICE_URL}/breeding/train",
            json={"dataset": dataset},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout:
        logger.error("ML service train: timeout")
        return {"error": "ML service timeout"}
    except requests.ConnectionError:
        logger.error("ML service train: недоступен")
        return {"error": "ML service unavailable"}
    except requests.HTTPError as e:
        logger.error(f"ML service train HTTP error: {e}")
        return {"error": f"HTTP error: {e}"}
    except requests.RequestException as e:
        logger.error(f"ML service train error: {e}")
        return {"error": str(e)}


def check_health() -> dict:
    """Проверяет что ML сервис работает."""
    try:
        resp = requests.get(f"{ML_SERVICE_URL}/breeding/health", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout:
        return {"status": "unavailable", "error": "timeout"}
    except requests.ConnectionError:
        return {"status": "unavailable", "error": "connection error"}
    except requests.RequestException as e:
        logger.error(f"ML service health check failed: {e}")
        return {"status": "unavailable", "error": str(e)}