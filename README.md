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
│   └── experiment.yaml             # Central reproducible experiment configuration
├── docs/
│   ├── architecture.md             # System architecture & Mermaid pipeline diagram
│   ├── colab_execution_guide.md    # Step-by-step Colab runbook & secrets guide
│   ├── experiment_protocol.md      # Formal benchmarking and evaluation protocol
│   ├── implementation_gap_analysis.md # Audit findings & resolution matrix
│   ├── implementation_status.md    # Live phase tracker
│   ├── known_limitations.md        # Scientific and hardware limitations
│   ├── research_requirements.md    # Requirements extracted from research brief
│   └── methodology/
│       ├── database_comparability.md # Two-stage recommendation methodology
│       └── data_collection_protocol.md # Strict provenance & validation protocol
├── notebooks/
│   └── NoSQL_RAG_Implementation_Colab.ipynb # Refactored Colab execution notebook
├── src/
│   └── nosql_rag/                  # Consolidated Python package
│       ├── adapters/               # Native DB adapters (Redis, Mongo, Cassandra, Neo4j, Qdrant)
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
│   ├── unit/                       # 17 fast unit tests covering all modules
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

### 4.3 Running Tests

Fast unit test suite (runs in ~25 seconds):
```bash
pytest -v -m "not integration"
```

Integration test suite (requires live database instances):
```bash
pytest -v -m integration
```

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
