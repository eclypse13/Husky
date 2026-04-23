from fastapi import FastAPI
from .routers import breeding

app = FastAPI(
    title="Breeding ML Service",
    description="ML предсказания для вязок собак",
    version="1.0.0",
)

app.include_router(breeding.router)


@app.get("/")
def root():
    return {"service": "breeding-ml", "status": "ok"}
