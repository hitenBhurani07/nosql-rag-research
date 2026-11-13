# Deployment Runbook & Operational Verification

Step-by-step checklist to deploy, preflight, benchmark, and tear down the research database environment.

---

## 1. Current Phase: Three Provisioned Databases (Phase 13.1)

At this stage of the research, three candidate database engines have been provisioned:
1. **Redis Cloud:** Key-Value engine (`profit-cook-stitch-74158.db.redis.io:18690`, AWS Mumbai `ap-south-1`).
2. **MongoDB Atlas:** Document engine (`cluster0.hqd8wfk.mongodb.net`, M0 Free).
3. **DataStax Astra DB:** Wide-Column engine / Cassandra (`nosql_rag_research`, AWS `us-east-2`, DB ID: `0d4339a2-6863-4ac6-bd99-82ae8c984887`).

*Unprovisioned Services:* **Neo4j** and **Qdrant** have not yet been provisioned. They are automatically and safely **SKIPPED** during connection checks without failing execution.

---

## 2. Preflight Health Verification in Google Colab

Follow this sequential workflow in [notebooks/NoSQL_RAG_Implementation_Colab.ipynb](file:///c:/Users/hiten/nosql-rag-research/notebooks/NoSQL_RAG_Implementation_Colab.ipynb):

### Step 1: Open Notebook & Set Safe Flags (Cell 4)
Verify that execution flags remain safe by default:
```python
RUN_SMOKE_TEST = True
RUN_CONNECTION_CHECKS = False   # Set to True only when secrets & bundle are ready
RUN_PILOT = False               # MUST remain False until Neo4j is provisioned
RUN_FULL_MATRIX = False
RUN_QDRANT_ANN_PILOT = False
RUN_BEIR_RAG = False
RUN_ML_TRAINING = False
RUN_SHAP = False
```

### Step 2: Bootstrap Package & Verify Submodules (Cells 10 & 11)
- **Cell 10:** Clones the repository if not present, or runs `git fetch origin` + `git pull --ff-only origin main` if already present, prints the checked-out commit SHA and log, and installs the package via `pip install -q -e ".[all]"`.
  - *Note:* If Colab was already open when GitHub was updated, reload the notebook via **File -> Open notebook -> GitHub** to get updated cell definitions, or re-run Cell 10 to update the underlying code and package.
- **Cell 11:** Verifies imports across all modules (`nosql_rag.adapters`, `nosql_rag.config`, etc.).

### Step 3: Discover Colab Public IP & Allowlist in Atlas (Cell 13)
- Execute **Cell 13**.
- Copy the displayed `Current Colab public IP: <COLAB_IP>`.
- In [MongoDB Atlas Console](https://cloud.mongodb.com/) $\to$ **Security** $\to$ **Network Access** $\to$ **IP Access List**:
  - Click **Add IP Address**.
  - Enter `<COLAB_IP>/32`.
  - (Recommended) Set entry to expire in 1 hour or 6 hours.

### Step 4: Stage DataStax Astra Secure Connect Bundle (Cell 15)
- Execute **Cell 15**.
- A file upload prompt will appear.
- Select your downloaded `secure-connect-nosql-rag-research.zip`.
- The cell validates the archive and stages it into `/tmp/astra_scb/secure-connect-bundle.zip` with permissions `0600`.
- *Note:* `/tmp` is ephemeral. If your runtime restarts, re-run Cell 15.

### Step 5: Configure Colab Secrets (Left Sidebar Key Icon)
Enter secrets per [docs/infrastructure/credential_setup_guide.md](file:///c:/Users/hiten/nosql-rag-research/docs/infrastructure/credential_setup_guide.md):
- `REDIS_URL`
- `MONGODB_URI`
- `MONGODB_DATABASE` (`nosql_rag_research`)
- `CASSANDRA_MODE` (`astra`)
- `CASSANDRA_KEYSPACE` (`nosql_rag_research`)
- `CASSANDRA_APPLICATION_TOKEN` (`AstraCS:...`)
- `CASSANDRA_SECURE_CONNECT_BUNDLE_PATH` (`/tmp/astra_scb/secure-connect-bundle.zip`)

### Step 6: Validate Runtime Configuration (Cell 17)
- Execute **Cell 17**.
- Inspect the output table to verify:
  - Redis: `configured`
  - MongoDB: `configured`
  - Cassandra: `configured`
  - Neo4j: `unconfigured (skipped in Phase 13.1)`
  - Qdrant: `unconfigured (skipped in Phase 13.1)`

### Step 7: Execute Live Connection Verification (Cell 25)
- In Cell 4, set `RUN_CONNECTION_CHECKS = True`.
- Execute **Cell 25**.
- Expected output for the partially provisioned environment:
  ```text
  =================================================================
    NoSQL RAG Research — Live Connection Verification
  =================================================================
  ✅ REDIS        CONNECTED (version: ..., ping: ...ms)
  ✅ MONGODB      CONNECTED (version: ..., ping: ...ms)
  ✅ CASSANDRA    CONNECTED (version: ..., ping: ...ms)
  ⏭️ NEO4J        SKIPPED (credentials not configured)
  ⏭️ QDRANT       SKIPPED (QDRANT_URL not configured)
  =================================================================
  Connection Summary:
  Required initial integrations: 3 (Redis, MongoDB, Cassandra/Astra)
  Successful live connections:   3
  Failed live connections:       0
  Skipped unconfigured services: 2
  =================================================================
  ```
- All diagnostic errors are sanitized; zero passwords, tokens, or URIs will appear in output tables or CSV exports.

---

### Step 8: Execute Pre-Flight Pilot Benchmark (Cell 35)
- When all 4 CRUD databases (Redis, MongoDB, Cassandra, Neo4j) are live and report `CONNECTED`:
  - Set `RUN_PILOT = True` in Cell 4.
  - Run **Cell 35**.
  - Cell 35 runs `verify_crud_pilot_readiness(db_config)` to confirm all 4 engines are CONNECTED before benchmarking.
  - Executes 2 profiles $\times$ 4 engines $\times$ 1 repetition = **8 genuine benchmark runs** (250 operations each, 20 warm-up operations excluded).
  - Appends to `data/raw/crud_benchmark_runs.csv` and displays the full metrics table and summary.
  - Resume support ensures re-running skips already-successful runs.

### Step 9: Isolated Vector and Graph Pilots (Cells 57, 59, 61)
- **Cell 57 (Qdrant ANN):** `RUN_QDRANT_ANN_PILOT = True` -> evaluates vector recall and query latency (`qdrant_ann_runs.json`).
- **Cell 59 (BEIR SciFact):** `RUN_BEIR_RAG = True` -> evaluates passage retrieval metrics (`beir_scifact_qdrant_results.json`).
- **Cell 61 (Neo4j Graph Traversal):** `RUN_NEO4J_GRAPH_PILOT = True` -> evaluates native $k$-hop traversal (`neo4j_graph_traversal_runs.json`). Results are never mixed into the CRUD dataset.

---

## 3. Important Experiment Safeguards

1. **Pilot Matrix Barrier:** The 8-run CRUD pilot requires all 4 CRUD engines (Redis, MongoDB, Cassandra, Neo4j) to be `CONNECTED`. If any engine is `FAILED` or `SKIPPED`, the readiness gate raises `RuntimeError` and halts execution.
2. **Qdrant Vector Isolation:** Qdrant ANN and BEIR SciFact experiments output to separate JSON files and never pollute `crud_benchmark_runs.csv`.
3. **Neo4j Graph Traversal Isolation:** Native graph traversal is evaluated independently in Cell 61 and persists to `neo4j_graph_traversal_runs.json`.
4. **Storage Hygiene:** Preflight executes non-destructive pings (`PING`, `ping`, CQL version lookups, and Cypher `LIMIT 1` component lookups). Benchmark runs clean up temporary collections/tables automatically when `CLEANUP_AFTER_RUN = True`.

---

## 4. Post-Experiment Teardown

1. **Ephemeral Bundle Cleanup:**
   ```bash
   rm -rf /tmp/astra_scb
   ```
2. **Atlas IP Allowlist Expiry:**
   - Temporary IP entries in Atlas Network Access expire automatically if configured with a 1–6 hour TTL.
