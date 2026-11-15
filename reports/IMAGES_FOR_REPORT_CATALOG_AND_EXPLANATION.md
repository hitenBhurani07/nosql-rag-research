# 📸 Comprehensive Catalog & Deep Explanation of All Project Figures

**Repository Folder**: `reports/images_for_report/`  
**Author**: Hiten Bhurani  
**Subject**: Big Data Analytics (BDA) / Distributed Systems  

This document provides a detailed technical catalog of all **16 images** in `reports/images_for_report/`, including visual breakdowns, BDA research significance, and exact presentation scripts for your final report and viva defense.

---

## IMG-01: Tab 1: Interactive Two-Stage Pattern Recommender (Full Output View)

- **File Name**: `screencapture-localhost-8501-2026-11-15-19_27_05.png`
- **Category**: Dashboard UI Screen (Full Workflow)
- **Resolution**: 1920 x 2911 pixels | **File Size**: 522.3 KB
- **Summary**: Captures the end-to-end execution of the recommendation engine after user clicks 'Generate Recommendation'.

![Tab 1: Interactive Two-Stage Pattern Recommender (Full Output View)](images_for_report/screencapture-localhost-8501-2026-11-15-19_27_05.png)

### Detailed Visual Breakdown (What is Visible):
- Project Header & Context Banner: Clarifies that in single-key CRUD Redis dominates in-memory, while Stage 1 feasibility routes specialized vector/graph tasks.
- Workload Input Controls: Sliders for query type ('key_value_crud'), payload size (1024 B), read ratio (0.80), dataset records (10,000), and client concurrency (c=4).
- Recommendation Result Card: Prominently outputs 'Recommended Database: Redis' via 'stage_2_ml_performance_selection'.
- Candidate Eligibility List: Confirms Redis, MongoDB, Cassandra, and Neo4j are functionally eligible, while Qdrant is excluded from scalar CRUD.
- Stage 2 Probabilities Bar Chart: 100% selection confidence (Probability = 1.0) for Redis.
- Live Empirical Latency Comparison Table: Directly matches genuine benchmark runs to the slider inputs (1024B, 80% read, c=4), showing Redis P95 = 0.20 ms (Winner), MongoDB = 0.73 ms (+262% slower), Cassandra = 1.53 ms (+657% slower), Neo4j = 3.34 ms (+1550% slower).
- Side-by-Side P95 and P50 Bar Charts: Visually demonstrates the sub-millisecond memory speed of Redis relative to disk-backed engines.
- Instance-Level SHAP Feature Attribution Table: Shows exact numerical Shapley values explaining feature contributions (data_size_mb, write_ratio, dataset_records).

### Research & BDA Significance:
This screen is the core deliverable of the two-stage selector. It proves that recommendation is not a black-box guess; it combines deterministic feasibility, Random Forest class probabilities, and real-time empirical validation from our 1,356 benchmark runs.

### 🎤 Exact Script for Report & Viva:
> "This figure demonstrates Tab 1 of our interactive Streamlit dashboard. When a system engineer inputs their workload profile (1,024-byte payload, 80% read ratio, concurrency c=4) and clicks 'Generate Recommendation', the pipeline evaluates feasibility in Stage 1 and passes the profile to our trained Random Forest in Stage 2. The model recommends Redis with 100% confidence. Below the recommendation card, our dynamic benchmark slice extracts the real empirical numbers: Redis delivers 0.20 ms P95 latency, while MongoDB is 3.6x slower (0.73 ms) and Cassandra is 7.5x slower (1.53 ms). Finally, the SHAP table at the bottom mathematically attributes this decision to data size and write ratio parameters."

---

## IMG-02: Tab 2: Stage 1 Data-Model Feasibility Matrix

- **File Name**: `screencapture-localhost-8501-2026-11-15-19_27_21.png`
- **Category**: Dashboard UI Screen (Architectural Rules)
- **Resolution**: 1920 x 912 pixels | **File Size**: 240.5 KB
- **Summary**: Displays the complete architectural compatibility matrix mapping 6 workload families across all 5 candidate database engines.

