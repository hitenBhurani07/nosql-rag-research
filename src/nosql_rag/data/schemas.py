"""Data schemas, provenance categories, and column contracts."""

from __future__ import annotations

from enum import Enum


class DataProvenance(str, Enum):
    """Strict provenance tags separating synthetic demos from genuine experiments."""

    SYNTHETIC_DEMO = "synthetic_demo"
    PILOT_BENCHMARK = "pilot_benchmark"
    REMOTE_CLOUD_PILOT = "remote_cloud_pilot"
    INVALID_MEASUREMENT_ARTIFACT = "invalid_measurement_artifact"
    HOST_PORT_FORWARD_PILOT = "host_port_forward_pilot"
    GENUINE_BENCHMARK = "genuine_benchmark"
    AGGREGATED_EXPERIMENTAL = "aggregated_experimental"
    MODEL_READY = "model_ready"


REQUIRED_RAW_RUN_COLUMNS: tuple[str, ...] = (
    "run_id",
    "workload_id",
    "configuration_id",
    "database",
    "database_version",
    "query_type",
    "payload_bytes",
    "dataset_records",
    "read_ratio",
    "write_ratio",
    "concurrency",
    "n_operations",
    "warmup_operations",
    "repetition",
    "started_utc",
    "finished_utc",
    "p50_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "mean_latency_ms",
    "throughput_ops_sec",
    "error_count",
    "error_rate",
    "status",
    "data_provenance",
)

LATENCY_METRICS: tuple[str, ...] = (
    "p50_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "mean_latency_ms",
)
