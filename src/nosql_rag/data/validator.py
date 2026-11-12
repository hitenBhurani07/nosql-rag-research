"""Dataset validation checks for raw, aggregated, and model-ready tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from nosql_rag.data.schemas import REQUIRED_RAW_RUN_COLUMNS, DataProvenance


@dataclass
class ValidationReport:
    """Structured outcome of dataset quality and integrity checks."""

    is_valid: bool
    total_rows: int
    valid_rows: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def validate_raw_runs(
    runs: pd.DataFrame,
    profiles: pd.DataFrame | None = None,
    max_error_rate: float = 0.01,
    min_repetitions: int = 1,
    allow_synthetic: bool = False,
) -> ValidationReport:
    """Run all required integrity and quality checks on raw benchmark runs."""
    errors: list[str] = []
    warnings: list[str] = []

    if runs.empty:
        return ValidationReport(
            is_valid=False,
            total_rows=0,
            valid_rows=0,
            errors=["Raw runs table is empty."],
        )

    missing_cols = sorted(set(REQUIRED_RAW_RUN_COLUMNS) - set(runs.columns))
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")
        return ValidationReport(
            is_valid=False,
            total_rows=len(runs),
            valid_rows=0,
            errors=errors,
        )

    if not allow_synthetic and (runs["data_provenance"] == DataProvenance.SYNTHETIC_DEMO.value).any():
        errors.append(
            "Dataset contains synthetic_demo rows. Synthetic data cannot be used as genuine experimental data."
        )

    if runs["run_id"].duplicated().any():
        dup_count = int(runs["run_id"].duplicated().sum())
        errors.append(f"Found {dup_count} duplicate run_id entries.")

    failed_mask = runs["status"] != "success"
    if failed_mask.any():
        warnings.append(f"{int(failed_mask.sum())} runs did not complete with status='success'.")

    err_rate_mask = runs["error_rate"].fillna(1.0) > max_error_rate
    if err_rate_mask.any():
        warnings.append(
            f"{int(err_rate_mask.sum())} runs exceeded max_error_rate={max_error_rate}."
        )

    success_runs = runs[(runs["status"] == "success") & (~err_rate_mask)].copy()

    # Check missing measurements and invalid latency ordering on successful runs
    if not success_runs.empty:
        null_lat = success_runs[["p50_latency_ms", "p95_latency_ms", "p99_latency_ms"]].isna().any(axis=1)
        if null_lat.any():
            errors.append(f"{int(null_lat.sum())} successful runs have missing latency percentiles.")

        non_positive = (
            (success_runs["p50_latency_ms"] <= 0)
            | (success_runs["p95_latency_ms"] <= 0)
            | (success_runs["p99_latency_ms"] <= 0)
        )
        if non_positive.any():
            errors.append(f"{int(non_positive.sum())} successful runs have non-positive latency values.")

        bad_order = (
            (success_runs["p50_latency_ms"] > success_runs["p95_latency_ms"])
            | (success_runs["p95_latency_ms"] > success_runs["p99_latency_ms"])
        )
        if bad_order.any():
            errors.append(
                f"{int(bad_order.sum())} successful runs violate p50 <= p95 <= p99 latency ordering."
            )

        # Inconsistent database configuration check (different versions for same database)
        version_counts = success_runs.groupby("database")["database_version"].nunique()
        multi_ver = version_counts[version_counts > 1]
        if not multi_ver.empty:
            warnings.append(
                f"Multiple database_version values recorded for: {multi_ver.to_dict()}"
            )

        # Outlier detection via IQR on p95_latency_ms per database
        outlier_count = 0
        for _, grp in success_runs.groupby("database"):
            if len(grp) >= 4:
                q1 = float(grp["p95_latency_ms"].quantile(0.25))
                q3 = float(grp["p95_latency_ms"].quantile(0.75))
                iqr = max(q3 - q1, 1e-6)
                outlier_count += int((grp["p95_latency_ms"] > q3 + 5.0 * iqr).sum())
        if outlier_count > 0:
            warnings.append(f"Detected {outlier_count} extreme p95 latency outlier runs (>5x IQR).")

        # Incomplete repetitions check
        rep_counts = success_runs.groupby(["workload_id", "database"]).size()
        incomplete = rep_counts[rep_counts < min_repetitions]
        if not incomplete.empty:
            warnings.append(
                f"{len(incomplete)} (workload_id, database) pairs have fewer than {min_repetitions} repetitions."
            )

    if profiles is not None and not profiles.empty:
        known_ids = set(profiles["workload_id"].astype(str))
        missing_meta = sorted(set(runs["workload_id"].astype(str)) - known_ids)
        if missing_meta:
            errors.append(
                f"{len(missing_meta)} workload_id values in runs are missing from workload profiles."
            )

    summary = {
        "total_runs": len(runs),
        "successful_valid_runs": len(success_runs),
        "databases": sorted(runs["database"].dropna().unique().tolist()),
        "workloads": int(runs["workload_id"].nunique()),
        "provenance_counts": runs["data_provenance"].value_counts().to_dict(),
    }

    return ValidationReport(
        is_valid=len(errors) == 0 and len(success_runs) > 0,
        total_rows=len(runs),
        valid_rows=len(success_runs),
        errors=errors,
        warnings=warnings,
        summary=summary,
    )


def ensure_no_synthetic_contamination(df: pd.DataFrame, allow_synthetic: bool = False) -> None:
    """Guardrail preventing synthetic data from entering genuine research models."""
    if allow_synthetic or df.empty:
        return
    if "data_provenance" not in df.columns:
        raise ValueError("Dataset is missing mandatory 'data_provenance' column.")
    if (df["data_provenance"] == DataProvenance.SYNTHETIC_DEMO.value).any():
        raise ValueError(
            "Refusing to train or evaluate research models on 'synthetic_demo' data."
        )
