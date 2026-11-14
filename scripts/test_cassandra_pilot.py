"""Run 2-workload sanity pilot for Cassandra in-container and print comparison."""

from __future__ import annotations

import pandas as pd

from nosql_rag.benchmarking.runner import benchmark_common_crud
from nosql_rag.config import DatabaseConfig
from nosql_rag.data.schemas import DataProvenance


def main():
    profiles = pd.read_csv("data/processed/workload_profiles.csv")
    w1 = profiles[profiles["workload_id"] == "W0001"].iloc[0].to_dict()
    w2 = profiles[profiles["workload_id"] == "W0002"].iloc[0].to_dict()

    cfg = DatabaseConfig(
        cassandra_mode="local",
        cassandra_hosts="nosql-rag-cassandra",
        cassandra_port=9042,
        cassandra_keyspace="nosql_rag_research",
        hosting_region="local_container",
        deployment_notes="in-container-compose-network; cpus=2.0,mem=1024m",
    )

    print("Running W0001 (c=1)...")
    r1 = benchmark_common_crud("Cassandra", w1, cfg, repetition=1, provenance=DataProvenance.PILOT_BENCHMARK)
    print(f"W0001: status={r1['status']}, P50={r1['p50_latency_ms']:.3f} ms, P95={r1['p95_latency_ms']:.3f} ms, throughput={r1['throughput_ops_sec']:.0f} ops/s, errs={r1['error_count']}")

    print("\nRunning W0002 (c=4)...")
    r2 = benchmark_common_crud("Cassandra", w2, cfg, repetition=1, provenance=DataProvenance.PILOT_BENCHMARK)
    print(f"W0002: status={r2['status']}, P50={r2['p50_latency_ms']:.3f} ms, P95={r2['p95_latency_ms']:.3f} ms, throughput={r2['throughput_ops_sec']:.0f} ops/s, errs={r2['error_count']}")


if __name__ == "__main__":
    main()
