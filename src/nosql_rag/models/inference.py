"""Inference engine with Stage 1 feasibility filtering and Stage 2 ML ranking."""

from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.pipeline import Pipeline

from nosql_rag.features.pipeline import DEFAULT_FEATURE_COLUMNS
from nosql_rag.workloads.compatibility import evaluate_feasibility


def recommend_database(
    workload_input: dict[str, Any],
    trained_pipeline: Pipeline | None = None,
    training_data: pd.DataFrame | None = None,
    feature_columns: list[str] | tuple[str, ...] = DEFAULT_FEATURE_COLUMNS,
) -> dict[str, Any]:
    """Two-stage recommendation combining feasibility rules and ML performance ranking."""
    feasibility = evaluate_feasibility(workload_input)

    # Stage 1: Deterministic resolution if exactly 1 feasible engine
    if not feasibility.requires_ml_selection or len(feasibility.feasible_databases) == 1:
        recommended = feasibility.feasible_databases[0]
        return {
            "recommended_database": recommended,
            "stage": "stage_1_feasibility_deterministic",
            "workload_family": feasibility.workload_family,
            "feasible_databases": feasibility.feasible_databases,
            "rejected_reasons": feasibility.rejected_reasons,
            "evaluation_protocol": feasibility.evaluation_protocol,
            "class_probabilities": {recommended: 1.0},
            "generalization_warnings": [],
            "notes": feasibility.notes,
        }

    # Stage 2: ML ranking among feasible engines
    if trained_pipeline is None:
        raise ValueError(
            "Trained ML pipeline is required for operational CRUD multi-engine selection."
        )

    missing = sorted(set(feature_columns) - set(workload_input))
    if missing:
        raise ValueError(f"Missing required workload input features: {missing}")

    frame = pd.DataFrame([{col: workload_input[col] for col in feature_columns}])
    raw_pred = str(trained_pipeline.predict(frame)[0])

    probabilities: dict[str, float] = {}
    if hasattr(trained_pipeline, "predict_proba"):
        probs = trained_pipeline.predict_proba(frame)[0]
        classes = [str(c) for c in trained_pipeline.named_steps["model"].classes_]
        for c, p in zip(classes, probs):
            probabilities[c] = float(p)

    feasible_set = set(feasibility.feasible_databases)
    if raw_pred in feasible_set:
        final_recommended = raw_pred
    else:
        # Constrain to feasible candidates only
        feasible_probs = {c: probabilities.get(c, 0.0) for c in feasible_set}
        final_recommended = max(feasible_probs, key=lambda k: feasible_probs[k])

    warnings: list[str] = []
    if training_data is not None:
        for col in [c for c in feature_columns if c not in {"query_type", "consistency_requirement"}]:
            if col in training_data.columns and col in workload_input:
                lo = float(training_data[col].min())
                hi = float(training_data[col].max())
                val = float(workload_input[col])
                if val < lo or val > hi:
                    warnings.append(f"{col}={val} is outside training range [{lo}, {hi}]")

    return {
        "recommended_database": final_recommended,
        "stage": "stage_2_ml_performance_selection",
        "workload_family": feasibility.workload_family,
        "feasible_databases": feasibility.feasible_databases,
        "rejected_reasons": feasibility.rejected_reasons,
        "class_probabilities": probabilities,
        "generalization_warnings": warnings,
        "evaluation_protocol": feasibility.evaluation_protocol,
        "notes": feasibility.notes,
    }
