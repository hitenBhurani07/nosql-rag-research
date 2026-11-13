"""Configuration, secret resolution, project paths, and logging setup."""

from __future__ import annotations

import logging
import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


def _get_secret(name: str, default: str | None = None) -> str | None:
    """Read a secret from Google Colab Secrets first, then environment variables.

    Never prints or logs secret values.
    """
    try:
        from google.colab import userdata  # type: ignore[import-not-found]

        value = userdata.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    value = os.environ.get(name)
    if value is not None and value != "":
        return value
    return default


def _parse_bool(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ProjectPaths:
    """Canonical directory layout relative to the project root."""

    root: Path
    configs: Path = field(init=False)
    data_raw: Path = field(init=False)
    data_processed: Path = field(init=False)
    data_sample: Path = field(init=False)
    results_benchmarks: Path = field(init=False)
    results_models: Path = field(init=False)
    results_figures: Path = field(init=False)
    results_tables: Path = field(init=False)
    logs: Path = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "configs", self.root / "configs")
        object.__setattr__(self, "data_raw", self.root / "data" / "raw")
        object.__setattr__(self, "data_processed", self.root / "data" / "processed")
        object.__setattr__(self, "data_sample", self.root / "data" / "sample")
        object.__setattr__(self, "results_benchmarks", self.root / "results" / "benchmarks")
        object.__setattr__(self, "results_models", self.root / "results" / "models")
        object.__setattr__(self, "results_figures", self.root / "results" / "figures")
        object.__setattr__(self, "results_tables", self.root / "results" / "tables")
        object.__setattr__(self, "logs", self.root / "logs")

    def ensure_dirs(self) -> None:
        for path in (
            self.data_raw,
            self.data_processed,
            self.data_sample,
            self.results_benchmarks,
            self.results_models,
            self.results_figures,
            self.results_tables,
            self.logs,
        ):
            path.mkdir(parents=True, exist_ok=True)


