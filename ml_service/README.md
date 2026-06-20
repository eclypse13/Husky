# ML Service

Микросервис прогнозирования наследственных рисков вязки для платформы НКП «Сибирский хаски». Обучается на парах «родители — потомок» из БД и предсказывает вероятность дисплазии тазобедренных суставов и патологии глаз у будущего потомства.

## Стек

- **FastAPI** — HTTP API
- **CatBoost** — градиентный бустинг, две независимые модели (hip / eye)
- **scikit-learn** — кросс-валидация, метрики
- **Docker** — изоляция от основного Django-приложения

## Архитектура

```
ml_service/
├── app/
│   ├── main.py                 # FastAPI app, регистрация роутеров
│   ├── config.py               # FEATURE_COLS, гиперпараметры, пути
│   ├── routers/
│   │   └── breeding.py         # /predict, /train, /health
│   ├── schemas/
│   │   └── breeding.py         # Pydantic-модели запросов/ответов
│   └── services/
│       ├── trainer.py          # обучение CatBoostClassifier с CV
│       ├── predictor.py        # инференс
│       └── model_store.py      # загрузка/сохранение .cbm с кэшем
└── requirements.txt
```

## API

| Метод | Эндпоинт | Назначение |
|---|---|---|
| `GET`  | `/health`  | проверка работоспособности |
| `POST` | `/predict` | прогноз риска для пары признаков |
| `POST` | `/train`   | переобучение моделей на переданном датасете |

Все вызовы идут из Django по внутренней Docker-сети через `ml_client`.

## Признаки

Модели принимают **26 признаков** (см. `config.FEATURE_COLS`):
- 12 прямых признаков родителей (бёдра, глаза, локти, DM, PRA, COI каждого)
- 12 агрегатов по предкам (BFS на 4 поколения, отдельно для линии отца и матери)
- 2 признака пары (pair_coi, avg_hip_score)

Сборка вектора выполняется в Django через `feature_builder.py` — единый источник для обучения и инференса.

## Запуск

```bash
docker compose up ml-service
```

Сервис поднимается на `http://ml-service:8001`. Модели сохраняются в `/app/data/models/catboost_{hip,eye}.cbm`.

## Переобучение

```bash
docker compose exec web python manage.py shell -c "
from dogs_module.tasks.tasks_ml import train_ml_model_task
train_ml_model_task.delay(augment=True, n_synthetic=2000)
"
```