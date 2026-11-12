"""Integration tests requiring live database endpoints configured via `.env`."""

import pytest

from nosql_rag.adapters import check_crud_connections, check_qdrant_connection
from nosql_rag.config import DatabaseConfig


@pytest.mark.integration
def test_live_crud_connections_when_configured() -> None:
    cfg = DatabaseConfig.from_env()
    statuses = cfg.safe_status()
    configured = [s["database"] for s in statuses if s["configured"] and s["database"] != "Qdrant"]
    if not configured:
        pytest.skip("No CRUD database endpoints configured in environment/.env")

    results = check_crud_connections(cfg, databases=tuple(configured))
    for r in results:
        assert r["connected"] is True, f"{r['database']} failed: {r['error']}"


@pytest.mark.integration
def test_live_qdrant_connection_when_configured() -> None:
    cfg = DatabaseConfig.from_env()
    if not cfg.qdrant_url:
        pytest.skip("QDRANT_URL not configured in environment/.env")
    res = check_qdrant_connection(cfg)
    assert res["connected"] is True, f"Qdrant failed: {res['error']}"
