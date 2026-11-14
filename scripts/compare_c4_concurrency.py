"""Compare ThreadPoolExecutor vs Multiprocessing at c=4 across 10 workloads.

This directly addresses user requirement #2:
'c=4 validity check: run a small sample (10 workloads) at c=4 with a multiprocess client
 (or asyncio) and compare p95 with the threaded client. If they differ materially,
 switch to the approach that does not bottleneck on the Python GIL for ALL engines and re-run.'
"""

from __future__ import annotations

import multiprocessing as mp
import random
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np
import pandas as pd

from nosql_rag.adapters import build_crud_adapter
from nosql_rag.config import DatabaseConfig
from nosql_rag.workloads.generator import make_payload


# Worker function for multiprocessing
def _mp_worker(
    database_name: str,
    db_config_dict: dict[str, Any],
    run_id: str,
    ops_slice: list[tuple[str, str, str]],
    queue: mp.Queue,
) -> None:
    db_config = DatabaseConfig(**db_config_dict)
    adapter = build_crud_adapter(database_name, db_config)
    latencies = []
    errors = []
    try:
        for op, rec_id, payload in ops_slice:
            t0 = time.perf_counter()
            try:
                ok = adapter.read(run_id, rec_id) if op == "read" else adapter.update(run_id, rec_id, payload)
                elapsed = (time.perf_counter() - t0) * 1000.0
                if ok:
                    latencies.append(elapsed)
                else:
                    errors.append("returned_false")
            except Exception as e:
                errors.append(str(e))
    finally:
        adapter.close()
    queue.put((latencies, errors))


def run_workload_threaded(
    workload: dict[str, Any],
    database_name: str,
    db_config: DatabaseConfig,
) -> dict[str, float]:
    run_id = f"test_th_{workload['workload_id']}_{int(time.time()*1000)}"
    adapter = build_crud_adapter(database_name, db_config)
    n_records = int(workload["dataset_records"])
    payload_bytes = int(workload["payload_bytes"])
    seed = int(workload["random_seed"])
    records = [{"record_id": str(i), "payload_json": make_payload(i, payload_bytes, seed)} for i in range(n_records)]
    adapter.prepare(run_id, records)

    rng = random.Random(seed + 1)
    n_ops = int(workload["n_operations"])
    read_ratio = float(workload["read_ratio"])
    operations = [
        ("read" if rng.random() < read_ratio else "update",
         str(rng.randrange(n_records)),
         make_payload(int(rng.randrange(n_records)), payload_bytes, seed + op_idx))
        for op_idx in range(n_ops)
    ]

    # Warmup
    for op, rec_id, payload in operations[:20]:
        if op == "read":
            adapter.read(run_id, rec_id)
        else:
            adapter.update(run_id, rec_id, payload)

    latencies = []
    def _execute_one(item: tuple[str, str, str]) -> tuple[float, bool]:
        op, rec_id, payload = item
        t0 = time.perf_counter()
        try:
            ok = adapter.read(run_id, rec_id) if op == "read" else adapter.update(run_id, rec_id, payload)
            return (time.perf_counter() - t0) * 1000.0, ok
        except Exception:
            return 0.0, False

    t_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        res = list(pool.map(_execute_one, operations))
    wall_sec = time.perf_counter() - t_start

    for lat, ok in res:
        if ok:
            latencies.append(lat)

    adapter.cleanup(run_id)
    adapter.close()

    return {
        "p50": float(np.percentile(latencies, 50)),
        "p95": float(np.percentile(latencies, 95)),
        "throughput": len(latencies) / wall_sec,
    }


