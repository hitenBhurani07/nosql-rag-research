# ML-Driven NoSQL Pattern Selection for Retrieval-Augmented Generation Workloads

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A research system and explainable machine-learning framework that recommends appropriate NoSQL database patterns for diverse workloads (including Retrieval-Augmented Generation) using workload characteristics and empirical database performance measurements.

---

## 1. Research Overview

NoSQL store selection has historically relied on qualitative rules of thumb or vendor-driven advice. This research framework:
1. Defines a **requirements-first, two-stage recommendation architecture** that respects fundamental data-model boundaries (Key-Value, Document, Wide-Column, Graph, Vector).
2. Measures empirical latency and throughput across **Redis, MongoDB, Apache Cassandra, Neo4j, and Qdrant** under reproducible, controlled workload matrices.
3. Trains explainable machine-learning models (Decision Tree, Random Forest, Gradient Boosting) using **leakage-safe grouped splits**.
4. Quantifies feature contributions via **SHAP** and evaluates recommendations using **relative latency regret** against the Oracle best feasible engine.
5. Validates vector similarity retrieval in an end-to-end RAG setting on **BEIR SciFact**.

### 1.1 Empirical Results Summary (Verified Benchmark)

The experimental benchmark was completed on Windows 11 with local containerized engines:
- **CRUD Matrix Execution**: **900 genuine benchmark runs** across 150 workload profiles (75 base profiles $\times$ 2 concurrency levels $c=1, 4$ $\times$ 3 repetitions) across Redis and MongoDB.
- **Derived Labels**: 150 ground-truth labels under `min_p95_latency_ms` (85 Redis, 65 MongoDB).
- **Best Machine Learning Model**: **Random Forest**
  - **Cross-Validation Macro-F1**: **0.8245** ($\pm 0.0300$) via 5-fold StratifiedGroupKFold (`base_workload_id`).
  - **Held-Out Test Macro-F1**: **0.7871** (Accuracy = 0.7895).
- **Latency Regret**:
  - **ML Recommender**: **4.33%** mean relative regret vs Oracle best feasible engine.
  - **Baselines**: Majority-class (13.46%), Rule-based heuristic (14.08%), Random feasible (15.16%), Single-store MongoDB default (19.11%).
- **Specialized Vector Store (Qdrant)**:
  - **Native ANN**: **100% Recall@10** on 2,000 vectors with 15.07 ms P50 query latency.
  - **BEIR SciFact RAG Retrieval**: **0.8720 Recall@10**, **0.7384 NDCG@10**, and **0.7047 MRR**.
