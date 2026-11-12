"""Streamlit research dashboard for NoSQL pattern recommendation and results inspection."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from nosql_rag.data.persistence import load_raw_runs
from nosql_rag.models.inference import recommend_database
from nosql_rag.models.training import load_model_artifacts
from nosql_rag.workloads.compatibility import ALL_DATABASES

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
    st.success(
        f"✅ Loaded {len(runs_df)} genuine benchmark run records. Data provenance: Genuine Benchmarks."
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

tab_rec, tab_feasibility, tab_benchmarks, tab_about = st.tabs(
    ["🎯 Pattern Recommender", "⚖️ Compatibility Matrix", "📊 Benchmark Explorer", "📖 Research Methodology"]
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
        st.markdown("---")
        pipeline = None
        if model_path.exists():
            try:
                pipeline = load_model_artifacts(model_path)
            except Exception as e:
                st.error(f"Failed to load trained model: {e}")

        # Execute two-stage recommendation
        result = recommend_database(workload_input, trained_pipeline=pipeline)

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
                    st.write(f"- ✅ **{db}**: Feasible for this workload")
                else:
                    reason = result["rejected_reasons"].get(db, "Incompatible data model")
                    st.write(f"- ❌ **{db}**: {reason}")

            if result.get("class_probabilities"):
                st.markdown("#### Model Selection Probabilities")
                prob_df = pd.DataFrame(
                    [
                        {"Database": k, "Probability": round(v, 4)}
                        for k, v in result["class_probabilities"].items()
                    ]
                )
                st.bar_chart(prob_df.set_index("Database"))

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
    st.dataframe(pd.DataFrame(matrix_data), use_container_width=True)

# -----------------------------------------------------------------------------
# Tab 3: Benchmark Explorer
# -----------------------------------------------------------------------------
with tab_benchmarks:
    st.subheader("Experimental Results Explorer")
    if runs_df.empty:
        st.write("No measurements available.")
    else:
        st.dataframe(runs_df.head(50), use_container_width=True)
        if "p95_latency_ms" in runs_df.columns and "database" in runs_df.columns:
            st.markdown("#### Latency by Database (p95 ms)")
            fig_data = (
                runs_df[runs_df["status"] == "success"]
                .groupby("database")["p95_latency_ms"]
                .median()
                .reset_index()
            )
            st.bar_chart(fig_data.set_index("database"))

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
           - Grouped splits by `workload_id` guarantee no test-set leakage.
        3. **Explainability & Regret:**
           - Feature contributions are interpreted via SHAP.
           - Quality is measured by relative latency regret against the Oracle best feasible store.
        """
    )
