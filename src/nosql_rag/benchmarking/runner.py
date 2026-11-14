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
        "cleanup_result": "skipped" if not cleanup else "pending",
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
                    row["cleanup_result"] = "success"
                except Exception as cleanup_exc:
                    logger.warning("Cleanup failed for %s: %s", run_id, cleanup_exc)
                    row["cleanup_result"] = f"failed: {str(cleanup_exc)[:100]}"
            else:
                row["cleanup_result"] = "skipped"
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
    completed: set[tuple[str, str, int, int]] = set()
    if not existing.empty:
        required_resume_columns = {
            "workload_id",
            "database",
            "concurrency",
            "repetition",
            "status",
            "data_provenance",
            "error_count",
            "error_rate",
            "p50_latency_ms",
            "p95_latency_ms",
            "p99_latency_ms",
        }
        missing_resume_columns = sorted(required_resume_columns - set(existing.columns))
        if missing_resume_columns:
            raise ValueError(
                "Cannot safely resume from a CSV missing completion-validation columns: "
                f"{missing_resume_columns}"
            )

        numeric = existing[
            [
                "concurrency",
                "repetition",
                "error_count",
                "error_rate",
                "p50_latency_ms",
                "p95_latency_ms",
                "p99_latency_ms",
            ]
        ].apply(pd.to_numeric, errors="coerce")
        latency = numeric[["p50_latency_ms", "p95_latency_ms", "p99_latency_ms"]]
        valid_latency = (
            latency.notna().all(axis=1)
            & np.isfinite(latency).all(axis=1)
            & (latency > 0).all(axis=1)
            & (latency["p50_latency_ms"] <= latency["p95_latency_ms"])
            & (latency["p95_latency_ms"] <= latency["p99_latency_ms"])
        )
        completed_mask = (
            (existing["status"].astype(str) == "success")
            & (existing["data_provenance"].astype(str) == DataProvenance.GENUINE_BENCHMARK.value)
            & (numeric["error_count"] == 0)
            & (numeric["error_rate"].between(0, 0.01))
            & valid_latency
        )
        completed = {
            (
                str(row["workload_id"]),
                str(row["database"]),
                int(numeric.loc[index, "concurrency"]),
                int(numeric.loc[index, "repetition"]),
            )
            for index, row in existing.loc[completed_mask].iterrows()
        }

    pending: list[tuple[dict[str, Any], str, int]] = []
    for _, prof in profiles.iterrows():
        prof_dict = prof.to_dict()
        for rep in range(1, repetitions + 1):
            for db in databases:
                key = (
                    str(prof_dict["workload_id"]),
                    str(db),
                    int(prof_dict["concurrency"]),
                    rep,
                )
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


def verify_crud_pilot_readiness(
    db_config: DatabaseConfig,
    required_databases: list[str] | tuple[str, ...] = ("Redis", "MongoDB", "Cassandra", "Neo4j"),
) -> dict[str, dict[str, Any]]:
    """Verify that all required candidate CRUD databases are live and connected.

    Accepts the list[dict[str, Any]] returned by check_crud_connections(db_config).
    Indexes results by each entry's 'database' field.
    Raises RuntimeError if any required engine is FAILED, SKIPPED, missing, or not connected,
    preventing an incomplete, scientifically invalid comparison.
    """
    from nosql_rag.adapters import check_crud_connections

    raw_results = check_crud_connections(db_config)
    if isinstance(raw_results, list):
        statuses: dict[str, dict[str, Any]] = {
            item["database"]: item
            for item in raw_results
            if isinstance(item, dict) and "database" in item
        }
    elif isinstance(raw_results, dict):
        statuses = raw_results
    else:
        statuses = {}

    unconnected: list[str] = []

    for db in required_databases:
        info = statuses.get(db)
        if not info:
            unconnected.append(f"{db} (MISSING: no health check record returned)")
        elif info.get("status") != "CONNECTED" or not info.get("connected"):
            status_str = info.get("status", "UNKNOWN")
            err = info.get("error") or "not connected"
            unconnected.append(f"{db} ({status_str}: {err})")

    if unconnected:
        raise RuntimeError(
            "Pilot execution gate failed: Not all required CRUD databases are CONNECTED.\n"
            "Unconnected required databases:\n  - " + "\n  - ".join(unconnected) + "\n\n"
            "All four CRUD databases (Redis, MongoDB, Cassandra, Neo4j) must report CONNECTED "
            "before executing the pilot comparison. Please verify your credentials, network access, "
            "and bundle staging."
        )

    return statuses