def run_workload_multiprocess(
    workload: dict[str, Any],
    database_name: str,
    db_config: DatabaseConfig,
) -> dict[str, float]:
    run_id = f"test_mp_{workload['workload_id']}_{int(time.time()*1000)}"
    adapter = build_crud_adapter(database_name, db_config)
    n_records = int(workload["dataset_records"])
    payload_bytes = int(workload["payload_bytes"])
    seed = int(workload["random_seed"])
    records = [{"record_id": str(i), "payload_json": make_payload(i, payload_bytes, seed)} for i in range(n_records)]
    adapter.prepare(run_id, records)

    rng = random.Random(seed + 1)
    n_ops = int(workload["n_operations"])
    read_ratio = float(workload["read_ratio"])
    operations = [
        ("read" if rng.random() < read_ratio else "update",
         str(rng.randrange(n_records)),
         make_payload(int(rng.randrange(n_records)), payload_bytes, seed + op_idx))
        for op_idx in range(n_ops)
    ]

    # Warmup
    for op, rec_id, payload in operations[:20]:
        if op == "read":
            adapter.read(run_id, rec_id)
        else:
            adapter.update(run_id, rec_id, payload)

    # Split operations into 4 interleaved slices for 4 processes
    slices = [operations[i::4] for i in range(4)]
    queue: mp.Queue = mp.Queue()
    procs = []
    db_cfg_dict = db_config.model_dump()

    t_start = time.perf_counter()
    for i in range(4):
        p = mp.Process(target=_mp_worker, args=(database_name, db_cfg_dict, run_id, slices[i], queue))
        procs.append(p)
        p.start()

    all_lats = []
    for _ in range(4):
        lats, _ = queue.get()
        all_lats.extend(lats)

    for p in procs:
        p.join()
    wall_sec = time.perf_counter() - t_start

    adapter.cleanup(run_id)
    adapter.close()

    return {
        "p50": float(np.percentile(all_lats, 50)),
        "p95": float(np.percentile(all_lats, 95)),
        "throughput": len(all_lats) / wall_sec,
    }


def main():
    profiles_df = pd.read_csv("/workspace/data/processed/workload_profiles.csv")
    c4_workloads = profiles_df[profiles_df["concurrency"] == 4].head(10).to_dict(orient="records")

    db_config = DatabaseConfig(
        redis_url="redis://nosql-rag-redis:6379/0",
        hosting_region="local_container",
        deployment_notes="c=4 concurrency benchmark validation",
    )

    print(f"{'Workload':<10} | {'Threaded P50':<14} | {'MP P50':<10} | {'Threaded P95':<14} | {'MP P95':<10} | {'Diff P95 %':<12} | {'Th Thrpt':<10} | {'MP Thrpt':<10}")
    print("-" * 105)

    results = []
    for wl in c4_workloads:
        w_id = wl["workload_id"]
        res_th = run_workload_threaded(wl, "Redis", db_config)
        res_mp = run_workload_multiprocess(wl, "Redis", db_config)

        diff_p95_pct = ((res_mp["p95"] - res_th["p95"]) / res_th["p95"]) * 100.0
        print(f"{w_id:<10} | {res_th['p50']:<14.3f} | {res_mp['p50']:<10.3f} | {res_th['p95']:<14.3f} | {res_mp['p95']:<10.3f} | {diff_p95_pct:>+10.1f}% | {res_th['throughput']:<10.0f} | {res_mp['throughput']:<10.0f}")
        results.append({
            "workload_id": w_id,
            "th_p50": res_th["p50"],
            "mp_p50": res_mp["p50"],
            "th_p95": res_th["p95"],
            "mp_p95": res_mp["p95"],
            "diff_p95_pct": diff_p95_pct,
            "th_throughput": res_th["throughput"],
            "mp_throughput": res_mp["throughput"],
        })

    avg_th_p95 = np.mean([r["th_p95"] for r in results])
    avg_mp_p95 = np.mean([r["mp_p95"] for r in results])
    print("-" * 105)
    print(f"Mean P95: Threaded = {avg_th_p95:.3f} ms, Multiprocess = {avg_mp_p95:.3f} ms (Difference: {((avg_mp_p95 - avg_th_p95)/avg_th_p95)*100.0:+.2f}%)")


if __name__ == "__main__":
    main()

