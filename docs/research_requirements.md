# Research Requirements

Extracted from [Paper2_NoSQL_Pattern_Selection_RAG (1).docx](file:///c:/Users/hiten/nosql-rag-research/docs/source/Paper2_NoSQL_Pattern_Selection_RAG%20(1).docx) and [README.md](file:///c:/Users/hiten/nosql-rag-research/README.md).

## 1. Research Title and Type

- **Title:** ML-Driven NoSQL Pattern Selection for Retrieval-Augmented Generation Workloads
- **Module / Category:** Module 2: MapReduce, Algorithms and NoSQL — Method with benchmark dataset

## 2. Research Objectives

1. Construct a labelled workload-to-store benchmark dataset across key-value, document, wide-column, graph, and vector stores using reproducible workload measurements.
2. Build an explainable ML-based recommender that maps workload characteristics (e.g., read/write ratio, query type, data size, payload size, concurrency, vector dimensionality, consistency level) to the best feasible NoSQL database pattern.
3. Explain feature contributions driving recommendations using SHAP analysis.
4. Evaluate recommendation quality using accuracy, macro-F1, and latency regret against rule-based, majority-class, and single-store baselines.
5. Validate the practical usefulness of the recommender in a Retrieval-Augmented Generation (RAG) retrieval case study (e.g., BEIR).
6. Provide a practitioner-oriented decision flowchart and interactive recommendation dashboard.

## 3. Research Gaps Identified in Brief

1. Store-selection guidance is largely qualitative or vendor-driven; no labelled workload-to-best-store dataset exists.
2. Vector stores are typically studied separately from key-value, document, wide-column, and graph patterns.
3. Existing database recommenders lack explainability and regret-based evaluation.
4. End-to-end validation on RAG pipelines is limited.

## 4. Candidate Database Technologies

1. **Redis** — Key-value store
2. **MongoDB** — Document store
3. **Apache Cassandra** — Wide-column store
4. **Neo4j** — Graph store
5. **Qdrant** — Vector database (explicitly chosen in the project `README.md` and Colab notebook as the vector store candidate)

## 5. Workload Dimensions and Benchmarks

### Workload Features (Brief + Experimental Design)
- Query type / workload class
- Read/write ratio
- Payload size / record size
- Dataset size (records and MB/GB)
- Concurrency
- Vector dimensionality (for vector/ANN workloads)
- Consistency level (when varied)
- Graph traversal depth (for graph workloads)

### Benchmark Suites Referenced in Brief
- **YCSB (Workloads A–F):** General key-value / record CRUD access patterns
- **LDBC-SNB:** Graph traversal workloads
- **ANN-Benchmarks (e.g., SIFT1M / GloVe / GIST1M) or seeded vector ANN:** Vector similarity search
- **BEIR (e.g., SciFact, MS MARCO, Natural Questions):** RAG passage retrieval validation

## 6. Required ML Models and Evaluation

### Models
1. Decision Tree
2. Random Forest
3. Gradient Boosting

### Evaluation Metrics
- **Classification:** Accuracy, Macro-F1, Weighted-F1, Precision, Recall, Confusion Matrix
- **Regret:** Relative latency regret vs. Oracle best feasible store, compared against:
  - Rule-based selector
  - Majority-class baseline
  - Single-store default
  - Random baseline
- **Explainability:** SHAP global feature importance, summary plots, and per-instance attributions
- **Vector / RAG Retrieval:** ANN query latency (p50, p95), Recall@K, NDCG@K, MRR

## 7. Expected Contributions

1. A released benchmark dataset of workload features and measured best-store labels (at least 300 configurations in the full matrix).
2. An explainable recommender covering key-value, document, wide-column, graph, and vector stores.
3. A regret-based evaluation protocol for store selection.
4. A RAG retrieval case study and a practitioner decision flowchart.

## 8. Constraints and Limitations

- **Hardware dependence:** Measurements depend on client/server hardware, hosting region, and network path.
- **Engine version drift:** Database versions must be recorded per run.
- **Limited store set:** Five representative engines rather than exhaustive market coverage.
- **Local hardware constraint:** Development machine has 16 GB RAM; five database containers should not be run simultaneously locally.
- **Research integrity:** Synthetic data must never be misrepresented as genuine benchmark measurements; no fabricated metrics or bracketed paper placeholders filled without real execution.