class DatabaseConfig(BaseModel):
    """Connection settings for all five candidate databases.

    Credentials are never serialized into logs or repr outputs.
    """

    # Redis (Key-Value)
    redis_url: str | None = None

    # MongoDB (Document)
    mongodb_uri: str | None = None
    mongodb_database: str = "nosql_rag_research"

    # Apache Cassandra / DataStax Astra (Wide-Column)
    cassandra_mode: str = "standard"  # 'standard' or 'astra'
    cassandra_hosts: str | None = None
    cassandra_port: int = 9042
    cassandra_username: str | None = None
    cassandra_password: str | None = None
    cassandra_keyspace: str | None = None
    cassandra_ssl: bool = False
    cassandra_secure_connect_bundle_path: str | None = None
    cassandra_application_token: str | None = None

    # Neo4j (Graph)
    neo4j_uri: str | None = None
    neo4j_username: str | None = None
    neo4j_password: str | None = None
    neo4j_database: str = "neo4j"

    # Qdrant (Vector)
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None

    # Hosting & Deployment Telemetry
    hosting_region: str = "local"
    deployment_notes: str = "unspecified"

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> DatabaseConfig:
        """Load database configuration from `.env`, Colab Secrets, and environment."""
        if env_file is not None and env_file.exists():
            load_dotenv(dotenv_path=env_file, override=False)
        else:
            load_dotenv(override=False)

        port_raw = _get_secret("CASSANDRA_PORT", "9042") or "9042"
        cassandra_mode = (_get_secret("CASSANDRA_MODE", "standard") or "standard").lower().strip()
        bundle_path = _get_secret("CASSANDRA_SECURE_CONNECT_BUNDLE_PATH")
        app_token = _get_secret("CASSANDRA_APPLICATION_TOKEN") or _get_secret("ASTRA_DB_APPLICATION_TOKEN")
        # Auto-detect astra mode if bundle path or token is present
        if bundle_path or app_token:
            cassandra_mode = "astra"

        return cls(
            redis_url=_get_secret("REDIS_URL"),
            mongodb_uri=_get_secret("MONGODB_URI"),
            mongodb_database=_get_secret("MONGODB_DATABASE", "nosql_rag_research")
            or "nosql_rag_research",
            cassandra_mode=cassandra_mode,
            cassandra_hosts=_get_secret("CASSANDRA_HOSTS"),
            cassandra_port=int(port_raw),
            cassandra_username=_get_secret("CASSANDRA_USERNAME"),
            cassandra_password=_get_secret("CASSANDRA_PASSWORD"),
            cassandra_keyspace=_get_secret("CASSANDRA_KEYSPACE"),
            cassandra_ssl=_parse_bool(_get_secret("CASSANDRA_SSL", "false")),
            cassandra_secure_connect_bundle_path=bundle_path,
            cassandra_application_token=app_token,
            neo4j_uri=_get_secret("NEO4J_URI"),
            neo4j_username=_get_secret("NEO4J_USERNAME") or _get_secret("NEO4J_USER"),
            neo4j_password=_get_secret("NEO4J_PASSWORD"),
            neo4j_database=_get_secret("NEO4J_DATABASE", "neo4j") or "neo4j",
            qdrant_url=_get_secret("QDRANT_URL"),
            qdrant_api_key=_get_secret("QDRANT_API_KEY"),
            hosting_region=_get_secret("DATABASE_HOSTING_REGION", "local") or "local",
            deployment_notes=_get_secret("DATABASE_DEPLOYMENT_NOTES", "unspecified")
            or "unspecified",
        )

    def safe_status(self) -> list[dict[str, Any]]:
        """Return non-sensitive configuration presence flags."""
        is_cassandra_configured = False
        if self.cassandra_mode == "astra":
            is_cassandra_configured = bool(
                self.cassandra_secure_connect_bundle_path
                and self.cassandra_application_token
                and self.cassandra_keyspace
            )
        else:
            is_cassandra_configured = bool(self.cassandra_hosts and self.cassandra_keyspace)

        return [
            {"database": "Redis", "setting": "redis_url", "configured": bool(self.redis_url)},
            {
                "database": "MongoDB",
                "setting": "mongodb_uri",
                "configured": bool(self.mongodb_uri),
            },
            {
                "database": "Cassandra",
                "setting": f"mode={self.cassandra_mode}",
                "configured": is_cassandra_configured,
            },
            {
                "database": "Neo4j",
                "setting": "neo4j_uri_and_auth",
                "configured": bool(self.neo4j_uri and self.neo4j_username and self.neo4j_password),
            },
            {"database": "Qdrant", "setting": "qdrant_url", "configured": bool(self.qdrant_url)},
        ]


