"""Unit tests for the CRUD pilot execution gate, resume logic, and provenance contracts."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from nosql_rag.benchmarking import (
    analyze_pilot_progress,
    run_crud_matrix,
    verify_crud_pilot_readiness,
)
from nosql_rag.config import DatabaseConfig
from nosql_rag.data import DataProvenance, append_raw_runs, load_raw_runs, validate_raw_runs
from nosql_rag.workloads import generate_workload_profiles


def test_verify_crud_pilot_readiness_all_connected_list_structure() -> None:
    # check_crud_connections returns list[dict[str, Any]]
    mock_statuses = [
        {"database": "Redis", "status": "CONNECTED", "configured": True, "connected": True, "version": "8.8.0", "connect_check_ms": 10.0, "error": None},
        {"database": "MongoDB", "status": "CONNECTED", "configured": True, "connected": True, "version": "8.0.37", "connect_check_ms": 25.0, "error": None},
        {"database": "Cassandra", "status": "CONNECTED", "configured": True, "connected": True, "version": "4.0.11", "connect_check_ms": 40.0, "error": None},
        {"database": "Neo4j", "status": "CONNECTED", "configured": True, "connected": True, "version": "5.27", "connect_check_ms": 15.0, "error": None},
    ]
    cfg = DatabaseConfig()
    with patch("nosql_rag.adapters.check_crud_connections", return_value=mock_statuses):
        res = verify_crud_pilot_readiness(cfg)
        assert isinstance(res, dict)
        assert len(res) == 4
        assert all(v["connected"] for v in res.values())
        assert set(res.keys()) == {"Redis", "MongoDB", "Cassandra", "Neo4j"}


def test_verify_crud_pilot_readiness_mongodb_failed_list_structure() -> None:
    mock_statuses = [
        {"database": "Redis", "status": "CONNECTED", "configured": True, "connected": True, "version": "8.8.0", "error": None},
        {"database": "MongoDB", "status": "FAILED", "configured": True, "connected": False, "version": None, "error": "ServerSelectionTimeoutError: SSL handshake failed"},
        {"database": "Cassandra", "status": "CONNECTED", "configured": True, "connected": True, "version": "4.0.11", "error": None},
        {"database": "Neo4j", "status": "CONNECTED", "configured": True, "connected": True, "version": "5.27", "error": None},
    ]
    cfg = DatabaseConfig()
    with patch("nosql_rag.adapters.check_crud_connections", return_value=mock_statuses):
        with pytest.raises(RuntimeError, match="MongoDB.*FAILED.*SSL handshake failed"):
            verify_crud_pilot_readiness(cfg)


def test_verify_crud_pilot_readiness_cassandra_skipped_list_structure() -> None:
    mock_statuses = [
        {"database": "Redis", "status": "CONNECTED", "configured": True, "connected": True, "version": "8.8.0", "error": None},
        {"database": "MongoDB", "status": "CONNECTED", "configured": True, "connected": True, "version": "8.0.37", "error": None},
        {"database": "Cassandra", "status": "SKIPPED", "configured": False, "connected": False, "version": None, "error": "SCB bundle not staged"},
        {"database": "Neo4j", "status": "CONNECTED", "configured": True, "connected": True, "version": "5.27", "error": None},
    ]
    cfg = DatabaseConfig()
    with patch("nosql_rag.adapters.check_crud_connections", return_value=mock_statuses):
        with pytest.raises(RuntimeError, match="Cassandra.*SKIPPED.*SCB bundle not staged"):
            verify_crud_pilot_readiness(cfg)


def test_verify_crud_pilot_readiness_missing_database_raises() -> None:
    # List is missing Neo4j entirely
    mock_statuses = [
        {"database": "Redis", "status": "CONNECTED", "configured": True, "connected": True, "version": "8.8.0", "error": None},
        {"database": "MongoDB", "status": "CONNECTED", "configured": True, "connected": True, "version": "8.0.37", "error": None},
        {"database": "Cassandra", "status": "CONNECTED", "configured": True, "connected": True, "version": "4.0.11", "error": None},
    ]
    cfg = DatabaseConfig()
    with patch("nosql_rag.adapters.check_crud_connections", return_value=mock_statuses):
        with pytest.raises(RuntimeError, match="Neo4j.*MISSING"):
            verify_crud_pilot_readiness(cfg)


def test_run_crud_matrix_resume_after_partial_failures(tmp_path: Path) -> None:
    csv_file = tmp_path / "test_runs.csv"
    profiles = generate_workload_profiles(n_profiles=2, operations=10, records=10, concurrency_levels=[1], id_prefix="P")
    cfg = DatabaseConfig()

    # Simulate historical attempts:
    # Attempt 1: All 8 failed
    # Attempt 2: Redis (P0001, P0002) and Neo4j (P0001, P0002) succeeded; MongoDB and Cassandra failed
    # Total historical rows = 16 (4 successes, 12 failures)
    historical_rows = []
    for wid in ["P0001", "P0002"]:
        for db in ["Redis", "MongoDB", "Cassandra", "Neo4j"]:
            # Attempt 1 failed
            historical_rows.append({
                "run_id": f"{wid.lower()}_{db.lower()}_att1_failed",
                "workload_id": wid,
                "configuration_id": f"{wid}__{db}",
                "database": db,
                "database_version": "unknown",
                "query_type": "key_value_crud",
                "payload_bytes": 128,
                "dataset_records": 10,
                "read_ratio": 0.5,
                "write_ratio": 0.5,
                "concurrency": 1,
                "n_operations": 10,
                "warmup_operations": 2,
                "repetition": 1,
                "started_utc": "2026-01-01T00:00:00Z",
                "finished_utc": "2026-01-01T00:00:01Z",
                "p50_latency_ms": None,
                "p95_latency_ms": None,
                "p99_latency_ms": None,
                "mean_latency_ms": None,
                "throughput_ops_sec": None,
                "error_count": 10,
                "error_rate": 1.0,
                "status": "failed",
                "error_summary": f"{db} initial connection failed",
                "data_provenance": DataProvenance.GENUINE_BENCHMARK.value,
                "cleanup_result": "skipped",
            })
            # Attempt 2: Redis and Neo4j succeeded, MongoDB and Cassandra failed again
            is_success = db in ["Redis", "Neo4j"]
            historical_rows.append({
                "run_id": f"{wid.lower()}_{db.lower()}_att2_{'ok' if is_success else 'failed'}",
                "workload_id": wid,
                "configuration_id": f"{wid}__{db}",
                "database": db,
                "database_version": "1.0" if is_success else "unknown",
                "query_type": "key_value_crud",
                "payload_bytes": 128,
                "dataset_records": 10,
                "read_ratio": 0.5,
                "write_ratio": 0.5,
                "concurrency": 1,
                "n_operations": 10,
                "warmup_operations": 2,
                "repetition": 1,
                "started_utc": "2026-01-01T00:01:00Z",
                "finished_utc": "2026-01-01T00:01:01Z",
                "p50_latency_ms": 2.0 if is_success else None,
                "p95_latency_ms": 3.0 if is_success else None,
                "p99_latency_ms": 4.0 if is_success else None,
                "mean_latency_ms": 2.5 if is_success else None,
                "throughput_ops_sec": 400.0 if is_success else None,
                "error_count": 0 if is_success else 10,
                "error_rate": 0.0 if is_success else 1.0,
                "status": "success" if is_success else "failed",
                "error_summary": None if is_success else ("TLS handshake failed" if db == "MongoDB" else "Astra SCB missing"),
                "data_provenance": DataProvenance.GENUINE_BENCHMARK.value,
                "cleanup_result": "success" if is_success else "skipped",
            })

    append_raw_runs(historical_rows, csv_file)
    initial_runs = load_raw_runs(csv_file)
    assert len(initial_runs) == 16
    assert (initial_runs["status"] == "success").sum() == 4
    assert (initial_runs["status"] == "failed").sum() == 12

    # Verify pre-execution analysis
    pre_analysis = analyze_pilot_progress(initial_runs, profiles, candidate_databases=["Redis", "MongoDB", "Cassandra", "Neo4j"])
    assert pre_analysis["target_configurations_count"] == 8
    assert pre_analysis["successful_configurations_count"] == 4
    assert pre_analysis["pending_configurations_count"] == 4
    assert pre_analysis["is_pilot_complete"] is False
    assert pre_analysis["total_historical_attempts"] == 16

    # Mock runner executing only pending runs (MongoDB and Cassandra for P0001 and P0002)
    def mock_benchmark_impl(database_name, workload, db_config, repetition=1, **kwargs):
        wid = workload["workload_id"]
        return {
            "run_id": f"{wid.lower()}_{database_name.lower()}_att3_ok",
            "workload_id": wid,
            "configuration_id": f"{wid}__{database_name}",
            "database": database_name,
            "database_version": "2.0",
            "query_type": "key_value_crud",
            "payload_bytes": 128,
            "dataset_records": 10,
            "read_ratio": 0.5,
            "write_ratio": 0.5,
            "concurrency": 1,
            "n_operations": 10,
            "warmup_operations": 2,
            "repetition": repetition,
            "started_utc": "2026-01-01T00:02:00Z",
            "finished_utc": "2026-01-01T00:02:01Z",
            "p50_latency_ms": 3.5,
            "p95_latency_ms": 4.5,
            "p99_latency_ms": 5.5,
            "mean_latency_ms": 3.8,
            "throughput_ops_sec": 300.0,
            "error_count": 0,
            "error_rate": 0.0,
            "status": "success",
            "cleanup_result": "success",
            "error_summary": None,
            "data_provenance": DataProvenance.GENUINE_BENCHMARK.value,
        }

    with patch("nosql_rag.benchmarking.runner.benchmark_common_crud", side_effect=mock_benchmark_impl) as mock_bench:
        updated_df = run_crud_matrix(
            profiles=profiles,
            databases=["Redis", "MongoDB", "Cassandra", "Neo4j"],
            db_config=cfg,
            output_csv=csv_file,
            repetitions=1,
            batch_size=4,
        )

        # EXACTLY 4 pending runs should have been executed (P0001 MongoDB, P0001 Cassandra, P0002 MongoDB, P0002 Cassandra)
        # Redis and Neo4j must NOT have been re-executed!
        assert mock_bench.call_count == 4
        executed_dbs = {call[1]["database_name"] for call in mock_bench.call_args_list}
        assert executed_dbs == {"MongoDB", "Cassandra"}

        # Total rows in CSV: 16 historical + 4 new = 20 rows
        assert len(updated_df) == 20
        # Historical attempts remain strictly preserved
        assert (updated_df["status"] == "failed").sum() == 12
        assert (updated_df["status"] == "success").sum() == 8

        # Post-execution analysis: all 8 unique target configurations now successful
        post_analysis = analyze_pilot_progress(updated_df, profiles, candidate_databases=["Redis", "MongoDB", "Cassandra", "Neo4j"])
        assert post_analysis["target_configurations_count"] == 8
        assert post_analysis["successful_configurations_count"] == 8
        assert post_analysis["pending_configurations_count"] == 0
        assert post_analysis["is_pilot_complete"] is True
        assert post_analysis["total_historical_attempts"] == 20


def test_synthetic_data_provenance_strictly_separated() -> None:
    profiles = generate_workload_profiles(n_profiles=2)
    fake_runs = pd.DataFrame([
        {
            "run_id": "syn_run_1",
            "workload_id": "P0001",
            "configuration_id": "P0001__Redis",
            "database": "Redis",
            "database_version": "7.0",
            "query_type": "key_value_crud",
            "payload_bytes": 128,
            "dataset_records": 10,
            "read_ratio": 0.5,
            "write_ratio": 0.5,
            "concurrency": 1,
            "n_operations": 10,
            "warmup_operations": 2,
            "repetition": 1,
            "started_utc": "2026-01-01T00:00:00Z",
            "finished_utc": "2026-01-01T00:00:01Z",
            "p50_latency_ms": 1.0,
            "p95_latency_ms": 2.0,
            "p99_latency_ms": 3.0,
            "mean_latency_ms": 1.5,
            "throughput_ops_sec": 500.0,
            "error_count": 0,
            "error_rate": 0.0,
            "status": "success",
            "data_provenance": DataProvenance.SYNTHETIC_DEMO.value,
        }
    ])
    # Validator must reject synthetic data when allow_synthetic=False (the research default)
    report = validate_raw_runs(fake_runs, profiles=profiles, allow_synthetic=False)
    assert not report.is_valid
    assert any("synthetic_demo" in err for err in report.errors)
