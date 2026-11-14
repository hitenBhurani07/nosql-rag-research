# Research Final Report: ML-Driven NoSQL Pattern Selection for RAG Workloads

**Author**: Hiten Bhurani  
**Date**: November 2026  
**Repository**: `C:\Users\hiten\nosql-rag-research`  
**Hardware Environment**: Microsoft Windows 11 Home Single Language (Build 26300, 64-bit), Intel Core i5-12500H (12 physical cores, 16 threads), 16 GB Physical RAM, NVMe SSD, Python 3.12.13 (uv environment) / Python 3.14.0 (host), Docker Desktop with WSL2 capped at 3 GB memory.  

---

## Executive Summary

Retrieval-Augmented Generation (RAG) architectures exhibit heterogeneous data access patterns across operational memory, passage indexing, structured entity relationships, and dense vector similarity search. Selecting an inappropriate database backend introduces avoidable latency penalties and resource inefficiencies.

This research project designs, implements, and experimentally validates an **end-to-end ML-driven NoSQL pattern selector** for RAG operational workloads, accompanied by dedicated vector retrieval evaluation on Qdrant and graph traversal on Neo4j.

### Key Milestones & Findings
1. **Flawed Measurement Path Uncovered & Resolved**:
   - Host-based loopback port forwarding on Windows WSL2 introduced socket queueing overhead and ~40 ms stalls on payloads $\ge 4\text{ KB}$ (hypothesized to be WSL2 hypervisor TCP segmentation and delayed-ACK buffering on multi-segment frames).
   - This network artifact flipped the ground-truth P95 latency winner on **42.67% of workloads** (64 / 150 profiles).
   - Replaced host execution with a pinned in-container compose-network client (`nosql-rag-client:1.0`), unlocking true sub-millisecond local NVMe latencies across all engines.
2. **$c=4$ Concurrency Validity Verification**:
   - Multi-threaded execution in Python suffered an 80.64% queueing overhead under concurrent load due to GIL and single-process event contention.
   - Refactored the benchmark engine to process-based multiprocessing (`spawn` context), increasing $c=4$ throughput by **4.25x** (4,580 $\rightarrow$ 19,490 ops/s) and dropping Redis P95 latency from 1.375 ms to 0.266 ms.
3. **Execution of 1,356 In-Container Genuine Benchmark Runs**:
   - **Redis**: 450 runs (150 profiles $\times$ 3 reps, 0 errors, median P50: 0.090 ms, P95: 0.175 ms).
   - **MongoDB**: 450 runs (150 profiles $\times$ 3 reps, 0 errors, median P50: 0.296 ms, P95: 0.584 ms).
   - **Cassandra**: 228 runs (76 profiles $\times$ 3 reps, 0 errors, median P50: 0.613 ms, P95: 1.133 ms).
   - **Neo4j**: 228 runs (76 profiles $\times$ 3 reps, 0 errors, median P50: 0.902 ms, P95: 3.269 ms).
4. **Empirical Distribution & Machine Learning Evaluation**:
   - In pure single-key CRUD access, in-memory Redis naturally outperforms document, wide-column, and property graph stores across nearly all tested configurations (149/150 wins in 2-engine, 76/76 in 4-engine).
   - Because the held-out test sets contain a single class (`Redis`), the 1.0000 Test Accuracy and Macro-F1 scores are degenerate: the ML models only match the majority baseline, and there is no learnable multi-class signal in single-key CRUD.
   - Unanimous 3-repetition winner stability: **98.67%** (2-engine) and **100.00%** (4-engine).
   - Regret analysis: Defaulting to Redis incurs 0.00% latency regret vs Oracle. Single-store alternatives incur severe latency penalties: MongoDB incurs +206.82% regret, Cassandra +576.10%, and Neo4j +1,770.67%.
5. **Full RAG Passage Retrieval & Vector Search (BEIR SciFact)**:
   - Evaluated all 300 test queries of BEIR SciFact on Qdrant: **Recall@10 = 0.7833**, **NDCG@10 = 0.6451**, **MRR = 0.6047**, with P50 search latency of 15.32 ms (host-path, not comparable to in-container CRUD latencies).
   - Native Qdrant ANN search achieved **100.0% Recall@10** on 2,000 vectors with P50 latency of 15.07 ms (host-path, not comparable).

---

## 1. Experimental Methodology & Network Diagnostic Resolution

