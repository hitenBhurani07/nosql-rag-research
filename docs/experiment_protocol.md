# Experiment Protocol

Formal, reproducible protocol governing database benchmarking, dataset construction, and evaluation for the research project.

---

## 1. Experimental Objectives

1. Quantify operational latency and throughput across diverse NoSQL data models (`key_value_crud`, `document_crud`, `wide_column_crud`).
2. Construct an empirical, labelled workload-to-best-store dataset derived strictly from measured database executions.
3. Train an explainable machine-learning recommender (Decision Tree, Random Forest, Gradient Boosting) using leakage-safe grouped splits.
4. Measure recommendation quality using relative latency regret against an Oracle best feasible engine and baseline selectors.
5. Benchmark high-dimensional vector ANN search on Qdrant and validate end-to-end passage retrieval on BEIR SciFact.

---

## 2. Workload Definitions and Data Model Semantics

### 2.1 Operational Record CRUD Family
- **Candidates:** Redis, MongoDB, Apache Cassandra, Neo4j (as operational overhead baseline).
- **Semantics:**
  - Record payload: Standardized JSON object with metadata (`record_id`, `category`, `version`) and deterministic string padding matching target payload bytes.
  - Read: Single primary-key indexed point lookup.
  - Update: Complete replacement of record payload by primary key.
- **Controlled Dimensions:**
  - Read/Write ratios: 0.20, 0.50, 0.80, 0.95.
  - Payload sizes: 128, 512, 2048, 8192 bytes.
  - Working set records: 500, 1000, 2000 records.
  - Concurrency: 1 and 4 parallel worker threads.

### 2.2 Graph Traversal Family
- **Candidate:** Neo4j.
- **Semantics:** Directed graph with seeded nodes and edges. Evaluates multi-hop neighborhood discovery queries (`MATCH (n)-[:LINKS_TO*1..k]->(m)`) across traversal depths $k \in \{2, 3\}$.
- **Metrics:** Traversal latency (p50, p95, p99 ms) and traversed nodes/sec.

### 2.3 Vector Similarity Search Family
- **Candidate:** Qdrant.
- **Semantics:** 2,000 seeded 128-dimensional vectors with cosine metric, HNSW index construction, and 100 ANN search queries for Top-K=10 nearest neighbors.
- **Metrics:** Query latency (p50, p95, p99 ms), throughput (QPS), and Recall@K against brute-force linear scan.

### 2.4 RAG Passage Retrieval Family
- **Candidate:** Qdrant.
- **Corpus:** BEIR SciFact (5,183 scientific research abstracts).
- **Embedding:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors, normalized).
- **Metrics:** Information retrieval metrics: Recall@10, NDCG@10, and Mean Reciprocal Rank (MRR).

---

## 3. Labeling and Winner Derivation Policy

- **Primary Objective:** Minimum 95th percentile latency (`min_p95_latency_ms`) subject to $\text{error\_rate} \le 0.01$.
- **Aggregation:** Median of metric values across successful repetitions for each `(workload_id, database)` pair.
- **Eligibility Requirement:** A workload profile must have successful measurements from at least **2 feasible candidate engines** to establish a comparative winner.
- **Tie-Breaking Rule:** If two engines produce median p95 latencies within 1.0% of each other, the engine with higher throughput (`throughput_ops_sec`) is designated the winner.

---

## 4. Machine Learning & Regret Evaluation Protocol

- **Inference-Time Features ($X$):**
  - `query_type`: Categorical (`key_value_crud`, `document_crud`, `wide_column_crud`).
  - `read_ratio`, `write_ratio`: Float.
  - `payload_bytes`: Integer.
  - `dataset_records`: Integer.
  - `data_size_mb`: Float.
  - `concurrency`: Integer.
  *(Target-derived performance metrics like p50/p95 latency are strictly forbidden).*
- **Target ($y$):** Categorical `best_store` (`Redis`, `MongoDB`, `Cassandra`, `Neo4j`).
- **Splitting:** `GroupShuffleSplit` on `workload_id` (test size = 0.25, random state = 42).
- **Relative Latency Regret:**
  $$\text{Regret}(W) = \frac{\text{Latency}_{\text{recommended}}(W) - \min_{d \in \text{Feasible}(W)} \text{Latency}_d(W)}{\min_{d \in \text{Feasible}(W)} \text{Latency}_d(W)}$$
- **Baselines Evaluated:** Oracle best feasible, Majority-class baseline, Rule-based selector, Single-store default (MongoDB), Random feasible baseline.
