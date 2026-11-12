"""Unit tests for data provenance, validation rules, and append-only persistence."""

from pathlib import Path

import pandas as pd
import pytest

from nosql_rag.data import (
    DataProvenance,
    aggregate_crud_runs,
    append_raw_runs,
    derive_best_store_labels,
    ensure_no_synthetic_contamination,
    generate_synthetic_demo_runs,
    load_raw_runs,
    validate_raw_runs,
)
from nosql_rag.workloads import generate_workload_profiles


def test_synthetic_contamination_blocked() -> None:
    profiles = generate_workload_profiles(n_profiles=4)
    syn = generate_synthetic_demo_runs(profiles, repetitions=1)
    assert (syn["data_provenance"] == DataProvenance.SYNTHETIC_DEMO.value).all()

    report = validate_raw_runs(syn, profiles=profiles, allow_synthetic=False)
    assert report.is_valid is False
    assert any("synthetic_demo" in err for err in report.errors)

    with pytest.raises(ValueError, match="synthetic_demo"):
        ensure_no_synthetic_contamination(syn, allow_synthetic=False)


def test_validation_rejects_bad_latency_and_duplicates() -> None:
    profiles = generate_workload_profiles(n_profiles=2)
    syn = generate_synthetic_demo_runs(profiles, repetitions=1)
    syn["data_provenance"] = DataProvenance.GENUINE_BENCHMARK.value

    # Corrupt p50 > p95
    bad = syn.copy()
    bad.loc[0, "p50_latency_ms"] = 9999.0
    rep = validate_raw_runs(bad, profiles=profiles)
    assert rep.is_valid is False
    assert any("ordering" in e for e in rep.errors)

    # Duplicate run_id
    dup = pd.concat([syn, syn.iloc[[0]]], ignore_index=True)
    rep_dup = validate_raw_runs(dup, profiles=profiles)
    assert rep_dup.is_valid is False
    assert any("duplicate run_id" in e for e in rep_dup.errors)


def test_append_only_and_aggregation(tmp_path: Path) -> None:
    csv_path = tmp_path / "raw_runs.csv"
    profiles = generate_workload_profiles(n_profiles=3)
    syn = generate_synthetic_demo_runs(profiles, repetitions=2)

    append_raw_runs(syn.iloc[:4].to_dict("records"), csv_path)
    append_raw_runs(syn.iloc[4:].to_dict("records"), csv_path)
    loaded = load_raw_runs(csv_path)
    assert len(loaded) == len(syn)

    agg = aggregate_crud_runs(loaded, allow_synthetic=True)
    assert len(agg) == 3 * 4
    labels = derive_best_store_labels(agg, profiles)
    assert len(labels) == 3
    assert set(labels["best_store"]).issubset({"Redis", "MongoDB", "Cassandra", "Neo4j"})
