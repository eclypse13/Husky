"""
Обучение CatBoost моделей — по одной на каждую болезнь.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

from .model_store import save_model, invalidate_cache
from ..config import settings, FEATURE_COLS, TARGETS

logger = logging.getLogger(__name__)


def _train_one(X: pd.DataFrame, y: pd.Series, name: str) -> dict:
    from catboost import CatBoostClassifier, Pool

    positive = int(y.sum())
    total = len(y)
    rate = positive / total if total else 0

    if positive < settings.min_positive_samples:
        msg = f"мало позитивных случаев: {positive} (нужно {settings.min_positive_samples})"
        logger.warning(f"trainer {name}: {msg}")
        return {"skipped": True, "reason": msg, "positive": positive}

    logger.info(f"trainer {name}: {total} записей, позитивных: {positive} ({rate:.1%})")

    n_splits = min(5, positive)
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    auc_scores = []

    for train_idx, val_idx in cv.split(X, y):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        fold_model = CatBoostClassifier(
            iterations=settings.catboost_iterations,
            learning_rate=settings.catboost_learning_rate,
            depth=settings.catboost_depth,
            auto_class_weights="Balanced",
            eval_metric="AUC",
            random_seed=42,
            verbose=False,
            allow_writing_files=False,
        )
        fold_model.fit(
            Pool(X_tr, y_tr),
            eval_set=Pool(X_val, y_val),
            early_stopping_rounds=50,
        )
        proba = fold_model.predict_proba(X_val)[:, 1]
        auc_scores.append(roc_auc_score(y_val, proba))

    final_model = CatBoostClassifier(
        iterations=settings.catboost_iterations,
        learning_rate=settings.catboost_learning_rate,
        depth=settings.catboost_depth,
        auto_class_weights="Balanced",
        eval_metric="AUC",
        random_seed=42,
        verbose=False,
        allow_writing_files=False,
    )
    final_model.fit(Pool(X, y))

    save_model(final_model, name)

    auc_mean = round(float(np.mean(auc_scores)), 3)
    auc_std = round(float(np.std(auc_scores)), 3)

    importances = dict(zip(
        FEATURE_COLS,
        [round(v, 3) for v in final_model.get_feature_importance()]
    ))

    logger.info(f"trainer {name}: ROC-AUC={auc_mean}±{auc_std}")
    return {
        "skipped": False,
        "positive": positive,
        "positive_rate": round(rate, 3),
        "roc_auc": auc_mean,
        "roc_auc_std": auc_std,
        "feature_importances": importances,
        "best_model": "catboost",
    }


def train(dataset: list[dict]) -> dict:
    """Обучает модели для всех болезней."""
    if len(dataset) < 30:
        return {"error": f"Мало данных: {len(dataset)} (нужно минимум 30)"}

    clean = [{k: v for k, v in row.items() if not k.startswith("_")} for row in dataset]
    df = pd.DataFrame(clean)

    # reindex (не df[FEATURE_COLS]): недостающие колонки → NaN вместо KeyError.
    X_full = df.reindex(columns=FEATURE_COLS)

    results = {"dataset_size": len(df), "models": {}}

    for short_name, col in TARGETS.items():
        if col not in df.columns:
            results["models"][short_name] = {
                "skipped": True,
                "reason": f"колонка {col} отсутствует",
            }
            continue

        # Берём только строки с непустой меткой для этой модели
        mask = df[col].notna()
        X_subset = X_full[mask]
        y = df.loc[mask, col].astype(int)

        if len(y) == 0:
            results["models"][short_name] = {
                "skipped": True,
                "reason": "нет размеченных примеров",
            }
            continue

        result = _train_one(X_subset, y, short_name)
        result["labeled_samples"] = len(y)  # сколько строк фактически в обучении
        results["models"][short_name] = result

        if not result.get("skipped"):
            invalidate_cache(short_name)

    trained = [k for k, v in results["models"].items() if not v.get("skipped")]
    skipped = [k for k, v in results["models"].items() if v.get("skipped")]
    results["trained"] = trained
    results["skipped"] = skipped

    logger.info(f"trainer: обучено={trained}, пропущено={skipped}")
    return results
