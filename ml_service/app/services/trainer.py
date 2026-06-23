"""
Обучение CatBoost моделей .
"""

import logging
import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    brier_score_loss,
)
from sklearn.model_selection import StratifiedKFold

from .model_store import save_model, invalidate_cache
from ..config import settings, FEATURE_COLS, TARGETS

logger = logging.getLogger(__name__)

# Вычисление метрик
def _compute_metrics(y_true, proba, threshold: float = 0.5) -> dict:
    preds = (proba >= threshold).astype(int)
    return {
        "roc_auc": roc_auc_score(y_true, proba),
        "pr_auc": average_precision_score(y_true, proba),
        "precision": precision_score(y_true, preds, zero_division=0),
        "recall": recall_score(y_true, preds, zero_division=0),
        "f1": f1_score(y_true, preds, zero_division=0),
        "accuracy": accuracy_score(y_true, preds),
        "brier": brier_score_loss(y_true, proba),
    }

# Усреднение метрик по фолдам, расчет std для каждой
def _aggregate_metrics(per_fold_metrics: list[dict]) -> dict:
    if not per_fold_metrics:
        return {}
    keys = per_fold_metrics[0].keys()
    out = {}
    for k in keys:
        values = [m[k] for m in per_fold_metrics]
        out[k] = round(float(np.mean(values)), 3)
        out[f"{k}_std"] = round(float(np.std(values)), 3)
    return out


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
    per_fold_metrics: list[dict] = []

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
        per_fold_metrics.append(_compute_metrics(y_val.values, proba))

    # Усреднение по фолдам
    agg = _aggregate_metrics(per_fold_metrics)

    # Финальная модель на всех данных
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

    importances = dict(zip(
        FEATURE_COLS,
        [round(v, 3) for v in final_model.get_feature_importance()]
    ))

    # Лог в виде красивой строки
    logger.info(
        f"trainer {name}: "
        f"ROC-AUC={agg['roc_auc']}±{agg['roc_auc_std']} | "
        f"PR-AUC={agg['pr_auc']}±{agg['pr_auc_std']} | "
        f"Precision={agg['precision']}±{agg['precision_std']} | "
        f"Recall={agg['recall']}±{agg['recall_std']} | "
        f"F1={agg['f1']}±{agg['f1_std']} | "
        f"Accuracy={agg['accuracy']}±{agg['accuracy_std']} | "
        f"Brier={agg['brier']}±{agg['brier_std']}"
    )

    return {
        "skipped": False,
        "positive": positive,
        "positive_rate": round(rate, 3),
        # Главная метрика (для обратной совместимости)
        "roc_auc": agg["roc_auc"],
        "roc_auc_std": agg["roc_auc_std"],
        # Полный набор метрик
        "metrics": agg,
        "feature_importances": importances,
        "best_model": "catboost",
    }


def train(dataset: list[dict]) -> dict:
    """Обучает модели для всех болезней."""
    if len(dataset) < 30:
        return {"error": f"Мало данных: {len(dataset)} (нужно минимум 30)"}

    clean = [{k: v for k, v in row.items() if not k.startswith("_")} for row in dataset]
    df = pd.DataFrame(clean)

    X_full = df.reindex(columns=FEATURE_COLS)

    results = {"dataset_size": len(df), "models": {}}

    for short_name, col in TARGETS.items():
        if col not in df.columns:
            results["models"][short_name] = {
                "skipped": True,
                "reason": f"колонка {col} отсутствует",
            }
            continue

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
        result["labeled_samples"] = len(y)
        results["models"][short_name] = result

        if not result.get("skipped"):
            invalidate_cache(short_name)

    trained = [k for k, v in results["models"].items() if not v.get("skipped")]
    skipped = [k for k, v in results["models"].items() if v.get("skipped")]
    results["trained"] = trained
    results["skipped"] = skipped

    logger.info(f"trainer: обучено={trained}, пропущено={skipped}")
    return results
