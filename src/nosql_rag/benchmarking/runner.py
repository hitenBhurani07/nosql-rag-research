"""Controlled workload benchmarking engine with resume, warm-up, and provenance."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psutil

from nosql_rag.adapters import AdapterError, Neo4jAdapter, build_crud_adapter
from nosql_rag.config import DatabaseConfig
from nosql_rag.data.persistence import append_raw_runs, load_raw_runs
from nosql_rag.data.schemas import DataProvenance
from nosql_rag.workloads.generator import make_payload

logger = logging.getLogger("nosql_rag.benchmarking")


def _compute_config_hash(
    workload: dict[str, Any],
    database_name: str,
    database_version: str,
    db_config: DatabaseConfig,
) -> str:
    fingerprint = {
        "workload": {
            k: (v.item() if isinstance(v, np.generic) else v) for k, v in workload.items()
        },
        "database": database_name,
        "database_version": database_version,
        "hosting_region": db_config.hosting_region,
        "deployment_notes": db_config.deployment_notes,
    }
    return hashlib.sha256(json.dumps(fingerprint, sort_keys=True, default=str).encode()).hexdigest()[
        :20
    ]


def benchmark_common_crud(
    database_name: str,
    workload: dict[str, Any],
    db_config: DatabaseConfig,
    repetition: int = 1,
    warmup_operations: int = 20,
    cleanup: bool = True,
    timeout_seconds: int = 120,
    provenance: DataProvenance = DataProvenance.GENUINE_BENCHMARK,
) -> dict[str, Any]:
    """Execute one controlled CRUD benchmark run against a configured database."""
    adapter = None
    run_id = f"{str(workload['workload_id']).lower()}_{database_name.lower()}_r{repetition}_{uuid.uuid4().hex[:8]}"
    started_utc = datetime.now(timezone.utc).isoformat()
    process = psutil.Process(os.getpid())
    rss_before = process.memory_info().rss / (1024**2)
    cpu_before = process.cpu_times().user + process.cpu_times().system

    row: dict[str, Any] = {
        "run_id": run_id,
        "workload_id": str(workload["workload_id"]),
        "configuration_id": f"{workload['workload_id']}__{database_name}",
        "database": database_name,
        "database_version": "unknown",
        "query_type": str(workload["query_type"]),
        "payload_bytes": int(workload["payload_bytes"]),
        "dataset_records": int(workload["dataset_records"]),
        "read_ratio": float(workload["read_ratio"]),
        "write_ratio": float(workload["write_ratio"]),
        "concurrency": int(workload["concurrency"]),
        "n_operations": int(workload["n_operations"]),
        "warmup_operations": int(warmup_operations),
        "repetition": int(repetition),
        "started_utc": started_utc,
        "finished_utc": started_utc,
        "p50_latency_ms": np.nan,
        "p95_latency_ms": np.nan,
        "p99_latency_ms": np.nan,
        "mean_latency_ms": np.nan,
        "throughput_ops_sec": np.nan,
        "error_count": 0,
        "error_rate": 1.0,
        "setup_seconds": np.nan,
        "wall_seconds": np.nan,
        "rss_delta_mb": np.nan,
        "cpu_seconds": np.nan,
        "config_hash": "",
        "hosting_region": db_config.hosting_region,
        "status": "failed",
        "error_summary": None,
        "data_provenance": provenance.value,
    }

    try:
        adapter = build_crud_adapter(database_name, db_config)
        if not adapter.check():
            raise AdapterError("Database health check returned False")

        n_records = int(workload["dataset_records"])
        payload_bytes = int(workload["payload_bytes"])
        seed = int(workload["random_seed"])
        records = [
            {"record_id": str(i), "payload_json": make_payload(i, payload_bytes, seed)}
            for i in range(n_records)
        ]

        setup_start = time.perf_counter()
        adapter.prepare(run_id, records)
        setup_seconds = time.perf_counter() - setup_start

        rng = random.Random(seed + repetition)
        n_ops = int(workload["n_operations"])
        read_ratio = float(workload["read_ratio"])
        operations = []
        for op_idx in range(n_ops):
            op = "read" if rng.random() < read_ratio else "update"
            rec_id = str(rng.randrange(n_records))
            operations.append(
                (op, rec_id, make_payload(int(rec_id), payload_bytes, seed + op_idx + repetition))
            )

        # Warm-up excluded from measured latencies
        for op, rec_id, payload_json in operations[: min(warmup_operations, len(operations))]:
            if op == "read":
                adapter.read(run_id, rec_id)
            else:
                adapter.update(run_id, rec_id, payload_json)

        deadline = time.perf_counter() + float(timeout_seconds)
        latencies_ms: list[float] = []
        failures: list[str] = []

        def _execute_one(item: tuple[str, str, str]) -> tuple[float, str | None]:
            if time.perf_counter() > deadline:
                return 0.0, "TimeoutError: benchmark exceeded timeout_seconds"
            op, rec_id, payload_json = item
            op_start = time.perf_counter()
            try:
                ok = (
                    adapter.read(run_id, rec_id)
                    if op == "read"
                    else adapter.update(run_id, rec_id, payload_json)
                )
                elapsed = (time.perf_counter() - op_start) * 1000.0
                if not ok:
                    return elapsed, "operation_returned_false"
                return elapsed, None
            except Exception as exc:
                return (time.perf_counter() - op_start) * 1000.0, f"{type(exc).__name__}: {str(exc)[:200]}"

        concurrency = max(1, int(workload["concurrency"]))
        bench_start = time.perf_counter()
        if concurrency == 1:
            results = [_execute_one(item) for item in operations]
        else:
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                results = list(pool.map(_execute_one, operations))
        wall_seconds = time.perf_counter() - bench_start

        for lat, err in results:
            if err is None:
                latencies_ms.append(lat)
            else:
                failures.append(err)

        rss_after = process.memory_info().rss / (1024**2)
        cpu_after = process.cpu_times().user + process.cpu_times().system
        total_ops = len(operations)
        successful = len(latencies_ms)
        error_count = total_ops - successful
        error_rate = error_count / total_ops if total_ops else 1.0
        db_version = getattr(adapter, "version", "unknown")

        row.update(
            {
                "database_version": db_version,
                "p50_latency_ms": float(np.percentile(latencies_ms, 50)) if latencies_ms else np.nan,
                "p95_latency_ms": float(np.percentile(latencies_ms, 95)) if latencies_ms else np.nan,
                "p99_latency_ms": float(np.percentile(latencies_ms, 99)) if latencies_ms else np.nan,
                "mean_latency_ms": float(np.mean(latencies_ms)) if latencies_ms else np.nan,
                "throughput_ops_sec": (successful / wall_seconds) if wall_seconds > 0 else np.nan,
                "error_count": error_count,
                "error_rate": error_rate,
                "setup_seconds": round(setup_seconds, 4),
                "wall_seconds": round(wall_seconds, 4),
                "rss_delta_mb": round(rss_after - rss_before, 3),
                "cpu_seconds": round(cpu_after - cpu_before, 4),
                "config_hash": _compute_config_hash(workload, database_name, db_version, db_config),
                "status": "success" if error_count == 0 else ("partial" if successful > 0 else "failed"),
                "error_summary": "; ".join(sorted(set(failures))[:3]) if failures else None,
            }
        )
    except Exception as exc:
        logger.warning("Benchmark failed for %s (%s): %s", database_name, workload["workload_id"], exc)
        row["status"] = "failed"
        row["error_summary"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    finally:
        if adapter is not None:
            if cleanup:
                try:
                    adapter.cleanup(run_id)
                except Exception as cleanup_exc:
                    logger.warning("Cleanup failed for %s: %s", run_id, cleanup_exc)
            try:
                adapter.close()
            except Exception:
                pass
        row["finished_utc"] = datetime.now(timezone.utc).isoformat()

    return row


def run_crud_matrix(
    profiles: pd.DataFrame,
    databases: list[str] | tuple[str, ...],
    db_config: DatabaseConfig,
    output_csv: Path,
    repetitions: int = 1,
    batch_size: int = 5,
    warmup_operations: int = 20,
    cleanup: bool = True,
    timeout_seconds: int = 120,
    provenance: DataProvenance = DataProvenance.GENUINE_BENCHMARK,
) -> pd.DataFrame:
    """Execute a matrix of CRUD benchmarks in small batches with resume support."""
    existing = load_raw_runs(output_csv)
    completed: set[tuple[str, str, int]] = set()
    if not existing.empty and {"workload_id", "database", "repetition", "status"}.issubset(
        existing.columns
    ):
        ok_rows = existing[existing["status"] == "success"]
        completed = {
            (str(r["workload_id"]), str(r["database"]), int(r["repetition"]))
            for _, r in ok_rows.iterrows()
        }

    pending: list[tuple[dict[str, Any], str, int]] = []
    for _, prof in profiles.iterrows():
        prof_dict = prof.to_dict()
        for rep in range(1, repetitions + 1):
            for db in databases:
                key = (str(prof_dict["workload_id"]), str(db), rep)
                if key not in completed:
                    pending.append((prof_dict, str(db), rep))

    logger.info("Pending CRUD runs: %d (already completed: %d)", len(pending), len(completed))
    batch: list[dict[str, Any]] = []
    for idx, (prof_dict, db, rep) in enumerate(pending, start=1):
        result = benchmark_common_crud(
            database_name=db,
            workload=prof_dict,
            db_config=db_config,
            repetition=rep,
            warmup_operations=warmup_operations,
            cleanup=cleanup,
            timeout_seconds=timeout_seconds,
            provenance=provenance,
        )
        batch.append(result)
        if len(batch) >= batch_size or idx == len(pending):
            append_raw_runs(batch, output_csv)
            batch.clear()

    return load_raw_runs(output_csv)


def benchmark_neo4j_graph_traversal(
    db_config: DatabaseConfig,
    n_nodes: int = 200,
    n_edges: int = 600,
    n_queries: int = 100,
    depth: int = 2,
    seed: int = 42,
    cleanup: bool = True,
) -> dict[str, Any]:
    """Execute a native multi-hop graph traversal benchmark on Neo4j."""
    if not all([db_config.neo4j_uri, db_config.neo4j_username, db_config.neo4j_password]):
        raise AdapterError("NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD are required")

    run_id = f"neo4j_graph_{uuid.uuid4().hex[:8]}"
    adapter = Neo4jAdapter(
        uri=db_config.neo4j_uri or "",
        username=db_config.neo4j_username or "",
        password=db_config.neo4j_password or "",
        database=db_config.neo4j_database,
    )
    rng = random.Random(seed)
    try:
        adapter.check()
        records = [{"record_id": str(i), "payload_json": "{}"} for i in range(n_nodes)]
        adapter.prepare(run_id, records)
        edges = [(str(rng.randrange(n_nodes)), str(rng.randrange(n_nodes))) for _ in range(n_edges)]
        adapter.prepare_graph_edges(run_id, edges)

        latencies: list[float] = []
        wall_start = time.perf_counter()
        for _ in range(n_queries):
            src = str(rng.randrange(n_nodes))
            t0 = time.perf_counter()
            adapter.traverse_neighbors(run_id, src, depth=depth)
            latencies.append((time.perf_counter() - t0) * 1000.0)
        wall_s = time.perf_counter() - wall_start

        return {
            "run_id": run_id,
            "database": "Neo4j",
            "database_version": adapter.version,
            "workload_type": "graph_traversal",
            "n_nodes": n_nodes,
            "n_edges": n_edges,
            "n_queries": n_queries,
            "traversal_depth": depth,
            "p50_latency_ms": float(np.percentile(latencies, 50)),
            "p95_latency_ms": float(np.percentile(latencies, 95)),
            "p99_latency_ms": float(np.percentile(latencies, 99)),
            "throughput_ops_sec": n_queries / wall_s if wall_s > 0 else np.nan,
            "status": "success",
            "data_provenance": DataProvenance.GENUINE_BENCHMARK.value,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        if cleanup:
            try:
                adapter.cleanup(run_id)
            except Exception:
                pass
        adapter.close()
