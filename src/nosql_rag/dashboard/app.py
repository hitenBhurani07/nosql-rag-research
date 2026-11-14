"""Streamlit research dashboard for NoSQL pattern recommendation and results inspection."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from nosql_rag.benchmarking import audit_crud_matrix
from nosql_rag.data.persistence import load_raw_runs
from nosql_rag.explainability.shap_explainer import explain_instance_with_shap
from nosql_rag.models.inference import recommend_database
from nosql_rag.models.training import load_model_artifacts
from nosql_rag.workloads.compatibility import ALL_DATABASES, evaluate_feasibility

st.set_page_config(
    page_title="NoSQL Pattern Selector — RAG Research",
    page_icon="🧭",
    layout="wide",
)

st.title("🧭 ML-Driven NoSQL Pattern Selector for RAG Workloads")
st.caption(
    "Explainable two-stage database pattern selection based on workload characteristics and measured benchmarks."
)

# -----------------------------------------------------------------------------
# Data Provenance Banner
# -----------------------------------------------------------------------------
raw_runs_path = Path("data/raw/crud_benchmark_runs.csv")
sample_syn_path = Path("data/sample/synthetic_demo_runs.csv")
model_path = Path("results/models/best_nosql_recommender.joblib")
model_metrics_path = Path("reports/tables/model_comparison.csv")
regret_table_path = Path("reports/tables/latency_regret_by_workload.csv")
figures_path = Path("results/figures")
benchmark_results_path = Path("results/benchmarks")

runs_df = pd.DataFrame()
if raw_runs_path.exists() and raw_runs_path.stat().st_size > 0:
    runs_df = load_raw_runs(raw_runs_path)
    provenance_type = "genuine_experiments"
elif sample_syn_path.exists() and sample_syn_path.stat().st_size > 0:
    runs_df = load_raw_runs(sample_syn_path)
    provenance_type = "synthetic_demo"
else:
    provenance_type = "none"

if provenance_type == "genuine_experiments":
    provenance = runs_df.get("data_provenance", pd.Series(dtype=str))
    genuine_count = int((provenance == "genuine_benchmark").sum())
    synthetic_count = int((provenance == "synthetic_demo").sum())
    st.success(f"Loaded {genuine_count} genuine benchmark rows ({len(runs_df)} total records).")
    if synthetic_count:
        st.warning(
            f"The raw file contains {synthetic_count} synthetic demo rows. "
            "They are excluded from genuine benchmark comparisons."
        )
elif provenance_type == "synthetic_demo":
    st.warning(
        "⚠️ DEMONSTRATION MODE: Using synthetic demonstration measurements (`data_provenance=synthetic_demo`). "
        "No live database credentials were detected on this machine. Synthetic data is never represented as genuine research findings."
    )
else:
    st.info(
        "ℹ️ No benchmark data available yet. Please run the pilot or full benchmark matrix via CLI or Google Colab."
    )

tab_rec, tab_feasibility, tab_benchmarks, tab_models, tab_regret, tab_retrieval, tab_about = st.tabs(
    [
        "Pattern Recommender",
        "Compatibility",
        "CRUD Benchmarks",
        "Models & SHAP",
        "Latency Regret",
        "Retrieval & Graph",
        "Methodology",
    ]
)

# -----------------------------------------------------------------------------
# Tab 1: Recommender
# -----------------------------------------------------------------------------
with tab_rec:
    st.subheader("Workload Profile Input")
    col1, col2, col3 = st.columns(3)
    with col1:
        query_type = st.selectbox(
            "Query / Workload Type",
            [
                "key_value_crud",
                "document_crud",
                "wide_column_crud",
                "graph_traversal",
                "vector_similarity",
                "rag_retrieval",
                "rag_hybrid",
            ],
            help="Defines the core functional pattern required by the workload.",
        )
        payload_bytes = st.select_slider(
            "Average Payload Size (Bytes)",
            options=[128, 512, 1024, 2048, 4096, 8192, 16384],
            value=1024,
        )
    with col2:
        read_ratio = st.slider("Read Ratio (vs. Write)", 0.05, 1.0, 0.80, step=0.05)
        write_ratio = round(1.0 - read_ratio, 2)
        st.caption(f"Write Ratio: {write_ratio}")
        dataset_records = st.number_input(
            "Dataset Records", min_value=100, max_value=10000000, value=10000, step=1000
        )
    with col3:
        concurrency = st.selectbox("Client Concurrency Level", [1, 2, 4, 8, 16], index=2)
        vector_dim = (
            st.number_input("Vector Dimensions", min_value=0, max_value=4096, value=384, step=64)
            if query_type in {"vector_similarity", "rag_retrieval", "rag_hybrid"}
            else 0
        )
        top_k = (
            st.number_input("Top-K Nearest Neighbors", min_value=1, max_value=100, value=10)
            if query_type in {"vector_similarity", "rag_retrieval", "rag_hybrid"}
            else 0
        )
        graph_depth = (
            st.slider("Graph Traversal Depth (hops)", 1, 4, 2)
            if query_type == "graph_traversal"
            else 0
        )

    workload_input = {
        "query_type": query_type,
        "read_ratio": read_ratio,
        "write_ratio": write_ratio,
        "payload_bytes": payload_bytes,
        "dataset_records": dataset_records,
        "data_size_mb": round(dataset_records * payload_bytes / (1024**2), 4),
        "concurrency": concurrency,
        "vector_dimensions": vector_dim,
        "top_k": top_k,
        "graph_depth": graph_depth,
    }

    if st.button("Generate Recommendation", type="primary"):
        pipeline = None
        if model_path.exists():
            try:
                pipeline = load_model_artifacts(model_path)
            except Exception as exc:
                st.error(f"Failed to load trained model: {exc}")

        try:
            feasibility = evaluate_feasibility(workload_input)
        except (KeyError, TypeError, ValueError) as exc:
            st.error(f"Could not evaluate workload feasibility: {exc}")
        else:
            if pipeline is None and feasibility.requires_ml_selection:
                st.warning(
                    "Feasibility was evaluated, but ML ranking is unavailable until a "
                    "validated model artifact is installed. No store was guessed."
                )
                st.write(f"**Feasible candidates:** {', '.join(feasibility.feasible_databases)}")
                st.write(feasibility.notes)
            else:
                try:
                    result = recommend_database(workload_input, trained_pipeline=pipeline)
                except (KeyError, TypeError, ValueError) as exc:
                    st.error(f"Recommendation unavailable: {exc}")
                else:
                    rec_col, detail_col = st.columns([1, 2])
                    with rec_col:
                        st.metric(
                            label="Recommended Pattern",
                            value=result["recommended_database"],
                            delta=f"Stage: {result['stage']}",
                        )
                        st.info(f"**Workload Family:** `{result['workload_family']}`")
                        st.markdown(f"**Evaluation Protocol:** `{result['evaluation_protocol']}`")

                    with detail_col:
                        st.markdown("#### Selection Rationale")
                        st.write(result["notes"])
                        st.markdown("#### Feasible vs. Rejected Engines")
                        for db in ALL_DATABASES:
                            if db in result["feasible_databases"]:
                                st.write(f"- **{db}**: feasible for this workload")
                            else:
                                reason = result["rejected_reasons"].get(db, "Incompatible data model")
                                st.write(f"- **{db}**: {reason}")

                        if result.get("class_probabilities"):
                            st.markdown("#### Model Selection Probabilities")
                            prob_df = pd.DataFrame(
                                [
                                    {"Database": key, "Probability": round(value, 4)}
                                    for key, value in result["class_probabilities"].items()
                                ]
                            )
                            st.bar_chart(prob_df.set_index("Database"))

                    if pipeline is not None and result["stage"] == "stage_2_ml_performance_selection":
                        st.markdown("#### SHAP explanation for this workload")
                        try:
                            attribution = explain_instance_with_shap(
                                pipeline,
                                pd.DataFrame([workload_input]),
                                result["recommended_database"],
                            )
                            st.dataframe(attribution.head(12), width="stretch")
                            st.caption(
                                "SHAP attributions explain model output behavior, not causal effects."
                            )
                        except Exception as exc:
                            st.info(f"Instance explanation is unavailable: {exc}")

# -----------------------------------------------------------------------------
# Tab 2: Compatibility Matrix
# -----------------------------------------------------------------------------
with tab_feasibility:
    st.subheader("Stage 1 Compatibility & Feasibility Matrix")
    st.markdown(
        """
        The five databases cannot be forced into a single flat latency ranking without violating scientific comparability.
        The table below specifies the functional eligibility of each store by workload class:
        """
    )
    matrix_data = [
        {
            "Workload Family": "Key-Value CRUD (YCSB A-F)",
            "Redis": "✅ Native (Primary)",
            "MongoDB": "✅ Native (_id index)",
            "Cassandra": "✅ Native (Partition key)",
            "Neo4j": "✅ Supported (Indexed node)",
            "Qdrant": "❌ Excluded (Vector store)",
        },
        {
            "Workload Family": "Document / Nested JSON",
            "Redis": "⚠️ RedisJSON module required",
            "MongoDB": "✅ Native (Primary)",
            "Cassandra": "⚠️ Schema required",
            "Neo4j": "⚠️ Property map",
            "Qdrant": "❌ Excluded (Vector store)",
        },
        {
            "Workload Family": "High-Throughput Partitioned Writes",
            "Redis": "⚠️ In-memory size bound",
            "MongoDB": "⚠️ Sharding setup required",
            "Cassandra": "✅ Native (Wide-column leader)",
            "Neo4j": "⚠️ Transactional overhead",
            "Qdrant": "❌ Excluded (Vector store)",
        },
        {
            "Workload Family": "Multi-hop Graph Traversal (LDBC)",
            "Redis": "❌ Infeasible natively",
            "MongoDB": "❌ Multi-hop $graphLookup slow",
            "Cassandra": "❌ Infeasible natively",
            "Neo4j": "✅ Native (Index-free adjacency)",
            "Qdrant": "❌ Excluded (Vector store)",
        },
        {
            "Workload Family": "Dense Vector ANN (SIFT / GloVe)",
            "Redis": "⚠️ Vector module required",
            "MongoDB": "⚠️ Atlas Vector Search only",
            "Cassandra": "⚠️ CEP-30 extension only",
            "Neo4j": "⚠️ Vector index limited",
            "Qdrant": "✅ Native (HNSW + Payload filter)",
        },
        {
            "Workload Family": "RAG Passage Retrieval (BEIR)",
            "Redis": "⚠️ Metadata cache only",
            "MongoDB": "⚠️ Metadata store only",
            "Cassandra": "⚠️ Corpus store only",
            "Neo4j": "⚠️ Graph-RAG relations",
            "Qdrant": "✅ Native Dense Retrieval",
        },
    ]
    st.dataframe(pd.DataFrame(matrix_data), width="stretch")

# -----------------------------------------------------------------------------
# Tab 3: CRUD Benchmark Explorer
# -----------------------------------------------------------------------------
with tab_benchmarks:
    st.subheader("Experimental CRUD Results")
    if runs_df.empty:
        st.info("No CRUD measurements are available.")
    else:
        successful = runs_df[runs_df.get("status", pd.Series(index=runs_df.index)) == "success"]
        if "data_provenance" in successful:
            genuine = successful[successful["data_provenance"] == "genuine_benchmark"]
        else:
            genuine = successful.iloc[0:0]

        metric_cols = st.columns(3)
        metric_cols[0].metric("Raw attempts", len(runs_df))
        metric_cols[1].metric("Successful attempts", len(successful))
        metric_cols[2].metric("Genuine successful rows", len(genuine))

        try:
            matrix_audit = audit_crud_matrix(runs_df)
        except (KeyError, TypeError, ValueError) as exc:
            st.warning(f"Matrix completeness could not be established: {exc}")
        else:
            st.metric(
                "Validated expected matrix keys",
                f"{matrix_audit['completed_genuine_keys']} / {matrix_audit['expected_run_keys']}",
            )
            if not matrix_audit["is_complete"]:
                st.warning("The saved CRUD data does not yet complete the approved 1,800-run matrix.")
            if matrix_audit["duplicate_run_ids"] or matrix_audit["duplicate_successful_keys"]:
                st.error("Duplicate run IDs or successful configuration keys require review.")
            if matrix_audit["successful_measurement_errors"]:
                st.error("Some successful rows have invalid latency or error-rate measurements.")
            if matrix_audit["profile_mismatches"]:
                st.error("Recorded workload concurrency or base grouping does not match the profile design.")
            if not matrix_audit["integrity_passed"]:
                st.error("The raw dataset has integrity issues and must be reviewed before training.")

        if not genuine.empty and {"p95_latency_ms", "database"}.issubset(genuine.columns):
            st.markdown("#### Genuine run p95 latency by database")
            summary = (
                genuine.groupby("database")["p95_latency_ms"]
                .agg(median_p95_ms="median", run_count="count")
                .reset_index()
            )
            st.dataframe(summary, width="stretch", hide_index=True)
            st.bar_chart(summary.set_index("database")["median_p95_ms"])

        st.markdown("#### Raw run records")
        st.dataframe(runs_df, width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Tab 4: Model Evaluation and SHAP
# -----------------------------------------------------------------------------
with tab_models:
    st.subheader("Model Evaluation and Explainability")
    if model_metrics_path.exists():
        metrics = pd.read_csv(model_metrics_path)
        st.markdown("#### Held-out model comparison")
        st.dataframe(metrics, width="stretch", hide_index=True)
    else:
        st.info("Held-out model metrics are not available yet.")

    for filename, title in (
        ("confusion_matrix_best_model.png", "Held-out confusion matrix"),
        ("model_comparison.png", "Held-out model metrics"),
        ("shap_summary.png", "Global multi-class SHAP summary"),
    ):
        figure = figures_path / filename
        st.markdown(f"#### {title}")
        if figure.exists():
            st.image(str(figure), width="stretch")
        else:
            st.info(f"{filename} has not been generated from validated benchmark data.")

# -----------------------------------------------------------------------------
# Tab 5: Latency Regret
# -----------------------------------------------------------------------------
with tab_regret:
    st.subheader("Latency Regret Against Baselines")
    regret_figure = figures_path / "latency_regret_comparison.png"
    if regret_figure.exists():
        st.image(str(regret_figure), width="stretch")
    else:
        st.info("Latency regret visualization is not available yet.")
    if regret_table_path.exists():
        regret = pd.read_csv(regret_table_path)
        st.dataframe(regret, width="stretch", hide_index=True)
    else:
        st.info("Per-workload regret measurements are not available yet.")

# -----------------------------------------------------------------------------
# Tab 6: Separate Retrieval and Graph Results
# -----------------------------------------------------------------------------
with tab_retrieval:
    st.subheader("Separate RAG Retrieval and Graph Experiments")
    result_files = (
        ("qdrant_ann_runs.json", "Qdrant ANN"),
        ("beir_scifact_qdrant_results.json", "BEIR SciFact retrieval"),
        ("neo4j_graph_traversal_runs.json", "Neo4j graph traversal"),
    )
    for filename, title in result_files:
        result_path = benchmark_results_path / filename
        with st.expander(title, expanded=True):
            if result_path.exists():
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    st.error(f"Could not read {filename}: {exc}")
                else:
                    st.json(result)
            else:
                st.info(f"{filename} is not available.")

# -----------------------------------------------------------------------------
# Tab 4: Methodology
# -----------------------------------------------------------------------------
with tab_about:
    st.markdown(
        """
        ### Methodology and Research Principles

        1. **Two-Stage Architecture:**
           - **Stage 1 (Feasibility):** Filters candidates using deterministic data-model compatibility.
           - **Stage 2 (Performance):** Ranks feasible candidates using ML models trained strictly on genuine experimental measurements.
        2. **Research Integrity:**
           - Synthetic demonstration data is strictly tagged `synthetic_demo` and barred from training research models.
           - Grouped splits by `base_workload_id` keep matched concurrency pairs out of different splits.
        3. **Explainability & Regret:**
           - Feature contributions are interpreted via SHAP.
           - Quality is measured by relative latency regret against the Oracle best feasible store.
        """
    )
