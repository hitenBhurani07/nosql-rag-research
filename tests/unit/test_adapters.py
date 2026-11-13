"""Unit tests for adapter interfaces, safe identifiers, and live connection error handling."""

from unittest.mock import MagicMock, patch

import pytest

from nosql_rag.adapters import (
    AdapterError,
    build_crud_adapter,
    check_crud_connections,
    check_qdrant_connection,
    safe_identifier,
)
from nosql_rag.config import DatabaseConfig


def test_safe_identifier() -> None:
    assert safe_identifier("123-abc!def") == "bench_123_abc_def"
    assert len(safe_identifier("a" * 100)) <= 48


def test_unconfigured_adapters_fail_honestly() -> None:
    empty_cfg = DatabaseConfig()
    with pytest.raises(AdapterError):
        build_crud_adapter("Redis", empty_cfg)
    with pytest.raises(AdapterError):
        build_crud_adapter("MongoDB", empty_cfg)
    with pytest.raises(AdapterError):
        build_crud_adapter("Cassandra", empty_cfg)
    with pytest.raises(AdapterError):
        build_crud_adapter("Neo4j", empty_cfg)

    crud_status = check_crud_connections(empty_cfg)
    assert all(r["connected"] is False for r in crud_status)
    assert all(r["status"] == "SKIPPED" for r in crud_status)
    q_status = check_qdrant_connection(empty_cfg)
    assert q_status["connected"] is False
    assert q_status["status"] == "SKIPPED"


def test_check_crud_connections_partial_provisioning() -> None:
    cfg = DatabaseConfig(
        redis_url="redis://localhost:6379",
        mongodb_uri="mongodb://localhost:27017",
        neo4j_uri=None,  # unconfigured
    )
    with patch("nosql_rag.adapters.crud.build_crud_adapter") as mock_build:
        mock_adapter = MagicMock()
        mock_adapter.check.return_value = True
        mock_adapter.version = "1.0.0"
        mock_build.return_value = mock_adapter

        crud_status = {r["database"]: r for r in check_crud_connections(cfg, databases=("Redis", "MongoDB", "Neo4j"))}

        assert crud_status["Redis"]["status"] == "CONNECTED"
        assert crud_status["Redis"]["connected"] is True

        assert crud_status["MongoDB"]["status"] == "CONNECTED"
        assert crud_status["MongoDB"]["connected"] is True

        assert crud_status["Neo4j"]["status"] == "SKIPPED"
        assert crud_status["Neo4j"]["connected"] is False
        assert "skipped" in crud_status["Neo4j"]["error"].lower()


def test_check_crud_connections_sanitizes_errors() -> None:
    cfg = DatabaseConfig(
        redis_url="redis://default:my_secret_pass_999@localhost:6379",
    )
    with patch("nosql_rag.adapters.crud.build_crud_adapter") as mock_build:
        mock_build.side_effect = RuntimeError(
            "Auth failed for redis://default:my_secret_pass_999@localhost:6379"
        )
        results = check_crud_connections(cfg, databases=("Redis",))
        assert len(results) == 1
        res = results[0]
        assert res["status"] == "FAILED"
        assert res["connected"] is False
        assert "my_secret_pass_999" not in res["error"]
        assert "[REDACTED]" in res["error"]