def analyze_pilot_progress(
    runs_df: pd.DataFrame,
    pilot_profiles: pd.DataFrame,
    candidate_databases: list[str] | tuple[str, ...] = ("Redis", "MongoDB", "Cassandra", "Neo4j"),
    repetitions: int = 1,
) -> dict[str, Any]:
    """Analyze append-only benchmark runs against target pilot configurations.

    Distinguishes total historical attempts from current completion status across
    the unique (workload_id, database, repetition) configurations.
    """
    pilot_ids = set(pilot_profiles["workload_id"].astype(str)) if not pilot_profiles.empty else set()

    if runs_df.empty or "workload_id" not in runs_df.columns:
        pilot_history = pd.DataFrame()
    else:
        pilot_history = runs_df[runs_df["workload_id"].astype(str).isin(pilot_ids)].copy()

    total_attempts = len(pilot_history)
    hist_success = int((pilot_history["status"] == "success").sum()) if not pilot_history.empty else 0
    hist_failed = int((pilot_history["status"] == "failed").sum()) if not pilot_history.empty else 0
    hist_partial = int((pilot_history["status"] == "partial").sum()) if not pilot_history.empty else 0

    target_configs: list[tuple[str, str, int]] = []
    for wid in sorted(pilot_ids):
        for db in candidate_databases:
            for rep in range(1, repetitions + 1):
                target_configs.append((str(wid), str(db), rep))

    config_rows: list[dict[str, Any]] = []
    successful_configs = 0

    for wid, db, rep in target_configs:
        if pilot_history.empty:
            matches = pd.DataFrame()
        else:
            matches = pilot_history[
                (pilot_history["workload_id"].astype(str) == wid)
                & (pilot_history["database"].astype(str) == db)
                & (pilot_history["repetition"].astype(int) == rep)
            ]

        attempts = len(matches)
        successes = matches[matches["status"] == "success"] if not matches.empty else pd.DataFrame()

        diagnostic_hint = None
        if not successes.empty:
            successful_configs += 1
            best_row = successes.iloc[-1]
            status = "success"
            err_summary = None
        elif not matches.empty:
            best_row = matches.iloc[-1]
            status = str(best_row.get("status", "failed"))
            err_summary = str(best_row.get("error_summary", "Unknown failure"))

            err_lower = err_summary.lower()
            if any(k in err_lower for k in ["ssl", "tls", "handshake", "serverselection", "connection closed", "timeout"]):
                diagnostic_hint = (
                    "MongoDB TLS Handshake / Network Error: Verify Colab public IP is allowlisted in MongoDB Atlas "
                    "Network Access (<COLAB_IP>/32 from Cell 13), or enable 0.0.0.0/0 temporarily."
                )
            elif any(k in err_lower for k in ["bundle", "secure_connect", "astra", "scb", "not found"]):
                diagnostic_hint = (
                    "Cassandra Astra SCB Missing: Re-run Cell 15 to upload and stage secure-connect-bundle.zip "
                    "into /tmp/astra_scb/secure-connect-bundle.zip."
                )
        else:
            best_row = pd.Series(dtype=object)
            status = "pending"
            err_summary = "Not yet attempted"

        config_rows.append(
            {
                "workload_id": wid,
                "database": db,
                "repetition": rep,
                "attempts": attempts,
                "current_status": status,
                "run_id": best_row.get("run_id") if not best_row.empty else None,
                "database_version": best_row.get("database_version") if not best_row.empty else None,
                "p50_latency_ms": best_row.get("p50_latency_ms") if not best_row.empty else None,
                "p95_latency_ms": best_row.get("p95_latency_ms") if not best_row.empty else None,
                "p99_latency_ms": best_row.get("p99_latency_ms") if not best_row.empty else None,
                "throughput_ops_sec": best_row.get("throughput_ops_sec") if not best_row.empty else None,
                "cleanup_result": best_row.get("cleanup_result") if not best_row.empty else None,
                "error_summary": err_summary,
                "diagnostic_hint": diagnostic_hint,
                "data_provenance": best_row.get("data_provenance") if not best_row.empty else None,
            }
        )

    config_df = pd.DataFrame(config_rows)
    target_count = len(target_configs)
    is_complete = (successful_configs == target_count and target_count > 0)

    return {
        "target_configurations_count": target_count,
        "successful_configurations_count": successful_configs,
        "pending_configurations_count": target_count - successful_configs,
        "is_pilot_complete": is_complete,
        "total_historical_attempts": total_attempts,
        "historical_successes": hist_success,
        "historical_failures": hist_failed,
        "historical_partials": hist_partial,
        "config_summary_df": config_df,
        "history_df": pilot_history,
    }


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
