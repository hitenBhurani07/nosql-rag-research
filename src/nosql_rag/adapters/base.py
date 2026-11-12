"""Base database adapter contract and shared utilities."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any


class AdapterError(RuntimeError):
    """Raised when a database adapter cannot connect, configure, or execute."""


def safe_identifier(value: str, prefix: str = "bench") -> str:
    """Sanitize a run or collection identifier for safe database object naming."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", str(value))
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"{prefix}_{cleaned}"
    return cleaned[:48]


class BaseAdapter(ABC):
    """Common lifecycle and health-check interface for all NoSQL adapters."""

    name: str = "Base"
    version: str = "unknown"

    @abstractmethod
    def check(self) -> bool:
        """Verify connectivity and populate `self.version`."""

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return non-sensitive database engine metadata."""

    @abstractmethod
    def cleanup(self, run_id: str) -> None:
        """Remove temporary benchmark artifacts created for `run_id`."""

    def close(self) -> None:
        """Release underlying client connections."""
        return None


class BaseCRUDAdapter(BaseAdapter):
    """Interface for operational record-level CRUD benchmarking."""

    @abstractmethod
    def prepare(self, run_id: str, records: list[dict[str, str]]) -> None:
        """Create schema/index if needed and seed `records` for `run_id`."""

    @abstractmethod
    def read(self, run_id: str, record_id: str) -> bool:
        """Read a single record by ID."""

    @abstractmethod
    def update(self, run_id: str, record_id: str, payload_json: str) -> bool:
        """Update a single record's payload."""
