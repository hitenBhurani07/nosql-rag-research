"""Native Qdrant vector database adapter."""

from __future__ import annotations

import time
from typing import Any

from nosql_rag.adapters.base import AdapterError, BaseAdapter
from nosql_rag.config import DatabaseConfig


class QdrantAdapter(BaseAdapter):
    """Qdrant vector store adapter using qdrant-client."""

    name = "Qdrant"

    def __init__(self, url: str, api_key: str | None = None, timeout: int = 60) -> None:
        from qdrant_client import QdrantClient

        if not url:
            raise AdapterError("QDRANT_URL is not configured")
        self.client = QdrantClient(url=url, api_key=api_key, timeout=timeout)

    def check(self) -> bool:
        self.client.get_collections()
        self.version = "qdrant-remote"
        return True

    def metadata(self) -> dict[str, Any]:
        return {"database": self.name, "version": self.version, "model": "vector"}

    def create_collection(self, collection_name: str, vector_size: int, distance: str = "COSINE") -> None:
        from qdrant_client.models import Distance, VectorParams

        dist_enum = getattr(Distance, distance.upper(), Distance.COSINE)
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=dist_enum),
        )

    def upsert_points(self, collection_name: str, points: list[Any]) -> None:
        self.client.upsert(collection_name=collection_name, points=points, wait=True)

    def query(self, collection_name: str, query_vector: list[float], limit: int = 10) -> list[Any]:
        response = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
        )
        return list(response.points)

    def cleanup(self, run_id: str) -> None:
        self.client.delete_collection(collection_name=run_id)

    def close(self) -> None:
        self.client.close()


def check_qdrant_connection(config: DatabaseConfig) -> dict[str, Any]:
    """Verify live connectivity to Qdrant."""
    started = time.perf_counter()
    adapter: QdrantAdapter | None = None
    try:
        if not config.qdrant_url:
            raise AdapterError("QDRANT_URL is not configured")
        adapter = QdrantAdapter(url=config.qdrant_url, api_key=config.qdrant_api_key, timeout=15)
        ok = adapter.check()
        return {
            "database": "Qdrant",
            "connected": bool(ok),
            "version": adapter.version,
            "connect_check_ms": round((time.perf_counter() - started) * 1000, 3),
            "error": None,
        }
    except Exception as exc:
        return {
            "database": "Qdrant",
            "connected": False,
            "version": None,
            "connect_check_ms": round((time.perf_counter() - started) * 1000, 3),
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
        }
    finally:
        if adapter is not None:
            try:
                adapter.close()
            except Exception:
                pass
