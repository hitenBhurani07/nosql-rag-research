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

    # status
    subparsers.add_parser("status", help="Print summary of research artifacts and system status")

    # generate-profiles
    gen_parser = subparsers.add_parser("generate-profiles", help="Generate workload profiles")
    gen_parser.add_argument("--count", type=int, default=75)
    gen_parser.add_argument("--prefix", type=str, default="W")
    gen_parser.add_argument("--output", type=Path, default=Path("data/processed/workload_profiles.csv"))

    # validate-data
    val_parser = subparsers.add_parser("validate-data", help="Validate raw benchmark runs")
    val_parser.add_argument("--runs", type=Path, default=Path("data/raw/crud_benchmark_runs.csv"))
    val_parser.add_argument("--allow-synthetic", action="store_true")

    # label
    lbl_parser = subparsers.add_parser("label", help="Aggregate raw runs and derive ground truth labels")
    lbl_parser.add_argument("--runs", type=Path, default=Path("data/raw/crud_benchmark_runs.csv"))
    lbl_parser.add_argument("--output", type=Path, default=Path("data/processed/labelled_workloads.csv"))
    lbl_parser.add_argument("--allow-synthetic", action="store_true")

    # train
    train_parser = subparsers.add_parser("train", help="Train and compare ML recommenders")
    train_parser.add_argument("--labels", type=Path, default=Path("data/processed/labelled_workloads.csv"))
    train_parser.add_argument("--allow-synthetic", action="store_true")

    # evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate models and compute latency regret")
    eval_parser.add_argument("--labels", type=Path, default=Path("data/processed/labelled_workloads.csv"))
    eval_parser.add_argument("--allow-synthetic", action="store_true")

    # explain
    exp_parser = subparsers.add_parser("explain", help="Generate explainability / SHAP figures")
    exp_parser.add_argument("--model", type=Path, default=Path("results/models/best_nosql_recommender.joblib"))
    exp_parser.add_argument("--labels", type=Path, default=Path("data/processed/labelled_workloads.csv"))

    # recommend
    rec_parser = subparsers.add_parser("recommend", help="Recommend database pattern for a workload JSON")
    rec_parser.add_argument("--input", type=str, required=True, help="JSON string or file path")
    rec_parser.add_argument("--model", type=Path, default=Path("results/models/best_nosql_recommender.joblib"))

    # qdrant
    q_parser = subparsers.add_parser("qdrant", help="Run local Qdrant native ANN benchmark")
    q_parser.add_argument("--vectors", type=int, default=2000)
    q_parser.add_argument("--queries", type=int, default=100)

    # beir
    b_parser = subparsers.add_parser("beir", help="Run BEIR SciFact RAG benchmark")
    b_parser.add_argument("--queries", type=int, default=50)

    # benchmark
    bm_parser = subparsers.add_parser("benchmark", help="Run benchmark runner for an engine")
    bm_parser.add_argument("--engine", type=str, required=True, choices=["redis", "mongodb", "qdrant"])
    bm_parser.add_argument("--reps", type=int, default=3)

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

    if args.command == "status":
        raw_p = Path("data/raw/crud_benchmark_runs.csv")
        lbl_p = Path("data/processed/labelled_workloads.csv")
        mod_p = Path("results/models/best_nosql_recommender.joblib")
        ann_p = Path("results/benchmarks/qdrant_ann_runs.json")
        beir_p = Path("results/benchmarks/beir_scifact_qdrant_results.json")

        print("=== NoSQL RAG Research System Status ===")
        if raw_p.exists():
            import pandas as pd
            df_raw = pd.read_csv(raw_p)
            genuine = len(df_raw[df_raw.get("data_provenance", "") == "genuine_benchmark"])
            pilot = len(df_raw[df_raw.get("data_provenance", "") == "remote_cloud_pilot"])
            print(f"Raw Benchmark Runs: {len(df_raw)} total ({genuine} genuine local runs, {pilot} remote cloud pilot)")
        else:
            print("Raw Benchmark Runs: Not found")

        if lbl_p.exists():
            import pandas as pd
            df_lbl = pd.read_csv(lbl_p)
            print(f"Labelled Workloads: {len(df_lbl)} rows (Distribution: {dict(df_lbl['best_store'].value_counts())})")
        else:
            print("Labelled Workloads: Not found")

        print(f"Trained Best Model: {'EXISTS (' + str(mod_p) + ')' if mod_p.exists() else 'Missing'}")
        print(f"Qdrant ANN Benchmark: {'EXISTS (' + str(ann_p) + ')' if ann_p.exists() else 'Missing'}")
        print(f"BEIR SciFact Benchmark: {'EXISTS (' + str(beir_p) + ')' if beir_p.exists() else 'Missing'}")

    elif args.command == "check-connections":
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

    elif args.command == "label":
        import pandas as pd

        from nosql_rag.data import aggregate_crud_runs, derive_best_store_labels

        runs = pd.read_csv(args.runs)
        if not args.allow_synthetic and "data_provenance" in runs.columns:
            runs = runs[runs["data_provenance"] == "genuine_benchmark"]
        agg = aggregate_crud_runs(runs)
        profs = pd.read_csv("data/processed/workload_profiles.csv")
        labels = derive_best_store_labels(agg, profiles=profs)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        labels.to_csv(args.output, index=False)
        print(f"Derived {len(labels)} labels -> {args.output}")
        print(f"Distribution: {dict(labels['best_store'].value_counts())}")

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

    elif args.command == "evaluate":
        import pandas as pd

        from nosql_rag.data import aggregate_crud_runs
        from nosql_rag.evaluation import calculate_latency_regret, summarize_regret

        if not args.labels.exists():
            print(f"Labels not found at {args.labels}")
            sys.exit(1)
        model_path = Path("results/models/best_nosql_recommender.joblib")
        if not model_path.exists():
            print("Trained model not found at results/models/best_nosql_recommender.joblib")
            sys.exit(1)

        model = load_model_artifacts(model_path)
        labels_df = pd.read_csv(args.labels)
        clean, X, y, groups = prepare_ml_dataset(labels_df, allow_synthetic=args.allow_synthetic)
        split = grouped_train_test_split(X, y, groups, clean)

        raw_df = load_raw_runs(Path("data/raw/crud_benchmark_runs.csv"))
        if not args.allow_synthetic and "data_provenance" in raw_df.columns:
            raw_df = raw_df[raw_df["data_provenance"] == "genuine_benchmark"]
        agg_df = aggregate_crud_runs(raw_df)

        regret_df = calculate_latency_regret(
            pipeline=model,
            X_test=split["X_test"],
            y_test=split["y_test"],
            test_meta=split["meta_test"],
            aggregated_measurements=agg_df,
            y_train=split["y_train"],
        )
        summary = summarize_regret(regret_df)
        print("=== Latency Regret Summary ===")
        print(summary.to_string(index=False))

    elif args.command == "explain":
        import pandas as pd

        from nosql_rag.explainability import generate_shap_summary_plot

        if not args.model.exists():
            print(f"Model not found at {args.model}")
            sys.exit(1)
        model = load_model_artifacts(args.model)
        labels_df = pd.read_csv(args.labels)
        clean, X, y, groups = prepare_ml_dataset(labels_df)
        out_fig = Path("reports/figures/shap_summary.png")
        out_fig.parent.mkdir(parents=True, exist_ok=True)
        generate_shap_summary_plot(model, X, output_path=out_fig)
        print(f"Generated SHAP summary plot -> {out_fig}")

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

    elif args.command == "qdrant":
        from nosql_rag.rag.qdrant_benchmark import run_qdrant_ann_benchmark

        cfg = DatabaseConfig.from_env()
        print(f"Running Qdrant ANN benchmark ({args.vectors} vectors, {args.queries} queries)...")
        res = run_qdrant_ann_benchmark(
            db_config=cfg,
            n_vectors=args.vectors,
            n_queries=args.queries,
            cleanup=True,
        )
        print(f"Recall@10: {res['mean_recall_at_k']:.4f}")
        print(f"P50: {res['p50_query_latency_ms']:.3f} ms, P95: {res['p95_query_latency_ms']:.3f} ms")

    elif args.command == "beir":
        from nosql_rag.rag.qdrant_benchmark import run_beir_scifact_rag

        cfg = DatabaseConfig.from_env()
        print(f"Running BEIR SciFact benchmark ({args.queries} queries)...")
        res = run_beir_scifact_rag(
            db_config=cfg,
            dataset_name="scifact",
            max_queries=args.queries,
            cleanup=True,
        )
        print(f"Recall@10: {res.get('recall_at_10')}")
        print(f"NDCG@10: {res.get('ndcg_at_10')}")
        print(f"MRR: {res.get('mrr')}")

    elif args.command == "benchmark":
        print(f"Benchmarking engine '{args.engine}' with {args.reps} repetitions...")
        print("Note: In MINIMAL plan, run Redis and MongoDB via scripts/run_full_matrix.py or sanity pilot.")


if __name__ == "__main__":
    main()
