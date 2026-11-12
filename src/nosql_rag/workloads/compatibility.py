"""Stage 1 compatibility and feasibility filtering for NoSQL pattern selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALL_DATABASES: tuple[str, ...] = ("Redis", "MongoDB", "Cassandra", "Neo4j", "Qdrant")
CRUD_DATABASES: tuple[str, ...] = ("Redis", "MongoDB", "Cassandra", "Neo4j")

WORKLOAD_FAMILIES: tuple[str, ...] = (
    "key_value_crud",
    "document_crud",
    "wide_column_crud",
    "graph_traversal",
    "vector_similarity",
    "rag_retrieval",
    "rag_hybrid",
)


@dataclass(frozen=True)
class FeasibilityResult:
    """Outcome of Stage 1 compatibility filtering for a workload."""

    workload_family: str
    feasible_databases: list[str]
    rejected_reasons: dict[str, str]
    requires_ml_selection: bool
    evaluation_protocol: str
    notes: str


def evaluate_feasibility(workload: dict[str, Any]) -> FeasibilityResult:
    """Determine which databases can validly serve the requested workload.

    Enforces methodological comparability:
    - Vector similarity / RAG retrieval requires Qdrant.
    - Graph traversal (depth >= 2 or query_type == 'graph_traversal') requires Neo4j.
    - Record CRUD workloads (key_value_crud, document_crud, wide_column_crud) are
      feasible across Redis, MongoDB, Cassandra, and Neo4j (subject to optional
      hard constraints such as schema flexibility or vector dimensions).
    """
    query_type = str(workload.get("query_type", "key_value_crud"))
    vector_dims = int(workload.get("vector_dimensions", 0) or 0)
    top_k = int(workload.get("top_k", 0) or 0)
    graph_depth = int(workload.get("graph_depth", 0) or 0)
    requires_graph = bool(workload.get("requires_graph_traversal", False)) or graph_depth >= 2
    requires_vector = (
        query_type in {"vector_similarity", "rag_retrieval", "rag_hybrid"}
        or vector_dims > 0
        or top_k > 0
    )

    rejected: dict[str, str] = {}

    if query_type == "rag_hybrid":
        return FeasibilityResult(
            workload_family="rag_hybrid",
            feasible_databases=["Qdrant", "Redis", "MongoDB"],
            rejected_reasons={
                "Cassandra": "Not selected for dense vector retrieval in hybrid RAG",
                "Neo4j": "Optional graph-RAG extension; not required for standard hybrid cache+vector",
            },
            requires_ml_selection=False,
            evaluation_protocol="rag_retrieval_plus_operational_store",
            notes="Hybrid RAG pairs Qdrant (dense retrieval) with an operational store (Redis/MongoDB) for metadata or caching.",
        )

    if requires_vector:
        for db in CRUD_DATABASES:
            rejected[db] = "Not evaluated as a native dense HNSW vector ANN store in this study"
        return FeasibilityResult(
            workload_family="rag_retrieval" if query_type == "rag_retrieval" else "vector_similarity",
            feasible_databases=["Qdrant"],
            rejected_reasons=rejected,
            requires_ml_selection=False,
            evaluation_protocol="vector_ann_and_retrieval_quality",
            notes="Vector similarity and RAG passage retrieval are routed to Qdrant and evaluated on ANN latency + Recall@K/NDCG@K.",
        )

    if query_type == "graph_traversal" or requires_graph:
        for db in ("Redis", "MongoDB", "Cassandra", "Qdrant"):
            rejected[db] = "Does not support native multi-hop property graph traversal"
        return FeasibilityResult(
            workload_family="graph_traversal",
            feasible_databases=["Neo4j"],
            rejected_reasons=rejected,
            requires_ml_selection=False,
            evaluation_protocol="native_graph_traversal",
            notes="Multi-hop graph traversal is routed deterministically to Neo4j.",
        )

    feasible = list(CRUD_DATABASES)
    rejected["Qdrant"] = "Qdrant is a specialized vector store and is excluded from non-vector CRUD comparisons"

    return FeasibilityResult(
        workload_family=query_type if query_type in WORKLOAD_FAMILIES else "key_value_crud",
        feasible_databases=feasible,
        rejected_reasons=rejected,
        requires_ml_selection=len(feasible) >= 2,
        evaluation_protocol="common_crud_latency_throughput",
        notes="Operational CRUD workload feasible across Redis, MongoDB, Cassandra, and Neo4j; Stage 2 ML selects the optimal engine.",
    )
