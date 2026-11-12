"""Unit tests for adapter interfaces, safe identifiers, and live connection error handling."""

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
    q_status = check_qdrant_connection(empty_cfg)
    assert q_status["connected"] is False
