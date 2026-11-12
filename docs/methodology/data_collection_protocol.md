# Data Collection and Research Integrity Protocol

## 1. Data Provenance Categories

Every dataset and measurement row in this repository MUST carry an explicit `data_provenance` tag:

1. `synthetic_demo`: Generated deterministically in memory for unit tests, pipeline verification, and dashboard UI demonstrations. **Never** used to train or report the research model.
2. `pilot_benchmark`: Genuine measurements collected from real database endpoints during small-scale pilot runs (e.g., 2 profiles × 250 ops). Used to validate adapters, timing, and cleanup.
3. `genuine_benchmark`: Full-matrix genuine measurements collected from real database endpoints under frozen experimental policies.
4. `aggregated_experimental`: Median-aggregated per `(workload_id, database)` metrics derived strictly from validated `genuine_benchmark` (or `pilot_benchmark`) runs.
5. `model_ready`: Labelled per-workload feature/target table derived strictly from `aggregated_experimental` data where at least two feasible engines succeeded.

## 2. Append-Only Raw Storage

- Raw benchmark runs are appended to `data/raw/crud_benchmark_runs.csv` (and `data/raw/qdrant_ann_runs.csv`, `data/raw/neo4j_graph_runs.csv`).
- Aggregated tables are written separately to `data/processed/`.
- Raw logs are **never** overwritten by aggregation scripts.

## 3. Mandatory Dataset Validation Checks

Before aggregation or ML training, `nosql_rag.data.validator` enforces:
- **Missing measurements:** Required columns (`run_id`, `workload_id`, `database`, `status`, `p50_latency_ms`, `p95_latency_ms`, `p99_latency_ms`, `throughput_ops_sec`, `error_rate`, `data_provenance`) must be present and non-null for successful runs.
- **Duplicate runs:** Duplicate `run_id` entries are rejected.
- **Invalid latency:** `p50_latency_ms <= p95_latency_ms <= p99_latency_ms` and all latencies `> 0`.
- **Failed executions:** Runs with `status != "success"` or `error_rate > MAX_ALLOWED_ERROR_RATE` are excluded from winner derivation (and logged in quality reports).
- **Inconsistent database configuration:** `config_hash` and `database_version` are tracked per `(workload_id, database)`.
- **Outliers:** Extreme latency outliers (e.g., > 5× IQR within repetitions of the same configuration) are flagged for inspection.
- **Missing workload metadata:** Every `workload_id` in runs must join cleanly to a known workload profile.
- **Incomplete repetitions:** Configurations with fewer than `min_repetitions` successful runs are flagged.
- **Synthetic contamination check:** Training pipelines raise `ValueError` if any row has `data_provenance == "synthetic_demo"` unless `allow_synthetic=True` is explicitly passed for unit tests.

## 4. Leakage Prevention

- Train/test splitting and cross-validation use `GroupShuffleSplit` / `StratifiedGroupKFold` grouped by `workload_id` so all runs/repetitions of a workload profile stay in the same partition.
- Target-derived performance columns (`p50_latency_ms`, `p95_latency_ms`, `throughput_ops_sec`, `best_p95_latency_ms`, etc.) are strictly excluded from `FEATURE_COLUMNS`.
