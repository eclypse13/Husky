# ml_service/app/routers/breeding.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..schemas.breeding import BreedingPredictRequest, BreedingPredictResponse
from ..services.predictor import predict
from ..services.trainer import train
from ..services.model_store import list_trained_models, invalidate_cache

router = APIRouter(prefix="/breeding", tags=["breeding"])


class TrainRequest(BaseModel):
    dataset: list[dict]


@router.post("/predict", response_model=BreedingPredictResponse)
def predict_breeding(req: BreedingPredictRequest):
    """Предсказывает риски для пары sire × dam."""
    try:
        return predict(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train")
def train_model(req: TrainRequest):
    """
    Обучает модели на датасете.
    Вызывается из Django Celery задачи.
    """
    if not req.dataset:
        raise HTTPException(status_code=400, detail="Пустой датасет")
    result = train(req.dataset)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/health")
def health():
    """Статус сервиса и список обученных моделей."""
    return {
        "status": "ok",
        "models": list_trained_models(),
    }