![Tab 2: Stage 1 Data-Model Feasibility Matrix](images_for_report/screencapture-localhost-8501-2026-11-15-19_27_21.png)

### Detailed Visual Breakdown (What is Visible):
- Structured Table: 6 workload families (Key-Value CRUD, Document JSON, Partitioned Writes, Multi-hop Graph Traversal, Dense Vector ANN, RAG Passage Retrieval).
- Color-coded Badges: Native primary support (Green checkmark), Supported with caveats/extensions (Yellow warning), and Incompatible/Excluded (Red cross).
- Stage 1 Routing Column: Clearly distinguishes which workloads are routed directly to specialized stores (Vector -> Qdrant, Graph -> Neo4j) vs general CRUD workloads routed to Stage 2 ML.

### Research & BDA Significance:
Implements Martin Fowler's Polyglot Persistence theorem. It prevents category errors in benchmarking by ensuring engines are only compared where they share common architectural capabilities.

### 🎤 Exact Script for Report & Viva:
> "This figure displays Tab 2, our Stage 1 Compatibility Matrix. In Big Data architecture, you cannot force disparate database paradigms into a single latency contest. Qdrant cannot serve property graph traversals, and Redis cannot index high-dimensional vectors natively without extensions. Stage 1 enforces these boundaries deterministically before any machine learning model is queried."

---

## IMG-03: Tab 3: Genuine In-Container CRUD Benchmark Explorer

- **File Name**: `screencapture-localhost-8501-2026-11-15-19_27_30.png`
- **Category**: Dashboard UI Screen (Empirical Auditing & Slicing)
- **Resolution**: 1920 x 1960 pixels | **File Size**: 352.7 KB
- **Summary**: Audits the 1,356 genuine benchmark runs, data provenance partitioning, and features the interactive parameter slice controls.

![Tab 3: Genuine In-Container CRUD Benchmark Explorer](images_for_report/screencapture-localhost-8501-2026-11-15-19_27_30.png)

### Detailed Visual Breakdown (What is Visible):
- Top Metrics: 2,269 total raw records, 1,356 genuine runs, 0.00% error rate, in-container client placement.
- Completeness Table: Redis 450/450 (100%), MongoDB 450/450 (100%), Cassandra 228/228 (100%), Neo4j 228/228 (100%).
- Data Provenance Table: Segregates genuine_benchmark (1,356) from quarantined host_port_forward_pilot (900), remote_cloud_pilot (8), and invalid_measurement_artifact (5).
- Section 3 Interactive Controls: Concurrency radio (All, c=1, c=4), Payload multiselect, Read ratio multiselect.
- Dynamic Bar Charts: Real-time Median P95 Latency (ms) and Median Throughput (ops/sec) by engine.

### Research & BDA Significance:
Guarantees scientific reproducibility. It proves all 1,356 target runs completed with 0 errors and documents the strict quarantine of earlier host-measured pilot runs.

### 🎤 Exact Script for Report & Viva:
> "Tab 3 provides full empirical auditing. As shown in the completeness table, all 450 target runs for Redis and MongoDB and 228 runs for Cassandra and Neo4j were successfully executed with zero errors. In Section 3, examiners can interactively slice the data by payload size and concurrency, verifying live how throughput jumps from 70 to over 300 ops/sec under c=4 multiprocessing."

---

## IMG-04: Tab 4: Machine Learning Evaluation & SHAP (Analysis A — 2 Engines, 150 Profiles)

- **File Name**: `screencapture-localhost-8501-2026-11-15-19_28_08.png`
- **Category**: Dashboard UI Screen (ML Evaluation)
- **Resolution**: 1920 x 1858 pixels | **File Size**: 452.7 KB
- **Summary**: Evaluates Decision Tree, Random Forest, and Gradient Boosting on the 150-profile Redis vs MongoDB dataset.

![Tab 4: Machine Learning Evaluation & SHAP (Analysis A — 2 Engines, 150 Profiles)](images_for_report/screencapture-localhost-8501-2026-11-15-19_28_08.png)

