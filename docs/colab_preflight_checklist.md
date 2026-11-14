# Google Colab Pre-Flight Checklist

Comprehensive pre-flight verification checklist for running [notebooks/NoSQL_RAG_Implementation_Colab.ipynb](file:///c:/Users/hiten/nosql-rag-research/notebooks/NoSQL_RAG_Implementation_Colab.ipynb) in a fresh Google Colab session.

---

## 1. Environment & Runtime Pre-Checks

- [ ] **Runtime Type:** Standard CPU runtime selected (or T4 GPU if fast SentenceTransformers encoding is desired).
- [ ] **Python Compatibility:** Python 3.10+ detected in Colab (`sys.version`).
- [ ] **Google Drive Space:** Minimum 1 GB available storage on connected Google Drive for persistent benchmark logs, models, and artifacts.

---

## 2. GitHub Authentication & Package Installation

- [ ] **Public Repository Mode:** Clones without credentials (`git clone --depth 1 https://github.com/hitenBhurani07/nosql-rag-research.git`).
- [ ] **Private Repository Mode:**
  - Token added to Google Colab Secrets under key `GITHUB_TOKEN`.
  - Token permission verified: Personal Access Token (classic or fine-grained) with **Contents: Read** (or `repo` scope).
  - Notebook uses temporary in-memory `GIT_ASKPASS` helper (never embeds token in Git URL, logs, or disk).
- [ ] **Package Installation:** `pip install -q -e ".[all]"` installs `nosql-rag-research==0.1.0` along with `databases`, `rag`, and `dashboard` dependency groups.
- [ ] **Module Import Gate:** All 10 submodules import cleanly without errors:
  - `nosql_rag.config`
  - `nosql_rag.workloads`
  - `nosql_rag.adapters`
  - `nosql_rag.benchmarking`
  - `nosql_rag.data`
  - `nosql_rag.features`
  - `nosql_rag.models`
  - `nosql_rag.explainability`
  - `nosql_rag.evaluation`
  - `nosql_rag.rag`

---

## 3. Database-Independent Smoke Test (Offline Gate)

- [ ] **Execute Smoke Test:** Run Cell 23 (`RUN_SMOKE_TEST = True`):
  - [x] CLI `--help` invocation succeeds (`nosql-rag`).
  - [x] Configuration loading verifies default `min_p95_latency_ms` objective.
  - [x] Workload generator produces 4 test profiles.
  - [x] Synthetic demo measurements generated with explicit `data_provenance=synthetic_demo`.
  - [x] Data validator verifies latency ordering and zero duplicate runs.
  - [x] Synthetic records saved to persistent Google Drive directory (`data/raw/smoke_test_synthetic_runs.csv`).

---

## 4. Database Secrets & Endpoint Verification

Add the following secrets in Google Colab (Key icon in left sidebar) and enable **Notebook access**:

| Secret Key | Description | Status in Secrets |
| --- | --- | --- |
| `REDIS_URL` | Redis endpoint URI (`redis://` or `rediss://`) | [ ] Configured |
| `MONGODB_URI` | MongoDB Atlas connection string | [ ] Configured |
| `MONGODB_DATABASE` | MongoDB database name (default: `nosql_rag_research`) | [ ] Configured |
| `CASSANDRA_HOSTS` | Cassandra cluster contact points / Astra host | [ ] Configured |
| `CASSANDRA_PORT` | CQL Port (default: `9042`) | [ ] Configured |
| `CASSANDRA_KEYSPACE`| Cassandra CQL keyspace (`nosql_rag_research`) | [ ] Configured |
| `CASSANDRA_USERNAME`| Cassandra user / Astra client ID | [ ] Configured |
| `CASSANDRA_PASSWORD`| Cassandra password / Astra secret | [ ] Configured |
| `CASSANDRA_SSL` | Enable SSL/TLS (`true` or `false`) | [ ] Configured |
| `NEO4J_URI` | Neo4j AuraDB / Bolt URI (`neo4j+s://...`) | [ ] Configured |
| `NEO4J_USERNAME` | Neo4j user (`neo4j`) | [ ] Configured |
| `NEO4J_PASSWORD` | Neo4j instance password | [ ] Configured |
| `NEO4J_DATABASE` | Neo4j database name (default: `neo4j`) | [ ] Configured |
| `QDRANT_URL` | Qdrant Cloud or remote endpoint URL | [ ] Configured |
| `QDRANT_API_KEY` | Qdrant Cloud API Key | [ ] Configured |

- [ ] **Connection Check Gate:** Run Cell 21. Confirm that all required stores report `connected: True`.

---

## 5. Sequential Execution Progression

1. **Step 1 (Pilot):** Set `RUN_PILOT = True` $\to$ Execute 8 operational CRUD runs (250 ops/run) $\to$ Validate `data/raw/crud_benchmark_runs.csv`.
2. **Step 2 (Vector/RAG Pilot):** Set `RUN_QDRANT_ANN_PILOT = True` and `RUN_BEIR_RAG = True` $\to$ Confirm ANN Recall@K and BEIR IR metrics.
3. **Step 3 (Full Matrix):** Set `RUN_FULL_MATRIX = True` $\to$ Execute the 1,800-run Approach B matrix (75 base workloads x concurrency 1/4 x 4 engines x 3 repetitions) in resumable batches.
4. **Step 4 (Validation & Labeling):** Validate all 1,800 expected keys and derive measured labels. Keep the 150 matched profiles grouped into 75 `base_workload_id` groups for all ML splits.
5. **Step 5 (ML & Explainability):** Set `RUN_ML_TRAINING = True` and `RUN_SHAP = True` $\to$ Train Decision Tree, Random Forest, Gradient Boosting $\to$ Evaluate latency regret vs. Oracle $\to$ Export SHAP summary.
6. **Step 6 (Export):** Run Cells 55–57 $\to$ Download `NoSQL_RAG_Research_Artifacts.zip`.
