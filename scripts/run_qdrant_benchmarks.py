import json
from pathlib import Path

from nosql_rag.config import DatabaseConfig
from nosql_rag.rag.qdrant_benchmark import run_beir_scifact_rag, run_qdrant_ann_benchmark

cfg = DatabaseConfig(qdrant_url="http://127.0.0.1:6333", hosting_region="local-docker")

print("=== Running Local Qdrant Native ANN Benchmark ===")
ann_results = run_qdrant_ann_benchmark(
    db_config=cfg,
    n_vectors=2000,
    n_queries=100,
    vector_size=128,
    top_k=10,
    seed=42,
    batch_size=256,
    cleanup=True
)
print(f"Mean Recall@10: {ann_results['mean_recall_at_k']:.4f}")
print(f"P50 Latency: {ann_results['p50_query_latency_ms']:.3f} ms, P95: {ann_results['p95_query_latency_ms']:.3f} ms")

ann_path = Path("results/benchmarks/qdrant_ann_runs.json")
ann_path.parent.mkdir(parents=True, exist_ok=True)
with open(ann_path, "w", encoding="utf-8") as f:
    json.dump(ann_results, f, indent=2, default=str)
print(f"Saved local Qdrant ANN benchmark to {ann_path}")

print("\n=== Running Local BEIR SciFact RAG Retrieval Benchmark ===")
try:
    beir_results = run_beir_scifact_rag(
        db_config=cfg,
        dataset_name="scifact",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        top_k=10,
        max_queries=50,
        cleanup=True
    )
    print(f"BEIR Recall@10: {beir_results.get('recall_at_10')}")
    print(f"BEIR NDCG@10: {beir_results.get('ndcg_at_10')}")
    print(f"BEIR MRR: {beir_results.get('mrr')}")
    beir_path = Path("results/benchmarks/beir_scifact_qdrant_results.json")
    with open(beir_path, "w", encoding="utf-8") as f:
        json.dump(beir_results, f, indent=2, default=str)
    print(f"Saved local BEIR SciFact benchmark to {beir_path}")
except Exception as e:
    print(f"BEIR run note: {e}")
