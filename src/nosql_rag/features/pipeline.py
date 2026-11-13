"""Feature engineering, leakage prevention, and grouped train/test splitting."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from nosql_rag.data.validator import ensure_no_synthetic_contamination

DEFAULT_FEATURE_COLUMNS: tuple[str, ...] = (
    "query_type",
    "read_ratio",
    "write_ratio",
    "payload_bytes",
    "dataset_records",
    "data_size_mb",
    "concurrency",
)

FORBIDDEN_TARGET_DERIVED_COLUMNS: frozenset[str] = frozenset(
    {
        "p50_latency_ms",
        "p95_latency_ms",
        "p99_latency_ms",
        "mean_latency_ms",
        "throughput_ops_sec",
        "best_p95_latency_ms",
        "setup_seconds",
        "wall_seconds",
        "error_rate",
        "error_count",
        "best_store",
    }
)


def build_preprocessor(feature_columns: list[str] | tuple[str, ...] = DEFAULT_FEATURE_COLUMNS) -> ColumnTransformer:
    """Create a scikit-learn ColumnTransformer for workload features."""
    categorical = [c for c in feature_columns if c in {"query_type", "consistency_requirement"}]
    numeric = [c for c in feature_columns if c not in categorical]

    try:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)

    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric:
        transformers.append(
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", encoder),
                    ]
                ),
                categorical,
            )
        )

    return ColumnTransformer(transformers=transformers)


def prepare_ml_dataset(
    labelled: pd.DataFrame,
    feature_columns: list[str] | tuple[str, ...] = DEFAULT_FEATURE_COLUMNS,
    target_column: str = "best_store",
    group_column: str = "workload_id",
    allow_synthetic: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Validate features, enforce provenance & leakage rules, and extract X, y, groups."""
    if labelled.empty:
        raise ValueError("Labelled dataset is empty. Run genuine benchmarks first.")

    ensure_no_synthetic_contamination(labelled, allow_synthetic=allow_synthetic)

    leaked = set(feature_columns) & FORBIDDEN_TARGET_DERIVED_COLUMNS
    if leaked:
        raise ValueError(f"Target-derived columns cannot be used as features: {sorted(leaked)}")

    # Auto-detect base_workload_id for matched concurrency groups if present
    effective_group = (
        "base_workload_id"
        if group_column == "workload_id" and "base_workload_id" in labelled.columns
        else group_column
    )

    required = set(feature_columns) | {target_column, effective_group}
    missing = sorted(required - set(labelled.columns))
    if missing:
        raise ValueError(f"Labelled dataset is missing required columns: {missing}")

    clean = labelled.dropna(subset=[target_column]).copy()
    X = clean[list(feature_columns)].copy()
    y = clean[target_column].astype(str).copy()
    groups = clean[effective_group].astype(str).copy()

    if y.nunique() < 2:
        raise ValueError("At least two distinct best_store classes are required to train a classifier.")

    return clean, X, y, groups


def grouped_train_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    meta: pd.DataFrame,
    test_size: float = 0.25,
    random_state: int = 42,
) -> dict[str, Any]:
    """Split data strictly by group (`workload_id`) to prevent workload-profile leakage."""
    if groups.nunique() < 2:
        raise ValueError("Need at least 2 distinct workload groups for grouped train/test split.")

    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(splitter.split(X, y, groups))

    train_groups = set(groups.iloc[train_idx])
    test_groups = set(groups.iloc[test_idx])
    overlap = train_groups & test_groups
    if overlap:
        raise AssertionError(f"Data leakage detected: overlapping groups {overlap}")

    return {
        "X_train": X.iloc[train_idx].reset_index(drop=True),
        "X_test": X.iloc[test_idx].reset_index(drop=True),
        "y_train": y.iloc[train_idx].reset_index(drop=True),
        "y_test": y.iloc[test_idx].reset_index(drop=True),
        "groups_train": groups.iloc[train_idx].reset_index(drop=True),
        "groups_test": groups.iloc[test_idx].reset_index(drop=True),
        "meta_train": meta.iloc[train_idx].reset_index(drop=True),
        "meta_test": meta.iloc[test_idx].reset_index(drop=True),
    }