### 1.1 The Windows Port-Forwarding Stall Hypothesis & Evidence
Initial benchmarks executed from the Windows host against Docker forwarded ports (`127.0.0.1:PORT`) exhibited severe latency anomalies:
- Cassandra writes stalled at **48.0 ms** for payloads $\ge 4\text{ KB}$, whereas payloads $\le 2\text{ KB}$ ran at 15.5 ms.
- Read latencies remained flat at 15.5 ms regardless of payload size.

```text
Payload Sweep (Cassandra Host-Measured, c=1):
Payload Size | Write P50 (ms) | Write P95 (ms) | Read P50 (ms) | Read P95 (ms)
128 B        | 15.457         | 22.095         | 15.590        | 16.302
512 B        | 15.448         | 16.110         | 15.557        | 19.963
1024 B       | 15.436         | 16.257         | 15.480        | 16.285
2048 B       | 15.626         | 24.427         | 15.586        | 22.079
4096 B       | 47.924         | 57.360         | 15.533        | 22.621
8192 B       | 48.012         | 59.978         | 15.590        | 16.654
```

To diagnose whether this was engine cost or network infrastructure, internal server diagnostics were queried:
```text
docker exec nosql-rag-cassandra nodetool proxyhistograms
Percentile       Read Latency      Write Latency      Range Latency   CAS Read Latency  CAS Write Latency View Write Latency
                     (micros)           (micros)           (micros)           (micros)           (micros)           (micros)
50%                    179.00             258.00            1109.00               0.00               0.00               0.00
75%                    215.00             310.00            1916.00               0.00               0.00               0.00
95%                    924.00            2299.00            3973.00               0.00               0.00               0.00
98%                   1916.00            2759.00            3973.00               0.00               0.00               0.00
99%                   2299.00            3311.00            3973.00               0.00               0.00               0.00
Min                     30.00              30.00             373.00               0.00               0.00               0.00
Max                   2759.00            5722.00            3973.00               0.00               0.00               0.00
```
Cassandra's internal storage engine required a median of only **$258\,\mu\text{s}$ (0.258 ms)** for writes. The remaining **~47.7 ms** measured by the host client was identified as an artifact of host-to-container port forwarding. The working hypothesis is that Windows WSL2 hypervisor loopback relaying introduces packet segmentation and delayed-ACK buffering on multi-segment TCP frames ($> 1,460\text{ B}$).

### 1.2 Pinned In-Container Benchmark Architecture
To eliminate host virtualization artifacts, all benchmarks were transitioned to an internal compose-network client:
- Pinned image `nosql-rag-client:1.0` (Debian Linux, Python 3.11, driver versions pinned).
- Direct container-to-container communication over bridge network `nosql-rag-research_default`.
- Client limits: `cpus=2.0`, `mem=1024m`.
- Result: 8KB Cassandra writes dropped from **48.0 ms to 0.491 ms (a 98x speedup)**, confirming that server-side write latency (median 258 $\mu$s in `nodetool proxyhistograms`) was never the bottleneck.

### 1.3 Concurrency Validity Verification ($c=4$: Threading vs. Multiprocessing)
To test whether client concurrency was bottlenecked by Python's Global Interpreter Lock (GIL), a 10-workload sweep at $c=4$ was performed comparing `ThreadPoolExecutor` with a dedicated `multiprocessing` worker pool:

