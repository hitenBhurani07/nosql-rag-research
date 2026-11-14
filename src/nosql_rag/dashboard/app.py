"""Streamlit research dashboard for NoSQL pattern recommendation and results inspection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from nosql_rag.data.persistence import load_raw_runs
from nosql_rag.explainability.shap_explainer import explain_instance_with_shap
from nosql_rag.models.inference import recommend_database
from nosql_rag.models.training import load_model_artifacts
from nosql_rag.workloads.compatibility import ALL_DATABASES, evaluate_feasibility

# -----------------------------------------------------------------------------
# Repository Root & Path Resolution
# -----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]

st.set_page_config(
    page_title="NoSQL Pattern Selector — RAG Research",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Cached Data & Model Loaders (Path-Safe & Offline)
# -----------------------------------------------------------------------------
@st.cache_data
def load_benchmark_runs(file_path_str: str) -> pd.DataFrame:
    """Load raw benchmark runs from disk with caching."""
    path = Path(file_path_str)
    if path.exists() and path.stat().st_size > 0:
        return load_raw_runs(path)
    return pd.DataFrame()


@st.cache_resource
def load_trained_pipeline(model_path_str: str) -> Any | None:
    """Load trained ML recommender artifact with caching."""
    path = Path(model_path_str)
    if path.exists() and path.stat().st_size > 0:
        try:
            return load_model_artifacts(path)
        except Exception:
            return None
    return None


@st.cache_data
def load_json_benchmark(json_path_str: str) -> dict[str, Any] | None:
    """Load JSON benchmark result with caching."""
    path = Path(json_path_str)
    if path.exists() and path.stat().st_size > 0:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


@st.cache_data
def load_csv_table(table_path_str: str) -> pd.DataFrame:
    """Load tabular CSV result with caching."""
    path = Path(table_path_str)
    if path.exists() and path.stat().st_size > 0:
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


# Paths relative to repo root
RAW_RUNS_PATH = REPO_ROOT / "data" / "raw" / "crud_benchmark_runs.csv"
MODEL_PATH = REPO_ROOT / "results" / "models" / "best_nosql_recommender.joblib"
MODEL_METRICS_PATH = REPO_ROOT / "reports" / "tables" / "model_comparison.csv"
CV_METRICS_PATH = REPO_ROOT / "reports" / "tables" / "cv_metrics.csv"
REGRET_TABLE_PATH = REPO_ROOT / "reports" / "tables" / "latency_regret.csv"
FIGURES_PATH = REPO_ROOT / "reports" / "figures"
BENCHMARKS_PATH = REPO_ROOT / "results" / "benchmarks"

# Load primary datasets
runs_df = load_benchmark_runs(str(RAW_RUNS_PATH))
pipeline = load_trained_pipeline(str(MODEL_PATH))

# -----------------------------------------------------------------------------
# Header & Project Overview
# -----------------------------------------------------------------------------
st.title("🧭 ML-Driven NoSQL Pattern Selector for RAG Workloads")
st.markdown(
    """
    **An empirical research framework and explainable machine-learning system** that evaluates and recommends
    appropriate NoSQL database patterns (**Redis, MongoDB, Apache Cassandra, Neo4j, Qdrant**) for diverse operational
    and Retrieval-Augmented Generation (RAG) workloads. Powered by **1,356 genuine in-container benchmark runs**,
    leakage-safe grouped cross-validation, and SHAP explainability.
    """
)

# -----------------------------------------------------------------------------
# Sidebar: Project Status & Data Provenance Breakdown
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("🔬 Project Environment")
    st.markdown(
        """
        - **Host OS**: Microsoft Windows 11
        - **CPU**: Intel Core i5-12500H (12C / 16T)
        - **RAM**: 16 GB (WSL2 capped at 3 GB)
        - **Storage**: NVMe SSD
        - **Client**: `nosql-rag-client:1.0` (in-container compose network)
        - **Concurrency Backend**: Multiprocessing ($c=4$)
        """
    )
    st.divider()

    st.header("📊 Data Provenance Summary")
    if not runs_df.empty and "data_provenance" in runs_df.columns:
        prov_counts = runs_df["data_provenance"].value_counts().to_dict()
        genuine_count = prov_counts.get("genuine_benchmark", 0)
        host_pilot_count = prov_counts.get("host_port_forward_pilot", 0)
        cloud_count = prov_counts.get("remote_cloud_pilot", 0)
        invalid_count = prov_counts.get("invalid_measurement_artifact", 0)

        st.metric("Total Raw Records", len(runs_df))
        st.metric("Genuine In-Container Runs", genuine_count, help="100% genuine benchmark runs used for ML")
        st.metric("Quarantined Host Pilot", host_pilot_count, help="Flawed Windows port-forwarding pilot")

        with st.expander("Detailed Provenance Counts"):
            st.write(f"- **genuine_benchmark**: {genuine_count}")
            st.write(f"- **host_port_forward_pilot**: {host_pilot_count}")
            st.write(f"- **remote_cloud_pilot**: {cloud_count}")
            st.write(f"- **invalid_measurement_artifact**: {invalid_count}")
            st.caption("⚠️ Pilot & artifact rows are quarantined and excluded from ML models.")
    else:
        st.warning(f"Benchmark file not found: `{RAW_RUNS_PATH}`")

    st.divider()
    st.caption("Offline Research Dashboard • Zero live database connection required.")

# -----------------------------------------------------------------------------
# 7 Core Research Tabs
# -----------------------------------------------------------------------------
tab_rec, tab_feasibility, tab_benchmarks, tab_models, tab_regret, tab_retrieval, tab_about = st.tabs(
    [
        "1. Pattern Recommender",
        "2. Compatibility Matrix",
        "3. CRUD Benchmark Explorer",
        "4. Models & SHAP",
        "5. Latency Regret",
        "6. Retrieval & Graph",
        "7. Methodology & Findings",
    ]
)

# -----------------------------------------------------------------------------
# Tab 1: Pattern Recommender
# -----------------------------------------------------------------------------
with tab_rec:
    st.subheader("Interactive Two-Stage Pattern Recommender")
    st.info(
        "💡 **In single-key CRUD, Redis wins almost everything; the model matches the majority baseline. "
        "Stage 1 feasibility (vector -> Qdrant, graph -> Neo4j) is where other stores become relevant.**"
    )

    st.markdown("#### Input Workload Profile")
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
            help="Defines the core functional access pattern required by the workload.",
        )
        payload_bytes = st.select_slider(
            "Average Payload Size (Bytes)",
            options=[128, 512, 1024, 2048, 4096, 8192, 16384],
            value=1024,
        )
    with col2:
        read_ratio = st.slider("Read Ratio (vs. Write)", 0.05, 1.0, 0.80, step=0.05)
        write_ratio = round(1.0 - read_ratio, 2)
        st.caption(f"Calculated Write Ratio: **{write_ratio}**")
        dataset_records = st.number_input(
            "Dataset Records", min_value=100, max_value=10_000_000, value=10_000, step=1000
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

    if st.button("Generate Recommendation", type="primary", use_container_width=True):
        try:
            feasibility = evaluate_feasibility(workload_input)
        except Exception as exc:
            st.error(f"Could not evaluate workload feasibility: {exc}")
            feasibility = None

        if feasibility is not None:
            if pipeline is None and feasibility.requires_ml_selection:
                st.warning(
                    f"Feasibility evaluated, but trained model artifact is missing at `{MODEL_PATH}`. "
                    "No ML score could be calculated."
                )
                st.write(f"**Feasible candidates:** {', '.join(feasibility.feasible_databases)}")
                st.write(feasibility.notes)
            else:
                try:
                    result = recommend_database(workload_input, trained_pipeline=pipeline)
                except Exception as exc:
                    st.error(f"Recommendation calculation failed: {exc}")
                else:
                    st.divider()
                    rec_col, detail_col = st.columns([1, 2])
                    with rec_col:
                        st.metric(
                            label="Recommended Database",
                            value=result["recommended_database"],
                            delta=f"Via {result['stage']}",
                        )
                        st.info(f"**Workload Family:** `{result['workload_family']}`")
                        st.caption(f"**Evaluation Protocol:** `{result['evaluation_protocol']}`")

                    with detail_col:
                        st.markdown("#### Selection Rationale")
                        st.write(result["notes"])
                        st.markdown("#### Candidate Eligibility Breakdown")
                        for db in ALL_DATABASES:
                            if db in result["feasible_databases"]:
                                st.write(f"- ✅ **{db}**: Feasible for this data model and access pattern.")
                            else:
                                reason = result["rejected_reasons"].get(db, "Incompatible data model")
                                st.write(f"- ❌ **{db}**: {reason}")

                        if result.get("class_probabilities"):
                            st.markdown("#### Stage 2 Model Selection Probabilities")
                            prob_df = pd.DataFrame(
                                [
                                    {"Database": key, "Probability": round(value, 4)}
                                    for key, value in result["class_probabilities"].items()
                                ]
                            )
                            st.bar_chart(prob_df.set_index("Database"), y="Probability")

                    if not runs_df.empty and "data_provenance" in runs_df.columns:
                        genuine_runs = runs_df[runs_df["data_provenance"] == "genuine_benchmark"]
                        if not genuine_runs.empty and result["stage"] == "stage_2_ml_performance_selection":
                            st.markdown("#### Live Measured Latency Comparison for Your Workload Profile")
                            avail_p = sorted(genuine_runs["payload_bytes"].dropna().unique())
                            avail_r = sorted(genuine_runs["read_ratio"].dropna().unique())
                            avail_c = sorted(genuine_runs["concurrency"].dropna().unique())

                            closest_p = min(avail_p, key=lambda x: abs(x - payload_bytes))
                            closest_r = min(avail_r, key=lambda x: abs(x - read_ratio))
                            closest_c = min(avail_c, key=lambda x: abs(x - concurrency))

                            matched_slice = genuine_runs[
                                (genuine_runs["payload_bytes"] == closest_p)
                                & (genuine_runs["read_ratio"] == closest_r)
                                & (genuine_runs["concurrency"] == closest_c)
                            ]

                            if not matched_slice.empty:
                                st.caption(
                                    f"Dynamic benchmark slice matching your inputs: **{closest_p} B payload**, "
                                    f"**{int(closest_r * 100)}% read ratio**, **c={closest_c} concurrency**."
                                )
                                lat_agg = (
                                    matched_slice.groupby("database")[["p50_latency_ms", "p95_latency_ms"]]
                                    .median()
                                    .reset_index()
                                )
                                best_p95 = lat_agg["p95_latency_ms"].min()
                                lat_agg["Latency Penalty vs Winner"] = lat_agg["p95_latency_ms"].apply(
                                    lambda v: "0.00% (Winner)"
                                    if v == best_p95
                                    else f"+{((v - best_p95) / best_p95) * 100:.1f}% slower"
                                )
                                lat_agg.columns = [
                                    "Database",
                                    "Median P50 (ms)",
                                    "Median P95 (ms)",
                                    "Latency Penalty vs Winner",
                                ]
                                st.dataframe(lat_agg, width="stretch", hide_index=True)

                                col_c1, col_c2 = st.columns(2)
                                with col_c1:
                                    st.markdown("##### Median P95 Latency (ms) — Lower is Better")
                                    st.bar_chart(lat_agg.set_index("Database")["Median P95 (ms)"])
                                with col_c2:
                                    st.markdown("##### Median P50 Latency (ms) — Lower is Better")
                                    st.bar_chart(lat_agg.set_index("Database")["Median P50 (ms)"])

                    if pipeline is not None and result["stage"] == "stage_2_ml_performance_selection":
                        st.markdown("#### Instance-Level SHAP Feature Attribution")
                        try:
                            attribution = explain_instance_with_shap(
                                pipeline,
                                pd.DataFrame([workload_input]),
                                result["recommended_database"],
                            )
                            st.dataframe(attribution.head(10), width="stretch", hide_index=True)
                            st.caption(
                                "Attributions indicate directional feature influence toward the selected class."
                            )
                        except Exception as exc:
                            st.info(f"Instance SHAP explanation unavailable: {exc}")

# -----------------------------------------------------------------------------
# Tab 2: Compatibility Matrix
# -----------------------------------------------------------------------------
with tab_feasibility:
    st.subheader("Stage 1 Data-Model Feasibility Matrix")
    st.markdown(
        """
        The candidate stores cannot be compared along a single flat latency benchmark without violating scientific comparability.
        **Stage 1** enforces hard data-model boundaries before any performance model is queried:
        """
    )
    matrix_data = [
        {
            "Workload Family": "Key-Value CRUD (Single-Key Point Reads/Updates)",
            "Redis": "✅ Native (In-Memory Key-Value)",
            "MongoDB": "✅ Native (_id index)",
            "Cassandra": "✅ Native (Partition key)",
            "Neo4j": "✅ Supported (Indexed node)",
            "Qdrant": "❌ Excluded (Specialized vector store)",
            "Stage 1 Routing": "Passes to Stage 2 (Empirical ML selection)",
        },
        {
            "Workload Family": "Document / Nested JSON Entities",
            "Redis": "⚠️ RedisJSON required",
            "MongoDB": "✅ Native (BSON document engine)",
            "Cassandra": "⚠️ Rigid schema required",
            "Neo4j": "⚠️ Property map serialization",
            "Qdrant": "❌ Excluded (Specialized vector store)",
            "Stage 1 Routing": "Passes to Stage 2 (Empirical ML selection)",
        },
        {
            "Workload Family": "High-Throughput Partitioned Writes",
            "Redis": "⚠️ In-memory size bounded",
            "MongoDB": "⚠️ Sharded collection overhead",
            "Cassandra": "✅ Native (LSM append commitlog)",
            "Neo4j": "⚠️ Transaction lock contention",
            "Qdrant": "❌ Excluded (Specialized vector store)",
            "Stage 1 Routing": "Passes to Stage 2 (Empirical ML selection)",
        },
        {
            "Workload Family": "Multi-hop Graph Traversal (Depth >= 2)",
            "Redis": "❌ Infeasible natively",
            "MongoDB": "❌ Multi-hop $graphLookup slow",
            "Cassandra": "❌ Infeasible natively",
            "Neo4j": "✅ Native (Index-Free Adjacency)",
            "Qdrant": "❌ Excluded (Specialized vector store)",
            "Stage 1 Routing": "Deterministic routing directly to Neo4j",
        },
        {
            "Workload Family": "Dense Vector ANN Search",
            "Redis": "⚠️ Requires RediSearch extension",
            "MongoDB": "⚠️ Atlas Vector Search required",
            "Cassandra": "⚠️ CEP-30 extension required",
            "Neo4j": "⚠️ Basic vector index",
            "Qdrant": "✅ Native (HNSW + Payload filter)",
            "Stage 1 Routing": "Deterministic routing directly to Qdrant",
        },
        {
            "Workload Family": "End-to-End RAG Passage Retrieval",
            "Redis": "⚠️ Metadata cache only",
            "MongoDB": "⚠️ Passage metadata store only",
            "Cassandra": "⚠️ Large corpus store only",
            "Neo4j": "⚠️ Graph-RAG entity relationships",
            "Qdrant": "✅ Native Dense Retrieval",
            "Stage 1 Routing": "Deterministic routing directly to Qdrant",
        },
    ]
    st.dataframe(pd.DataFrame(matrix_data), width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Tab 3: CRUD Benchmark Explorer
# -----------------------------------------------------------------------------
with tab_benchmarks:
    st.subheader("Genuine In-Container CRUD Benchmark Explorer")
    if runs_df.empty:
        st.warning(f"No benchmark runs found at `{RAW_RUNS_PATH}`.")
    else:
        genuine_df = runs_df[runs_df.get("data_provenance") == "genuine_benchmark"]

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Total Raw Records", len(runs_df))
        col_m2.metric("Genuine Benchmark Runs", len(genuine_df), delta="100% genuine")
        col_m3.metric("Error Rate (Genuine)", f"{genuine_df['error_rate'].mean():.2%}")
        col_m4.metric("Client Placement", "in-container bridge")

        st.markdown("#### 1. Completeness Audit by Database Engine")
        expected_runs = {"Redis": 450, "MongoDB": 450, "Cassandra": 228, "Neo4j": 228}
        engine_rows = []
        for db, expected in expected_runs.items():
            completed = int((genuine_df["database"] == db).sum())
            engine_rows.append(
                {
                    "Database": db,
                    "Target Runs": expected,
                    "Completed Genuine Runs": completed,
                    "Completeness": f"{(completed / expected) * 100:.1f}%",
                    "Status": "✅ Complete" if completed == expected else "⚠️ Incomplete",
                }
            )
        st.dataframe(pd.DataFrame(engine_rows), width="stretch", hide_index=True)

        st.markdown("#### 2. Provenance Partitioning & Quarantine Status")
        prov_summary = (
            runs_df.groupby("data_provenance")
            .agg(
                record_count=("run_id", "count"),
                successful_count=("status", lambda s: (s == "success").sum()),
                databases=("database", lambda s: ", ".join(sorted(s.unique()))),
            )
            .reset_index()
        )
        prov_summary["Included in Research ML"] = prov_summary["data_provenance"].apply(
            lambda p: "✅ Yes" if p == "genuine_benchmark" else "❌ No (Quarantined)"
        )
        st.dataframe(prov_summary, width="stretch", hide_index=True)

        st.markdown("#### 3. Interactive Parameter Slice & Live Benchmark Visualization")
        st.caption("Select parameters below to dynamically filter benchmark runs and watch the charts re-render live:")

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_concurrency = st.radio(
                "Filter Concurrency",
                options=["All Concurrencies", "c=1 (Sequential)", "c=4 (Multiprocessing)"],
                horizontal=True,
            )
        with col_f2:
            avail_payloads = sorted(genuine_df["payload_bytes"].dropna().unique())
            filter_payloads = st.multiselect(
                "Filter Payload Size",
                options=avail_payloads,
                default=avail_payloads,
                format_func=lambda x: f"{x} Bytes",
            )
        with col_f3:
            avail_reads = sorted(genuine_df["read_ratio"].dropna().unique())
            filter_reads = st.multiselect(
                "Filter Read Ratio",
                options=avail_reads,
                default=avail_reads,
                format_func=lambda x: f"{int(x * 100)}% Read",
            )

        # Apply user filters
        sliced_df = genuine_df.copy()
        if filter_concurrency == "c=1 (Sequential)":
            sliced_df = sliced_df[sliced_df["concurrency"] == 1]
        elif filter_concurrency == "c=4 (Multiprocessing)":
            sliced_df = sliced_df[sliced_df["concurrency"] == 4]

        if filter_payloads:
            sliced_df = sliced_df[sliced_df["payload_bytes"].isin(filter_payloads)]
        if filter_reads:
            sliced_df = sliced_df[sliced_df["read_ratio"].isin(filter_reads)]

        if not sliced_df.empty:
            slice_summary = (
                sliced_df.groupby("database")
                .agg(
                    median_p50_ms=("p50_latency_ms", "median"),
                    median_p95_ms=("p95_latency_ms", "median"),
                    median_throughput_ops=("throughput_ops_sec", "median"),
                    matching_runs=("run_id", "count"),
                )
                .reset_index()
            )
            st.dataframe(slice_summary, width="stretch", hide_index=True)

            col_ch1, col_ch2 = st.columns(2)
            with col_ch1:
                st.markdown("##### Dynamic Median P95 Latency (ms) — Lower is Better")
                st.bar_chart(slice_summary.set_index("database")["median_p95_ms"])
            with col_ch2:
                st.markdown("##### Dynamic Median Throughput (ops/sec) — Higher is Better")
                st.bar_chart(slice_summary.set_index("database")["median_throughput_ops"])
        else:
            st.info("No benchmark runs match the selected parameter filter.")

        with st.expander("Explore Raw Filtered Run Records"):
            selected_dbs = st.multiselect(
                "Filter by Database",
                options=sorted(runs_df["database"].dropna().unique()),
                default=sorted(runs_df["database"].dropna().unique()),
            )
            selected_prov = st.multiselect(
                "Filter by Provenance",
                options=sorted(runs_df["data_provenance"].dropna().unique()),
                default=["genuine_benchmark"],
            )
            filtered_df = runs_df[
                runs_df["database"].isin(selected_dbs) & runs_df["data_provenance"].isin(selected_prov)
            ]
            st.dataframe(filtered_df, width="stretch", hide_index=True)

# -----------------------------------------------------------------------------
# Tab 4: Models & SHAP
# -----------------------------------------------------------------------------
with tab_models:
    st.subheader("Machine Learning Evaluation & SHAP Explainability")
    st.warning(
        "⚠️ **Evaluation Degeneracy Finding**: Because in-memory Redis uniformly dominates disk-backed engines "
        "across single-key CRUD workloads under local networking, the held-out test sets contain a single class (`Redis`). "
        "The reported 1.0000 Test Accuracy and Macro-F1 scores are mathematically degenerate: the models merely match the "
        "majority baseline, and there is **no learnable multi-class signal** in scalar CRUD."
    )
    st.info(
        "ℹ️ **Historical Flawed Pilot Note**: Earlier host-path benchmarks through Windows port forwarding artificially delayed "
        "multi-segment packets, producing an apparent 0.8245 Macro-F1. That was a measurement artifact (42.67% label error) "
        "and is quarantined as `host_port_forward_pilot`."
    )

    selected_analysis = st.radio(
        "Select Machine Learning Dataset Analysis",
        ["Analysis A (2 Engines: Redis + MongoDB, 150 Profiles)", "Analysis B (4 Engines: Redis + MongoDB + Cassandra + Neo4j, 76 Profiles)"],
        horizontal=True,
    )

    dataset_key = (
        "2-Engine (Redis + MongoDB, 150 Profiles)"
        if "2 Engines" in selected_analysis
        else "4-Engine (Redis + MongoDB + Cassandra + Neo4j, 76 Profiles)"
    )

    model_comp_df = load_csv_table(str(MODEL_METRICS_PATH))
    cv_comp_df = load_csv_table(str(CV_METRICS_PATH))

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### Held-Out Test Evaluation")
        if not model_comp_df.empty and "dataset" in model_comp_df.columns:
            subset_test = model_comp_df[model_comp_df["dataset"] == dataset_key]
            st.dataframe(subset_test, width="stretch", hide_index=True)
        else:
            st.warning(f"Model comparison table not available: `{MODEL_METRICS_PATH}`")

    with col_t2:
        st.markdown("#### Leakage-Safe Grouped Cross-Validation")
        if not cv_comp_df.empty and "dataset" in cv_comp_df.columns:
            subset_cv = cv_comp_df[cv_comp_df["dataset"] == dataset_key]
            st.dataframe(subset_cv, width="stretch", hide_index=True)
        else:
            st.warning(f"CV metrics table not available: `{CV_METRICS_PATH}`")

    st.markdown("#### Evaluation Visualizations")
    col_img1, col_img2 = st.columns(2)
    with col_img1:
        cm_path = FIGURES_PATH / "confusion_matrix.png"
        if cm_path.exists():
            st.image(str(cm_path), caption="Held-Out Confusion Matrix (Reflects Single-Class Redis Test Set)", width="stretch")
        else:
            st.info(f"Confusion matrix image not found: `{cm_path}`")

    with col_img2:
        shap_file = (
            "shap_summary_2-engine_(redis_+_mongodb,_150_profiles).png"
            if "2 Engines" in selected_analysis
            else "shap_summary_4-engine_(redis_+_mongodb_+_cassandra_+_neo4j,_76_profiles).png"
        )
        shap_path = FIGURES_PATH / shap_file
        if not shap_path.exists():
            shap_path = FIGURES_PATH / "shap_summary.png"
        if shap_path.exists():
            st.image(str(shap_path), caption=f"Global SHAP Feature Attribution ({dataset_key})", width="stretch")
        else:
            st.info(f"SHAP summary image not found: `{shap_path}`")

# -----------------------------------------------------------------------------
# Tab 5: Latency Regret
# -----------------------------------------------------------------------------
with tab_regret:
    st.subheader("Latency Regret Evaluation vs. Oracle Best")
    st.markdown(
        r"""
        Latency regret quantifies the performance penalty incurred by a selected engine relative to the Oracle:
        $$\text{Regret}(W) = \frac{\text{Latency}_{\text{selected}}(W) - \text{Latency}_{\text{oracle}}(W)}{\text{Latency}_{\text{oracle}}(W)}$$
        """
    )

    regret_df = load_csv_table(str(REGRET_TABLE_PATH))
    if not regret_df.empty and "dataset" in regret_df.columns:
        sel_reg_analysis = st.radio(
            "Select Regret Dataset",
            ["Analysis A (2-Engine, 150 Profiles)", "Analysis B (4-Engine, 76 Profiles)"],
            horizontal=True,
        )
        reg_key = (
            "2-Engine (Redis + MongoDB, 150 Profiles)"
            if "2-Engine" in sel_reg_analysis
            else "4-Engine (Redis + MongoDB + Cassandra + Neo4j, 76 Profiles)"
        )

        sub_reg = regret_df[regret_df["dataset"] == reg_key].copy()
        sub_reg["mean_regret_pct"] = sub_reg["mean_regret"].apply(lambda v: f"{v * 100:.2f}%")
        sub_reg["median_regret_pct"] = sub_reg["median_regret"].apply(lambda v: f"{v * 100:.2f}%")
        sub_reg["p95_regret_pct"] = sub_reg["p95_regret"].apply(lambda v: f"{v * 100:.2f}%")

        col_reg_table, col_reg_chart = st.columns([1, 1])
        with col_reg_table:
            st.markdown(f"#### Regret Table: {reg_key}")
            display_cols = ["strategy", "mean_regret_pct", "median_regret_pct", "p95_regret_pct", "evaluated_workloads"]
            st.dataframe(sub_reg[display_cols], width="stretch", hide_index=True)

        with col_reg_chart:
            st.markdown(f"#### Strategy Latency Overhead vs Oracle ({reg_key})")
            reg_chart_data = sub_reg.set_index("strategy")[["mean_regret", "median_regret"]]
            reg_chart_data.columns = ["Mean Regret Multiplier", "Median Regret Multiplier"]
            st.bar_chart(reg_chart_data)

            with st.expander("View Publication Density Plot", expanded=False):
                reg_fig_name = (
                    "latency_regret_2-engine_(redis_+_mongodb,_150_profiles).png"
                    if "2-Engine" in sel_reg_analysis
                    else "latency_regret_4-engine_(redis_+_mongodb_+_cassandra_+_neo4j,_76_profiles).png"
                )
                reg_fig_path = FIGURES_PATH / reg_fig_name
                if not reg_fig_path.exists():
                    reg_fig_path = FIGURES_PATH / "latency_regret.png"
                if reg_fig_path.exists():
                    st.image(str(reg_fig_path), caption=f"Latency Regret Distribution ({reg_key})", width="stretch")
                else:
                    st.info(f"Regret plot not found: `{reg_fig_path}`")
    else:
        st.warning(f"Regret table not available at `{REGRET_TABLE_PATH}`.")

# -----------------------------------------------------------------------------
# Tab 6: Retrieval & Graph
# -----------------------------------------------------------------------------
with tab_retrieval:
    st.subheader("Specialized Workload Evaluation: Vector Search & Graph Traversal")

    st.markdown("### 1. Full BEIR SciFact RAG Retrieval (All 300 Test Queries)")
    beir_res = load_json_benchmark(str(BENCHMARKS_PATH / "beir_scifact_qdrant_results.json"))
    if beir_res:
        b_c1, b_c2, b_c3, b_c4 = st.columns(4)
        b_c1.metric("Recall@10", f"{beir_res.get('recall_at_10', 0):.4f}")
        b_c2.metric("NDCG@10", f"{beir_res.get('ndcg_at_10', 0):.4f}")
        b_c3.metric("MRR", f"{beir_res.get('mrr', 0):.4f}")
        b_c4.metric("Queries Evaluated", beir_res.get("queries_evaluated", 300))

        b_l1, b_l2 = st.columns(2)
        b_l1.metric("P50 Search Latency", f"{beir_res.get('p50_query_latency_ms', 0):.2f} ms")
        b_l2.metric("P95 Search Latency", f"{beir_res.get('p95_query_latency_ms', 0):.2f} ms")
        st.caption("⚠️ **Measurement Placement**: Measured from host client; labeled as host-path, not comparable to in-container CRUD latencies.")
        with st.expander("Inspect Full BEIR SciFact JSON"):
            st.json(beir_res)
    else:
        st.warning("BEIR SciFact results file not found.")

    st.divider()

    st.markdown("### 2. Native Qdrant Dense Vector ANN Indexing")
    qdrant_ann = load_json_benchmark(str(BENCHMARKS_PATH / "qdrant_ann_runs.json"))
    if qdrant_ann:
        q_c1, q_c2, q_c3 = st.columns(3)
        q_c1.metric("Mean Recall@10", f"{qdrant_ann.get('mean_recall_at_k', 0):.4f} (100%)")
        q_c2.metric("Vector Dimensions", qdrant_ann.get("vector_size", 128))
        q_c3.metric("Vector Index Size", f"{qdrant_ann.get('n_vectors', 2000):,} vectors")

        q_l1, q_l2 = st.columns(2)
        q_l1.metric("P50 Latency", f"{qdrant_ann.get('p50_query_latency_ms', 0):.2f} ms")
        q_l2.metric("P95 Latency", f"{qdrant_ann.get('p95_query_latency_ms', 0):.2f} ms")
        st.caption("⚠️ **Measurement Placement**: Measured from host client; labeled as host-path, not comparable to in-container CRUD latencies.")
        with st.expander("Inspect Full Qdrant ANN JSON"):
            st.json(qdrant_ann)
    else:
        st.warning("Qdrant ANN results file not found.")

    st.divider()

    st.markdown("### 3. Neo4j Multi-Hop Graph Traversal")
    neo_res = load_json_benchmark(str(BENCHMARKS_PATH / "neo4j_graph_traversal_runs.json"))
    if neo_res:
        n_c1, n_c2, n_c3 = st.columns(3)
        n_c1.metric("Graph Topology", f"{neo_res.get('n_nodes', 200)} nodes / {neo_res.get('n_edges', 600)} edges")
        n_c2.metric("Traversal Depth", f"{neo_res.get('traversal_depth', 2)} hops")
        n_c3.metric("Throughput", f"{neo_res.get('throughput_ops_sec', 0):.1f} ops/sec")

        n_l1, n_l2, n_l3 = st.columns(3)
        n_l1.metric("P50 Latency", f"{neo_res.get('p50_latency_ms', 0):.2f} ms")
        n_l2.metric("P95 Latency", f"{neo_res.get('p95_latency_ms', 0):.2f} ms")
        n_l3.metric("P99 Latency", f"{neo_res.get('p99_latency_ms', 0):.2f} ms")
        st.caption("Demonstration benchmark executed on a synthetic 200-node graph.")
        with st.expander("Inspect Full Neo4j Graph Traversal JSON"):
            st.json(neo_res)
    else:
        st.warning("Neo4j graph traversal results file not found.")

# -----------------------------------------------------------------------------
# Tab 7: Methodology & Findings
# -----------------------------------------------------------------------------
with tab_about:
    st.subheader("Methodology, Network Findings & Limitations")

    st.markdown(
        r"""
        ### 1. Windows Host Port-Forwarding Artifact (Hypothesis & Resolution)
        - **Symptom**: Initial Windows host-measured Cassandra writes exhibited 48.0 ms latency for payloads $\ge 4\text{ KB}$, whereas internal `nodetool proxyhistograms` showed median write latency of only **258 $\mu$s** (0.258 ms).
        - **Working Hypothesis**: Windows WSL2 hypervisor loopback relaying introduces packet segmentation and delayed-ACK buffering on multi-segment TCP frames ($> 1,460\text{ B}$).
        - **Impact on ML**: Flipped the ground truth winner on **42.67% of workloads** (64 / 150 profiles), generating artificial wins for MongoDB.
        - **Resolution**: Implemented pinned compose-network client (`nosql-rag-client:1.0`), bypassing host virtualization and restoring sub-millisecond local NVMe latencies across all engines (8KB Cassandra writes dropped from 48 ms to 0.491 ms). Earlier host runs were quarantined as `host_port_forward_pilot`.

        ### 2. Concurrency Validity ($c=4$: Multiprocessing vs. Threading)
        - Multi-threaded Python benchmarks suffered an **80.64% queueing overhead** at $c=4$ due to GIL contention and single-process socket serialization.
        - Migrating to a dedicated process worker pool (`multiprocessing.spawn`) increased throughput by **4.25x** (4,580 $\rightarrow$ 19,490 ops/s) and reduced Redis P95 latency from 1.375 ms to 0.266 ms.

        ### 3. Empirical Distribution & Ground Truth Degeneracy
        - **Redis Dominance in Single-Key CRUD**: In pure key-value point reads and updates under local in-container networking, Redis wins 149/150 profiles in Analysis A and 76/76 profiles in Analysis B.
        - **Degenerate Classifier Scores**: Because held-out test splits contain exclusively Redis, models achieve 1.0000 Accuracy/Macro-F1 by matching the majority-class baseline. There is no learnable multi-class signal in single-key CRUD.

        ### 4. Hardware Scope & Research Limitations
        1. **Single-Node Execution**: Containers operated on the same host across a Docker bridge network; distributed replication, WAN latency, and partition tolerance were not modeled.
        2. **Sequential Container Execution**: Engines ran sequentially to strictly respect the 3 GB WSL2 memory cap.
        3. **Untuned Default Configurations with 512M Heaps**: Cassandra and Neo4j ran with minimal 512M JVM heaps to respect RAM limits. Production multi-gigabyte tuning would alter absolute ceilings.
        4. **Sub-Millisecond Sensitivity**: When operations run below 1 ms, driver socket serialization (BSON, RESP, CQL, Bolt) represents a substantial fraction of total time.
        5. **Small-Scale Graph Topology**: The Neo4j graph traversal evaluation was performed on a synthetic demonstration graph of 200 nodes and 600 edges.
        """
    )
