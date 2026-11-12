"""Regret-based evaluation comparing ML against random, majority, rule-based, and oracle."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from nosql_rag.workloads.compatibility import evaluate_feasibility


def calculate_latency_regret(
    pipeline: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    test_meta: pd.DataFrame,
    aggregated_measurements: pd.DataFrame,
    y_train: pd.Series,
    seed: int = 42,
) -> pd.DataFrame:
    """Calculate relative latency regret against the Oracle best feasible engine.

    Relative latency regret for workload W:
    Regret(W) = (Latency_selected(W) - Latency_oracle(W)) / Latency_oracle(W)

    Feasibility constraints are strictly enforced: no baseline or recommender
    is evaluated against an infeasible database.
    """
    if aggregated_measurements.empty:
        raise ValueError("Aggregated measurements are required to compute latency regret.")

    rng = np.random.default_rng(seed)
    predicted_ml = pipeline.predict(X_test)

    # Pre-index p95 latencies by (workload_id, database)
    latency_map = (
        aggregated_measurements.set_index(["workload_id", "database"])["p95_latency_ms"].to_dict()
    )

    # Establish baselines
    majority_store = str(y_train.value_counts().idxmax())
    rule_map = {
        "key_value_crud": "Redis",
        "document_crud": "MongoDB",
        "wide_column_crud": "Cassandra",
    }
    candidate_engines = sorted(aggregated_measurements["database"].unique().tolist())

    rows: list[dict[str, Any]] = []

    for idx, (_, meta_row) in enumerate(test_meta.iterrows()):
        wid = str(meta_row["workload_id"])
        q_type = str(meta_row["query_type"])
        feasibility = evaluate_feasibility(meta_row.to_dict())
        feasible_dbs = set(feasibility.feasible_databases)

        # Oracle best feasible latency
        feasible_latencies = {
            db: latency_map.get((wid, db))
            for db in feasible_dbs
            if (wid, db) in latency_map and latency_map.get((wid, db)) is not None
        }
        if not feasible_latencies:
            continue

        best_feasible_db = min(feasible_latencies, key=lambda k: float(feasible_latencies[k]))
        best_feasible_lat = float(feasible_latencies[best_feasible_db])
        if best_feasible_lat <= 0:
            continue

        # Baseline store selections
        ml_store = str(predicted_ml[idx])
        rule_store = rule_map.get(q_type, "MongoDB")
        random_candidates = [db for db in candidate_engines if db in feasible_dbs]
        random_store = str(rng.choice(random_candidates)) if random_candidates else majority_store

        selection_methods = [
            ("ML recommender", ml_store),
            ("Oracle best", best_feasible_db),
            ("Rule-based baseline", rule_store),
            ("Majority-class baseline", majority_store),
            ("Single-store default (MongoDB)", "MongoDB"),
            ("Random feasible baseline", random_store),
        ]

        for method_name, selected_db in selection_methods:
            # Check feasibility
            is_feasible = selected_db in feasible_dbs
            selected_lat = (
                float(latency_map[(wid, selected_db)])
                if is_feasible and (wid, selected_db) in latency_map
                else None
            )

            if selected_lat is not None and selected_lat > 0:
                regret = (selected_lat - best_feasible_lat) / best_feasible_lat
            else:
                # Infeasible or missing execution penalty
                regret = np.nan

            rows.append(
                {
                    "workload_id": wid,
                    "query_type": q_type,
                    "method": method_name,
                    "selected_store": selected_db,
                    "is_feasible": is_feasible,
                    "selected_p95_latency_ms": selected_lat,
                    "best_feasible_store": best_feasible_db,
                    "best_feasible_p95_latency_ms": best_feasible_lat,
                    "relative_latency_regret": regret,
                }
            )

    return pd.DataFrame(rows)


def summarize_regret(regret_df: pd.DataFrame) -> pd.DataFrame:
    """Compute summary statistics for relative latency regret across methods."""
    if regret_df.empty:
        return pd.DataFrame()
    return (
        regret_df.groupby("method")["relative_latency_regret"]
        .agg(
            count="count",
            mean="mean",
            median="median",
            p90=lambda x: np.percentile(x.dropna(), 90) if len(x.dropna()) > 0 else np.nan,
            max="max",
        )
        .reset_index()
        .sort_values("mean")
    )
