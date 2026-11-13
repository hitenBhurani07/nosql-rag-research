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

In the Google Colab left sidebar, open the **Key icon (Secrets)** and define the following secrets. Set **Notebook access** to **ON** for each:

| Colab Secret Name | Required for Live Integrations | Description | Example / Target Format |
| --- | --- | --- | --- |
| `REDIS_URL` | **Yes (Redis Cloud)** | Redis Cloud TLS connection URI | `rediss://default:<password>@profit-cook-stitch-74158.db.redis.io:18690/0` |
| `MONGODB_URI` | **Yes (MongoDB Atlas)** | MongoDB Atlas connection string | `mongodb+srv://rag_research:<password>@cluster0.hqd8wfk.mongodb.net/?retryWrites=true&w=majority` |
| `MONGODB_DATABASE` | Optional | Database name (defaults to `nosql_rag_research`) | `nosql_rag_research` |
| `CASSANDRA_MODE` | **Yes (DataStax Astra)** | Cassandra mode | `astra` |
| `CASSANDRA_KEYSPACE` | **Yes (DataStax Astra)** | Cassandra keyspace name | `nosql_rag_research` |
| `CASSANDRA_SECURE_CONNECT_BUNDLE_PATH` | **Yes (DataStax Astra)** | Local path to staged SCB ZIP | `/tmp/astra_scb/secure-connect-bundle.zip` |
| `CASSANDRA_APPLICATION_TOKEN` | **Yes (DataStax Astra)** | Astra token with DB Administrator role | `AstraCS:xxxx` |
| `NEO4J_URI` | *Pending Stage 2* | Neo4j AuraDB Bolt URI | `neo4j+s://xxxx.databases.neo4j.io` |
| `NEO4J_USERNAME` | *Pending Stage 2* | Neo4j username (`neo4j`) | `neo4j` |
| `NEO4J_PASSWORD` | *Pending Stage 2* | Neo4j password | `<neo4j_password>` |
| `NEO4J_DATABASE` | *Pending Stage 2* | Neo4j database (default `neo4j`) | `neo4j` |
| `QDRANT_URL` | *Pending Stage 2* | Qdrant Cloud cluster endpoint | `https://xxxx.cloud.qdrant.io:6333` |
| `QDRANT_API_KEY` | *Pending Stage 2* | Qdrant API key | `<qdrant_api_key>` |

> [!IMPORTANT]
> - Never write passwords, tokens, or URIs directly in notebook cells.
> - Ensure the **Notebook access** toggle switch is flipped to **ON** for each secret in Colab.
> - Unconfigured engines (`NEO4J`, `QDRANT`) are cleanly recognized as `SKIPPED` during connection verification without blocking the three live engines.

---

## 3. Pre-Flight Execution Workflow

### Step 1: Initialize Runtime (Cells 0–11)
1. Run Cell 4 (`Runtime setup and experiment controls`).
   - Default flags keep all expensive runs OFF:
     - `RUN_SMOKE_TEST = True` (Database-independent pipeline test)
     - `RUN_CONNECTION_CHECKS = False` (Set to `True` when ready to test live connections)
     - `RUN_PILOT = False`
     - `RUN_FULL_MATRIX = False`
     - `RUN_QDRANT_ANN_PILOT = False`
     - `RUN_BEIR_RAG = False`
     - `RUN_ML_TRAINING = False`
     - `RUN_SHAP = False`
2. Run Cell 8 (`USE_GOOGLE_DRIVE = True`). Mounts Google Drive to `/content/drive/MyDrive/NoSQL_RAG_Research` for persistent storage across Colab restarts.
3. Run Cell 10 to securely bootstrap the repository and install dependencies:
   - If `/content/nosql-rag-research` does not exist, it clones freshly from `origin/main`.
   - If it already exists, it executes `git fetch origin` followed by `git pull --ff-only origin main` to guarantee the latest code is active.
   - Verifies and prints the checked-out commit SHA and latest commit log.
   - For private repositories: Reads `GITHUB_TOKEN` from Colab Secrets and uses an ephemeral `GIT_ASKPASS` helper (never prints or saves tokens).
   - Installs package using editable mode: `pip install -q -e ".[all]"`.
   - *Note on open notebooks:* A previously opened Colab browser tab will not auto-reload newly pushed `.ipynb` cell definitions. To load new cells, use **File -> Open notebook -> GitHub** to reload `NoSQL_RAG_Implementation_Colab.ipynb`, or refresh the browser.
4. Run Cell 11 to import core Python packages.

### Step 2: Discover Colab Public IP for MongoDB Atlas Allowlisting (Cells 12–13)
1. Run Cell 13.
2. It fetches Colab's public IPv4 via `https://api.ipify.org` and formats the CIDR notation `<COLAB_PUBLIC_IP>/32`.
3. In MongoDB Atlas console -> **Network Access** -> **Add IP Address**, paste `<COLAB_PUBLIC_IP>/32` (or allow `0.0.0.0/0` temporarily with short TTL during active experiments).

