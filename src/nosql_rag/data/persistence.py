"""Append-only raw run persistence, aggregation, labeling, and demo synthesis."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nosql_rag.data.schemas import DataProvenance
from nosql_rag.workloads.compatibility import CRUD_DATABASES


def append_raw_runs(rows: list[dict[str, Any]], path: Path) -> pd.DataFrame:
    """Append benchmark run rows to an append-only CSV without overwriting history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new_df = pd.DataFrame(rows)
    if path.exists() and path.stat().st_size > 0:
        existing = pd.read_csv(path)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["run_id"], keep="first")
    else:
        combined = new_df
    combined.to_csv(path, index=False)
    return combined


def load_raw_runs(path: Path) -> pd.DataFrame:
    """Load raw benchmark runs CSV if present, otherwise return empty DataFrame."""
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def aggregate_crud_runs(
    runs: pd.DataFrame,
    max_allowed_error_rate: float = 0.01,
    allow_synthetic: bool = False,
) -> pd.DataFrame:
    """Compute median metrics per (workload_id, database) from successful raw runs."""
    if runs.empty:
        return pd.DataFrame()

    good = runs[
        (runs["status"] == "success") & (runs["error_rate"].fillna(1.0) <= max_allowed_error_rate)
    ].copy()
    if not allow_synthetic and "data_provenance" in good.columns:
        good = good[good["data_provenance"] != DataProvenance.SYNTHETIC_DEMO.value]

    if good.empty:
        return pd.DataFrame()

    metric_cols = [
        c
        for c in (
            "p50_latency_ms",
            "p95_latency_ms",
            "p99_latency_ms",
            "mean_latency_ms",
            "throughput_ops_sec",
            "error_rate",
            "setup_seconds",
            "wall_seconds",
        )
        if c in good.columns
    ]
    agg = good.groupby(["workload_id", "database"], as_index=False)[metric_cols].median()
    counts = (
        good.groupby(["workload_id", "database"])
        .size()
        .rename("successful_repetitions")
        .reset_index()
    )
    merged = agg.merge(counts, on=["workload_id", "database"], how="left")
    merged["data_provenance"] = DataProvenance.AGGREGATED_EXPERIMENTAL.value
    return merged


def derive_best_store_labels(
    aggregated: pd.DataFrame,
    profiles: pd.DataFrame,
    objective: str = "min_p95_latency_ms",
) -> pd.DataFrame:
    """Derive one labelled row per workload_id using the frozen objective policy."""
    if aggregated.empty or profiles.empty:
        return pd.DataFrame()

    profile_index = profiles.drop_duplicates("workload_id").set_index("workload_id")
    rows: list[dict[str, Any]] = []

    for workload_id, group in aggregated.groupby("workload_id"):
        if workload_id not in profile_index.index or len(group) < 2:
            continue

        if objective == "max_throughput_ops_sec":
            winner = group.sort_values("throughput_ops_sec", ascending=False).iloc[0]
        elif objective == "min_p50_latency_ms":
            winner = group.sort_values("p50_latency_ms", ascending=True).iloc[0]
        else:
            winner = group.sort_values("p95_latency_ms", ascending=True).iloc[0]

        base = profile_index.loc[workload_id].to_dict()
        base["workload_id"] = workload_id
        base.update(
            {
                "best_store": str(winner["database"]),
                "best_p95_latency_ms": float(winner["p95_latency_ms"]),
                "eligible_database_count": int(len(group)),
                "label_objective": objective,
                "data_provenance": DataProvenance.MODEL_READY.value,
            }
        )
        rows.append(base)

    return pd.DataFrame(rows)


def generate_synthetic_demo_runs(
    profiles: pd.DataFrame,
    repetitions: int = 2,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate clearly tagged `synthetic_demo` measurements for tests and UI demos ONLY."""
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    for _, prof in profiles.iterrows():
        q_type = prof["query_type"]
        read_ratio = float(prof["read_ratio"])
        payload_bytes = int(prof["payload_bytes"])
        concurrency = int(prof["concurrency"])

        for db in CRUD_DATABASES:
            # Deterministic illustrative latency profile by store characteristics
            base = {"Redis": 1.8, "MongoDB": 2.4, "Cassandra": 2.9, "Neo4j": 4.2}[db]
            if q_type == "key_value_crud" and db == "Redis":
                base *= 0.55
            elif q_type == "document_crud" and payload_bytes >= 2048 and db == "MongoDB":
                base *= 0.45
            elif q_type == "wide_column_crud" and read_ratio <= 0.5 and db == "Cassandra":
                base *= 0.40
            elif concurrency >= 4 and db in {"Redis", "Cassandra"}:
                base *= 0.85

            for rep in range(1, repetitions + 1):
                jitter = float(rng.uniform(0.9, 1.12))
                p50 = round(base * jitter, 3)
                p95 = round(p50 * float(rng.uniform(1.3, 1.7)), 3)
                p99 = round(p95 * float(rng.uniform(1.15, 1.35)), 3)
                rows.append(
                    {
                        "run_id": f"syn_{prof['workload_id']}_{db.lower()}_r{rep}_{uuid.uuid4().hex[:6]}",
                        "workload_id": prof["workload_id"],
                        "configuration_id": f"{prof['workload_id']}__{db}",
                        "database": db,
                        "database_version": "synthetic-demo",
                        "query_type": q_type,
                        "payload_bytes": payload_bytes,
                        "dataset_records": int(prof["dataset_records"]),
                        "read_ratio": read_ratio,
                        "write_ratio": float(prof["write_ratio"]),
                        "concurrency": concurrency,
                        "n_operations": int(prof["n_operations"]),
                        "warmup_operations": 20,
                        "repetition": rep,
                        "started_utc": now,
                        "finished_utc": now,
                        "p50_latency_ms": p50,
                        "p95_latency_ms": p95,
                        "p99_latency_ms": p99,
                        "mean_latency_ms": round((p50 + p95) / 2.0, 3),
                        "throughput_ops_sec": round(1000.0 / max(p50, 0.1) * concurrency, 2),
                        "error_count": 0,
                        "error_rate": 0.0,
                        "status": "success",
                        "data_provenance": DataProvenance.SYNTHETIC_DEMO.value,
                    }
                )
    return pd.DataFrame(rows)