def validate_runtime_configuration(config: DatabaseConfig) -> list[dict[str, Any]]:
    """Validate runtime database configurations without exposing any sensitive values.

    Performs structural and endpoint validation for:
    - Redis: REDIS_URL scheme (redis/rediss), hostname, port.
    - MongoDB: MONGODB_URI scheme (mongodb/mongodb+srv), hostname, database name.
    - Cassandra: Astra mode, token presence, keyspace name, SCB path existence and ZIP validity.
    - Neo4j & Qdrant: Reports configured if credentials present, else unconfigured/skipped.
    """
    results: list[dict[str, Any]] = []

    # 1. Redis
    redis_configured = bool(config.redis_url)
    redis_valid = False
    redis_notes = "Not configured"
    if redis_configured:
        try:
            parsed = urlparse(config.redis_url or "")
            if parsed.scheme not in ("redis", "rediss"):
                redis_notes = f"Invalid scheme '{parsed.scheme}' (expected redis:// or rediss://)"
            elif not parsed.hostname or not parsed.port:
                redis_notes = "Missing host or port in REDIS_URL"
            else:
                redis_valid = True
                redis_notes = f"Valid {parsed.scheme}:// endpoint ({parsed.hostname}:{parsed.port})"
        except Exception as exc:
            redis_notes = f"Malformed REDIS_URL: {type(exc).__name__}"
    results.append(
        {
            "database": "Redis",
            "configured": redis_configured,
            "valid": redis_valid,
            "status": "configured" if redis_valid else ("invalid" if redis_configured else "unconfigured"),
            "details": redis_notes,
        }
    )

    # 2. MongoDB
    mongo_configured = bool(config.mongodb_uri)
    mongo_valid = False
    mongo_notes = "Not configured"
    if mongo_configured:
        try:
            parsed = urlparse(config.mongodb_uri or "")
            if parsed.scheme not in ("mongodb", "mongodb+srv"):
                mongo_notes = f"Invalid scheme '{parsed.scheme}' (expected mongodb:// or mongodb+srv://)"
            elif not parsed.hostname:
                mongo_notes = "Missing hostname in MONGODB_URI"
            elif config.mongodb_database != "nosql_rag_research":
                mongo_notes = f"Expected database 'nosql_rag_research', got '{config.mongodb_database}'"
            else:
                mongo_valid = True
                mongo_notes = f"Valid {parsed.scheme}:// cluster ({parsed.hostname}) / db: {config.mongodb_database}"
        except Exception as exc:
            mongo_notes = f"Malformed MONGODB_URI: {type(exc).__name__}"
    results.append(
        {
            "database": "MongoDB",
            "configured": mongo_configured,
            "valid": mongo_valid,
            "status": "configured" if mongo_valid else ("invalid" if mongo_configured else "unconfigured"),
            "details": mongo_notes,
        }
    )

    # 3. Apache Cassandra (Astra DB)
    if config.cassandra_mode == "astra":
        has_token = bool(config.cassandra_application_token)
        has_keyspace = (config.cassandra_keyspace == "nosql_rag_research")
        scb_path = config.cassandra_secure_connect_bundle_path
        has_scb_path = bool(scb_path)

        file_exists = False
        zip_valid = False
        astra_markers = False
        if has_scb_path and Path(scb_path).is_file():
            file_exists = True
            try:
                with zipfile.ZipFile(scb_path, "r") as zf:
                    if zf.testzip() is None:
                        zip_valid = True
                        namelist = set(zf.namelist())
                        expected = {"config.json", "cqlshrc", "cert", "key", "truststore.jks", "ca.crt"}
                        if namelist & expected or any("cert" in n.lower() or "cqlsh" in n.lower() for n in namelist):
                            astra_markers = True
            except Exception:
                zip_valid = False

        astra_configured = has_token and has_keyspace and file_exists
        astra_valid = astra_configured and zip_valid and astra_markers

        if not has_token:
            astra_notes = "Missing CASSANDRA_APPLICATION_TOKEN (AstraCS:...)"
        elif not has_keyspace:
            astra_notes = f"Expected keyspace 'nosql_rag_research', got '{config.cassandra_keyspace}'"
        elif not has_scb_path:
            astra_notes = "Missing CASSANDRA_SECURE_CONNECT_BUNDLE_PATH"
        elif not file_exists:
            astra_notes = f"Secure Connect Bundle missing at {scb_path} (upload required)"
        elif not zip_valid:
            astra_notes = "Corrupt or invalid ZIP archive at SCB path"
        elif not astra_markers:
            astra_notes = "ZIP archive is missing standard Astra certificate/config markers"
        else:
            astra_notes = f"Astra mode validated (keyspace: {config.cassandra_keyspace}, SCB: {scb_path})"

        results.append(
            {
                "database": "Cassandra",
                "configured": astra_configured,
                "valid": astra_valid,
                "status": "configured" if astra_valid else ("missing_bundle" if (has_token and not file_exists) else "invalid"),
                "details": astra_notes,
            }
        )
    else:
        std_configured = bool(config.cassandra_hosts and config.cassandra_keyspace)
        results.append(
            {
                "database": "Cassandra",
                "configured": std_configured,
                "valid": std_configured,
                "status": "configured" if std_configured else "unconfigured",
                "details": f"Standard mode ({config.cassandra_hosts or 'no hosts'})",
            }
        )

    # 4. Neo4j
    neo4j_configured = bool(config.neo4j_uri and config.neo4j_username and config.neo4j_password)
    results.append(
        {
            "database": "Neo4j",
            "configured": neo4j_configured,
            "valid": neo4j_configured,
            "status": "configured" if neo4j_configured else "unconfigured (skipped in Phase 13.1)",
            "details": "Configured" if neo4j_configured else "Not yet provisioned (skipped in Phase 13.1)",
        }
    )

    # 5. Qdrant
    qdrant_configured = bool(config.qdrant_url)
    results.append(
        {
            "database": "Qdrant",
            "configured": qdrant_configured,
            "valid": qdrant_configured,
            "status": "configured" if qdrant_configured else "unconfigured (skipped in Phase 13.1)",
            "details": "Configured" if qdrant_configured else "Not yet provisioned (skipped in Phase 13.1)",
        }
    )

    return results


