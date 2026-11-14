# Design and Execution Decisions

## Decision 1: MINIMAL Plan Selected
**Date**: 2026-11-14  
**Reason**: Free physical RAM at baseline (WSL + Docker stopped) was 4.16 GB, placing us in the 3–5 GB MINIMAL range per revised thresholds.  
**Impact**: Only Redis, MongoDB, and Qdrant are benchmarked one at a time.  
**Cassandra**: Skipped. Its Docker container requires 2 GB heap (JVM). With 4.16 GB baseline free and WSL2 + Docker overhead already consuming ~2.5 GB, launching Cassandra would exceed safe memory bounds and cause OOM or swap-induced result corruption.  
**Neo4j**: Skipped. Neo4j Community requires 1–1.5 GB heap. The JVM startup + heap would bring the system below 1 GB free, risking benchmark contamination from swap/GC pressure.  
**Documentation**: Both exclusions are noted in FINAL_REPORT.md under Limitations.

## Decision 2: Cassandra Excluded (Memory Safety)
**Date**: 2026-11-14  
**Reason**: See Decision 1. Cassandra 2 GB heap limit would require 2+ GB free after all other processes.  
**Alternative considered**: Reducing MAX_HEAP_SIZE to 512m. Rejected — Cassandra behaves unpredictably under severe heap pressure and results would not be representative.

## Decision 3: Neo4j Excluded (Memory Safety)
**Date**: 2026-11-14  
**Reason**: See Decision 1. Neo4j 1.5 GB heap limit on a system with 4.16 GB baseline free and Docker overhead.  
**Alternative considered**: Running Neo4j instead of MongoDB. Rejected — MongoDB is a more common RAG store and must not be excluded per the prompt's hard rules.

## Decision 4: Operations Count Reduced for MINIMAL Plan
**Date**: 2026-11-14  
**Reason**: 150 profiles × 3 engines × 3 reps × 1500 ops = 2.025M ops. At local Docker speed (~1000-5000 ops/sec), this is 7-30 minutes, acceptable. However, to target ≥300 distinct configurations while staying within ~3h:  
- profiles: 50 base × 2 concurrency = 100 profiles  
- engines: 3 (Redis, MongoDB, Qdrant-CRUD excluded — Qdrant runs ANN separately)  
- Wait: Qdrant is vector-only — CRUD benchmark engines are Redis and MongoDB only (2 CRUD engines)  
- 100 profiles × 2 CRUD engines × 3 reps = 600 runs  
- With 500 ops/run at local speed, estimated ~15-30 min  
- **Revised**: 50 base profiles × 2 concurrency = 100 profiles, 2 CRUD engines (Redis, MongoDB), 3 reps = **600 planned CRUD runs**  
- Qdrant: ANN benchmark separately (2000 vectors, 100 queries)  
- BEIR SciFact: separate RAG evaluation

## Decision 5: Old Cloud Pilot Rows Relabelled
**Date**: 2026-11-14  
**Action**: The 8 Colab/cloud pilot rows in `data/raw/crud_benchmark_runs.csv` have `hosting_region` relabelled to `remote_cloud_pilot` and `data_provenance` set to indicate cloud origin. They are EXCLUDED from ML training.  
**Reason**: Latencies (59–236 ms) reflect Google Cloud network RTT to Atlas/Astra/Redis Cloud, not engine performance.

## Decision 6: train_and_compare_models Argument Order Confirmed
**Date**: 2026-11-14  
**Verification**: Actual signature in `src/nosql_rag/models/training.py` line 104: `train_and_compare_models(X_train, y_train, X_test, y_test, ...)`.  
The other AI's notebook correction (`X_train, y_train, X_test, y_test`) matches the real signature. ✅

## Decision 7: group_column = base_workload_id for Approach B
**Date**: 2026-11-14  
**Reason**: Matched concurrency pairs (c=1 and c=4 of same base workload) must stay in the same fold. `prepare_ml_dataset` auto-detects `base_workload_id` if present.

## Decision 8: Engines Run One at a Time
**Date**: 2026-11-14  
**Reason**: Memory constraints. Each container is started, benchmarked fully, then stopped before the next starts. This ensures consistent system state across engine comparisons.