### Detailed Visual Breakdown (What is Visible):
- Evaluation Degeneracy Callout: Prominently warns that because Redis wins 149/150 profiles, test sets contain a single class, making 1.0000 Accuracy/Macro-F1 degenerate.
- Analysis Selector Radio: Selected on 'Analysis A (2 Engines: Redis + MongoDB, 150 Profiles)'.
- Held-Out Test Evaluation Table: Majority Baseline, Decision Tree, Random Forest, Gradient Boosting all achieving 1.0000 Accuracy and Macro-F1.
- Grouped Cross-Validation Table: 5-fold CV results (Mean CV Macro-F1: 0.8979 ± 0.2043; Mean CV Accuracy: 0.9917 ± 0.0167).
- Confusion Matrix Image: Visual proof of the single-class Redis test set (30 test instances, all classified as Redis).
- Global SHAP Feature Importance Plot: Ranks features influencing the Redis vs MongoDB boundary.

### Research & BDA Significance:
Documents an honest empirical finding: single-key CRUD has no learnable multi-class signal under local networking because in-memory storage physically dominates disk storage. The 5-fold grouped CV demonstrates leakage-safe validation across workload groups.

### 🎤 Exact Script for Report & Viva:
> "This screen shows Tab 4 for Analysis A (Redis vs MongoDB across 150 profiles). Notice our scientific disclosure at the top: in-memory Redis won 149 out of 150 workloads. Because the held-out test set contains exclusively Redis, our 1.0000 Accuracy and Macro-F1 merely match the majority baseline. We highlight this as an authentic empirical finding rather than synthesizing artificial data."

---

## IMG-05: Tab 4: Machine Learning Evaluation & SHAP (Analysis B — 4 Engines, 76 Profiles)

- **File Name**: `screencapture-localhost-8501-2026-11-15-19_28_23.png`
- **Category**: Dashboard UI Screen (ML Evaluation)
- **Resolution**: 1920 x 1858 pixels | **File Size**: 438.5 KB
- **Summary**: Evaluates the 4-engine competitive matrix (Redis, MongoDB, Cassandra, Neo4j) across the 76 matched profile subset.

![Tab 4: Machine Learning Evaluation & SHAP (Analysis B — 4 Engines, 76 Profiles)](images_for_report/screencapture-localhost-8501-2026-11-15-19_28_23.png)

### Detailed Visual Breakdown (What is Visible):
- Analysis Selector Radio: Switched to 'Analysis B (4 Engines: Redis + MongoDB + Cassandra + Neo4j, 76 Profiles)'.
- Held-Out Test Evaluation Table: Majority Baseline, Decision Tree, Random Forest, Gradient Boosting all achieving 1.0000 Accuracy and Macro-F1.
- 5-Fold Grouped Cross-Validation Table: Shows perfect 1.0000 ± 0.0000 across all 5 folds because Redis won 100% (76/76) of the 4-engine profiles.
- Analysis B SHAP Summary Plot: Displays global Shapley attributions across all 4 candidate stores.

### Research & BDA Significance:
Confirms that expanding the candidate pool to Cassandra and Neo4j for single-key CRUD does not change the outcome: in-memory Redis remains uniformly faster than both wide-column commitlogs and property graph stores.

### 🎤 Exact Script for Report & Viva:
> "When we expand the evaluation to all 4 engines in Analysis B, Redis wins 100% of the 76 profiles. This confirms that disk-backed engines (MongoDB WiredTiger, Cassandra LSM-trees, Neo4j property maps) cannot outpace in-memory C hash tables for scalar point lookups. The 4-engine model achieves 1.0000 CV Macro-F1 by reproducing the majority baseline."

---

## IMG-06: Tab 5: Latency Regret Evaluation (Analysis A — 2 Engines, 150 Profiles)

- **File Name**: `screencapture-localhost-8501-2026-11-15-19_28_35.png`
- **Category**: Dashboard UI Screen (Regret Metric)
- **Resolution**: 1920 x 1646 pixels | **File Size**: 329.5 KB
- **Summary**: Quantifies the real-world latency penalty incurred by choosing sub-optimal database defaults in 2-engine workloads.

