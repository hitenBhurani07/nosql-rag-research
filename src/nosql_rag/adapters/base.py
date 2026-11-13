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


def sanitize_error_message(text: str | None) -> str | None:
    """Robustly redact secrets, passwords, tokens, and credentials from error diagnostics.

    Never allows credentials (Redis, MongoDB, Astra, Neo4j, Qdrant) to leak into logs,
    outputs, reports, or exception traces.
    """
    if not text:
        return None

    sanitized = str(text)

    # 1. Redact DataStax Astra application tokens first
    sanitized = re.sub(
        r"AstraCS:[A-Za-z0-9_\-:]+",
        "AstraCS:[REDACTED]",
        sanitized,
    )

    # 2. Redact Authorization headers and Bearer tokens
    sanitized = re.sub(
        r"(Authorization\s*[:=]\s*(?:Bearer\s+)?)(?!\[REDACTED\])[A-Za-z0-9_\-\.]{6,}",
        r"\1[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"(\bBearer\s+)(?!\[REDACTED\])[A-Za-z0-9_\-\.]{6,}",
        r"\1[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )

    # 3. Redact URI userinfo with user:password (e.g. mongodb+srv://user:pass@host, neo4j+s://user:pass@host)
    sanitized = re.sub(
        r"://([^:\s/@]+):([^\s/]+)@([a-zA-Z0-9_.-]+(?::[0-9]+)?(?:[/?#\s]|$))",
        r"://\1:[REDACTED]@\3",
        sanitized,
    )
    # Redact URI userinfo with empty user (e.g. redis://:password@host)
    sanitized = re.sub(
        r"://:([^\s/]+)@([a-zA-Z0-9_.-]+(?::[0-9]+)?(?:[/?#\s]|$))",
        r"://:[REDACTED]@\2",
        sanitized,
    )
    # Redact URI userinfo without colon (e.g. redis://password@host)
    sanitized = re.sub(
        r"://([^:@\s/]+)@([a-zA-Z0-9_.-]+(?::[0-9]+)?(?:[/?#\s]|$))",
        r"://[REDACTED]@\2",
        sanitized,
    )

    # 4. Redact URL query parameters (e.g. ?api_key=... or &token=...)
    sanitized = re.sub(
        r"([?&](?:api[_-]?key|token|password|secret|auth)=)([^&\s]+)",
        r"\1[REDACTED]",
        sanitized,
        flags=re.IGNORECASE,
    )

    # 5. Redact key-value assignments: token=..., api_key: ..., password = ...
    # Negative lookahead prevents mangling values that were already redacted
    sanitized = re.sub(
        r"((?:api[_-]?key|password|token|secret)\s*[:=]\s*)(['\"]?)(?!\[REDACTED\]|AstraCS:\[REDACTED\])[^'\",\s;&]+\2",
        r"\1\2[REDACTED]\2",
        sanitized,
        flags=re.IGNORECASE,
    )

    return sanitized


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
