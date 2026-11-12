"""Unit tests for feature leakage prevention, grouped splits, ML training, and regret."""

import pytest

from nosql_rag.data import (
    aggregate_crud_runs,
    derive_best_store_labels,
    generate_synthetic_demo_runs,
)
from nosql_rag.evaluation import calculate_latency_regret, summarize_regret
from nosql_rag.features import grouped_train_test_split, prepare_ml_dataset
from nosql_rag.models import recommend_database, train_and_compare_models
from nosql_rag.workloads import generate_workload_profiles


def test_target_leakage_forbidden() -> None:
    profiles = generate_workload_profiles(n_profiles=8)
    syn = generate_synthetic_demo_runs(profiles, repetitions=1)
    agg = aggregate_crud_runs(syn, allow_synthetic=True)
    labelled = derive_best_store_labels(agg, profiles)

    with pytest.raises(ValueError, match="Target-derived"):
        prepare_ml_dataset(
            labelled,
            feature_columns=["query_type", "p95_latency_ms"],
            allow_synthetic=True,
        )


def test_grouped_split_and_ml_regret_pipeline() -> None:
    profiles = generate_workload_profiles(n_profiles=20, seed=7)
    syn = generate_synthetic_demo_runs(profiles, repetitions=2, seed=7)
    agg = aggregate_crud_runs(syn, allow_synthetic=True)
    labelled = derive_best_store_labels(agg, profiles)

    clean, X, y, groups = prepare_ml_dataset(labelled, allow_synthetic=True)
    split = grouped_train_test_split(X, y, groups, clean, test_size=0.25, random_state=42)

    # Assert zero workload_id overlap between train and test
    assert set(split["groups_train"]).isdisjoint(set(split["groups_test"]))

    fitted, preds, metrics, best_name = train_and_compare_models(
        split["X_train"], split["y_train"], split["X_test"], split["y_test"]
    )
    assert set(fitted.keys()) == {"Decision Tree", "Random Forest", "Gradient Boosting"}
    assert best_name in fitted
    assert not metrics.empty

    regret_df = calculate_latency_regret(
        fitted[best_name],
        split["X_test"],
        split["y_test"],
        split["meta_test"],
        agg,
        split["y_train"],
    )
    summary = summarize_regret(regret_df)
    oracle_row = summary[summary["method"] == "Oracle best"].iloc[0]
    assert oracle_row["mean"] == pytest.approx(0.0)

    # Test two-stage inference
    crud_rec = recommend_database(
        {
            "query_type": "key_value_crud",
            "read_ratio": 0.9,
            "write_ratio": 0.1,
            "payload_bytes": 256,
            "dataset_records": 1000,
            "data_size_mb": 0.25,
            "concurrency": 1,
        },
        trained_pipeline=fitted[best_name],
        training_data=clean,
    )
    assert crud_rec["stage"] == "stage_2_ml_performance_selection"
    assert crud_rec["recommended_database"] in {"Redis", "MongoDB", "Cassandra", "Neo4j"}

    vec_rec = recommend_database(
        {"query_type": "vector_similarity", "vector_dimensions": 128, "top_k": 10},
        trained_pipeline=fitted[best_name],
    )
    assert vec_rec["recommended_database"] == "Qdrant"
    assert vec_rec["stage"] == "stage_1_feasibility_deterministic"
