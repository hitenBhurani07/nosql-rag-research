"""Tests for read-only factorial-matrix completeness reporting."""

from nosql_rag.benchmarking import audit_crud_matrix
from nosql_rag.data.persistence import generate_synthetic_demo_runs
from nosql_rag.workloads import generate_workload_profiles


def test_matrix_audit_maps_matched_profiles_and_rejects_synthetic_completions() -> None:
    profiles = generate_workload_profiles(
        n_profiles=2,
        operations=10,
        records=10,
        concurrency_levels=[1, 4],
        id_prefix="W",
        matched_concurrency=True,
    )
    synthetic = generate_synthetic_demo_runs(profiles, repetitions=1)

    report = audit_crud_matrix(synthetic, profiles=profiles, repetitions=1)

    assert report["total_rows"] == 16
    assert report["expected_run_keys"] == 16
    assert report["completed_genuine_keys"] == 0
    assert report["is_complete"] is False
    assert report["unique_matrix_workload_ids_observed"] == 4
    assert report["unique_base_workload_ids_observed"] == 2
    assert report["expected_concurrency_levels"] == [1, 4]
    assert len(report["missing_keys"]) == 16
    assert report["profile_mismatches"] == []