| Workload ID | Threaded P50 (ms) | Multiprocess P50 (ms) | Threaded P95 (ms) | Multiprocess P95 (ms) | P95 Difference (%) | Threaded Throughput (ops/s) | Multiprocess Throughput (ops/s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **W0002** | 0.743 | 0.146 | 1.366 | 0.271 | -80.2% | 4,407 | 17,703 |
| **W0004** | 0.724 | 0.152 | 1.269 | 0.302 | -76.2% | 5,006 | 19,321 |
| **W0006** | 0.803 | 0.135 | 1.613 | 0.288 | -82.2% | 4,385 | 21,502 |
| **W0008** | 0.735 | 0.128 | 1.300 | 0.247 | -81.0% | 4,676 | 22,464 |
| **W0010** | 0.812 | 0.125 | 1.633 | 0.242 | -85.2% | 3,930 | 20,920 |
| **W0012** | 0.723 | 0.120 | 1.344 | 0.240 | -82.2% | 4,610 | 22,794 |
| **W0014** | 0.705 | 0.133 | 1.322 | 0.272 | -79.4% | 5,041 | 21,417 |
| **W0016** | 0.717 | 0.141 | 1.222 | 0.279 | -77.1% | 4,727 | 14,037 |
| **W0018** | 0.746 | 0.152 | 1.388 | 0.283 | -79.6% | 4,140 | 14,422 |
| **W0020** | 0.729 | 0.120 | 1.294 | 0.239 | -81.6% | 4,876 | 20,323 |
| **Mean** | **0.744** | **0.135** | **1.375** | **0.266** | **-80.64%** | **4,580** | **19,490** |

Multiprocessing eliminated single-process socket serialization, reducing P95 latency by 80.64% and multiplying throughput 4.25x. Multiprocessing was consequently deployed across all engines for $c > 1$.

### 1.4 Methodology Finding: 42.67% Ground-Truth Label Flip Rate
Evaluating all 150 matched profiles revealed that host-based measurements flipped the ground truth winner on **64 out of 150 workloads (42.67%)**:
- **Host Pilot Labels**: Redis: 85 (56.7%), MongoDB: 65 (43.3%).
- **In-Container Genuine Labels**: Redis: 149 (99.3%), MongoDB: 1 (0.7%).
- **Mechanism (Hypothesis)**: Host port proxying across the Windows/WSL2 boundary imposed socket queueing overhead per operation. On $c=1$ read workloads, this delay masked Redis's raw memory-speed advantage (~0.08 ms P50, ~0.16 ms P95) and created artificial wins for MongoDB. Under direct network evaluation, Redis consistently prevailed.
- **Quarantine Action**: The earlier 900 host-path runs were reclassified as `data_provenance = 'host_port_forward_pilot'` and excluded from ML training.

---

## 2. Experimental Data Collection (Genuine In-Container Matrix)

Strict memory scheduling was enforced: exactly **one database container active at a time**, preceded by free RAM checks and followed by immediate container shutdown.

### 2.1 Genuine In-Container Run Summary
A total of **1,356 genuine benchmark runs** were executed with 0 errors (100% success rate):

| Database Engine | Version | Target Workloads | Target Repetitions | Completed Runs | Error Count | Memory Limit | Median P50 (ms) | Median P95 (ms) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Redis** | `7.4-alpine` | 150 | 3 | 450 | 0 | 256 MB | 0.090 | 0.175 |
| **MongoDB** | `7.0` | 150 | 3 | 450 | 0 | 1,024 MB | 0.296 | 0.584 |
| **Cassandra** | `4.1` | 76 | 3 | 228 | 0 | 1,536 MB | 0.613 | 1.133 |
| **Neo4j** | `5.26-community` | 76 | 3 | 228 | 0 | 1,024 MB | 0.902 | 3.269 |

### 2.2 Performance by Concurrency Level
```text
Database   | Concurrency | Median P50 (ms) | Median P95 (ms) | Mean Error Rate | Genuine Runs
------------------------------------------------------------------------------------------
Redis      | c=1         | 0.081           | 0.162           | 0.00%           | 225
Redis      | c=4         | 0.098           | 0.196           | 0.00%           | 225
MongoDB    | c=1         | 0.259           | 0.449           | 0.00%           | 225
MongoDB    | c=4         | 0.330           | 0.716           | 0.00%           | 225
Cassandra  | c=1         | 0.580           | 0.922           | 0.00%           | 114
Cassandra  | c=4         | 0.656           | 1.402           | 0.00%           | 114
Neo4j      | c=1         | 0.760           | 2.858           | 0.00%           | 114
Neo4j      | c=4         | 0.979           | 3.733           | 0.00%           | 114
```

### 2.3 Repetition Agreement & Median Absolute Gaps
- **3-Repetition Unanimous Winner Stability**:
  - 2-Engine Matrix (150 profiles): **98.67%** (148 / 150 workloads had identical winners across all 3 reps).
  - 4-Engine Matrix (76 profiles): **100.00%** (76 / 76 workloads had identical winners across all 3 reps).
- **Median Absolute P95 Gaps**:
  - $|\text{Redis} - \text{MongoDB}|$: **0.362 ms**
  - $|\text{Redis} - \text{Cassandra}|$: **0.960 ms**
  - $|\text{Redis} - \text{Neo4j}|$: **3.039 ms**
  - $|\text{MongoDB} - \text{Cassandra}|$: **0.513 ms**

---

## 3. Dual Machine Learning & Empirical Analysis

Per research guidelines, two analyses were executed independently and never combined:
1. **Analysis A**: 2 engines (Redis, MongoDB) across 150 profiles.
2. **Analysis B**: 4 engines (Redis, MongoDB, Cassandra, Neo4j) across 76 profiles (first 38 base workloads $\times c=1, 4$).

Feature sets excluded never-varied attributes (`vector_dimensions`, `top_k`, `graph_depth`, `consistency_requirement`). Predictive features were strictly limited to operational attributes: `query_type`, `read_ratio`, `write_ratio`, `payload_bytes`, `dataset_records`, `data_size_mb`, and `concurrency`. Leakage-safe grouped train/test splitting was enforced via `base_workload_id`.

### 3.1 Model Performance Comparison (Held-Out Test Sets)

| Dataset | Model Architecture | Test Accuracy | Test Macro-F1 | Mean CV Macro-F1 |
| :--- | :--- | :---: | :---: | :---: |
| **Analysis A** (2 Engines, 150 Profiles) | **Majority Baseline (Redis)** | **1.0000** | **1.0000** | 1.0000 |
| | Decision Tree | 1.0000 | 1.0000 | 0.9917 ($\pm 0.0167$) |
| | Random Forest | 1.0000 | 1.0000 | 1.0000 ($\pm 0.0000$) |
| | Gradient Boosting | 1.0000 | 1.0000 | 1.0000 ($\pm 0.0000$) |
| **Analysis B** (4 Engines, 76 Profiles) | **Majority Baseline (Redis)** | **1.0000** | **1.0000** | 1.0000 |
| | Decision Tree | 1.0000 | 1.0000 | 1.0000 ($\pm 0.0000$) |
| | Random Forest | 1.0000 | 1.0000 | 1.0000 ($\pm 0.0000$) |
| | Gradient Boosting | 1.0000 | 1.0000 | 1.0000 ($\pm 0.0000$) |

> **Degenerate Classifier Evaluation Note**: In both Analysis A and Analysis B, the held-out test sets contain a single class (`Redis`). Consequently, the 1.0000 Test Accuracy and Macro-F1 scores are mathematically degenerate: the trained machine learning models merely match the majority-class baseline. Because in-memory Redis uniformly dominates disk-backed and distributed engines across all single-key configurations, there is **no learnable multi-class signal** in scalar CRUD workloads.

### 3.2 Latency Regret Analysis vs. Baselines & Oracle

Latency regret measures the relative latency penalty incurred when deploying an engine relative to the Oracle:
$$\text{Regret}(W) = \frac{\text{Latency}_{\text{selected}}(W) - \text{Latency}_{\text{oracle}}(W)}{\text{Latency}_{\text{oracle}}(W)}$$

#### Analysis A (2 Engines, 150 Profiles, 30 Test Workloads):
```text
Strategy                         | Mean Regret | Median Regret | P95 Regret
---------------------------------------------------------------------------
Oracle Best                      |   0.00%     |   0.00%       |   0.00%
Majority Baseline (Redis)        |   0.00%     |   0.00%       |   0.00%
ML Recommender (Random Forest)   |   0.00%     |   0.00%       |   0.00%
Always-Redis                     |   0.00%     |   0.00%       |   0.00%
Always-MongoDB                   | 206.82%     | 211.80%       | 310.06%
```

#### Analysis B (4 Engines, 76 Profiles, 16 Test Workloads):
```text
Strategy                         | Mean Regret | Median Regret | P95 Regret
---------------------------------------------------------------------------
Oracle Best                      |   0.00%     |   0.00%       |   0.00%
Majority Baseline (Redis)        |   0.00%     |   0.00%       |   0.00%
ML Recommender (Random Forest)   |   0.00%     |   0.00%       |   0.00%
Always-Redis                     |   0.00%     |   0.00%       |   0.00%
Always-MongoDB                   | 264.39%     | 246.10%       | 431.23%
Always-Cassandra                 | 576.10%     | 604.25%       | 718.46%
Always-Neo4j                     | 1770.67%    | 1611.69%      | 2644.25%
```

### 3.3 Empirical Takeaway on Class Diversity & Operational CRUD
In single-key CRUD workloads, an in-memory key-value engine (Redis) consistently dominates disk-backed and distributed engines. When measured accurately without host network distortions, class diversity in single-key CRUD is non-existent (test sets contain exclusively the Redis class, producing degenerate 1.0000 metrics where models only replicate the majority baseline with no learnable multi-class signal). Rather than synthesizing artificial workloads or tuning parameters to force diversity, this research plainly reports this as an authoritative empirical finding:
* **Recommendation for Single-Key RAG Operational State**: Defaulting to Redis incurs 0.00% latency regret. Deploying MongoDB adds 2.06x latency overhead, Cassandra adds 5.76x overhead, and Neo4j adds 17.7x overhead.
* **Workload Specialization Boundary**: Database differentiation occurs along access pattern dimensions beyond single-key CRUD—specifically range scans, secondary index filtering, graph traversal, and high-dimensional vector search.

---

## 4. Specialized Workload Evaluation: Vector Retrieval & Graph Traversal

### 4.1 Full BEIR SciFact RAG Retrieval Benchmark (All 300 Queries)
Qdrant was benchmarked on the complete biomedical claim verification benchmark (BEIR SciFact):
- **Corpus**: 5,183 scientific abstracts.
- **Encoder**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, cosine distance).
- **Test Queries Evaluated**: All 300 benchmark queries (`max_queries=None`).
- **Information Retrieval Metrics**:
  - **Recall@10**: **0.7833**
  - **NDCG@10**: **0.6451**
  - **MRR**: **0.6047**
