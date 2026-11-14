"""Run BEIR SciFact RAG retrieval on all 300 queries."""

from __future__ import annotations

import json
from pathlib import Path

from nosql_rag.config import DatabaseConfig
from nosql_rag.rag.qdrant_benchmark import run_beir_scifact_rag


def main():
    cfg = DatabaseConfig(qdrant_url="http://127.0.0.1:6333", hosting_region="local_container")
    print("=== Running Full BEIR SciFact RAG Benchmark (All 300 queries) ===")
    results = run_beir_scifact_rag(
        db_config=cfg,
        dataset_name="scifact",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        top_k=10,
        max_queries=None,  # All queries
        cleanup=True,
    )

    print(f"Evaluated Queries: {results.get('evaluated_queries')}")
    print(f"Recall@10: {results.get('recall_at_10')}")
    print(f"NDCG@10: {results.get('ndcg_at_10')}")
    print(f"MRR: {results.get('mrr')}")
    print(f"P50 Query Latency: {results.get('p50_query_latency_ms')} ms")
    print(f"P95 Query Latency: {results.get('p95_query_latency_ms')} ms")

    out_path = Path("results/benchmarks/beir_scifact_qdrant_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Saved full BEIR SciFact benchmark to {out_path}")


if __name__ == "__main__":
    main()

