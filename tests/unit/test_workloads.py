"""Unit tests for workload profile generation, deterministic payloads, and feasibility."""

import json

from nosql_rag.workloads import evaluate_feasibility, generate_workload_profiles, make_payload


def test_make_payload_reproducible_and_sized() -> None:
    p1 = make_payload(record_id=42, payload_bytes=512, seed=123)
    p2 = make_payload(record_id=42, payload_bytes=512, seed=123)
    assert p1 == p2
    data = json.loads(p1)
    assert data["record_id"] == "42"
    assert "padding" in data
    # Check byte size is close to requested
    assert abs(len(p1.encode("utf-8")) - 512) <= 10


def test_generate_workload_profiles_schema() -> None:
    profiles = generate_workload_profiles(n_profiles=10, seed=42)
    assert len(profiles) == 10
    assert "workload_id" in profiles.columns
    assert "read_ratio" in profiles.columns
    assert "payload_bytes" in profiles.columns
    assert (profiles["read_ratio"] + profiles["write_ratio"]).round(2).eq(1.0).all()


def test_generate_workload_profiles_matched_concurrency() -> None:
    profiles = generate_workload_profiles(
        n_profiles=5,
        concurrency_levels=[1, 4],
        matched_concurrency=True,
        seed=42,
    )
    # 5 base profiles x 2 concurrency levels = 10 matched rows
    assert len(profiles) == 10
    assert "base_workload_id" in profiles.columns
    assert profiles["base_workload_id"].nunique() == 5
    # Each base workload has exactly 2 rows
    assert (profiles["base_workload_id"].value_counts() == 2).all()
    # Concurrency levels are [1, 4] for each pair
    for _, group in profiles.groupby("base_workload_id"):
        assert set(group["concurrency"]) == {1, 4}
        # Non-concurrency features must match exactly within a matched pair
        assert group["query_type"].nunique() == 1
        assert group["read_ratio"].nunique() == 1
        assert group["payload_bytes"].nunique() == 1
        assert group["dataset_records"].nunique() == 1


def test_feasibility_vector_and_rag() -> None:
    vec_workload = {"query_type": "vector_similarity", "vector_dimensions": 128, "top_k": 10}
    res = evaluate_feasibility(vec_workload)
    assert res.feasible_databases == ["Qdrant"]
    assert res.requires_ml_selection is False
    assert "Redis" in res.rejected_reasons

    rag_workload = {"query_type": "rag_retrieval", "vector_dimensions": 384, "top_k": 5}
    res_rag = evaluate_feasibility(rag_workload)
    assert res_rag.feasible_databases == ["Qdrant"]


def test_feasibility_graph_traversal() -> None:
    graph_workload = {"query_type": "graph_traversal", "graph_depth": 3}
    res = evaluate_feasibility(graph_workload)
    assert res.feasible_databases == ["Neo4j"]
    assert res.requires_ml_selection is False


def test_feasibility_crud_workload() -> None:
    crud_workload = {"query_type": "key_value_crud", "payload_bytes": 512}
    res = evaluate_feasibility(crud_workload)
    assert set(res.feasible_databases) == {"Redis", "MongoDB", "Cassandra", "Neo4j"}
    assert res.requires_ml_selection is True
    assert "Qdrant" in res.rejected_reasons
