# ML-Driven NoSQL Pattern Selection for Retrieval-Augmented Generation Workloads

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A research system and explainable machine-learning framework that recommends appropriate NoSQL database patterns for diverse workloads (including Retrieval-Augmented Generation) using workload characteristics and empirical database performance measurements.

**Author**: Hiten Bhurani (`2023.hiten.bhurani@ves.ac.in`)  
**Repository**: [https://github.com/hitenBhurani07/nosql-rag-research](https://github.com/hitenBhurani07/nosql-rag-research)  
**Hardware Environment**: Windows 11 Home, Intel Core i5-12500H (12 physical cores, 16 threads), 16 GB RAM, NVMe SSD, Docker Desktop with WSL2 capped at 3GB RAM.

---

## 1. Research Overview & Key Findings

NoSQL store selection has historically relied on qualitative rules of thumb or vendor-driven advice. This research framework:
1. Defines a **requirements-first, two-stage recommendation architecture** that respects fundamental data-model boundaries (Key-Value, Document, Wide-Column, Graph, Vector).
2. Measures empirical latency and throughput across **Redis, MongoDB, Apache Cassandra, Neo4j, and Qdrant** under reproducible, controlled workload matrices.
3. Employs a **pinned in-container benchmark client** (`nosql-rag-client:1.0`) on the internal compose network with process-based multiprocessing at $c=4$ to eliminate Windows loopback port-forwarding stalls and Python GIL contention.
4. Evaluates explainable machine-learning models (Decision Tree, Random Forest, Gradient Boosting) using **leakage-safe grouped cross-validation** (`base_workload_id`).
5. Quantifies feature contributions via **SHAP** and evaluates recommendations using **relative latency regret** against the Oracle best feasible engine.
6. Validates vector similarity retrieval in an end-to-end RAG setting on **BEIR SciFact** across all 300 test queries.

### 1.1 In-Container Experimental Results Summary (Verified Benchmark)

- **Total In-Container Genuine Runs**: **1,356 runs** across 4 engines with 0 errors (100% success rate):
  - **Redis**: 450 runs (150 profiles $\times$ 3 reps, median P50: 0.090 ms, P95: 0.175 ms).
  - **MongoDB**: 450 runs (150 profiles $\times$ 3 reps, median P50: 0.296 ms, P95: 0.584 ms).
  - **Cassandra**: 228 runs (76 profiles $\times$ 3 reps, median P50: 0.613 ms, P95: 1.133 ms).
  - **Neo4j**: 228 runs (76 profiles $\times$ 3 reps, median P50: 0.902 ms, P95: 3.269 ms).
- **Repetition Winner Stability**: **98.67%** unanimous 3-repetition agreement on 2-engine (150 profiles), **100.00%** on 4-engine (76 profiles).
- **Dual Machine Learning Analysis**:
  - **Analysis A (2 Engines, 150 Profiles)**: In pure single-key CRUD, in-memory Redis dominates (149/150 wins). Decision Tree, Random Forest, and Gradient Boosting achieve 1.0000 test accuracy and Macro-F1, matching the Majority-class baseline with **0.00% latency regret** vs. Oracle. Deploying Always-MongoDB incurs **206.82%** mean regret.
  - **Analysis B (4 Engines, 76 Profiles)**: Redis wins 76/76 profiles. Recommenders achieve 1.0000 accuracy / Macro-F1. Deploying Always-MongoDB incurs +264.39% regret, Always-Cassandra +576.10% regret, and Always-Neo4j +1770.67% regret.
- **Methodology Finding (Windows Port-Forwarding Artifact)**:
  - Host loopback proxying imposed a ~0.25 ms socket overhead that flipped ground truth winners on **42.67% of workloads** (64 / 150 profiles). Earlier 900 host-measured runs are quarantined as `data_provenance = 'host_port_forward_pilot'` and excluded from ML models.
- **$c=4$ Concurrency Validity**:
  - Python multi-threading suffered an 80.64% queueing penalty under $c=4$. Switching to process multiprocessing increased throughput 4.25x (from 4,580 to 19,490 ops/s) and dropped Redis P95 from 1.375 ms to 0.266 ms.
- **Specialized Vector & Graph Evaluation**:
  - **BEIR SciFact RAG Retrieval (All 300 Queries)**: **0.7833 Recall@10**, **0.6451 NDCG@10**, **0.6047 MRR**, with 15.32 ms P50 search latency.
  - **Native Qdrant ANN**: **100.0% Recall@10** on 2,000 vectors with 15.07 ms P50 latency.
  - **Neo4j Graph Traversal**: 100 queries at 2-hop depth, 270.4 ops/s, P50 latency: **2.99 ms**, P95: **4.09 ms**.

---

## 2. Candidate Database Technologies

| Database | Data Model | Native Workload Family | Role in Framework |
| --- | --- | --- | --- |
| **Redis** | Key-Value | `key_value_crud` | Sub-millisecond key-value reads/updates, operational state caching |
| **MongoDB** | Document | `document_crud` | JSON document CRUD, structured secondary indexing |
| **Apache Cassandra** | Wide-Column | `wide_column_crud` | High-throughput partitioned append writes and point lookups |
| **Neo4j** | Property Graph | `graph_traversal` | Multi-hop relationship traversal and graph pattern matching |
| **Qdrant** | Vector Store | `vector_similarity`, `rag_retrieval` | Dense HNSW vector similarity search and RAG retrieval |

---

## 3. Project Structure

```text
nosql-rag-research/
├── configs/
│   ├── experiment.yaml             # Central reproducible experiment configuration
│   └── infrastructure.yaml         # Cloud provider quotas, timeouts & deployment modes
├── data/
│   ├── raw/
│   │   └── crud_benchmark_runs.csv # 2,269 total runs (1,356 in-container genuine + 900 host pilot + 8 cloud + 5 artifacts)
│   ├── processed/
│   │   ├── workload_profiles.csv   # 150 factorial workload profiles (75 base x c=1, 4)
│   │   ├── aggregated_benchmark_runs.csv # Median metrics per workload and engine
│   │   └── labelled_workloads.csv  # Derived ground-truth labels for ML training
│   └── sample/
│       └── scifact/                # BEIR SciFact biomedical passage retrieval corpus
├── docker-compose.yml              # Pinned database services and in-container benchmark runner
├── Dockerfile.client               # Pinned client container definition (nosql-rag-client:1.0)
├── docs/
│   ├── GOAL_STATE.md               # Goal execution state, timestamps, time budget, and step log
│   ├── PREFLIGHT.md                # Hardware environment and memory threshold preflight record
│   ├── DECISIONS.md                # Architectural decisions, network latency resolution, and hardware safety rationale
│   ├── AUDIT.md                    # Workspace audit report
│   └── PROGRESS.md                 # Phase-by-phase execution progress log
├── reports/
│   ├── FINAL_REPORT.md             # Authoritative research report and methodology investigation
│   ├── figures/                    # Latency regret charts and SHAP summary plots
│   └── tables/                     # Model comparison, cross-validation, and regret tables
├── results/
│   ├── benchmarks/                 # Qdrant ANN, BEIR SciFact, and Neo4j graph traversal results
│   ├── figures/                    # Synced publication figures
│   └── models/
│       └── best_nosql_recommender.joblib # Persisted recommendation model pipeline
├── scripts/
│   ├── run_engine_matrix.py        # In-container CRUD matrix execution script
│   ├── run_dual_evaluation.py      # Dual ML evaluation and regret pipeline
│   ├── run_beir_full.py            # Complete 300-query BEIR SciFact evaluation
│   └── compare_c4_concurrency.py   # c=4 Threaded vs. Multiprocess validation
├── src/
│   └── nosql_rag/                  # Core Python package
└── tests/
    └── unit/                       # 44 unit tests covering schemas, validation, adapters & gating
```

---

## 4. Quick Start & Verification

### 4.1 Environment Setup
```powershell
# 1. Create virtual environment and install package
uv venv --python 3.12 .venv
.venv\Scripts\activate
uv pip install -e ".[all]"

# 2. Run test suite (44 passed)
uv run pytest tests/unit -q

# 3. Check code formatting
uv run ruff check .
```

### 4.2 In-Container Benchmark Execution
```powershell
# Build pinned client runner
docker build -t nosql-rag-client:1.0 -f Dockerfile.client .

# Run Redis matrix (150 profiles x 3 reps = 450 runs)
docker compose up -d redis
docker compose run --rm -T benchmark-runner python scripts/run_engine_matrix.py --database Redis --profiles-count 150 --repetitions 3
docker stop nosql-rag-redis

# Run MongoDB matrix (150 profiles x 3 reps = 450 runs)
docker compose up -d mongodb
docker compose run --rm -T benchmark-runner python scripts/run_engine_matrix.py --database MongoDB --profiles-count 150 --repetitions 3
docker stop nosql-rag-mongo
```

### 4.3 Re-Evaluating Dual Datasets & Latency Regret
```powershell
uv run python scripts/run_dual_evaluation.py
```

---

## 5. Research Integrity & Data Provenance

This repository enforces strict data provenance tags in `data/raw/crud_benchmark_runs.csv`:
- `genuine_benchmark` (1,356 rows): Genuine in-container compose-network measurements.
- `host_port_forward_pilot` (900 rows): Flawed host loopback pilot runs (strictly excluded from research ML models).
- `remote_cloud_pilot` (8 rows): Historical WAN cloud runs (excluded from local models).
- `invalid_measurement_artifact` (5 rows): Stalled host measurement artifacts (quarantined).
- `synthetic_demo`: Synthetic test data. Any attempt to train models on synthetic data raises a `ValueError`.

---

## 6. Citation & Contact

- **Author**: Hiten Bhurani
- **Email**: `2023.hiten.bhurani@ves.ac.in`
- **Institution**: VES / Research Engineering
