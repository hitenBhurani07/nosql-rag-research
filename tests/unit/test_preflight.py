"""Unit tests for the independent database preflight script."""

import json
from unittest.mock import MagicMock, patch

from nosql_rag.adapters.base import sanitize_error_message
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


def test_sanitize_error_message_removes_all_secret_patterns() -> None:
    cases = [
        (
            "Connection failed: redis://:MyRedisSecretPass123!@redis-host:6379/0",
            "MyRedisSecretPass123!",
            "redis://:[REDACTED]@redis-host:6379/0",
        ),
        (
            "Mongo auth failed: mongodb+srv://admin_user:P@ssw0rd999!@cluster0.abcde.mongodb.net/testdb?retry=true",
            "P@ssw0rd999!",
            "mongodb+srv://admin_user:[REDACTED]@cluster0.abcde.mongodb.net/testdb?retry=true",
        ),
        (
            "Invalid Astra token: AstraCS:sample_client_id_secret_key_12345 cannot connect",
            "AstraCS:sample_client_id_secret_key_12345",
            "AstraCS:[REDACTED]",
        ),
        (
            "Neo4j error on neo4j+s://neo4j:SecretGraphPass!@instance.databases.neo4j.io:7687",
            "SecretGraphPass!",
            "neo4j+s://neo4j:[REDACTED]@instance.databases.neo4j.io:7687",
        ),
        (
            "Qdrant 401 client error: https://cluster.qdrant.io:6333?api_key=my_super_secret_qdrant_key",
            "my_super_secret_qdrant_key",
            "https://cluster.qdrant.io:6333?api_key=[REDACTED]",
        ),
        (
            "Failed request with headers: Authorization: Bearer secret_bearer_token_xyz987654",
            "secret_bearer_token_xyz987654",
            "Authorization: Bearer [REDACTED]",
        ),
    ]

    for raw_message, raw_secret, expected_substring in cases:
        sanitized = sanitize_error_message(raw_message)
        assert sanitized is not None
        assert raw_secret not in sanitized, f"Secret {raw_secret} leaked in: {sanitized}"
        assert expected_substring in sanitized


def test_preflight_redacts_credentials_in_exception() -> None:
    cfg = DatabaseConfig(redis_url="redis://localhost:6379")
    secret_pass = "LeakedRedisPass99"
    leaked_msg = f"ConnectionError: Authentication failed for redis://:{secret_pass}@myhost.cloud.redns:1234"

    with patch("scripts.database_preflight.build_crud_adapter") as mock_build:
        mock_build.side_effect = RuntimeError(leaked_msg)

        summary = run_database_preflight(cfg)
        redis_entry = next(r for r in summary["databases"] if r["database"] == "Redis")

        assert redis_entry["status"] == "Fail"
        assert redis_entry["error_category"] == "AuthenticationError"
        assert secret_pass not in redis_entry["error_details"]
        assert "[REDACTED]" in redis_entry["error_details"]

        # Verify formatted table output
        table_output = format_table(summary)
        assert secret_pass not in table_output

        # Verify JSON serialized output
        json_output = json.dumps(summary)
        assert secret_pass not in json_output


def test_preflight_redacts_qdrant_api_key_in_exception() -> None:
    cfg = DatabaseConfig(qdrant_url="https://fake-cluster.cloud.qdrant.io:6333", qdrant_api_key="secret")
    raw_api_key = "super_secret_key_999"

    with patch("scripts.database_preflight.check_qdrant_connection") as mock_qdrant:
        mock_qdrant.return_value = {
            "database": "Qdrant",
            "connected": False,
            "version": None,
            "connect_check_ms": 15.0,
            "error": f"ClientError: 401 Unauthorized for api_key={raw_api_key}",
        }
        summary = run_database_preflight(cfg)
        qdrant_entry = next(r for r in summary["databases"] if r["database"] == "Qdrant")

        assert qdrant_entry["status"] == "Fail"
        assert qdrant_entry["error_category"] == "AuthenticationError"
        assert raw_api_key not in qdrant_entry["error_details"]
        assert "[REDACTED]" in qdrant_entry["error_details"]

        json_output = json.dumps(summary)
        assert raw_api_key not in json_output
