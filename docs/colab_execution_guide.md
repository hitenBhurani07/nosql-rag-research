# Google Colab Execution Guide and Runbook

Step-by-step pre-flight and execution runbook for [notebooks/NoSQL_RAG_Implementation_Colab.ipynb](file:///c:/Users/hiten/nosql-rag-research/notebooks/NoSQL_RAG_Implementation_Colab.ipynb).

---

## 1. Google Colab Environment & Compatibility

- **Python Runtime:** Python 3.10, 3.11, or 3.12 (Colab standard CPU runtime is sufficient; T4 GPU optional for faster SentenceTransformer encoding).
- **Package Source:** The notebook clones/pulls `nosql-rag-research` from GitHub or loads the mounted workspace, and installs the package in editable mode:
  ```bash
  !pip install -q -e .
  ```
- **OS Path Independence:** All internal paths use `pathlib.Path` with relative project roots (`Path.cwd()`). No local Windows paths (`C:\Users\...`) exist in notebook code.

---

## 2. Setting Up Colab Secrets (Zero Hardcoded Credentials)

In the Google Colab left sidebar, open the **Key icon (Secrets)** and define the following secrets:

| Colab Secret Name | Type | Description | Example Placeholder |
| --- | --- | --- | --- |
| `REDIS_URL` | String | Connection URI for Redis | `rediss://default:token@my-redis.cloud:6379/0` |
| `MONGODB_URI` | String | MongoDB Atlas or remote connection URI | `mongodb+srv://user:pass@cluster0.mongodb.net/?retryWrites=true&w=majority` |
| `MONGODB_DATABASE` | String | Database name (optional, defaults to `nosql_rag_research`) | `nosql_rag_research` |
| `CASSANDRA_HOSTS` | String | Cassandra contact points | `127.0.0.1` or Astra cluster host |
| `CASSANDRA_PORT` | Integer | Cassandra CQL port (default `9042`) | `9042` |
| `CASSANDRA_KEYSPACE` | String | Existing CQL keyspace | `nosql_rag_research` |
| `CASSANDRA_USERNAME` | String | Cassandra username or Astra client ID | `my_user` |
| `CASSANDRA_PASSWORD` | String | Cassandra password or Astra secret | `my_password` |
| `CASSANDRA_SSL` | Boolean | Enable SSL/TLS for Cassandra (default `false`) | `true` |
| `NEO4J_URI` | String | Neo4j AuraDB or Bolt URI | `neo4j+s://xxxx.databases.neo4j.io` |
| `NEO4J_USERNAME` | String | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | String | Neo4j password | `my_neo4j_password` |
| `NEO4J_DATABASE` | String | Neo4j database (default `neo4j`) | `neo4j` |
| `QDRANT_URL` | String | Qdrant Cloud or remote endpoint URL | `https://xxxx.cloud.qdrant.io:6333` |
| `QDRANT_API_KEY` | String | Qdrant Cloud API key | `my_qdrant_api_key` |

> [!IMPORTANT]
> Ensure the **Notebook access** toggle switch is flipped to **ON** for each secret in Colab.

---

## 3. Pre-Flight Execution Workflow

### Step 1: Initialize Runtime (Cells 0–11)
1. Run Cell 4 (`Runtime setup and experiment controls`).
   - Default flags keep all expensive runs OFF:
     - `RUN_CONNECTION_CHECKS = True`
     - `RUN_PILOT = False`
     - `RUN_FULL_MATRIX = False`
     - `RUN_QDRANT_ANN_PILOT = False`
     - `RUN_BEIR_RAG = False`
     - `RUN_ML_TRAINING = False`
     - `RUN_SHAP = False`
2. Run Cell 8 (`USE_GOOGLE_DRIVE = True`). Mounts Google Drive to `/content/drive/MyDrive/NoSQL_RAG_Research` for persistent storage across Colab restarts.
3. Run Cell 10 to install package dependencies:
   ```bash
   !pip install -q redis pymongo cassandra-driver neo4j qdrant-client sentence-transformers beir shap streamlit
   !pip install -q -e .
   ```

### Step 2: Secret & Connection Verification (Cells 12–21)
1. Run Cell 13. Verifies that `db_config = DatabaseConfig.from_env()` detects your secrets. Displays a safe status table (`configured: True/False`).
2. Run Cell 21. Tests live network handshakes to all 5 database endpoints.
   - **Verification Gate:** **All 5 databases must report `connected: True` before proceeding.**
   - If any database reports `connected: False`, inspect the reported exception (e.g., DNS error, authentication failure, TLS failure) and correct the secret.

### Step 3: Run Pre-Flight Pilot Benchmark (Cells 22–27)
1. In Cell 4, set `RUN_PILOT = True`.
2. Run Cells 23–27.
   - Executes 2 workload profiles $\times$ 4 CRUD engines = 8 runs (250 operations each).
   - Expected output file: `data/raw/crud_benchmark_runs.csv` (8 rows, `status='success'`).
   - Verifies that cleanup drops temporary tables/collections (`bench_p0001_...`).

### Step 4: Run Vector & RAG Pilots (Cells 48–51)
1. In Cell 4, set `RUN_QDRANT_ANN_PILOT = True` and run Cell 49.
   - Seeds 2,000 vectors (128-d) and runs 100 ANN queries.
   - Verifies HNSW collection creation, query latency, and Recall@K calculation against exact brute-force search.
2. In Cell 4, set `RUN_BEIR_RAG = True` and run Cell 51.
   - Downloads BEIR SciFact (5,183 docs), encodes with `all-MiniLM-L6-v2`, and evaluates retrieval metrics (Recall@10, NDCG@10, MRR).

### Step 5: Execute Full Matrix Benchmark (Cells 28–30)
1. Once the pilot passes cleanly, set `RUN_FULL_MATRIX = True` in Cell 4.
2. Run Cell 29.
   - Executes 75 profiles $\times$ 4 engines $\times$ 3 repetitions = 900 runs in batches of 5.
   - Automatically appends results to `data/raw/crud_benchmark_runs.csv`.
   - **Resume support:** If the runtime disconnects, re-running Cell 29 checks existing successful runs and resumes only pending configurations.

### Step 6: Data Validation & ML Training (Cells 31–41)
1. Run Cell 31 (`validate_raw_runs`). Ensures zero duplicate runs, correct latency ordering ($p50 \le p95 \le p99$), and acceptable error rates ($\le 1\%$).
2. Run Cell 33 (`derive_best_store_labels`). Aggregates median metrics and derives winning `best_store` labels. Output: `data/processed/labelled_workloads.csv` ($N = 75$ rows).
3. Set `RUN_ML_TRAINING = True` in Cell 4 and run Cells 35–41.
   - Partitions $75$ profiles using leakage-safe `GroupShuffleSplit` (grouped by `workload_id`).
   - Fits Decision Tree, Random Forest, and Gradient Boosting.
   - Saves the best model to `results/models/best_nosql_recommender.joblib`.

### Step 7: Regret Evaluation & Explainability (Cells 42–47)
1. Run Cell 43 (`calculate_latency_regret`). Computes relative latency regret against the Oracle best feasible store.
2. Set `RUN_SHAP = True` in Cell 4 and run Cell 45. Generates `results/figures/shap_summary.png`.
3. Run Cell 47 (`recommend_database`). Tests two-stage inference on a new workload profile.

### Step 8: Export Experiment Artifacts (Cells 54–57)
1. Run Cells 55–57 to package all raw runs, processed CSVs, trained models, and figures into `NoSQL_RAG_Research_Artifacts.zip`.