- **Comprehensive Audit**: See `PROJECT_STATUS.json` and [reports/FINAL_REPORT.md](file:///c:/Users/hiten/nosql-rag-research/reports/FINAL_REPORT.md).

---

## 2. Candidate Database Technologies

| Database | Data Model | Native Workload Family | Role in Framework |
| --- | --- | --- | --- |
| **Redis** | Key-Value | `key_value_crud` | Sub-millisecond key-value reads/updates, caching |
| **MongoDB** | Document | `document_crud` | Flexible JSON document CRUD, structured indexing |
| **Apache Cassandra** | Wide-Column | `wide_column_crud` | High-throughput partitioned writes and primary reads |
| **Neo4j** | Property Graph | `graph_traversal` | Multi-hop relationship traversal and graph pattern matching |
| **Qdrant** | Vector Store | `vector_similarity`, `rag_retrieval` | Dense HNSW vector similarity search and RAG retrieval |

---

## 3. Project Structure

```text
nosql-rag-research/
├── configs/
│   ├── experiment.yaml             # Central reproducible experiment configuration
│   └── infrastructure.yaml         # Cloud provider quotas, timeouts & deployment modes
├── docs/
│   ├── architecture.md             # System architecture & Mermaid pipeline diagram
│   ├── colab_execution_guide.md    # Step-by-step Colab runbook & secrets guide
│   ├── experiment_protocol.md      # Formal benchmarking and evaluation protocol
│   ├── implementation_gap_analysis.md # Audit findings & resolution matrix
│   ├── implementation_status.md    # Live phase tracker
│   ├── known_limitations.md        # Scientific and hardware limitations
│   ├── research_requirements.md    # Requirements extracted from research brief
│   ├── infrastructure/             # Cloud infrastructure guides (Redis, Mongo, Astra, Neo4j, Qdrant)
│   └── methodology/
│       ├── database_comparability.md # Two-stage recommendation methodology
│       └── data_collection_protocol.md # Strict provenance & validation protocol
├── notebooks/
│   └── NoSQL_RAG_Implementation_Colab.ipynb # Refactored Colab execution notebook
├── scripts/
│   └── database_preflight.py       # Independent multi-database health check script
├── src/
│   └── nosql_rag/                  # Consolidated Python package
│       ├── adapters/               # Native DB adapters (Redis, Mongo, Cassandra/Astra, Neo4j, Qdrant)
│       ├── benchmarking/           # Controlled benchmark harness & matrix runner
│       ├── dashboard/              # Streamlit interactive recommendation dashboard
│       ├── data/                   # Schemas, integrity validator, persistence & demo generator
│       ├── evaluation/             # Relative latency regret evaluator
│       ├── explainability/         # Multi-class SHAP global & instance explainer
│       ├── features/               # ColumnTransformer & GroupShuffleSplit
│       ├── models/                 # DT, RF, GBDT trainers & two-stage inference
│       ├── rag/                    # Qdrant ANN benchmark & BEIR SciFact evaluator
│       ├── workloads/              # Compatibility filter & profile generator
│       ├── cli.py                  # CLI entry point (nosql-rag)
│       └── config.py               # Pydantic configuration & safe secret handler
├── tests/
│   ├── unit/                       # 28 unit tests covering all modules, dual-mode adapters & redaction
│   └── integration/                # Marked integration tests requiring live databases
├── .env.example                    # Template for database credentials (never commit .env)
├── .gitignore                      # Excludes credentials, caches, raw/processed data, models
└── pyproject.toml                  # PEP 621 package and dependency definitions
```

---

## 4. Quick Start

### 4.1 Installation

```bash
git clone https://github.com/hitenBhurani07/nosql-rag-research.git
cd nosql-rag-research

# Create virtual environment and install in editable mode with dev tools
uv venv --python 3.12 .venv
.venv\Scripts\activate          # Windows (.venv/bin/activate on Linux/macOS)
uv pip install -e ".[dev,databases,dashboard]"
```

### 4.2 Configure Database Endpoints (Optional locally)

Copy `.env.example` to `.env` and fill in your connection strings:
```bash
cp .env.example .env
```

Verify endpoints without leaking credentials:
```bash
nosql-rag check-connections
```

### 4.2.1 Unified Research CLI

The system provides a unified CLI (`nosql-rag`) for the entire research lifecycle:
```powershell
# Check current research system status and artifact presence
uv run nosql-rag status

# Evaluate trained models, baselines, and calculate latency regret
uv run nosql-rag evaluate

# Explain best model with SHAP summary plots
uv run nosql-rag explain

# Get a two-stage recommendation for a workload
uv run nosql-rag recommend --input '{"query_type": "point_lookup", "read_ratio": 0.9, "write_ratio": 0.1, "payload_bytes": 1024, "concurrency": 4, "dataset_records": 5000, "data_size_mb": 5.0, "workload_family": "operational_crud"}'
```

### 4.3 Running Tests

Fast unit test suite (runs in ~25 seconds):
```bash
pytest -v -m "not integration"
```

Integration test suite (requires live database instances):
```bash
pytest -v -m integration
```

### 4.3.1 Auditing a Saved CRUD Matrix

The audit reads the CSV without changing it and compares run attempts with the
deterministic 1,800-key Approach B design:

```bash
python scripts/audit_crud_matrix.py data/raw/crud_benchmark_runs.csv
```

Pass another CSV path to audit a newly downloaded Google Drive checkpoint. Add
`--include-keys` to print every missing, failed, and repeated configuration key.

### 4.4 Launching the Interactive Dashboard

```bash
streamlit run src/nosql_rag/dashboard/app.py
```

### 4.5 Executing in Google Colab

Follow [docs/colab_execution_guide.md](file:///c:/Users/hiten/nosql-rag-research/docs/colab_execution_guide.md) to run the full benchmark matrix, train models, generate SHAP figures, and validate RAG retrieval on Google Colab with Colab Secrets.

---

## 5. Research Integrity & Provenance

This repository enforces strict data provenance guards:
- `synthetic_demo`: Synthetic illustrative data for unit tests and UI demonstration. **Never** used in research models.
- `pilot_benchmark`: Verified small-scale runs against live database endpoints.
- `genuine_benchmark`: Full-matrix experimental measurements under frozen policies.
- `model_ready`: Clean, validated features and best-store labels derived from genuine runs.

Any attempt to train a research model on `synthetic_demo` rows triggers an explicit `ValueError`.

---

## 6. Author and Contact

- **Author:** Hiten Bhurani
- **Email:** 2023.hiten.bhurani@ves.ac.in
- **Repository:** [https://github.com/hitenBhurani07/nosql-rag-research](https://github.com/hitenBhurani07/nosql-rag-research)
