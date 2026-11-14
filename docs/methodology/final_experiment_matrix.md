# Final Experiment Matrix & Workload Design

> **Current approved design (2026-11-13): Approach B.** Generate 75 base workloads at
> matched concurrency levels 1 and 4, producing 150 workload profiles. Run each profile
> against Redis, MongoDB, Cassandra, and Neo4j for three repetitions: 600 distinct
> workload-profile/database keys and **1,800 run records**. The two profiles sharing a
> `base_workload_id` must stay in the same ML split. Earlier 900-run and 2,160-run options
> below are historical alternatives and are not the active matrix.

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

## 3. Historical Experiment Matrix Options

The options in this section document prior planning and have been superseded by the
Approach B design stated above.

### Historical Option A: 75 unpaired profiles
- **Distinct Independent Profiles:** $75$
- **Candidate Databases per Profile:** $4$ (`Redis`, `MongoDB`, `Cassandra`, `Neo4j`)
- **Benchmark Configurations:** $75 \times 4 = 300$
- **Repetitions per Configuration:** $3$
- **Total Operational CRUD Runs:** $300 \times 3 = 900$ runs
- **Estimated Execution Time:** ~45–60 minutes in Google Colab (assuming ~3–4 seconds per 1500-op run in batches of 5).
- **Statistical Assessment:** With $N = 75$ independent profiles, a 75/25 split yields 56 training workloads and 19 testing workloads. Across 3 dominant winning classes (`Redis`, `MongoDB`, `Cassandra`), this provides ~18 samples per class. Suitable for pilot verification and initial model training.

### Historical Option B: 180 unpaired profiles
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

## 4. Current Experiment Matrix Lock

The approved primary matrix is Approach B. The expected run count is 75 base workloads x
2 matched concurrency levels x 4 CRUD databases x 3 repetitions = 1,800. These are run
records, not 1,800 independent workloads. There are 75 independent base workload groups
and 150 matched workload profiles.

| Stage | Base groups | Matched profiles | Engines per profile | Repetitions | Total executions | Purpose |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **Pre-Flight Pilot** | 2 pilot workloads | 2 | 4 | 1 | **8** | Verify connectivity, timeouts, schema, and cleanup |
| **Primary CRUD Matrix (Approach B)** | **75** | **150** | **4** | **3** | **1,800** | Train and evaluate the CRUD selector and regret baselines |
| **Qdrant ANN** | Separate track | Separate | 1 (Qdrant) | As recorded | Separate | Vector ANN latency and recall |
| **BEIR SciFact** | Separate track | Separate | 1 (Qdrant) | As recorded | Separate | Retrieval quality and latency |
| **Neo4j graph traversal** | Separate track | Separate | 1 (Neo4j) | As recorded | Separate | Native graph workload evaluation |

Do not treat a three-database run as complete. If MongoDB is unavailable during the
current three-engine pass, preserve that pass and execute only missing MongoDB keys after
connectivity is restored. Reconcile against the latest checkpoint before resuming.
