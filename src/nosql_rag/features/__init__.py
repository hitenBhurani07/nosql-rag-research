"""Feature engineering and leakage-safe dataset splitting."""

from nosql_rag.features.pipeline import (
    DEFAULT_FEATURE_COLUMNS,
    FORBIDDEN_TARGET_DERIVED_COLUMNS,
    build_preprocessor,
    grouped_train_test_split,
    prepare_ml_dataset,
)

__all__ = [
    "DEFAULT_FEATURE_COLUMNS",
    "FORBIDDEN_TARGET_DERIVED_COLUMNS",
    "build_preprocessor",
    "grouped_train_test_split",
    "prepare_ml_dataset",
]
