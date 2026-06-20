"""
HTTP клиент для обращения к ML сервису.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

ML_SERVICE_URL = getattr(settings, "ML_SERVICE_URL", "http://ml_service:8001")

PREDICT_TIMEOUT = 10
TRAIN_TIMEOUT = 120  # обучение долгое
HEALTH_TIMEOUT = 5


# Обертка для запросов
def _safe_request(method: str, url: str, **kwargs) -> dict:
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
    payload = {
        "sire": sire_data,
        "dam": dam_data,
        **pair_data,
    }
    return _safe_request("POST", f"{ML_SERVICE_URL}/breeding/predict", json=payload, timeout=PREDICT_TIMEOUT)


def train_models(dataset: list[dict]) -> dict:
    return _safe_request("POST", f"{ML_SERVICE_URL}/breeding/train", json={"dataset": dataset}, timeout=TRAIN_TIMEOUT)


def check_health() -> dict:
    return _safe_request("GET", f"{ML_SERVICE_URL}/breeding/health", timeout=HEALTH_TIMEOUT)
