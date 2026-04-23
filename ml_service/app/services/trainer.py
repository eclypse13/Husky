import logging
import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

MODELS_DIR = Path("/app/data/models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "sire_hips", "sire_eyes", "sire_coi",
    "dam_hips", "dam_eyes", "dam_coi",
    "pair_coi", "hip_ratio_4gen", "avg_hip_score",
]


def train(dataset: list[dict]) -> dict:
    """
    Обучает Random Forest и Logistic Regression.

    Каждая запись датасета:
    {
        "sire_hips": 1, "sire_eyes": 0, "sire_coi": 0.03,
        "dam_hips": 0, "dam_eyes": 0, "dam_coi": 0.02,
        "pair_coi": 0.04, "hip_ratio_4gen": 0.10, "avg_hip_score": 0.5,
        "offspring_has_dysplasia": 0   ← целевая переменная (0 или 1)
    }
    """
    if len(dataset) < 30:
        return {"error": f"Мало данных: {len(dataset)} (нужно минимум 30)"}

    df = pd.DataFrame(dataset)
    X = df[FEATURE_COLS].fillna(df[FEATURE_COLS].median())
    y = df["offspring_has_dysplasia"]

    logger.info(f"Обучение: {len(df)} записей, позитивных: {y.sum()} ({y.mean():.1%})")

    results = {}

    # Random Forest
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=42,
    )
    rf_scores = cross_val_score(rf, X, y, cv=5, scoring="roc_auc")
    rf.fit(X, y)
    joblib.dump(rf, MODELS_DIR / "random_forest.joblib")

    results["random_forest"] = {
        "roc_auc": round(float(rf_scores.mean()), 3),
        "roc_auc_std": round(float(rf_scores.std()), 3),
        "feature_importances": dict(zip(
            FEATURE_COLS,
            rf.feature_importances_.round(3).tolist()
        )),
    }

    # Logistic Regression
    lr = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)),
    ])
    lr_scores = cross_val_score(lr, X, y, cv=5, scoring="roc_auc")
    lr.fit(X, y)
    joblib.dump(lr, MODELS_DIR / "logistic_regression.joblib")

    results["logistic_regression"] = {
        "roc_auc": round(float(lr_scores.mean()), 3),
        "roc_auc_std": round(float(lr_scores.std()), 3),
    }

    results["dataset_size"] = len(df)
    results["positive_rate"] = round(float(y.mean()), 3)
    results["best_model"] = (
        "random_forest"
        if results["random_forest"]["roc_auc"] >= results["logistic_regression"]["roc_auc"]
        else "logistic_regression"
    )

    return results