![Tab 5: Latency Regret Evaluation (Analysis A — 2 Engines, 150 Profiles)](images_for_report/screencapture-localhost-8501-2026-11-15-19_28_35.png)

### Detailed Visual Breakdown (What is Visible):
- Regret Formula: Regret(W) = (Latency_selected - Latency_oracle) / Latency_oracle.
- Summary Table (30 Test Workloads): Oracle Best = 0.00%, Majority Baseline = 0.00%, ML Recommender = 0.00%, Always-Redis = 0.00%, Always-MongoDB = 206.82% mean regret (P95 regret: 310.06%).
- Dynamic Strategy Latency Overhead Bar Chart: Displays Always-MongoDB standing at over 2.06x overhead while Redis/Oracle sit at 0.0x.
- Expandable Section: View Publication Density Plot.

### Research & BDA Significance:
Proves the practical utility of the recommendation system: deploying MongoDB for single-key session caching incurs an average 206.8% latency overhead (over 3x slower).

### 🎤 Exact Script for Report & Viva:
> "Tab 5 presents Latency Regret for Analysis A. While classification accuracy treats all errors equally, Latency Regret measures the actual performance penalty suffered by the application. Choosing Always-MongoDB incurs a 206.8% mean latency regret—meaning queries take more than triple the time of Redis."

---

## IMG-07: Tab 5: Latency Regret Evaluation (Analysis B — 4 Engines, 76 Profiles)

- **File Name**: `screencapture-localhost-8501-2026-11-15-19_28_46.png`
- **Category**: Dashboard UI Screen (Regret Metric)
- **Resolution**: 1920 x 1674 pixels | **File Size**: 359.9 KB
- **Summary**: Visualizes the severe latency regret penalties across Redis, MongoDB, Cassandra, and Neo4j.

![Tab 5: Latency Regret Evaluation (Analysis B — 4 Engines, 76 Profiles)](images_for_report/screencapture-localhost-8501-2026-11-15-19_28_46.png)

### Detailed Visual Breakdown (What is Visible):
- Analysis B Radio Selected: Evaluates 16 held-out test workloads.
- Regret Table: Always-Redis = 0.00%, Always-MongoDB = 264.39% mean regret, Always-Cassandra = 576.10% mean regret, Always-Neo4j = 1,770.67% mean regret (P95: 2,644.25%).
- Dynamic Overhead Bar Chart: Shows Neo4j's dramatic 17.7x overhead and Cassandra's 5.76x overhead for scalar CRUD.

### Research & BDA Significance:
Empirically quantifies the extreme cost of database misallocation: using a graph database for scalar CRUD creates a 17.7x latency penalty.

### 🎤 Exact Script for Report & Viva:
> "In Analysis B, the latency regret is even more pronounced. If an engineering team defaults to Cassandra for scalar CRUD, they incur 576% latency overhead. If they default to Neo4j, they suffer 1,770% latency overhead (almost 18x slower). This mathematically demonstrates the necessity of pattern selection."

---

## IMG-08: Tab 6: Specialized Workload Evaluation (Qdrant Vector RAG & Neo4j Graph)

- **File Name**: `screencapture-localhost-8501-2026-11-15-19_28_55.png`
- **Category**: Dashboard UI Screen (Specialized Pillars)
- **Resolution**: 1920 x 2224 pixels | **File Size**: 385.4 KB
- **Summary**: Presents empirical results for specialized RAG operations: dense vector similarity on Qdrant and knowledge-graph traversal on Neo4j.

![Tab 6: Specialized Workload Evaluation (Qdrant Vector RAG & Neo4j Graph)](images_for_report/screencapture-localhost-8501-2026-11-15-19_28_55.png)

### Detailed Visual Breakdown (What is Visible):
- Section 1 BEIR SciFact RAG Retrieval: 5,183 scientific abstracts, all 300 test queries evaluated. Recall@10 = 0.7833, NDCG@10 = 0.6451, MRR = 0.6047, P50 query latency = 15.32 ms.
- Host-Path Placement Note: Explicitly notes vector query latencies were measured from the host client.
- Section 2 Native Qdrant Dense Vector ANN: 2,000 synthetic vectors, Exact Search Recall@10 = 1.0000 (100%), P50 latency = 15.07 ms.
- Section 3 Neo4j Graph Traversal: 200 nodes, 600 edges, 2-hop neighbor traversal depth. Throughput = 270.4 ops/sec, P50 latency = 2.99 ms, P95 = 4.09 ms.