class BenchmarkMatrixConfig(BaseModel):
    n_profiles: int = Field(ge=1)
    operations: int = Field(ge=1)
    records: int = Field(ge=1)
    repetitions: int = Field(ge=1)
    batch_size: int = Field(default=5, ge=1)
    concurrency_levels: list[int] = Field(default_factory=lambda: [1])
    warmup_operations: int = Field(default=20, ge=0)
    cleanup_after_run: bool = True
    timeout_seconds: int = Field(default=120, ge=1)


class QdrantANNConfig(BaseModel):
    n_vectors: int = Field(default=2000, ge=10)
    n_queries: int = Field(default=100, ge=1)
    vector_size: int = Field(default=128, ge=8)
    top_k: int = Field(default=10, ge=1)
    distance: str = "COSINE"
    batch_size: int = Field(default=256, ge=1)


class BeirRagConfig(BaseModel):
    dataset_name: str = "scifact"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    top_k: int = Field(default=10, ge=1)
    max_queries: int | None = 200
    chunk_strategy: str = "title_plus_body_full"
    normalize_embeddings: bool = True


class MLConfig(BaseModel):
    test_size: float = Field(default=0.25, gt=0.0, lt=1.0)
    cv_folds: int = Field(default=5, ge=2)
    group_column: str = "workload_id"
    target_column: str = "best_store"
    feature_columns: list[str] = Field(
        default_factory=lambda: [
            "query_type",
            "read_ratio",
            "write_ratio",
            "payload_bytes",
            "dataset_records",
            "data_size_mb",
            "concurrency",
        ]
    )


class ExperimentConfig(BaseModel):
    random_seed: int = 42
    primary_objective: str = "min_p95_latency_ms"
    max_allowed_error_rate: float = Field(default=0.01, ge=0.0, le=1.0)
    min_required_recall_at_k: float = Field(default=0.90, ge=0.0, le=1.0)
    pilot: BenchmarkMatrixConfig
    full_matrix: BenchmarkMatrixConfig
    qdrant_ann: QdrantANNConfig = Field(default_factory=QdrantANNConfig)
    beir_rag: BeirRagConfig = Field(default_factory=BeirRagConfig)
    ml: MLConfig = Field(default_factory=MLConfig)

    @field_validator("primary_objective")
    @classmethod
    def _validate_objective(cls, value: str) -> str:
        allowed = {"min_p95_latency_ms", "min_p50_latency_ms", "max_throughput_ops_sec"}
        if value not in allowed:
            raise ValueError(f"primary_objective must be one of {sorted(allowed)}")
        return value


def load_experiment_config(config_path: Path | None = None) -> ExperimentConfig:
    """Load experiment configuration from YAML or return validated defaults."""
    if config_path is None:
        default_path = Path("configs/experiment.yaml")
        config_path = default_path if default_path.exists() else None

    if config_path is not None and config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        return ExperimentConfig.model_validate(raw)

    return ExperimentConfig(
        pilot=BenchmarkMatrixConfig(
            n_profiles=2,
            operations=250,
            records=200,
            repetitions=1,
            concurrency_levels=[1],
        ),
        full_matrix=BenchmarkMatrixConfig(
            n_profiles=75,
            operations=1500,
            records=1000,
            repetitions=3,
            batch_size=5,
            concurrency_levels=[1, 4],
        ),
    )


def configure_logging(log_file: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """Configure package-wide structured logging without leaking credentials."""
    logger = logging.getLogger("nosql_rag")
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
