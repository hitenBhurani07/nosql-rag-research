"""Command-line interface for nosql-rag-research."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from nosql_rag.adapters import check_crud_connections, check_qdrant_connection
from nosql_rag.config import DatabaseConfig, ProjectPaths, configure_logging
from nosql_rag.data.persistence import (
    generate_synthetic_demo_runs,
    load_raw_runs,
)
from nosql_rag.data.validator import validate_raw_runs
from nosql_rag.features import grouped_train_test_split, prepare_ml_dataset
from nosql_rag.models import (
    load_model_artifacts,
    recommend_database,
    train_and_compare_models,
)
from nosql_rag.workloads import generate_workload_profiles


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nosql-rag",
        description="ML-Driven NoSQL Pattern Selection for RAG Workloads",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check-connections
    subparsers.add_parser("check-connections", help="Check live database endpoints")

    # generate-profiles
    gen_parser = subparsers.add_parser("generate-profiles", help="Generate workload profiles")
    gen_parser.add_argument("--count", type=int, default=75)
    gen_parser.add_argument("--prefix", type=str, default="W")
    gen_parser.add_argument("--output", type=Path, default=Path("data/processed/workload_profiles.csv"))

    # validate-data
    val_parser = subparsers.add_parser("validate-data", help="Validate raw benchmark runs")
    val_parser.add_argument("--runs", type=Path, default=Path("data/raw/crud_benchmark_runs.csv"))
    val_parser.add_argument("--allow-synthetic", action="store_true")

    # train
    train_parser = subparsers.add_parser("train", help="Train and compare ML recommenders")
    train_parser.add_argument("--labels", type=Path, default=Path("data/processed/labelled_workloads.csv"))
    train_parser.add_argument("--allow-synthetic", action="store_true")

    # recommend
    rec_parser = subparsers.add_parser("recommend", help="Recommend database pattern for a workload JSON")
    rec_parser.add_argument("--input", type=str, required=True, help="JSON string or file path")
    rec_parser.add_argument("--model", type=Path, default=Path("results/models/best_nosql_recommender.joblib"))

    # generate-synthetic-demo
    syn_parser = subparsers.add_parser(
        "generate-synthetic-demo",
        help="Generate synthetic demo data for unit tests and dashboard demo ONLY",
    )
    syn_parser.add_argument("--profiles", type=int, default=10)
    syn_parser.add_argument("--output", type=Path, default=Path("data/sample/synthetic_demo_runs.csv"))

    args = parser.parse_args()
    paths = ProjectPaths(root=Path.cwd())
    paths.ensure_dirs()
    configure_logging(paths.logs / "cli.log")

    if args.command == "check-connections":
        cfg = DatabaseConfig.from_env()
        print("\n--- Configured Secrets Status ---")
        for item in cfg.safe_status():
            print(f"  {item['database']:<12}: configured={item['configured']}")
        print("\n--- Live Endpoint Connectivity ---")
        crud_res = check_crud_connections(cfg)
        for r in crud_res:
            status = "CONNECTED" if r["connected"] else "FAILED"
            print(f"  {r['database']:<12}: {status} (latency={r['connect_check_ms']}ms, version={r['version']})")
            if r["error"]:
                print(f"    error: {r['error']}")
        qdrant_res = check_qdrant_connection(cfg)
        q_status = "CONNECTED" if qdrant_res["connected"] else "FAILED"
        print(f"  {qdrant_res['database']:<12}: {q_status} (latency={qdrant_res['connect_check_ms']}ms, version={qdrant_res['version']})")
        if qdrant_res["error"]:
            print(f"    error: {qdrant_res['error']}")

    elif args.command == "generate-profiles":
        df = generate_workload_profiles(n_profiles=args.count, id_prefix=args.prefix)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.output, index=False)
        print(f"Wrote {len(df)} workload profiles to {args.output}")

    elif args.command == "validate-data":
        runs = load_raw_runs(args.runs)
        rep = validate_raw_runs(runs, allow_synthetic=args.allow_synthetic)
        print(f"Valid: {rep.is_valid} | Valid rows: {rep.valid_rows}/{rep.total_rows}")
        if rep.errors:
            print("Errors:")
            for e in rep.errors:
                print(f"  - {e}")
        if rep.warnings:
            print("Warnings:")
            for w in rep.warnings:
                print(f"  - {w}")

    elif args.command == "generate-synthetic-demo":
        profs = generate_workload_profiles(n_profiles=args.profiles, id_prefix="SYN")
        syn = generate_synthetic_demo_runs(profs)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        syn.to_csv(args.output, index=False)
        print(f"Generated {len(syn)} synthetic demo rows -> {args.output}")
        print("NOTICE: Synthetic data carries data_provenance='synthetic_demo' and is never used in research models.")

    elif args.command == "train":
        if not args.labels.exists():
            print(f"Labelled dataset not found at {args.labels}. Run benchmarks and derive labels first.")
            sys.exit(1)
        import pandas as pd

        df = pd.read_csv(args.labels)
        clean, X, y, groups = prepare_ml_dataset(df, allow_synthetic=args.allow_synthetic)
        split = grouped_train_test_split(X, y, groups, clean)
        fitted, preds, metrics, best_name = train_and_compare_models(
            split["X_train"], split["y_train"], split["X_test"], split["y_test"]
        )
        print(f"Best model: {best_name}")
        print(metrics.to_string(index=False))

    elif args.command == "recommend":
        inp_str = args.input
        if Path(inp_str).exists():
            with open(inp_str, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = json.loads(inp_str)
        pipe = load_model_artifacts(args.model) if args.model.exists() else None
        res = recommend_database(data, trained_pipeline=pipe)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
