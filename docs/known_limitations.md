# Known Limitations

Scientific and operational limitations of the current research implementation.

## 1. Hardware and Network Dependence

- **Latency measurements:** Point-lookup and batch latency measurements are inherently dependent on the client machine, network round-trip time (RTT), TLS termination, and cloud database instance hardware (CPU/RAM/IOPS).
- **Cross-region latency:** If databases are deployed across different cloud regions or providers (e.g., MongoDB in GCP us-east1, Qdrant in AWS eu-central1), network latency differences can overshadow database engine performance. Every experiment records `hosting_region` and `deployment_notes` to mitigate unrecorded divergence.

## 2. Database Version Drift

- Performance characteristics change across major database releases (e.g., Redis 7 vs. 8, MongoDB 6 vs. 7, Qdrant 1.8 vs. 1.10).
- The framework records the exact engine version returned by server metadata for every individual run.

## 3. Scope of Candidates

- The study focuses on five canonical representatives (Redis, MongoDB, Cassandra, Neo4j, Qdrant).
- Multi-model extensions (e.g., RedisJSON, RedisSearch, MongoDB Atlas Vector Search, Cassandra CEP-30) are noted in the compatibility matrix but not treated as primary native replacements for pure vector/graph engines in the default experimental protocol.

## 4. Cold Starts and Cache Dynamics

- Although warm-up operations (20 ops) are executed prior to latency recording, disk cache warming, OS page cache dynamics, and connection pool establishment can introduce variance in early repetitions. Aggregation uses the median across repetitions to reduce sensitivity to transient spikes.

## 5. RAG Evaluation Scope

- The BEIR SciFact experiment validates dense retrieval quality (Recall@10, NDCG@10, MRR) and vector search latency. It does not measure end-to-end LLM generative answer quality (e.g., ROUGE, BLEU, or LLM-as-a-judge factuality), which is influenced by LLM prompt engineering and model weights rather than NoSQL database performance.
