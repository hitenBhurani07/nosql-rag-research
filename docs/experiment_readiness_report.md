# Experiment Readiness & Pre-Flight Report

Date: 2026-11-12
Status: **LOCKED FOR PRE-FLIGHT EXECUTION**
Workspace: `nosql-rag-research`

> **Superseded matrix note (2026-11-13):** The 900-run design below is historical. The
> current approved design is Approach B: 75 base workloads x 2 matched concurrency levels
> (1 and 4) x 4 CRUD databases x 3 repetitions = 1,800 run records. See
> `docs/methodology/final_experiment_matrix.md` for the active matrix and current
> execution evidence.

---

## 1. Defensible Workload Comparability Assessment

### Is the Workload Comparison Scientifically Defensible?
**YES, under the two-stage feasibility architecture.**
- Operational record CRUD point lookups and updates are evaluated with identical semantics and payloads across Redis, MongoDB, Cassandra, and Neo4j (measuring operational overhead).
- Qdrant is **strictly excluded** from general CRUD rankings and evaluated solely on high-dimensional vector similarity ANN search and RAG document retrieval.
- Neo4j is identified as the **sole native property-graph store** for multi-hop graph traversals (`graph_traversal`), avoiding false comparisons against non-graph engines.
- Full methodological rationale is codified in [docs/methodology/database_comparability.md](file:///c:/Users/hiten/nosql-rag-research/docs/methodology/database_comparability.md).

---

## 2. Workload Families and Eligible Database Engines

| Workload Family | Eligible Database Candidates | Primary Evaluation Metrics |
| --- | --- | --- |
| **`key_value_crud`** | `Redis`, `MongoDB`, `Cassandra`, `Neo4j` | p95 Latency (ms), Throughput (ops/sec) |
| **`document_crud`** | `MongoDB`, `Redis`, `Cassandra`, `Neo4j` | p95 Latency (ms), Throughput (ops/sec) |
| **`wide_column_crud`** | `Cassandra`, `Redis`, `MongoDB` | p95 Latency (ms), Throughput (ops/sec) |
| **`graph_traversal`** | `Neo4j` | Multi-hop Traversal Latency (ms), Nodes/sec |
| **`vector_similarity`** | `Qdrant` | ANN Query Latency (ms), Recall@K vs. Brute-Force |
| **`rag_retrieval`** | `Qdrant` | Recall@10, NDCG@10, MRR, Retrieval Latency (ms) |

---

## 3. Sample Size and Matrix Design

- **Independent Workload Profiles:** **$N = 75$ distinct profiles** in the primary matrix.
- **Candidate Engines per Profile:** 4 engines.
- **Repetitions:** 3 runs per configuration.
- **Total Operational CRUD Runs:** $75 \times 4 \times 3 = 900$ runs.
- **Distinction Enforced:** 900 measurement runs produce 300 configuration rows and **exactly 75 independent labelled training examples** ($y_i = \text{best\_store}(W_i)$).
- **Expanded Option:** An expanded 180-profile matrix ($2,160$ runs, ~3.5 hours) is documented in [docs/methodology/final_experiment_matrix.md](file:///c:/Users/hiten/nosql-rag-research/docs/methodology/final_experiment_matrix.md) for potential post-pilot scale-up.

---

## 4. Pre-Flight Pilot Configuration

Before launching the 900-run full matrix, the following pilot matrix must be executed to verify system mechanics:
- **Profiles:** 2 profiles (`P0001`: read-heavy 512B KV, `P0002`: write-heavy 2048B Document).
- **Engines:** 4 engines (`Redis`, `MongoDB`, `Cassandra`, `Neo4j`).
- **Repetitions:** 1 repetition.
- **Operations per Run:** 250 operations (20 unmeasured warm-up).
- **Total Pilot Runs:** **8 executions**.
- **Vector Pilot:** 2,000 vectors $\times$ 100 queries on Qdrant.
- **RAG Pilot:** 50 queries on BEIR SciFact corpus.
- **Estimated Duration:** < 5 minutes total.

---

## 5. Required Credentials & Service Endpoints

The following credentials must be configured in Google Colab Secrets (or a local `.env` file):

| Secret Key | Target Service | Free-Tier / Managed Provider Recommendation |
| --- | --- | --- |
| `REDIS_URL` | Redis | Redis Cloud Free Tier (30MB) or Upstash |
| `MONGODB_URI` | MongoDB | MongoDB Atlas M0 Free Cluster |
| `CASSANDRA_HOSTS` | Apache Cassandra | DataStax Astra DB Free Tier or local Docker |
| `CASSANDRA_KEYSPACE`| Apache Cassandra | Keyspace name (`nosql_rag_research`) |
| `CASSANDRA_USERNAME`| Apache Cassandra | Client ID or Cassandra username |
| `CASSANDRA_PASSWORD`| Apache Cassandra | Client secret or Cassandra password |
| `NEO4J_URI` | Neo4j | Neo4j AuraDB Free Instance |
| `NEO4J_USERNAME` | Neo4j | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j | AuraDB instance password |
| `QDRANT_URL` | Qdrant | Qdrant Cloud Free Tier Cluster (1GB) |
| `QDRANT_API_KEY` | Qdrant | Qdrant Cloud API Key |

---

## 6. Colab Package Access & Path Independence

- **Access Mechanism:** Colab clones the GitHub repository and runs:
  ```bash
  !pip install -q -e .
  ```
- **Path Independence:** All file loading and persistence relies on `ProjectPaths(Path.cwd())` and relative directory paths (`data/raw/`, `results/models/`).
- **Drive Persistence:** Automatically mirrors outputs to `/content/drive/MyDrive/NoSQL_RAG_Research` when `USE_GOOGLE_DRIVE = True`.

---

## 7. Pre-Flight Checklist Before Full Benchmarking

- [x] Python package installed and importable (`nosql_rag`).
- [x] Unit test suite passing 100% (17 unit tests passed).
- [x] Linter passing with zero errors (`ruff check src tests`).
- [x] Git ignores credentials (`.env`, `.env.*`) and unpublished source docs (`docs/source/*`).
- [x] Colab notebook refactored to use package modules without code duplication.
- [ ] Database credentials configured in Google Colab Secrets.
- [ ] Cell 21 connection check executed in Colab and returned `connected: True` for all 5 stores.
- [ ] Pre-flight pilot executed (`RUN_PILOT = True`, 8 runs completed with `status='success'`).
- [ ] Data validator confirms valid latency percentiles and zero duplicate runs in pilot data.
- [ ] Enable `RUN_FULL_MATRIX = True` and execute full 900-run matrix in Colab.
