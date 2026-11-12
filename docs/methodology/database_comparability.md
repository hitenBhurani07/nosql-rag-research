# Database Comparability and Workload Partitioning Methodology

## 1. Core Methodological Question: Is a Unified 5-Store Comparison Valid?

**Scientific Verdict: NO.** A naive, monolithic 5-class comparison across Redis, MongoDB, Apache Cassandra, Neo4j, and Qdrant is **fundamentally invalid**.

Different database engines optimize for fundamentally different access paths and structural paradigms:
1. **Redis (Key-Value):** Sub-millisecond in-memory string/hash lookups (`GET`/`SET`).
2. **MongoDB (Document):** Flexible nested JSON document CRUD, rich B-tree secondary indexes.
3. **Apache Cassandra (Wide-Column):** Append-only LSM log-structured merges, partitioned clustering keys, high-throughput distributed writes.
4. **Neo4j (Property Graph):** Index-free adjacency, recursive variable-length path traversals.
5. **Qdrant (Vector Store):** High-dimensional vector indexing (HNSW), cosine/dot-product distance metrics, payload filtering.

Forcing all five into a single latency ranking violates comparability:
- If a vector similarity search is presented, Redis, MongoDB, and Cassandra cannot natively compute HNSW ANN without external modules or full sequential scans.
- If a multi-hop graph traversal is presented, Redis, MongoDB, Cassandra, and Qdrant require expensive application-side round-trips or deep nested joins ($O(b^d)$ query expansion).
- If point-lookup CRUD is evaluated, Qdrant is burdened by vector indexing and payload wrapping overhead for a task it was never engineered to solve.

---

## 2. Definitive Resolution of Candidate Store Roles

### 2.1 The Operational CRUD Comparison (Redis vs. MongoDB vs. Cassandra)
- **Feasible Engines:** `Redis`, `MongoDB`, `Cassandra`.
- **Comparable Semantics:**
  - **Data payload:** UTF-8 JSON object containing fixed metadata (`record_id`, `category`, `version`) and deterministic string padding matching exact target byte sizes ($128$ B to $8,192$ B).
  - **Read operation:** Single-record retrieval by primary identifier:
    - Redis: `GET nosql_research:{run_id}:{record_id}`
    - MongoDB: `find_one({"_id": str(record_id)})`
    - Cassandra: `SELECT record_id FROM bench_{run_id} WHERE record_id = ?`
  - **Update operation:** Replacement of payload by primary identifier:
    - Redis: `SET nosql_research:{run_id}:{record_id} payload`
    - MongoDB: `update_one({"_id": str(record_id)}, {"$set": {"payload": payload}})`
    - Cassandra: `UPDATE bench_{run_id} SET payload_json = ? WHERE record_id = ?`
- **Scientific Validity:** **Valid**. All three engines offer native, index-backed primary-key point lookups and updates with equivalent functional semantics.

### 2.2 Role of Neo4j: CRUD Participant vs. Separate Graph Family
- **Can Neo4j participate in the CRUD benchmark?**
  - **Mechanically:** Yes. Neo4j can create an indexed node label `(:BenchRecord {run_id, record_id})` and execute `MATCH` / `SET`.
  - **Methodologically:** Neo4j incurs heavy transactional graph engine overhead (transaction log, ACID locks, graph pointer structures) for simple key-value operations. While testing it in CRUD demonstrates the cost of using a graph engine as a pure key-value store, **Neo4j is fundamentally disadvantaged when restricted to non-relational point lookups**.
- **Final Decision:**
  - Neo4j participates in the **Operational CRUD Benchmark** as an illustrative comparative baseline (quantifying the penalty of using a graph engine for pure CRUD).
  - Neo4j is the **sole native engine in the Graph Traversal Workload Family** (`graph_traversal`), where multi-hop neighborhood traversals (`MATCH (a)-[:LINKS_TO*1..k]->(b)`) are evaluated.

### 2.3 Role of Qdrant: Vector Retrieval Isolation
- **Can Qdrant participate in CRUD?** **NO.** Qdrant is excluded from the operational CRUD comparison.
- **Evaluation Protocol:**
  - Evaluated under the **Vector Similarity Search Family** (`vector_similarity`) and **RAG Retrieval Family** (`rag_retrieval`).
  - Evaluated on **two distinct axes**:
    1. **ANN Search Latency (p50, p95, p99 ms) & Throughput (QPS)**.
    2. **Retrieval Quality:** Approximate nearest neighbor Recall@K against brute-force exact vector search, and standard Information Retrieval metrics (Recall@10, NDCG@10, MRR) on the BEIR SciFact dataset.

---

## 3. Workload Family & Feasibility Matrix

| Workload Family | Target Access Pattern | Feasible Databases | Non-Feasible / Excluded | Evaluation Metric |
| --- | --- | --- | --- | --- |
| **`key_value_crud`** | Single-item read/write by primary key | `Redis`, `MongoDB`, `Cassandra`, `Neo4j`* | `Qdrant` | p95 Latency (ms), Throughput (ops/s) |
| **`document_crud`** | Nested JSON object read/update | `MongoDB`, `Redis` (JSON/string), `Cassandra`, `Neo4j` | `Qdrant` | p95 Latency (ms), Throughput (ops/s) |
| **`wide_column_crud`** | High-throughput write/partition read | `Cassandra`, `Redis`, `MongoDB` | `Qdrant`, `Neo4j` | p95 Latency (ms), Throughput (ops/s) |
| **`graph_traversal`** | Multi-hop relationship path traversal | `Neo4j` | `Redis`, `MongoDB`, `Cassandra`, `Qdrant` | Traversal Latency (ms), Traversed Nodes/sec |
| **`vector_similarity`** | Dense vector cosine/Euclidean ANN | `Qdrant` | `Redis`, `MongoDB`, `Cassandra`, `Neo4j` | ANN Latency (ms), Recall@K vs. Brute-Force |
| **`rag_retrieval`** | Document passage embedding retrieval | `Qdrant` | `Redis`, `MongoDB`, `Cassandra`, `Neo4j` | Recall@10, NDCG@10, MRR, Latency (ms) |
| **`rag_hybrid`** | Vector ANN + Document metadata storage | `Qdrant` (dense) + `MongoDB`/`Redis` (cache) | Pure single-model | Composite RAG retrieval + cache lookup |

*\*Neo4j included as operational baseline to measure transactional overhead.*

---

## 4. Two-Stage Recommendation Architecture Enforcement

1. **Stage 1 (Feasibility Filtering):** Evaluates hard workload requirements:
   - If `vector_dimensions > 0` or `top_k > 0` $\to$ Feasible set = `['Qdrant']` (or `['Qdrant', 'Redis']` in hybrid RAG).
   - If `query_type == 'graph_traversal'` or `graph_depth >= 2` $\to$ Feasible set = `['Neo4j']`.
   - If operational record CRUD $\to$ Feasible set = `['Redis', 'MongoDB', 'Cassandra', 'Neo4j']`.
2. **Stage 2 (Performance-Based Ranking):**
   - If $|\text{Feasible}| == 1$: Deterministic routing directly to the sole feasible engine.
   - If $|\text{Feasible}| \ge 2$: The trained ML recommender (Decision Tree / Random Forest / Gradient Boosting) ranks feasible options based on workload features (`read_ratio`, `payload_bytes`, `dataset_records`, `concurrency`), masking and renormalizing probabilities over feasible candidates only.
