# dogs_module/services/ml_client.py
"""
HTTP клиент для обращения к ML сервису.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ML_SERVICE_URL = getattr(settings, "ML_SERVICE_URL", "http://ml_service:8001")

# Таймауты HTTP к ML-сервису, сек
PREDICT_TIMEOUT = 10
TRAIN_TIMEOUT = 120  # обучение долгое
HEALTH_TIMEOUT = 5


def _safe_request(method: str, url: str, **kwargs) -> dict:
    """
    Единая обёртка для HTTP-запросов к ML-сервису.
    Обрабатывает Timeout, ConnectionError, HTTPError — без дублирования.
    """
    try:
        resp = requests.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout:
        logger.error(f"ML service {method} {url}: timeout")
        return {"error": "ML service timeout"}
    except requests.ConnectionError:
        logger.error(f"ML service {method} {url}: недоступен")
        return {"error": "ML service unavailable"}
    except requests.HTTPError as e:
        logger.error(f"ML service {method} {url} HTTP error: {e}")
        return {"error": f"HTTP error: {e}"}
    except requests.RequestException as e:
        logger.error(f"ML service {method} {url} error: {e}")
        return {"error": str(e)}


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
        "dam": dam_data,
        **pair_data,
    }
    return _safe_request("POST", f"{ML_SERVICE_URL}/breeding/predict", json=payload, timeout=PREDICT_TIMEOUT)


def train_models(dataset: list[dict]) -> dict:
    """
    Отправляет датасет в ML сервис для обучения моделей.
    Вызывается из Celery задачи.
    """
    return _safe_request("POST", f"{ML_SERVICE_URL}/breeding/train", json={"dataset": dataset}, timeout=TRAIN_TIMEOUT)


def check_health() -> dict:
    """Проверяет что ML сервис работает."""
    return _safe_request("GET", f"{ML_SERVICE_URL}/breeding/health", timeout=HEALTH_TIMEOUT)
