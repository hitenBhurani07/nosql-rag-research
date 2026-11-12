"""Unit tests for the independent database preflight script."""

from unittest.mock import MagicMock, patch

from nosql_rag.config import DatabaseConfig
from scripts.database_preflight import format_table, run_database_preflight


def test_preflight_all_skipped_when_unconfigured() -> None:
    empty_cfg = DatabaseConfig()
    summary = run_database_preflight(empty_cfg)
    assert summary["configured_count"] == 0
    assert summary["passed_count"] == 0
    assert summary["skipped_count"] == 5
    table_str = format_table(summary)
    assert "Skipped" in table_str
    assert "MissingCredentials" in table_str


def test_preflight_reports_pass_with_mocked_adapter() -> None:
    cfg = DatabaseConfig(
        redis_url="redis://localhost:6379",
    )
    with patch("scripts.database_preflight.build_crud_adapter") as mock_build:
        mock_adapter = MagicMock()
        mock_adapter.check.return_value = True
        mock_adapter.version = "7.2.4"
        mock_build.return_value = mock_adapter

        summary = run_database_preflight(cfg)
        redis_entry = next(r for r in summary["databases"] if r["database"] == "Redis")
        assert redis_entry["configured"] is True
        assert redis_entry["status"] == "Pass"
        assert redis_entry["version"] == "7.2.4"


def test_preflight_qdrant_mocked() -> None:
    cfg = DatabaseConfig(qdrant_url="https://fake-cluster.cloud.qdrant.io:6333", qdrant_api_key="secret")
    with patch("scripts.database_preflight.check_qdrant_connection") as mock_qdrant:
        mock_qdrant.return_value = {
            "database": "Qdrant",
            "connected": True,
            "version": "1.8.0",
            "connect_check_ms": 12.5,
            "error": None,
        }
        summary = run_database_preflight(cfg)
        qdrant_entry = next(r for r in summary["databases"] if r["database"] == "Qdrant")
        assert qdrant_entry["configured"] is True
        assert qdrant_entry["status"] == "Pass"
        assert qdrant_entry["version"] == "1.8.0"
