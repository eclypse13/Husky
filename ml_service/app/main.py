from fastapi import FastAPI
from .routers import breeding

app = FastAPI(
    title="Breeding ML Service",
    description="ML предсказания рисков для вязки собак",
    version="3.0.0",
)

app.include_router(breeding.router)


@app.get("/")
def root():
    return {"service": "breeding-ml", "version": "3.0.0", "status": "ok"}
