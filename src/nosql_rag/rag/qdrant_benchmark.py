"""Separate Qdrant vector search benchmarking and BEIR SciFact RAG retrieval validation."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
from tqdm import tqdm

from nosql_rag.adapters.base import AdapterError
from nosql_rag.adapters.qdrant_adapter import QdrantAdapter
from nosql_rag.config import DatabaseConfig

logger = logging.getLogger("nosql_rag.rag")


def run_qdrant_ann_benchmark(
    db_config: DatabaseConfig,
    n_vectors: int = 2000,
    n_queries: int = 100,
    vector_size: int = 128,
    top_k: int = 10,
    seed: int = 42,
    batch_size: int = 256,
    cleanup: bool = True,
) -> dict[str, Any]:
    """Execute seeded vector indexing and measure ANN query latency and Recall@K vs. exact brute-force."""
    if not db_config.qdrant_url:
        raise AdapterError("QDRANT_URL is not configured")

    from qdrant_client.models import Distance, PointStruct, VectorParams

    client_adapter = QdrantAdapter(
        url=db_config.qdrant_url, api_key=db_config.qdrant_api_key, timeout=60
    )
    client = client_adapter.client
    collection_name = f"nosql_ann_{uuid.uuid4().hex[:10]}"

    rng = np.random.default_rng(seed)
    vectors = rng.normal(size=(n_vectors, vector_size)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    queries = rng.normal(size=(n_queries, vector_size)).astype(np.float32)
    queries /= np.linalg.norm(queries, axis=1, keepdims=True)

    created = False
    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        created = True

        # Batch indexing
        for start in tqdm(range(0, n_vectors, batch_size), desc="Qdrant vector upload"):
            points = [
                PointStruct(
                    id=int(i),
                    vector=vectors[i].tolist(),
                    payload={"source_id": int(i)},
                )
                for i in range(start, min(start + batch_size, n_vectors))
            ]
            client.upsert(collection_name=collection_name, points=points, wait=True)

        latencies_ms: list[float] = []
        recalls: list[float] = []
        wall_start = time.perf_counter()

        for query_vector in queries:
            exact_scores = vectors @ query_vector
            exact_top_ids = set(np.argsort(exact_scores)[-top_k:][::-1].tolist())

            t0 = time.perf_counter()
            response = client.query_points(
                collection_name=collection_name,
                query=query_vector.tolist(),
                limit=top_k,
                with_payload=True,
            )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

            retrieved_ids = {int(p.id) for p in response.points}
            recalls.append(len(exact_top_ids & retrieved_ids) / float(top_k))

        query_wall_seconds = time.perf_counter() - wall_start

        return {
            "experiment_id": str(uuid.uuid4()),
            "database": "Qdrant",
            "workload_type": "vector_ann",
            "n_vectors": n_vectors,
            "n_queries": n_queries,
            "vector_size": vector_size,
            "top_k": top_k,
            "p50_query_latency_ms": round(float(np.percentile(latencies_ms, 50)), 3),
            "p95_query_latency_ms": round(float(np.percentile(latencies_ms, 95)), 3),
            "p99_query_latency_ms": round(float(np.percentile(latencies_ms, 99)), 3),
            "mean_query_latency_ms": round(float(np.mean(latencies_ms)), 3),
            "query_wall_seconds": round(query_wall_seconds, 4),
            "queries_per_second": (
                round(n_queries / query_wall_seconds, 2) if query_wall_seconds > 0 else np.nan
            ),
            "mean_recall_at_k": round(float(np.mean(recalls)), 4),
            "collection_name": collection_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        if created and cleanup:
            try:
                client.delete_collection(collection_name=collection_name)
            except Exception as exc:
                logger.warning("Cleanup failed for %s: %s", collection_name, exc)
        client.close()


def evaluate_ranked_results(
    ranked_doc_ids: list[list[str]],
    qrels: dict[str, set[str]],
    query_ids: list[str],
    k: int = 10,
) -> dict[str, float]:
    """Compute standard IR metrics: Recall@K, NDCG@K, and MRR."""
    recalls, ndcgs, reciprocal_ranks = [], [], []
    for qid, docs in zip(query_ids, ranked_doc_ids):
        relevant = qrels.get(str(qid), set())
        hits = [1 if str(doc) in relevant else 0 for doc in docs[:k]]
        recall = sum(hits) / float(len(relevant)) if relevant else np.nan

        # NDCG@k
        dcg = sum((hit / np.log2(rank + 2)) for rank, hit in enumerate(hits))
        ideal_hits = [1] * min(len(relevant), k)
        idcg = sum((1.0 / np.log2(rank + 2)) for rank in range(len(ideal_hits)))
        ndcg = (dcg / idcg) if idcg > 0 else 0.0

        # MRR
        rr = next((1.0 / (rank + 1) for rank, hit in enumerate(hits) if hit), 0.0)

        if relevant:
            recalls.append(recall)
            ndcgs.append(ndcg)
            reciprocal_ranks.append(rr)

    return {
        f"recall_at_{k}": round(float(np.nanmean(recalls)), 4) if recalls else np.nan,
        f"ndcg_at_{k}": round(float(np.nanmean(ndcgs)), 4) if ndcgs else np.nan,
        "mrr": round(float(np.mean(reciprocal_ranks)), 4) if reciprocal_ranks else np.nan,
        "evaluated_queries": len(recalls),
    }


def run_beir_scifact_rag(
    db_config: DatabaseConfig,
    dataset_name: str = "scifact",
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    top_k: int = 10,
    max_queries: int | None = 200,
    cleanup: bool = True,
) -> dict[str, Any]:
    """Run an end-to-end RAG passage retrieval validation experiment on BEIR SciFact."""
    if not db_config.qdrant_url:
        raise AdapterError("QDRANT_URL is not configured")

    from beir import util
    from beir.datasets.data_loader import GenericDataLoader
    from qdrant_client.models import Distance, PointStruct, VectorParams
    from sentence_transformers import SentenceTransformer

    url = f"https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{dataset_name}.zip"
    data_path = util.download_and_unzip(url, "data/sample")
    corpus, queries, qrels = GenericDataLoader(data_path).load(split="test")

    qrels_map: dict[str, set[str]] = {}
    for qid, docs in qrels.items():
        qrels_map[str(qid)] = {str(did) for did, score in docs.items() if score > 0}

    all_doc_ids = list(corpus.keys())
    doc_texts = [
        f"{corpus[doc_id].get('title', '')} {corpus[doc_id].get('text', '')}".strip()
        for doc_id in all_doc_ids
    ]

    query_ids = [qid for qid in queries if str(qid) in qrels_map]
    if max_queries:
        query_ids = query_ids[:max_queries]
    query_texts = [queries[qid] for qid in query_ids]

    logger.info("Encoding %d documents with %s...", len(doc_texts), model_name)
    encoder = SentenceTransformer(model_name)
    doc_embeddings = encoder.encode(
        doc_texts,
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    query_embeddings = encoder.encode(
        query_texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    vector_size = int(doc_embeddings.shape[1])

    client_adapter = QdrantAdapter(
        url=db_config.qdrant_url, api_key=db_config.qdrant_api_key, timeout=60
    )
    client = client_adapter.client
    collection_name = f"beir_{dataset_name}_{uuid.uuid4().hex[:8]}"
    created = False
    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        created = True

        for start in tqdm(range(0, len(all_doc_ids), 256), desc="Indexing BEIR corpus in Qdrant"):
            batch_slice = all_doc_ids[start : start + 256]
            points = [
                PointStruct(
                    id=start + i,
                    vector=doc_embeddings[start + i].tolist(),
                    payload={"doc_id": doc_id},
                )
                for i, doc_id in enumerate(batch_slice)
            ]
            client.upsert(collection_name=collection_name, points=points, wait=True)

        ranked_doc_ids: list[list[str]] = []
        latencies_ms: list[float] = []
        wall_start = time.perf_counter()

        for q_vec in tqdm(query_embeddings, desc="Running BEIR retrieval queries"):
            t0 = time.perf_counter()
            response = client.query_points(
                collection_name=collection_name,
                query=q_vec.tolist(),
                limit=top_k,
                with_payload=True,
            )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
            ranked_doc_ids.append(
                [
                    str(p.payload["doc_id"])
                    for p in response.points
                    if p.payload and "doc_id" in p.payload
                ]
            )

        wall_query_time = time.perf_counter() - wall_start
        ir_metrics = evaluate_ranked_results(ranked_doc_ids, qrels_map, query_ids, k=top_k)

        return {
            "dataset": dataset_name,
            "embedding_model": model_name,
            "top_k": top_k,
            "corpus_documents": len(all_doc_ids),
            "queries_evaluated": len(query_ids),
            "vector_dimensions": vector_size,
            "p50_query_latency_ms": round(float(np.percentile(latencies_ms, 50)), 3),
            "p95_query_latency_ms": round(float(np.percentile(latencies_ms, 95)), 3),
            "p99_query_latency_ms": round(float(np.percentile(latencies_ms, 99)), 3),
            "mean_query_latency_ms": round(float(np.mean(latencies_ms)), 3),
            "queries_per_second": (
                round(len(latencies_ms) / wall_query_time, 2) if wall_query_time > 0 else np.nan
            ),
            **ir_metrics,
            "collection_name": collection_name,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        if created and cleanup:
            try:
                client.delete_collection(collection_name=collection_name)
            except Exception as exc:
                logger.warning("Cleanup failed for %s: %s", collection_name, exc)
        client.close()
