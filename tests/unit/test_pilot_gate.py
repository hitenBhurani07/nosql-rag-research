"""Unit tests for the CRUD pilot execution gate, resume logic, and provenance contracts."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from nosql_rag.benchmarking import run_crud_matrix, verify_crud_pilot_readiness
from nosql_rag.config import DatabaseConfig
from nosql_rag.data import DataProvenance, append_raw_runs, load_raw_runs, validate_raw_runs
from nosql_rag.workloads import generate_workload_profiles


def test_verify_crud_pilot_readiness_all_connected() -> None:
    mock_statuses = {
        "Redis": {"status": "CONNECTED", "connected": True, "error": None},
        "MongoDB": {"status": "CONNECTED", "connected": True, "error": None},
        "Cassandra": {"status": "CONNECTED", "connected": True, "error": None},
        "Neo4j": {"status": "CONNECTED", "connected": True, "error": None},
    }
    cfg = DatabaseConfig()
    with patch("nosql_rag.adapters.check_crud_connections", return_value=mock_statuses):
        res = verify_crud_pilot_readiness(cfg)
        assert len(res) == 4
        assert all(v["connected"] for v in res.values())


def test_verify_crud_pilot_readiness_missing_or_skipped_engine_raises() -> None:
    mock_statuses = {
        "Redis": {"status": "CONNECTED", "connected": True, "error": None},
        "MongoDB": {"status": "CONNECTED", "connected": True, "error": None},
        "Cassandra": {"status": "CONNECTED", "connected": True, "error": None},
        "Neo4j": {"status": "SKIPPED", "connected": False, "error": "Unconfigured"},
    }
    cfg = DatabaseConfig()
    with patch("nosql_rag.adapters.check_crud_connections", return_value=mock_statuses):
        with pytest.raises(RuntimeError, match="Neo4j.*SKIPPED"):
            verify_crud_pilot_readiness(cfg)


def test_verify_crud_pilot_readiness_failed_engine_raises() -> None:
    mock_statuses = {
        "Redis": {"status": "CONNECTED", "connected": True, "error": None},
        "MongoDB": {"status": "FAILED", "connected": False, "error": "Auth failed"},
        "Cassandra": {"status": "CONNECTED", "connected": True, "error": None},
        "Neo4j": {"status": "CONNECTED", "connected": True, "error": None},
    }
    cfg = DatabaseConfig()
    with patch("nosql_rag.adapters.check_crud_connections", return_value=mock_statuses):
        with pytest.raises(RuntimeError, match="MongoDB.*FAILED"):
            verify_crud_pilot_readiness(cfg)


def test_run_crud_matrix_resume_behavior(tmp_path: Path) -> None:
    csv_file = tmp_path / "test_runs.csv"
    profiles = generate_workload_profiles(n_profiles=2, operations=10, records=10, concurrency_levels=[1])
    cfg = DatabaseConfig()

    # Pre-populate CSV with 1 successful run: (P0001, Redis, 1)
    existing_run = {
        "run_id": "p0001_redis_r1_test",
        "workload_id": str(profiles.iloc[0]["workload_id"]),
        "configuration_id": f"{profiles.iloc[0]['workload_id']}__Redis",
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
        "p50_latency_ms": 1.5,
        "p95_latency_ms": 2.5,
        "p99_latency_ms": 3.0,
        "mean_latency_ms": 1.8,
        "throughput_ops_sec": 500.0,
        "error_count": 0,
        "error_rate": 0.0,
        "status": "success",
        "data_provenance": DataProvenance.GENUINE_BENCHMARK.value,
    }
    append_raw_runs([existing_run], csv_file)
    assert len(load_raw_runs(csv_file)) == 1

    # Mock benchmark_common_crud to simulate executing only pending runs
    mock_run_outcome = dict(existing_run)
    mock_run_outcome["run_id"] = "p0002_redis_r1_test"
    mock_run_outcome["workload_id"] = str(profiles.iloc[1]["workload_id"])
    mock_run_outcome["configuration_id"] = f"{profiles.iloc[1]['workload_id']}__Redis"

    with patch("nosql_rag.benchmarking.runner.benchmark_common_crud", return_value=mock_run_outcome) as mock_bench:
        result_df = run_crud_matrix(
            profiles=profiles,
            databases=["Redis"],
            db_config=cfg,
            output_csv=csv_file,
            repetitions=1,
            batch_size=2,
        )
        # Should only have executed 1 benchmark call (for P0002), since P0001 was already completed
        assert mock_bench.call_count == 1
        assert len(result_df) == 2
        assert set(result_df["workload_id"]) == {str(profiles.iloc[0]["workload_id"]), str(profiles.iloc[1]["workload_id"])}


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