- **Query Latencies** *(measured from host client; labeled as host-path, not comparable to in-container CRUD latencies)*:
  - **P50 Query Latency**: **15.32 ms**
  - **P95 Query Latency**: **27.44 ms**

### 4.2 Native Vector Indexing (Qdrant ANN)
- **Dataset**: 2,000 synthetic 128-dimensional dense vectors, top-$k=10$.
- **Exact Search Recall@10**: **1.0000 (100.0%)**
- **Search Latencies** *(host-path, not comparable to in-container CRUD latencies)*:
  - **P50 Latency**: **15.07 ms** | **P95 Latency**: **26.88 ms**

### 4.3 Graph Traversal (Neo4j)
To capture graph-native access patterns not represented in scalar CRUD, multi-hop neighbor traversal was evaluated:
- **Graph Topology**: 200 nodes, 600 edges.
- **Workload**: 100 queries at 2-hop traversal depth (`traverse_neighbors`).
- **Throughput**: 270.4 ops/sec.
- **P50 Latency**: **2.99 ms** | **P95 Latency**: **4.09 ms** | **P99 Latency**: **22.97 ms**.

---

## 5. Demarcation of Flawed Host Pilot Results

To ensure scientific reproducibility and historical transparency, earlier host-path results are catalogued below as pilot data from a flawed measurement path:

```text
Historical Flawed Host-Path Pilot Results (DO NOT USE FOR PRODUCTION):
- Data Provenance Tag: host_port_forward_pilot (900 rows in data/raw/crud_benchmark_runs.csv)
- Host Cross-Validation Macro-F1: 0.8245 (flawed due to 42.67% label error from host proxy latency)
- Host Latency Regret: 4.33% (flawed due to artificial MongoDB wins)
- Root Cause Hypothesis: Windows WSL2 port-forwarding relay buffering multi-segment TCP frames.
```

---

## 6. Limitations & Scope

1. **Single-Node Execution**: Client and database containers operated on the same physical host across an internal Docker bridge network. While this eliminated Windows virtualization artifacts, it did not model multi-node distributed replication, inter-datacenter WAN latency, or network partition behavior.
2. **Sequential Container Execution**: To strictly respect the 3 GB WSL2 memory cap on a 16 GB host, engines were benchmarked sequentially. Concurrent resource contention between multiple active database engines was not evaluated.
3. **Sub-Millisecond Sensitivity**: When latencies operate below 1 ms, driver socket serialization and serialization formats (BSON vs. RESP vs. CQL vs. Bolt) represent substantial fractions of total elapsed time.
4. **CRUD Pattern Scope**: Workloads were restricted to single-key point reads and updates. Patterns where Cassandra (high-throughput append logging) or MongoDB (flexible document filtering) offer architectural advantages require multi-field or range-scan query definitions.
5. **Untuned Default Configurations with Constrained JVM Heaps**: Both Cassandra and Neo4j operated with default, untuned database settings and constrained 512 MB JVM heaps (`MAX_HEAP_SIZE=512M`, `HEAP_NEWSIZE=128M` for Cassandra; initial/max heap `512M`, pagecache `128M` for Neo4j) to respect the tight WSL2 memory cap. In production deployments, multi-gigabyte heaps, OS page-cache caching, and specialized engine tuning will alter absolute latencies and throughput ceilings.
6. **Small-Scale Graph Topology**: The Neo4j graph traversal evaluation was performed on a synthetic demonstration graph of 200 nodes and 600 edges. Real-world RAG knowledge graphs often encompass millions of entities and relationships, where index-free adjacency provides more pronounced performance divergence relative to relational or document stores.

---

## 7. Verification & Reproducibility

```powershell
# 1. Run unit test suite (44 tests)
uv run pytest tests/unit -q

# 2. Check code style and formatting
uv run ruff check .

# 3. View benchmark progress and status
uv run python scripts/audit_crud_matrix.py

# 4. Re-run dual ML and regret evaluation
uv run python scripts/run_dual_evaluation.py
```
