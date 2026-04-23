from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

from ..schemas.breeding import BreedingPredictRequest, BreedingPredictResponse
from ..services.predictor import predict
from ..services.trainer import train

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
    """Обучает модели на датасете."""
    if not req.dataset:
        raise HTTPException(status_code=400, detail="Пустой датасет")
    result = train(req.dataset)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/health")
def health():
    """Проверка что сервис работает и модели загружены."""
    rf = Path("/app/data/models/random_forest.joblib").exists()
    lr = Path("/app/data/models/logistic_regression.joblib").exists()
    return {
        "status": "ok",
        "models": {
            "random_forest": "ready" if rf else "not trained yet",
            "logistic_regression": "ready" if lr else "not trained yet",
        }
    }