### Step 3: Stage Astra DB Secure Connect Bundle (Cells 14–15)
1. In DataStax Astra DB console -> Database `nosql_rag_research` -> **Connect** -> download `secure-connect-nosql-rag-research.zip`.
2. Run Cell 15. An interactive upload widget opens (`google.colab.files.upload()`).
3. Select your local `.zip` bundle.
4. Cell 15 stages it to `/tmp/astra_scb/secure-connect-bundle.zip`, validates ZIP structure and internal Astra markers (`config.json`, `cqlshrc`, or `identity.jks`), enforces `0700`/`0600` permissions, and ensures it is never extracted or committed to Git/Drive.

### Step 4: Validate Configuration and Verify Connections (Cells 16–25)
1. Run Cell 17. Calls `validate_runtime_configuration(db_config)` to inspect Redis, MongoDB, and Astra configurations safely.
2. In Cell 4, set `RUN_CONNECTION_CHECKS = True`.
3. Run Cell 25. Executes live TCP/TLS and authentication handshakes to Redis, MongoDB, and Cassandra (Astra DB). Unconfigured engines (Neo4j, Qdrant) safely report `SKIPPED`.
4. Output format:
   ```text
   REDIS       CONNECTED / FAILED
   MONGODB     CONNECTED / FAILED
   CASSANDRA   CONNECTED / FAILED
   NEO4J       SKIPPED
   QDRANT      SKIPPED

   Required initial integrations: 3
   Successful live connections: <actual count>
   Failed live connections: <actual count>
   Skipped unconfigured services: 2
   ```

### Step 5: Run Database-Independent Smoke Test (Cells 26–27)
- Run Cell 27 (`RUN_SMOKE_TEST = True`).
- Offline gate: Tests CLI help invocation, experiment configuration loading, synthetic demo data generation (`data_provenance=synthetic_demo`), and dataset validator without requiring any live database connections.

### Step 6: Run Pre-Flight Pilot Benchmark (Cells 28–33)
1. In Cell 4, set `RUN_PILOT = True`.
2. Run Cells 29–33.
   - Executes 2 workload profiles $\times$ available CRUD engines = pilot test runs (250 operations each).
   - Expected output file: `data/raw/crud_benchmark_runs.csv`.
   - Verifies that cleanup drops temporary benchmark tables/collections.

### Step 7: Run Vector & RAG Pilots (Cells 54–57)
1. When Qdrant Cloud is provisioned, set `RUN_QDRANT_ANN_PILOT = True` in Cell 4 and run Cell 55.
   - Seeds 2,000 vectors (128-d) and runs 100 ANN queries.
   - Verifies HNSW collection creation, query latency, and Recall@K calculation against exact brute-force search.
2. Set `RUN_BEIR_RAG = True` in Cell 4 and run Cell 57.
   - Evaluates BEIR SciFact retrieval metrics (Recall@10, NDCG@10, MRR).

### Step 8: Execute Full Matrix Benchmark (Cells 34–35)
1. Once the pilot passes cleanly, set `RUN_FULL_MATRIX = True` in Cell 4.
2. Run Cell 35.
   - Executes workload profiles across engines $\times$ 3 repetitions in controlled batches.
   - Automatically appends results to `data/raw/crud_benchmark_runs.csv`.
   - **Resume support:** If runtime disconnects, re-running Cell 35 checks existing successful runs and resumes pending configurations.

### Step 9: Data Validation & ML Training (Cells 36–47)
1. Run Cell 37 (`validate_raw_runs`). Ensures zero duplicate runs, correct latency ordering ($p50 \le p95 \le p99$), and acceptable error rates ($\le 1\%$).
2. Run Cell 39 (`derive_best_store_labels`). Aggregates median metrics and derives winning `best_store` labels. Output: `data/processed/labelled_workloads.csv`.
3. Set `RUN_ML_TRAINING = True` in Cell 4 and run Cells 41–47.
   - Partitions profiles using leakage-safe `GroupShuffleSplit` (grouped by `workload_id`).
   - Fits Decision Tree, Random Forest, and Gradient Boosting.
   - Saves the best model to `results/models/best_nosql_recommender.joblib`.

### Step 10: Regret Evaluation & Explainability (Cells 48–53)
1. Run Cell 49 (`calculate_latency_regret`). Computes relative latency regret against the Oracle best feasible store.
2. Set `RUN_SHAP = True` in Cell 4 and run Cell 51. Generates `results/figures/shap_summary.png`.
3. Run Cell 53 (`recommend_database`). Tests two-stage inference on a new workload profile.

### Step 11: Export Experiment Artifacts (Cells 60–63)
1. Run Cells 61–63 to package all raw runs, processed CSVs, trained models, and figures into `NoSQL_RAG_Research_Artifacts.zip`.
