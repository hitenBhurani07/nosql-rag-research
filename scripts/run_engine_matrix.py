"""In-container CRUD Matrix Runner.

Executes controlled CRUD matrix benchmarks inside the container on the internal compose network.
Supports Redis, MongoDB, Cassandra, and Neo4j.
Persists runs directly to data/raw/crud_benchmark_runs.csv with DataProvenance.GENUINE_BENCHMARK.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from nosql_rag.benchmarking.runner import run_crud_matrix
from nosql_rag.config import DatabaseConfig
from nosql_rag.data.schemas import DataProvenance


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run in-container CRUD matrix benchmark.")
    parser.add_argument(
        "--database",
        type=str,
        required=True,
        choices=["Redis", "MongoDB", "Cassandra", "Neo4j"],
        help="Target database engine",
    )
    parser.add_argument(
        "--profiles-count",
        type=int,
        default=150,
        help="Number of workload profiles to run (150 for Redis/MongoDB, 76 for Cassandra/Neo4j)",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Number of repetitions per profile (default: 3)",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/raw/crud_benchmark_runs.csv"),
        help="Path to output CSV",
    )
    return parser.parse_args()


def get_db_config(database: str) -> DatabaseConfig:
    if database == "Redis":
        return DatabaseConfig(
            redis_url="redis://nosql-rag-redis:6379/0",
            hosting_region="local_container",
            deployment_notes="in-container-compose-network; cpus=2.0,mem=1024m",
        )
    elif database == "MongoDB":
        return DatabaseConfig(
            mongodb_uri="mongodb://nosql-rag-mongo:27017",
            mongodb_database="nosql_rag_research",
            hosting_region="local_container",
            deployment_notes="in-container-compose-network; cpus=2.0,mem=1024m",
        )
    elif database == "Cassandra":
        return DatabaseConfig(
            cassandra_mode="local",
            cassandra_hosts="nosql-rag-cassandra",
            cassandra_port=9042,
            cassandra_keyspace="nosql_rag_research",
            hosting_region="local_container",
            deployment_notes="in-container-compose-network; cpus=2.0,mem=1024m",
        )
    elif database == "Neo4j":
        return DatabaseConfig(
            neo4j_uri="bolt://nosql-rag-neo4j:7687",
            neo4j_username="neo4j",
            neo4j_password="nosql_rag_password",
            hosting_region="local_container",
            deployment_notes="in-container-compose-network; cpus=2.0,mem=1024m",
        )
    raise ValueError(f"Unknown database {database}")


def main() -> None:
    args = parse_args()
    profiles_path = Path("data/processed/workload_profiles.csv")
    if not profiles_path.exists():
        print(f"Error: {profiles_path} not found!", file=sys.stderr)
        sys.exit(1)

    all_profiles = pd.read_csv(profiles_path)

    if args.profiles_count == 76:
        # Cassandra / Neo4j 76-profile subset: first 38 base workloads, both c=1 and c=4
        base_38 = sorted(all_profiles["base_workload_id"].unique())[:38]
        profiles = all_profiles[all_profiles["base_workload_id"].isin(base_38)].copy()
        if len(profiles) != 76:
            profiles = profiles.head(76)
        print(f"Filtered to 76-profile subset (first 38 base workloads, c=1 and c=4): {len(profiles)} profiles.")
    else:
        profiles = all_profiles.head(args.profiles_count).copy()
        print(f"Running full {len(profiles)} profiles.")

    db_config = get_db_config(args.database)
    print(f"Starting in-container matrix for {args.database}: {len(profiles)} profiles x {args.repetitions} reps = {len(profiles) * args.repetitions} target runs.")
    print(f"Target CSV: {args.output_csv}")

    df_out = run_crud_matrix(
        profiles=profiles,
        databases=[args.database],
        db_config=db_config,
        output_csv=args.output_csv,
        repetitions=args.repetitions,
        batch_size=1,
        provenance=DataProvenance.GENUINE_BENCHMARK,
    )

    genuine_runs = df_out[(df_out["database"] == args.database) & (df_out["data_provenance"] == DataProvenance.GENUINE_BENCHMARK.value)]
    print(f"\n[DONE] {args.database} in-container matrix finished! Total genuine runs: {len(genuine_runs)}")


if __name__ == "__main__":
    main()

