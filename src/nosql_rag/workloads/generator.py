"""Reproducible workload profile and deterministic payload generation."""

from __future__ import annotations

import json
import random
from typing import Any

import numpy as np
import pandas as pd


def make_payload(record_id: int | str, payload_bytes: int, seed: int = 42) -> str:
    """Generate a deterministic JSON payload of approximately `payload_bytes` bytes."""
    rng = random.Random(int(seed) + int(record_id))
    base_obj = {"record_id": str(record_id), "category": "research_benchmark", "version": 1, "padding": ""}
    base_bytes = len(json.dumps(base_obj, separators=(",", ":")).encode("utf-8"))
    pad_len = max(0, int(payload_bytes) - base_bytes)
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    base_obj["padding"] = "".join(rng.choice(alphabet) for _ in range(pad_len))
    return json.dumps(base_obj, separators=(",", ":"))


def generate_workload_profiles(
    n_profiles: int = 75,
    seed: int = 42,
    operations: int = 1500,
    records: int = 1000,
    concurrency_levels: list[int] | None = None,
    id_prefix: str = "W",
    query_types: list[str] | None = None,
) -> pd.DataFrame:
    """Generate a reproducible matrix of operational CRUD workload profiles."""
    rng = np.random.default_rng(seed)
    concurrency_choices = concurrency_levels or [1, 4]
    q_types = query_types or ["key_value_crud", "document_crud", "wide_column_crud"]

    rows: list[dict[str, Any]] = []
    for idx in range(n_profiles):
        query_type = q_types[idx % len(q_types)]
        read_ratio = float(rng.choice([0.20, 0.50, 0.80, 0.95]))
        write_ratio = round(1.0 - read_ratio, 4)
        payload_bytes = int(rng.choice([128, 512, 2048, 8192]))
        n_records = int(rng.choice([max(100, records // 2), records, records * 2]))
        n_ops = int(rng.choice([max(100, operations // 2), operations, operations * 2]))
        concurrency = int(rng.choice(concurrency_choices))
        data_size_mb = n_records * payload_bytes / (1024**2)

        rows.append(
            {
                "workload_id": f"{id_prefix}{idx + 1:04d}",
                "query_type": query_type,
                "read_ratio": read_ratio,
                "write_ratio": write_ratio,
                "payload_bytes": payload_bytes,
                "dataset_records": n_records,
                "data_size_mb": round(data_size_mb, 6),
                "data_size_gb": round(data_size_mb / 1024, 8),
                "vector_dimensions": 0,
                "top_k": 0,
                "graph_depth": 0,
                "consistency_requirement": "default",
                "concurrency": concurrency,
                "n_operations": n_ops,
                "random_seed": int(seed + idx),
            }
        )

    return pd.DataFrame(rows)
