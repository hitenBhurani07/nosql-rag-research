"""Unit tests for configuration loading, secret handling, and ProjectPaths."""

import zipfile
from pathlib import Path

from nosql_rag.config import (
    DatabaseConfig,
    ProjectPaths,
    load_experiment_config,
    validate_runtime_configuration,
)


def test_project_paths_creation(tmp_path: Path) -> None:
    paths = ProjectPaths(root=tmp_path)
    assert paths.root == tmp_path
    assert paths.data_raw == tmp_path / "data" / "raw"
    assert paths.results_models == tmp_path / "results" / "models"
    paths.ensure_dirs()
    assert paths.data_raw.exists()
    assert paths.logs.exists()


def test_database_config_safe_status() -> None:
    cfg = DatabaseConfig(
        redis_url="redis://localhost:6379",
        mongodb_uri=None,
        cassandra_hosts="127.0.0.1",
        cassandra_keyspace="test_ks",
    )
    status = {item["database"]: item["configured"] for item in cfg.safe_status()}
    assert status["Redis"] is True
    assert status["MongoDB"] is False
    assert status["Cassandra"] is True
    assert status["Neo4j"] is False
    assert status["Qdrant"] is False


def test_experiment_config_validation() -> None:
    cfg = load_experiment_config(Path("configs/experiment.yaml"))
    assert cfg.random_seed == 42
    assert cfg.primary_objective == "min_p95_latency_ms"
    assert cfg.pilot.n_profiles >= 1
    assert cfg.full_matrix.n_profiles >= 10


def test_neo4j_username_and_user_alias(monkeypatch) -> None:
    # Test primary variable NEO4J_USERNAME
    monkeypatch.setenv("NEO4J_USERNAME", "admin_user")
    monkeypatch.delenv("NEO4J_USER", raising=False)
    cfg1 = DatabaseConfig.from_env()
    assert cfg1.neo4j_username == "admin_user"

    # Test fallback alias NEO4J_USER
    monkeypatch.delenv("NEO4J_USERNAME", raising=False)
    monkeypatch.setenv("NEO4J_USER", "fallback_user")
    cfg2 = DatabaseConfig.from_env()
    assert cfg2.neo4j_username == "fallback_user"


def test_validate_runtime_configuration_partial_provisioning(tmp_path: Path) -> None:
    # Create valid mock Astra bundle with expected config.json and cert
    scb_file = tmp_path / "secure-connect-bundle.zip"
    with zipfile.ZipFile(scb_file, "w") as zf:
        zf.writestr("config.json", '{"host": "mock.db.datastax.com"}')
        zf.writestr("cert", b"fake-certificate-bytes")
        zf.writestr("cqlshrc", "[cql]\nversion = 3.4.5")

    cfg = DatabaseConfig(
        redis_url="redis://default:secret@profit-cook-stitch-74158.db.redis.io:18690",
        mongodb_uri="mongodb+srv://rag_research:secret@cluster0.hqd8wfk.mongodb.net/nosql_rag_research",
        mongodb_database="nosql_rag_research",
        cassandra_mode="astra",
        cassandra_keyspace="nosql_rag_research",
        cassandra_application_token="AstraCS:test-token",
        cassandra_secure_connect_bundle_path=str(scb_file),
    )

    validation = {item["database"]: item for item in validate_runtime_configuration(cfg)}

    assert validation["Redis"]["status"] == "configured"
    assert validation["Redis"]["valid"] is True
    assert "secret" not in validation["Redis"]["details"]

    assert validation["MongoDB"]["status"] == "configured"
    assert validation["MongoDB"]["valid"] is True
    assert "secret" not in validation["MongoDB"]["details"]

    assert validation["Cassandra"]["status"] == "configured"
    assert validation["Cassandra"]["valid"] is True
    assert "AstraCS" not in validation["Cassandra"]["details"]

    assert validation["Neo4j"]["status"] == "unconfigured (skipped in Phase 13.1)"
    assert validation["Qdrant"]["status"] == "unconfigured (skipped in Phase 13.1)"


def test_validate_runtime_configuration_missing_scb(tmp_path: Path) -> None:
    non_existent = tmp_path / "missing-bundle.zip"
    cfg = DatabaseConfig(
        cassandra_mode="astra",
        cassandra_keyspace="nosql_rag_research",
        cassandra_application_token="AstraCS:test-token",
        cassandra_secure_connect_bundle_path=str(non_existent),
    )
    validation = {item["database"]: item for item in validate_runtime_configuration(cfg)}
    assert validation["Cassandra"]["status"] == "missing_bundle"
    assert validation["Cassandra"]["valid"] is False


def test_validate_runtime_configuration_invalid_schemes() -> None:
    cfg = DatabaseConfig(
        redis_url="http://localhost:6379",
        mongodb_uri="postgres://localhost:5432/db",
    )
    validation = {item["database"]: item for item in validate_runtime_configuration(cfg)}
    assert validation["Redis"]["status"] == "invalid"
    assert validation["Redis"]["valid"] is False
    assert validation["MongoDB"]["status"] == "invalid"
    assert validation["MongoDB"]["valid"] is False
