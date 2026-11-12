# System Architecture

## 1. End-to-End Modular Pipeline

```mermaid
flowchart TD
    W[Workload Definition\nquery_type, payload_bytes, records, concurrency] --> F[Stage 1: Compatibility & Feasibility\nEvaluate data-model requirements]
    F -->|Single Feasible Engine\ne.g., Vector ANN -> Qdrant, Graph -> Neo4j| DET[Deterministic Routing\nSpecialized Benchmark Protocol]
    F -->|Multiple Feasible Engines\ne.g., CRUD -> Redis, Mongo, Cassandra, Neo4j| ML_REC[Stage 2: ML Performance Recommender\nDecision Tree / Random Forest / Gradient Boosting]

    DB[(Candidate Databases\nRedis, MongoDB, Cassandra, Neo4j, Qdrant)] --> BENCH[Benchmarking Harness\nWarmup, Timers, Concurrency, Resource Monitor]
    BENCH --> RAW[(Raw Measurements Log\nAppend-only CSV with Provenance)]
    RAW --> VAL[Quality & Integrity Validator\nLatency ordering, duplicates, error rates]
    VAL --> AGG[Median Aggregator\nper workload and database]
    AGG --> LABELS[Best-Store Labeling\nObjective: min_p95_latency]
    LABELS --> SPLIT[Grouped Train/Test Split\nZero workload_id leakage]
    SPLIT --> ML_REC

    ML_REC --> SHAP[SHAP Explainability\nGlobal importance & instance attributions]
    ML_REC --> REGRET[Regret Evaluation\nvs. Oracle best, Majority, Rule-based, Single-store]

    DET --> RAG_VAL[RAG & Vector Validation\nBEIR SciFact: Recall@K, NDCG@K, MRR]

    ML_REC --> UI[Streamlit Dashboard & CLI\nInteractive Pattern Selection]
    REGRET --> UI
    SHAP --> UI
```

## 2. Package Architecture (`src/nosql_rag/`)

- `config.py`: Strict Pydantic models for database credentials, experiment parameters, paths, and logging.
- `workloads/`:
  - `compatibility.py`: Stage 1 feasibility engine.
  - `generator.py`: Reproducible workload profile generation and deterministic payload synthesis.
- `adapters/`:
  - `base.py`: Abstract `BaseAdapter` and `BaseCRUDAdapter`.
  - `crud.py`: Concrete adapters for Redis, MongoDB, Cassandra, Neo4j.
  - `qdrant_adapter.py`: Concrete adapter for Qdrant vector database.
- `benchmarking/`:
  - `runner.py`: Benchmark harness with warm-up, thread-pool concurrency, timeout guards, and process resource tracking.
- `data/`:
  - `schemas.py`: `DataProvenance` enums and required columns contract.
  - `validator.py`: Automated dataset sanity and synthetic contamination guards.
  - `persistence.py`: Append-only raw run logging and median aggregation.
- `features/`:
  - `pipeline.py`: Preprocessor ColumnTransformer, target-derived column rejection, and `GroupShuffleSplit`.
- `models/`:
  - `training.py`: Decision Tree, Random Forest, Gradient Boosting estimators, StratifiedGroupKFold CV, and artifact serialization.
  - `inference.py`: Two-stage inference pipeline with generalization warnings.
- `explainability/`:
  - `shap_explainer.py`: Multi-class TreeExplainer global importance and per-instance feature contributions.
- `evaluation/`:
  - `regret.py`: Feasibility-aware relative latency regret calculation against Oracle, Random, Majority, and Rule-based baselines.
- `rag/`:
  - `qdrant_benchmark.py`: Seeded ANN latency/recall benchmark and BEIR SciFact passage retrieval experiment.
- `dashboard/`:
  - `app.py`: Interactive Streamlit application with explicit provenance banners.
- `cli.py`: Unified `nosql-rag` command-line tool.
