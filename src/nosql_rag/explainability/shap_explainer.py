"""SHAP explainability for tree-based NoSQL recommendation models."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

logger = logging.getLogger("nosql_rag.explainability")


@dataclass
class ShapExplanationResult:
    feature_names: list[str]
    global_importance: pd.DataFrame
    summary_plot_path: Path | None
    class_names: list[str]


def explain_model_with_shap(
    pipeline: Pipeline,
    X_background: pd.DataFrame,
    X_explain: pd.DataFrame,
    output_figure_path: Path | None = None,
) -> ShapExplanationResult:
    """Compute TreeExplainer SHAP values and save multi-class summary plots."""
    try:
        import shap
    except ImportError as exc:
        raise RuntimeError("shap package is required for explainability analysis") from exc

    preprocessor = pipeline.named_steps["preprocess"]
    estimator = pipeline.named_steps["model"]

    X_explain_trans = preprocessor.transform(X_explain)
    feature_names = [str(name) for name in preprocessor.get_feature_names_out()]
    class_names = [str(c) for c in getattr(estimator, "classes_", ["model_output"])]

    explainer = shap.TreeExplainer(estimator)
    shap_values = explainer.shap_values(X_explain_trans)

    # Multi-class handling across shap versions
    if isinstance(shap_values, list):
        # List of [n_samples, n_features] arrays
        mean_abs = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
        plot_values = shap_values[0]
    else:
        arr = np.asarray(shap_values)
        if arr.ndim == 3:  # (samples, features, classes)
            mean_abs = np.abs(arr).mean(axis=(0, 2))
            plot_values = arr[:, :, 0]
        else:
            mean_abs = np.abs(arr).mean(axis=0)
            plot_values = arr

    importance_df = pd.DataFrame(
        {"feature": feature_names, "mean_abs_shap": mean_abs}
    ).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    summary_path: Path | None = None
    if output_figure_path is not None:
        output_figure_path.parent.mkdir(parents=True, exist_ok=True)
        plt.figure(figsize=(9, 5))
        shap.summary_plot(
            plot_values,
            X_explain_trans,
            feature_names=feature_names,
            show=False,
            plot_size=(9, 5),
        )
        plt.title(f"SHAP Summary — Class: {class_names[0]}")
        plt.tight_layout()
        plt.savefig(output_figure_path, dpi=200, bbox_inches="tight")
        plt.close()
        summary_path = output_figure_path

    return ShapExplanationResult(
        feature_names=feature_names,
        global_importance=importance_df,
        summary_plot_path=summary_path,
        class_names=class_names,
    )


def explain_instance_with_shap(
    pipeline: Pipeline,
    workload_row: pd.DataFrame,
    predicted_class: str,
) -> pd.DataFrame:
    """Return per-feature SHAP contributions for a single workload recommendation.

    Note: SHAP attributions explain model output behavior, not causal database physics.
    """
    import shap

    preprocessor = pipeline.named_steps["preprocess"]
    estimator = pipeline.named_steps["model"]
    X_trans = preprocessor.transform(workload_row)
    feature_names = [str(n) for n in preprocessor.get_feature_names_out()]
    classes = [str(c) for c in getattr(estimator, "classes_", [])]
    class_idx = classes.index(predicted_class) if predicted_class in classes else 0

    explainer = shap.TreeExplainer(estimator)
    shap_values = explainer.shap_values(X_trans)

    if isinstance(shap_values, list):
        contrib = np.asarray(shap_values[class_idx])[0]
    else:
        arr = np.asarray(shap_values)
        if arr.ndim == 3:
            contrib = arr[0, :, class_idx]
        elif arr.ndim == 2:
            contrib = arr[0]
        else:
            contrib = arr.ravel()

    return (
        pd.DataFrame(
            {
                "feature": feature_names,
                "shap_contribution": contrib,
                "abs_contribution": np.abs(contrib),
            }
        )
        .sort_values("abs_contribution", ascending=False)
        .reset_index(drop=True)
    )