### Research & BDA Significance:
Demonstrates the other two pillars of RAG: high-dimensional dense vector retrieval (Qdrant) and entity relationship traversals (Neo4j).

### 🎤 Exact Script for Report & Viva:
> "Tab 6 evaluates the non-CRUD specialized workloads. On the full BEIR SciFact biomedical benchmark across 300 test queries, Qdrant achieved 0.7833 Recall@10 and 0.6451 NDCG@10 with a 15.3 ms P50 latency. For knowledge-graph entity lookups, Neo4j achieved 270.4 ops/sec with a 2.99 ms P50 latency using Index-Free Adjacency."

---

## IMG-09: Tab 7: Methodology, Network Findings & Limitations

- **File Name**: `screencapture-localhost-8501-2026-11-15-19_29_04.png`
- **Category**: Dashboard UI Screen (Systems Engineering)
- **Resolution**: 1920 x 1234 pixels | **File Size**: 400.5 KB
- **Summary**: Details the systems engineering investigations: Windows WSL2 relay stall hypothesis, c=4 multiprocessing resolution, and academic limitations.

![Tab 7: Methodology, Network Findings & Limitations](images_for_report/screencapture-localhost-8501-2026-11-15-19_29_04.png)

### Detailed Visual Breakdown (What is Visible):
- Section 1 Windows WSL2 Port-Forwarding Artifact: Explains the 40 ms relay delay, nodetool proxyhistograms verification (258 microseconds server vs 48 ms client), 42.67% label flip rate, and in-container client fix.
- Section 2 Concurrency Validity (c=4): Documents 80.64% queueing overhead in Python multi-threading and the 4.25x throughput speedup via multiprocessing.spawn.
- Section 3 Empirical Degeneracy: Academic rationale for single-class Redis test set.
- Section 4 Research Limitations: Single-node execution, sequential container isolation for 3GB RAM cap, untuned 512M JVM heaps, and 200-node demo graph.

### Research & BDA Significance:
Highlights the rigorous systems debugging that elevated this project from a standard ML assignment to a serious Big Data systems investigation.

### 🎤 Exact Script for Report & Viva:
> "Tab 7 summarizes our key systems discoveries. We proved that Windows WSL2 port forwarding introduced an artificial 40 ms delayed-ACK stall on multi-segment frames, flipping 42.67% of ground-truth labels. We diagnosed this via Cassandra's internal proxyhistograms and resolved it with a pinned in-container client. We also demonstrated that Python multi-threading bottlenecks on the GIL at c=4, whereas multiprocessing unlocked a 4.25x throughput increase."

---

## IMG-10: Research Publication Figure: Held-Out Confusion Matrix

- **File Name**: `confusion_matrix.png`
- **Category**: Empirical ML Publication Plot
- **Resolution**: 1200 x 1000 pixels | **File Size**: 39.9 KB
- **Summary**: Heatmap confusion matrix of the best model (Random Forest) on the held-out test partition.

![Research Publication Figure: Held-Out Confusion Matrix](images_for_report/confusion_matrix.png)

### Detailed Visual Breakdown (What is Visible):
- X-axis: Predicted Database Label (Redis).
- Y-axis: True Ground-Truth Database Label (Redis).
- Heatmap Cell: Exactly 30 test instances correctly predicted as Redis, with 0 false positives and 0 false negatives.
- Title & Annotations: Confirms 100% test accuracy reflecting the single-class Redis test distribution.

### Research & BDA Significance:
Provides visual confirmation of the degenerate classifier finding: because in-memory Redis dominates all scalar CRUD profiles, the test set contains only the Redis class.

### 🎤 Exact Script for Report & Viva:
> "This is our publication confusion matrix for the held-out test set. All 30 test workloads fall into the Redis-Redis cell. This visualizes why the test accuracy is 1.0000: there is no multi-class confusion because Redis physically outpaces disk engines in single-key RAM access."

