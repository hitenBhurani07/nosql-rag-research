# Final Experiment Matrix & Workload Design

## 1. Workload Dimensions and Ranges Currently Implemented

The operational workload generator (`src/nosql_rag/workloads/generator.py`) implements a parameterized workload space:

| Dimension | Implemented Values | Description |
| --- | --- | --- |
| **`query_type`** | `key_value_crud`, `document_crud`, `wide_column_crud` | Core operational access pattern |
| **`read_ratio`** | `0.20`, `0.50`, `0.80`, `0.95` | Proportion of reads vs. updates ($W = 1.0 - R$) |
| **`payload_bytes`** | `128`, `512`, `2048`, `8192` | Payload size in bytes |
| **`dataset_records`**| `500`, `1000`, `2000` | Working set size (number of seeded records) |
| **`data_size_mb`** | Computed: $(\text{records} \times \text{payload}) / 1024^2$ | Dataset working footprint in megabytes |
| **`concurrency`** | `1`, `4` (pilot/full), expandable to `8` | Parallel client worker threads |
| **`n_operations`** | `250` (pilot), `1500` (full) | Measured operations per benchmark run |
| **`warmup_ops`** | `20` | Unmeasured pre-benchmark warm-up operations |

---

## 2. Rigorous Sample Size Distinction

A central contribution of this research audit is strictly distinguishing:
- **Independent Workload Profiles ($N_{\text{profiles}}$):** The number of distinct feature vectors $(X_i)$ entering model training.
- **Database Benchmark Configurations ($N_{\text{configs}}$):** $N_{\text{profiles}} \times N_{\text{databases}}$.
- **Benchmark Execution Runs ($N_{\text{runs}}$):** $N_{\text{configs}} \times N_{\text{repetitions}}$.

---

## 3. Evaluated Experiment Matrix Options

### Option A: The Current 75-Profile Matrix (Recommended Pilot-to-Intermediate Benchmark)
- **Distinct Independent Profiles:** $75$
- **Candidate Databases per Profile:** $4$ (`Redis`, `MongoDB`, `Cassandra`, `Neo4j`)
- **Benchmark Configurations:** $75 \times 4 = 300$
- **Repetitions per Configuration:** $3$
- **Total Operational CRUD Runs:** $300 \times 3 = 900$ runs
- **Estimated Execution Time:** ~45–60 minutes in Google Colab (assuming ~3–4 seconds per 1500-op run in batches of 5).
- **Statistical Assessment:** With $N = 75$ independent profiles, a 75/25 split yields 56 training workloads and 19 testing workloads. Across 3 dominant winning classes (`Redis`, `MongoDB`, `Cassandra`), this provides ~18 samples per class. Suitable for pilot verification and initial model training.

### Option B: The 180-Profile Expanded Matrix (Full Academic Dissertation Matrix)
- **Distinct Independent Profiles:** $180$ (Full factorial of 3 query types $\times$ 5 read ratios $\times$ 4 payload sizes $\times$ 3 concurrency levels).
- **Benchmark Configurations:** $180 \times 4 = 720$
- **Repetitions per Configuration:** $3$
- **Total Operational CRUD Runs:** $720 \times 3 = 2,160$ runs
- **Estimated Execution Time:** ~3.0–3.5 hours in Google Colab.
- **Statistical Assessment:** Yields 135 training workloads and 45 testing workloads (~45 samples per class). Provides high power for Random Forest and Gradient Boosting without sample starvation.

### Option C: The Phase 10 Pre-Flight Pilot Matrix (Mandatory First Step)
- **Distinct Independent Profiles:** $2$ (`P0001`: read-heavy 512B KV, `P0002`: write-heavy 2048B Document).
- **Candidate Databases per Profile:** $4$
- **Repetitions per Configuration:** $1$
- **Total Runs:** $2 \times 4 \times 1 = 8$ runs
- **Operations per Run:** $250$
- **Estimated Execution Time:** ~2–3 minutes.
- **Objective:** Pure system mechanics validation (network handshake, schema creation, seeding, timing, latency percentiles, error rate, cleanup).

---

## 4. Final Experiment Matrix Lock

To balance scientific defensibility with practical execution limits in Google Colab:

| Stage | Independent Profiles ($N$) | Engines per Profile | Repetitions | Total Executions | Operations / Run | Est. Duration | Purpose |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Pre-Flight Pilot** | **2** | 4 | 1 | **8** | 250 | ~2 mins | Verify connectivity, timeouts, schema, and cleanup |
| **Vector Pilot** | **1** | 1 (Qdrant) | 1 | **1** | 2000 vectors / 100 queries | ~1 min | Verify Qdrant HNSW and Recall@K calculation |
| **RAG Pilot** | **1** | 1 (Qdrant) | 1 | **1** | 50 queries (SciFact) | ~3 mins | Verify BEIR download, MiniLM encoding, and IR metrics |
| **Primary CRUD Matrix** | **75** | 4 | 3 | **900** | 1500 | ~50 mins | Primary benchmark for model training & regret evaluation |
| **Expanded CRUD Matrix (Optional)** | **180** | 4 | 3 | **2,160** | 1500 | ~3.5 hours | High-resolution sensitivity analysis for publication |
