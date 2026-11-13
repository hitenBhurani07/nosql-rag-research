"""Unit tests for mocked database adapters and Astra mode validation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nosql_rag.adapters import AdapterError, build_crud_adapter
from nosql_rag.adapters.crud import CassandraAdapter
from nosql_rag.config import DatabaseConfig


def test_cassandra_adapter_standard_mode_mocked() -> None:
    with patch("cassandra.cluster.Cluster") as mock_cluster:
        mock_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster.return_value = mock_instance
        mock_instance.connect.return_value = mock_session

        adapter = CassandraAdapter(
            mode="standard",
            hosts="127.0.0.1",
            port=9042,
            keyspace="test_ks",
        )
        assert adapter.mode == "standard"
        assert adapter.keyspace == "test_ks"
        mock_instance.connect.assert_called_once_with("test_ks")


def test_cassandra_adapter_astra_mode_mocked(tmp_path: Path) -> None:
    fake_bundle = tmp_path / "secure-connect-bundle.zip"
    fake_bundle.touch()

    with patch("cassandra.cluster.Cluster") as mock_cluster:
        mock_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster.return_value = mock_instance
        mock_instance.connect.return_value = mock_session

        adapter = CassandraAdapter(
            mode="astra",
            keyspace="test_ks",
            secure_connect_bundle_path=str(fake_bundle),
            application_token="AstraCS:fake-token",
        )
        assert adapter.mode == "astra"
        assert adapter.keyspace == "test_ks"
        mock_cluster.assert_called_once()
        call_kwargs = mock_cluster.call_args[1]
        assert call_kwargs["cloud"] == {"secure_connect_bundle": str(fake_bundle)}
        assert call_kwargs["protocol_version"] == 5
        mock_instance.connect.assert_called_once_with("test_ks")


def test_cassandra_adapter_astra_custom_protocol_version(tmp_path: Path) -> None:
    fake_bundle = tmp_path / "secure-connect-bundle.zip"
    fake_bundle.touch()

    with patch("cassandra.cluster.Cluster") as mock_cluster:
        mock_instance = MagicMock()
        mock_cluster.return_value = mock_instance
        mock_instance.connect.return_value = MagicMock()

        adapter = CassandraAdapter(
            mode="astra",
            keyspace="test_ks",
            secure_connect_bundle_path=str(fake_bundle),
            application_token="AstraCS:fake-token",
            protocol_version=4,
        )
        assert adapter.mode == "astra"
        call_kwargs = mock_cluster.call_args[1]
        assert call_kwargs["protocol_version"] == 4


def test_cassandra_adapter_astra_missing_bundle_raises() -> None:
    with pytest.raises(AdapterError, match="CASSANDRA_SECURE_CONNECT_BUNDLE_PATH"):
        CassandraAdapter(
            mode="astra",
            keyspace="test_ks",
            secure_connect_bundle_path=None,
            application_token="AstraCS:token",
        )


def test_cassandra_adapter_astra_nonexistent_bundle_raises(tmp_path: Path) -> None:
    non_existent = tmp_path / "does-not-exist.zip"
    with pytest.raises(AdapterError, match="not found at"):
        CassandraAdapter(
            mode="astra",
            keyspace="test_ks",
            secure_connect_bundle_path=str(non_existent),
            application_token="AstraCS:token",
        )


def test_build_crud_adapter_astra_routing(tmp_path: Path) -> None:
    fake_bundle = tmp_path / "bundle.zip"
    fake_bundle.touch()

    cfg = DatabaseConfig(
        cassandra_mode="astra",
        cassandra_keyspace="test_ks",
        cassandra_secure_connect_bundle_path=str(fake_bundle),
        cassandra_application_token="AstraCS:xyz",
    )
    with patch("cassandra.cluster.Cluster") as mock_cluster:
        mock_instance = MagicMock()
        mock_cluster.return_value = mock_instance
        mock_instance.connect.return_value = MagicMock()

        adapter = build_crud_adapter("Cassandra", cfg)
        assert isinstance(adapter, CassandraAdapter)
        assert adapter.mode == "astra"
