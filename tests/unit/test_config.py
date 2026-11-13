"""Unit tests for configuration loading, secret handling, and ProjectPaths."""

from pathlib import Path

from nosql_rag.config import DatabaseConfig, ProjectPaths, load_experiment_config


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
