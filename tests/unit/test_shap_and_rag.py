"""Unit tests for SHAP explainability and RAG IR metric calculations."""

from pathlib import Path

import pytest

from nosql_rag.data import (
    aggregate_crud_runs,
    derive_best_store_labels,
    generate_synthetic_demo_runs,
)
from nosql_rag.explainability import explain_instance_with_shap, explain_model_with_shap
from nosql_rag.features import grouped_train_test_split, prepare_ml_dataset
from nosql_rag.models import train_and_compare_models
from nosql_rag.rag import evaluate_ranked_results
from nosql_rag.workloads import generate_workload_profiles


def test_shap_global_and_instance_explanations(tmp_path: Path) -> None:
    profiles = generate_workload_profiles(n_profiles=16, seed=11)
    syn = generate_synthetic_demo_runs(profiles, repetitions=1, seed=11)
    agg = aggregate_crud_runs(syn, allow_synthetic=True)
    labelled = derive_best_store_labels(agg, profiles)

    clean, X, y, groups = prepare_ml_dataset(labelled, allow_synthetic=True)
    split = grouped_train_test_split(X, y, groups, clean, test_size=0.25, random_state=42)
    fitted, _, _, best_name = train_and_compare_models(
        split["X_train"], split["y_train"], split["X_test"], split["y_test"]
    )
    pipe = fitted[best_name]
    out_fig = tmp_path / "shap_summary.png"
    res = explain_model_with_shap(pipe, split["X_train"], split["X_test"], output_figure_path=out_fig)
    assert not res.global_importance.empty
    assert out_fig.exists()

    inst = explain_instance_with_shap(pipe, split["X_test"].iloc[[0]], str(split["y_test"].iloc[0]))
    assert "shap_contribution" in inst.columns
    assert len(inst) == len(res.feature_names)


def test_evaluate_ranked_results_ir_metrics() -> None:
    qrels = {"q1": {"d1", "d2"}, "q2": {"d3"}}
    ranked = [["d1", "d9", "d2"], ["d9", "d3", "d8"]]
    metrics = evaluate_ranked_results(ranked, qrels, ["q1", "q2"], k=3)
    assert metrics["evaluated_queries"] == 2
    assert metrics["recall_at_3"] == pytest.approx(1.0)
    # q1 RR = 1.0, q2 RR = 0.5 -> MRR = 0.75
    assert metrics["mrr"] == pytest.approx(0.75)
