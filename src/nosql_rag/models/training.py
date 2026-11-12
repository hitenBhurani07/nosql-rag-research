"""Model training, hyperparameter defaults, cross-validation, and persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from nosql_rag.features.pipeline import build_preprocessor


@dataclass
class TrainingArtifacts:
    fitted_models: dict[str, Pipeline]
    predictions: dict[str, np.ndarray]
    metrics_table: pd.DataFrame
    cv_metrics_table: pd.DataFrame
    best_model_name: str
    best_pipeline: Pipeline
    feature_names: list[str]
    training_metadata: dict[str, Any]


def get_model_definitions(random_state: int = 42) -> dict[str, Any]:
    """Return the three required models with reproducible hyperparameters."""
    return {
        "Decision Tree": DecisionTreeClassifier(
            max_depth=6,
            min_samples_leaf=2,
            random_state=random_state,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=2,
            random_state=random_state,
        ),
    }


def cross_validate_models(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    cv_folds: int = 5,
    random_state: int = 42,
    feature_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Evaluate models using leakage-safe StratifiedGroupKFold cross-validation."""
    n_groups = int(groups.nunique())
    folds = max(2, min(cv_folds, n_groups))
    sgkf = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=random_state)
    model_defs = get_model_definitions(random_state)

    rows: list[dict[str, Any]] = []
    cols = feature_columns or list(X.columns)

    for name, estimator in model_defs.items():
        accs, f1s = [], []
        for train_idx, val_idx in sgkf.split(X, y, groups):
            preprocessor = build_preprocessor(cols)
            pipe = Pipeline([("preprocess", preprocessor), ("model", estimator)])
            pipe.fit(X.iloc[train_idx], y.iloc[train_idx])
            pred = pipe.predict(X.iloc[val_idx])
            accs.append(accuracy_score(y.iloc[val_idx], pred))
            f1s.append(f1_score(y.iloc[val_idx], pred, average="macro", zero_division=0))

        rows.append(
            {
                "model": name,
                "cv_folds": folds,
                "mean_cv_accuracy": float(np.mean(accs)),
                "std_cv_accuracy": float(np.std(accs)),
                "mean_cv_macro_f1": float(np.mean(f1s)),
                "std_cv_macro_f1": float(np.std(f1s)),
            }
        )

    return pd.DataFrame(rows).sort_values("mean_cv_macro_f1", ascending=False).reset_index(drop=True)


def train_and_compare_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    random_state: int = 42,
    feature_columns: list[str] | None = None,
) -> tuple[dict[str, Pipeline], dict[str, np.ndarray], pd.DataFrame, str]:
    """Train Decision Tree, Random Forest, and Gradient Boosting and evaluate on held-out test data."""
    cols = feature_columns or list(X_train.columns)
    model_defs = get_model_definitions(random_state)
    fitted: dict[str, Pipeline] = {}
    preds: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []

    for name, estimator in model_defs.items():
        preprocessor = build_preprocessor(cols)
        pipe = Pipeline([("preprocess", preprocessor), ("model", estimator)])
        pipe.fit(X_train, y_train)
        pred = pipe.predict(X_test)
        fitted[name] = pipe
        preds[name] = pred

        rows.append(
            {
                "model": name,
                "accuracy": round(float(accuracy_score(y_test, pred)), 4),
                "macro_f1": round(
                    float(f1_score(y_test, pred, average="macro", zero_division=0)), 4
                ),
                "weighted_f1": round(
                    float(f1_score(y_test, pred, average="weighted", zero_division=0)), 4
                ),
                "macro_precision": round(
                    float(precision_score(y_test, pred, average="macro", zero_division=0)), 4
                ),
                "macro_recall": round(
                    float(recall_score(y_test, pred, average="macro", zero_division=0)), 4
                ),
            }
        )

    metrics_df = (
        pd.DataFrame(rows).sort_values(["macro_f1", "accuracy"], ascending=False).reset_index(drop=True)
    )
    best_name = str(metrics_df.loc[0, "model"])
    return fitted, preds, metrics_df, best_name


def save_model_artifacts(
    artifacts: TrainingArtifacts,
    output_dir: Path,
    prefix: str = "best_nosql_recommender",
) -> dict[str, Path]:
    """Persist the trained pipeline, schema, and metadata JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{prefix}.joblib"
    meta_path = output_dir / f"{prefix}_metadata.json"

    joblib.dump(artifacts.best_pipeline, model_path)
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(artifacts.training_metadata, f, indent=2, default=str)

    return {"model_path": model_path, "metadata_path": meta_path}


def load_model_artifacts(model_path: Path) -> Pipeline:
    """Load a persisted scikit-learn recommendation pipeline."""
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    return joblib.load(model_path)