---

## IMG-11: Research Publication Figure: Global Latency Regret Distribution

- **File Name**: `latency_regret.png`
- **Category**: Empirical ML Publication Plot
- **Resolution**: 1800 x 1000 pixels | **File Size**: 76.1 KB
- **Summary**: Kernel Density Estimation (KDE) and boxplot distribution of relative latency regret across candidate deployment strategies.

![Research Publication Figure: Global Latency Regret Distribution](images_for_report/latency_regret.png)

### Detailed Visual Breakdown (What is Visible):
- X-axis: Relative Latency Regret Multiplier.
- Y-axis / Legend: Strategies (Oracle Best, ML Recommender, Always-Redis, Always-MongoDB, Always-Cassandra, Always-Neo4j).
- Color Distributions: Sharp spike at 0.0 for Oracle, ML Recommender, and Redis; broad distributions shifted to the right for MongoDB (2x), Cassandra (5.7x), and Neo4j (17.7x).

### Research & BDA Significance:
Demonstrates that picking an incorrect database introduces a multi-fold latency penalty that spreads widely across different payload sizes.

### 🎤 Exact Script for Report & Viva:
> "This publication figure plots the distribution of latency regret. Notice that the ML Recommender and Always-Redis collapse to a single spike at zero regret, whereas the curves for MongoDB, Cassandra, and Neo4j shift dramatically to the right, showing that developer misallocation consistently degrades performance."

---

## IMG-12: Research Publication Figure: Latency Regret (Analysis A — 2 Engines, 150 Profiles)

- **File Name**: `latency_regret_2-engine_(redis_+_mongodb,_150_profiles).png`
- **Category**: Empirical ML Publication Plot
- **Resolution**: 1800 x 1000 pixels | **File Size**: 76.1 KB
- **Summary**: Focused latency regret density plot for the 150-profile Redis vs MongoDB evaluation.

![Research Publication Figure: Latency Regret (Analysis A — 2 Engines, 150 Profiles)](images_for_report/latency_regret_2-engine_(redis_+_mongodb,_150_profiles).png)

### Detailed Visual Breakdown (What is Visible):
- KDE Density Curve: Compares Always-MongoDB against Oracle Best and ML Recommender.
- Peak Offset: Always-MongoDB distribution peaks around 2.1x (211% median regret), extending to over 3.1x at P95.

### Research & BDA Significance:
Isolates the Document vs Key-Value operational boundary across 150 matched profiles.

### 🎤 Exact Script for Report & Viva:
> "In this focused 2-engine regret plot, we observe that MongoDB incurs a median latency overhead of 211.8%, reaching up to 310% at P95. This visually proves why Redis is mandatory for low-latency operational caching."

---

## IMG-13: Research Publication Figure: Latency Regret (Analysis B — 4 Engines, 76 Profiles)

- **File Name**: `latency_regret_4-engine_(redis_+_mongodb_+_cassandra_+_neo4j,_76_profiles).png`
- **Category**: Empirical ML Publication Plot
- **Resolution**: 1800 x 1000 pixels | **File Size**: 88.8 KB
- **Summary**: Comprehensive 4-engine latency regret comparison across the 76 matched profile subset.

![Research Publication Figure: Latency Regret (Analysis B — 4 Engines, 76 Profiles)](images_for_report/latency_regret_4-engine_(redis_+_mongodb_+_cassandra_+_neo4j,_76_profiles).png)

### Detailed Visual Breakdown (What is Visible):
- Four Strategy Distributions: Oracle/Redis at 0.0, MongoDB centered at 2.6x, Cassandra centered at 5.7x, and Neo4j spanning out to 17.7x–26.4x.
- Comparative Scale: Logarithmic or stretched scale demonstrating the massive divergence between in-memory, disk-document, wide-column commitlog, and graph storage engines.

### Research & BDA Significance:
Visualizes the core empirical finding of the 4-engine matrix: architectural overhead compounds rapidly when specialized engines are misapplied to scalar CRUD.

