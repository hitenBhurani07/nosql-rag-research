# Deployment Runbook & Operational Verification

Step-by-step checklist to deploy, preflight, benchmark, and tear down the five-database research environment.

---

## 1. Pre-Deployment Phase (User Responsibility)

Follow [docs/infrastructure/credential_setup_guide.md](file:///c:/Users/hiten/nosql-rag-research/docs/infrastructure/credential_setup_guide.md) to register free accounts and retrieve endpoints:
1. **Redis:** Get `REDIS_URL`.
2. **MongoDB:** Get `MONGODB_URI`.
3. **DataStax Astra:** Download `secure-connect-database.zip` and get `AstraCS:...` token.
4. **Neo4j:** Get `NEO4J_URI` and password.
5. **Qdrant:** Get `QDRANT_URL` and `QDRANT_API_KEY`.

---

## 2. Preflight Health Verification

### Option A: Local Run (via Terminal)
```bash
python scripts/database_preflight.py
```
- Expects: `Summary: 5 Passed, 0 Failed, 0 Skipped.`

### Option B: Google Colab Run
1. Open [notebooks/NoSQL_RAG_Implementation_Colab.ipynb](file:///c:/Users/hiten/nosql-rag-research/notebooks/NoSQL_RAG_Implementation_Colab.ipynb).
2. Upload `secure-connect-database.zip` into `/content/`.
3. Populate Colab Secrets.
4. In Cell 4, set:
   ```python
   RUN_CONNECTION_CHECKS = True
   RUN_SMOKE_TEST = True
   RUN_PILOT = False
   ```
5. Run Cells 0 to 23.
   - Verify Cell 21 shows `connected: True` across all 5 databases.

---

## 3. Benchmarking Execution Sequence

1. **Pre-Flight Pilot:**
   - In Cell 4, set `RUN_PILOT = True`.
   - Run Cells 25–27 (8 runs, 250 ops/run).
   - Verify `data/raw/crud_benchmark_runs.csv` was written and temporary tables were cleaned up.
2. **Vector Pilot:**
   - In Cell 4, set `RUN_QDRANT_ANN_PILOT = True`.
   - Run Cell 49. Confirm Recall@K and latency percentiles are generated.
3. **RAG Validation:**
   - In Cell 4, set `RUN_BEIR_RAG = True`.
   - Run Cell 51. Evaluates BEIR SciFact passage retrieval.
4. **Full Benchmark Matrix (Optional / User-Triggered):**
   - In Cell 4, set `RUN_FULL_MATRIX = True` and `RUN_ML_TRAINING = True`.
   - Run Cell 29 (900 runs in batches of 5).
   - Runs are append-only; resume support prevents duplicate executions on disconnect.

---

## 4. Post-Experiment Teardown

1. **Download Outputs:**
   - Run Cells 55–57 in the notebook to download `NoSQL_RAG_Research_Artifacts.zip`.
2. **Cluster Hibernation:**
   - If not actively querying, Neo4j, Qdrant, and MongoDB will auto-pause.
   - You may pause or delete the free databases in their respective web consoles.
