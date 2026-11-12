"""Unit tests for mocked database adapters and Astra mode validation."""

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


def test_cassandra_adapter_astra_mode_mocked() -> None:
    with patch("cassandra.cluster.Cluster") as mock_cluster:
        mock_instance = MagicMock()
        mock_session = MagicMock()
        mock_cluster.return_value = mock_instance
        mock_instance.connect.return_value = mock_session

        adapter = CassandraAdapter(
            mode="astra",
            keyspace="test_ks",
            secure_connect_bundle_path="/tmp/fake-bundle.zip",
            application_token="AstraCS:fake-token",
        )
        assert adapter.mode == "astra"
        assert adapter.keyspace == "test_ks"
        mock_cluster.assert_called_once()
        call_kwargs = mock_cluster.call_args[1]
        assert call_kwargs["cloud"] == {"secure_connect_bundle": "/tmp/fake-bundle.zip"}
        mock_instance.connect.assert_called_once_with("test_ks")


def test_cassandra_adapter_astra_missing_bundle_raises() -> None:
    with pytest.raises(AdapterError, match="CASSANDRA_SECURE_CONNECT_BUNDLE_PATH"):
        CassandraAdapter(
            mode="astra",
            keyspace="test_ks",
            secure_connect_bundle_path=None,
            application_token="AstraCS:token",
        )


def test_build_crud_adapter_astra_routing() -> None:
    cfg = DatabaseConfig(
        cassandra_mode="astra",
        cassandra_keyspace="test_ks",
        cassandra_secure_connect_bundle_path="/tmp/bundle.zip",
        cassandra_application_token="AstraCS:xyz",
    )
    with patch("cassandra.cluster.Cluster") as mock_cluster:
        mock_instance = MagicMock()
        mock_cluster.return_value = mock_instance
        mock_instance.connect.return_value = MagicMock()

        adapter = build_crud_adapter("Cassandra", cfg)
        assert isinstance(adapter, CassandraAdapter)
        assert adapter.mode == "astra"