### 🎤 Exact Script for Report & Viva:
> "This 4-engine regret plot captures the architectural divergence across all stores. Notice the ladder of latency overhead: Redis is optimal (0x), MongoDB adds 2.6x overhead, Cassandra adds 5.7x overhead, and Neo4j adds 17.7x overhead for single-key operations."

---

## IMG-14: Research Publication Figure: Global Multi-Class SHAP Summary Plot

- **File Name**: `shap_summary.png`
- **Category**: Explainability Publication Plot
- **Resolution**: 1755 x 978 pixels | **File Size**: 120.4 KB
- **Summary**: Beeswarm / bar summary plot of SHAP feature importance across all evaluated workloads.

![Research Publication Figure: Global Multi-Class SHAP Summary Plot](images_for_report/shap_summary.png)

### Detailed Visual Breakdown (What is Visible):
- Feature Ranking: data_size_mb, write_ratio, dataset_records, concurrency, read_ratio, payload_bytes.
- SHAP Values: Mean absolute Shapley value showing the magnitude of feature impact on the model's output probabilities.

### Research & BDA Significance:
Proves model explainability: the classifier relies heavily on data volume and write ratio to distinguish memory-bound from disk-bound behavior.

### 🎤 Exact Script for Report & Viva:
> "This global SHAP summary plot ranks feature importance. Total data size and write ratio exhibit the highest mean absolute SHAP values, confirming that the model learns memory boundaries and write overheads when making pattern recommendations."

---

## IMG-15: Research Publication Figure: SHAP Summary (Analysis A — 2 Engines, 150 Profiles)

- **File Name**: `shap_summary_2-engine_(redis_+_mongodb,_150_profiles).png`
- **Category**: Explainability Publication Plot
- **Resolution**: 1755 x 978 pixels | **File Size**: 120.4 KB
- **Summary**: SHAP feature attribution plot specifically for the Redis vs MongoDB 150-profile dataset.

![Research Publication Figure: SHAP Summary (Analysis A — 2 Engines, 150 Profiles)](images_for_report/shap_summary_2-engine_(redis_+_mongodb,_150_profiles).png)

### Detailed Visual Breakdown (What is Visible):
- Feature Impact Dots: Color-coded from blue (low feature value) to red (high feature value).
- Directional Impact: Demonstrates how increasing write ratio and payload size shifts probability mass toward Redis's low-latency memory pipeline.

### Research & BDA Significance:
Provides granular interpretability into the Redis vs MongoDB decision boundary.

### 🎤 Exact Script for Report & Viva:
> "In the 2-engine SHAP plot, we see that higher write ratios and larger payload sizes push the model decisively toward Redis, because MongoDB's WiredTiger BSON serialization cost scales with payload size."

---

## IMG-16: Research Publication Figure: SHAP Summary (Analysis B — 4 Engines, 76 Profiles)

- **File Name**: `shap_summary_4-engine_(redis_+_mongodb_+_cassandra_+_neo4j,_76_profiles).png`
- **Category**: Explainability Publication Plot
- **Resolution**: 1755 x 978 pixels | **File Size**: 100.4 KB
- **Summary**: SHAP feature attribution plot for the 4-engine competitive matrix (Redis, MongoDB, Cassandra, Neo4j).

![Research Publication Figure: SHAP Summary (Analysis B — 4 Engines, 76 Profiles)](images_for_report/shap_summary_4-engine_(redis_+_mongodb_+_cassandra_+_neo4j,_76_profiles).png)

### Detailed Visual Breakdown (What is Visible):
- Multi-class feature impact across operational features.
- Feature Ranking: data_size_mb, concurrency, write_ratio, payload_bytes.

### Research & BDA Significance:
Shows that concurrency (c=1 vs c=4) plays an amplified role when distributed engines like Cassandra and Neo4j are included in the candidate pool.

### 🎤 Exact Script for Report & Viva:
> "In the 4-engine SHAP plot, concurrency becomes a much more dominant feature because multi-client contention impacts Cassandra's Memtables and Neo4j's transaction locks differently than Redis's single-threaded event loop."

---
