"""Read-only completeness audit for the approved matched-concurrency CRUD matrix."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

from nosql_rag.workloads.compatibility import CRUD_DATABASES
from nosql_rag.workloads.generator import generate_workload_profiles


def audit_crud_matrix(
    runs: pd.DataFrame,
    profiles: pd.DataFrame | None = None,
    databases: tuple[str, ...] | list[str] = CRUD_DATABASES,
    repetitions: int = 3,
    max_error_rate: float = 0.01,
) -> dict[str, Any]:
    """Compare raw run attempts with expected workload/database/repetition keys.

    When raw rows do not contain ``base_workload_id``, the IDs are mapped from the
    deterministic workload profiles. Attempts are never removed or deduplicated.
    A key counts complete only when it has at least one genuine, successful,
    well-formed measurement with an acceptable error rate.
    """
    if profiles is None:
        profiles = generate_workload_profiles(
            n_profiles=75,
            seed=42,
            operations=1500,
            records=1000,
            concurrency_levels=[1, 4],
            id_prefix="W",
            matched_concurrency=True,
        )

    expected_columns = {"workload_id", "concurrency", "base_workload_id"}
    if not expected_columns.issubset(profiles.columns):
        raise ValueError(f"Profiles must contain {sorted(expected_columns)}")
    if profiles["workload_id"].duplicated().any():
        raise ValueError("Profiles contain duplicate workload_id values")

    profile_map = profiles.set_index("workload_id")[
        ["base_workload_id", "concurrency"]
    ].to_dict("index")
    workload_ids = list(profile_map)
    database_names = list(databases)
    expected_keys = {
        (str(wid), str(db), int(profile_map[wid]["concurrency"]), rep)
        for wid in workload_ids
        for db in database_names
        for rep in range(1, repetitions + 1)
    }

    required_columns = {"workload_id", "database", "concurrency", "repetition", "status"}
    missing_columns = sorted(required_columns - set(runs.columns))
    if missing_columns:
        raise ValueError(f"Raw runs are missing required columns: {missing_columns}")

    attempts: Counter[tuple[str, str, int, int]] = Counter()
    successful_keys: Counter[tuple[str, str, int, int]] = Counter()
    genuine_success_keys: Counter[tuple[str, str, int, int]] = Counter()
    success_measurement_errors: list[dict[str, Any]] = []
    profile_mismatches: list[dict[str, Any]] = []
    unknown_workload_ids: set[str] = set()

    for row_index, row in runs.iterrows():
        wid = str(row["workload_id"])
        database = str(row["database"])
        try:
            concurrency = int(row["concurrency"])
            repetition = int(row["repetition"])
        except (TypeError, ValueError, OverflowError):
            continue

        key = (wid, database, concurrency, repetition)
        if key in expected_keys:
            attempts[key] += 1
        if wid not in profile_map:
            unknown_workload_ids.add(wid)
            continue

        expected_concurrency = int(profile_map[wid]["concurrency"])
        expected_base_id = str(profile_map[wid]["base_workload_id"])
        recorded_base_id = row.get("base_workload_id")
        base_mismatch = (
            recorded_base_id is not None
            and not pd.isna(recorded_base_id)
            and str(recorded_base_id) != expected_base_id
        )
        if concurrency != expected_concurrency or base_mismatch:
            profile_mismatches.append(
                {
                    "row_index": int(row_index),
                    "workload_id": wid,
                    "recorded_concurrency": concurrency,
                    "expected_concurrency": expected_concurrency,
                    "recorded_base_workload_id": (
                        str(recorded_base_id)
                        if recorded_base_id is not None and not pd.isna(recorded_base_id)
                        else None
                    ),
                    "expected_base_workload_id": expected_base_id,
                }
            )
            continue
        if key not in expected_keys or str(row["status"]) != "success":
            continue

        successful_keys[key] += 1
        provenance = str(row.get("data_provenance", ""))
        if provenance != "genuine_benchmark":
            continue

        measurement_problems: list[str] = []
        for field in ("p50_latency_ms", "p95_latency_ms", "p99_latency_ms"):
            try:
                value = float(row[field])
            except (KeyError, TypeError, ValueError):
                measurement_problems.append(f"missing_or_invalid_{field}")
                continue
            if not np.isfinite(value) or value <= 0:
                measurement_problems.append(f"invalid_{field}")

        try:
            p50, p95, p99 = (float(row[f"p{q}_latency_ms"]) for q in (50, 95, 99))
            if not (p50 <= p95 <= p99):
                measurement_problems.append("percentile_order_violation")
        except (KeyError, TypeError, ValueError):
            pass

        try:
            error_rate = float(row["error_rate"])
            if not np.isfinite(error_rate) or not 0 <= error_rate <= max_error_rate:
                measurement_problems.append("error_rate_out_of_range")
        except (KeyError, TypeError, ValueError):
            measurement_problems.append("missing_or_invalid_error_rate")

        if measurement_problems:
            success_measurement_errors.append(
                {
                    "row_index": int(row_index),
                    "run_id": str(row.get("run_id", "")),
                    "key": list(key),
                    "problems": measurement_problems,
                }
            )
        else:
            genuine_success_keys[key] += 1

    missing_keys = sorted(expected_keys - set(genuine_success_keys))
    failed_keys = sorted(
        key for key in missing_keys if attempts.get(key, 0) > 0
    )
    pending_keys = sorted(key for key in missing_keys if attempts.get(key, 0) == 0)
    repeated_attempt_keys = sorted(key for key, count in attempts.items() if count > 1)
    duplicate_successful_keys = sorted(
        key for key, count in successful_keys.items() if count > 1
    )
    genuine_success_attempt_rows = sum(
        1
        for _, row in runs.iterrows()
        if str(row.get("status", "")) == "success"
        and str(row.get("data_provenance", "")) == "genuine_benchmark"
        and str(row.get("workload_id", "")) in profile_map
    )

    status_counts = (
        runs["status"].fillna("<missing>").astype(str).value_counts().sort_index().to_dict()
        if not runs.empty
        else {}
    )
    provenance_counts = (
        runs.get("data_provenance", pd.Series(dtype=str))
        .fillna("<missing>")
        .astype(str)
        .value_counts()
        .sort_index()
        .to_dict()
    )
    database_counts = runs.get("database", pd.Series(dtype=str)).fillna("<missing>").astype(str)
    concurrency_counts = (
        runs.get("concurrency", pd.Series(dtype=str)).fillna("<missing>").astype(str)
    )
    repetition_counts = runs.get("repetition", pd.Series(dtype=str)).fillna("<missing>").astype(str)

    if "run_id" in runs.columns:
        duplicate_run_ids = runs.loc[
            runs["run_id"].duplicated(keep=False), "run_id"
        ].astype(str).value_counts().sort_index().to_dict()
    else:
        duplicate_run_ids = {}

    observed_base_ids = {
        str(profile_map[wid]["base_workload_id"])
        for wid in runs.get("workload_id", pd.Series(dtype=str)).astype(str)
        if wid in profile_map
    }

    quality_successes = runs[
        (runs.get("status", pd.Series(index=runs.index, dtype=str)).astype(str) == "success")
        & (
            runs.get("data_provenance", pd.Series(index=runs.index, dtype=str)).astype(str)
            == "genuine_benchmark"
        )
    ]
    latency_percentile_summary: dict[str, dict[str, Any]] = {}
    for field in ("p50_latency_ms", "p95_latency_ms", "p99_latency_ms"):
        values = pd.to_numeric(quality_successes.get(field), errors="coerce")
        if values is None:
            values = pd.Series(dtype=float)
        finite_values = values[np.isfinite(values)]
        latency_percentile_summary[field] = {
            "valid_count": int(len(finite_values)),
            "missing_or_nonfinite_count": int(len(quality_successes) - len(finite_values)),
            "min": float(finite_values.min()) if not finite_values.empty else None,
            "median": float(finite_values.median()) if not finite_values.empty else None,
            "max": float(finite_values.max()) if not finite_values.empty else None,
        }

    error_rates = pd.to_numeric(runs.get("error_rate"), errors="coerce")
    if error_rates is None:
        error_rates = pd.Series(dtype=float)
    finite_error_rates = error_rates[np.isfinite(error_rates)]

    expected_count = len(expected_keys)
    completed_count = len(expected_keys & set(genuine_success_keys))
    contains_synthetic_rows = "synthetic_demo" in provenance_counts
    integrity_passed = not (
        duplicate_run_ids
        or duplicate_successful_keys
        or profile_mismatches
        or success_measurement_errors
        or contains_synthetic_rows
    )
    return {
        "total_rows": int(len(runs)),
        "expected_run_keys": expected_count,
        "completed_genuine_keys": completed_count,
        "genuine_success_attempt_rows": genuine_success_attempt_rows,
        "completion_fraction": completed_count / expected_count if expected_count else 0.0,
        "integrity_passed": integrity_passed,
        "contains_synthetic_rows": contains_synthetic_rows,
        "is_complete": completed_count == expected_count and integrity_passed,
        "unique_workload_ids_observed": int(
            runs.get("workload_id", pd.Series(dtype=str)).nunique()
        ),
        "unique_matrix_workload_ids_observed": len(
            set(runs.get("workload_id", pd.Series(dtype=str)).astype(str)) & set(workload_ids)
        ),
        "unique_base_workload_ids_observed": len(observed_base_ids),
        "base_workload_id_source": (
            "deterministic profile mapping; base_workload_id is not present in raw rows"
            if "base_workload_id" not in runs.columns
            else "raw column checked against deterministic profiles"
        ),
        "status_counts": status_counts,
        "provenance_counts": provenance_counts,
        "latency_percentile_summary": latency_percentile_summary,
        "error_rate_summary": {
            "valid_count": int(len(finite_error_rates)),
            "missing_or_nonfinite_count": int(len(runs) - len(finite_error_rates)),
            "above_threshold_count": int((finite_error_rates > max_error_rate).sum()),
            "threshold": max_error_rate,
            "min": float(finite_error_rates.min()) if not finite_error_rates.empty else None,
            "median": float(finite_error_rates.median()) if not finite_error_rates.empty else None,
            "max": float(finite_error_rates.max()) if not finite_error_rates.empty else None,
        },
        "database_row_counts": database_counts.value_counts().sort_index().to_dict(),
        "concurrency_row_counts": concurrency_counts.value_counts().sort_index().to_dict(),
        "repetition_row_counts": repetition_counts.value_counts().sort_index().to_dict(),
        "expected_databases": database_names,
        "expected_concurrency_levels": sorted(
            {int(value) for value in profiles["concurrency"].unique()}
        ),
        "expected_repetitions": list(range(1, repetitions + 1)),
        "missing_keys": [list(key) for key in missing_keys],
        "failed_keys": [list(key) for key in failed_keys],
        "pending_keys": [list(key) for key in pending_keys],
        "repeated_attempt_keys": [list(key) for key in repeated_attempt_keys],
        "duplicate_successful_keys": [list(key) for key in duplicate_successful_keys],
        "duplicate_run_ids": duplicate_run_ids,
        "unknown_workload_ids": sorted(unknown_workload_ids),
        "profile_mismatches": profile_mismatches,
        "successful_measurement_errors": success_measurement_errors,
    }
