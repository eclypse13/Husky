from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..schemas.breeding import BreedingPredictRequest, BreedingPredictResponse
from ..services.predictor import predict
from ..services.trainer import train
from ..services.model_store import list_trained_models

router = APIRouter(prefix="/breeding", tags=["breeding"])


class TrainRequest(BaseModel):
    dataset: list[dict]


# Предсказывает риски для пары sire × dam
@router.post("/predict", response_model=BreedingPredictResponse)
def predict_breeding(req: BreedingPredictRequest):
    try:
        return predict(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Обучает модели на датасете
@router.post("/train")
def train_model(req: TrainRequest):
    if not req.dataset:
        raise HTTPException(status_code=400, detail="Пустой датасет")
    result = train(req.dataset)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# Статус сервиса и список обученных моделей
@router.get("/health")
def health():
    return {
        "status": "ok",
        "models": list_trained_models(),
    }
