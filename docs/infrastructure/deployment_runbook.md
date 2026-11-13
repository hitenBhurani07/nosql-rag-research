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
- **Cell 10:** Clones the repository and installs the package via `pip install -q -e ".[all]"`.
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

## 3. Important Experiment Safeguards

1. **Pilot Matrix Barrier:** The 8-run CRUD pilot requires all 4 CRUD engines (Redis, MongoDB, Cassandra, Neo4j). Do NOT enable `RUN_PILOT = True` until Neo4j is provisioned in a subsequent phase.
2. **Qdrant Vector Barrier:** Qdrant ANN and BEIR SciFact experiments require `QDRANT_URL` and `QDRANT_API_KEY`. Keep `RUN_QDRANT_ANN_PILOT = False` and `RUN_BEIR_RAG = False`.
3. **Storage Hygiene:** No database records are created during connection checks. Preflight executes non-destructive pings (`PING`, `ping`, and CQL version lookups).

---

## 4. Post-Experiment Teardown

1. **Ephemeral Bundle Cleanup:**
   ```bash
   rm -rf /tmp/astra_scb
   ```
2. **Atlas IP Allowlist Expiry:**
   - Temporary IP entries in Atlas Network Access expire automatically if configured with a 1–6 hour TTL.
