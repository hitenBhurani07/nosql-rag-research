"""Dual Evaluation Pipeline for NoSQL RAG Research.

Strictly separates:
Dataset A: 2 engines (Redis, MongoDB) x 150 profiles
Dataset B: 4 engines (Redis, MongoDB, Cassandra, Neo4j) x 76 profiles

Computes:
- Median aggregation & best_store labeling
- Grouped train/test split by base_workload_id
- 5-fold GroupKFold cross-validation
- Models: Decision Tree, Random Forest, Gradient Boosting
- Held-out Macro-F1 vs Majority baseline
- Latency regret vs Oracle, Majority, and Always-<engine> baselines
- SHAP feature importance & summary plots
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from nosql_rag.explainability.shap_explainer import explain_model_with_shap
from nosql_rag.features.pipeline import DEFAULT_FEATURE_COLUMNS, build_preprocessor

RANDOM_STATE = 42

def evaluate_dataset(
    name: str,
    raw_df: pd.DataFrame,
    profiles_df: pd.DataFrame,
    target_databases: list[str],
    target_profiles: list[str],
    output_dir: Path,
) -> dict[str, Any]:
    print(f"\n{'='*70}\nEVALUATING DATASET: {name}\nTarget engines: {target_databases}\nProfiles count: {len(target_profiles)}\n{'='*70}")

    # 1. Filter genuine runs
    df_sub = raw_df[
        (raw_df["data_provenance"] == "genuine_benchmark")
        & (raw_df["database"].isin(target_databases))
        & (raw_df["workload_id"].isin(target_profiles))
        & (raw_df["status"] == "success")
    ].copy()

    # 2. Verify repetitions per profile/database
    rep_counts = df_sub.groupby(["workload_id", "database"]).size()
    valid_profiles = []
    for wid in target_profiles:
        profile_reps = [rep_counts.get((wid, db), 0) for db in target_databases]
        if all(r >= 2 for r in profile_reps):
            valid_profiles.append(wid)

    print(f"Profiles with >= 2 reps across all included engines: {len(valid_profiles)} / {len(target_profiles)}")
    df_sub = df_sub[df_sub["workload_id"].isin(valid_profiles)].copy()

    # 3. Median aggregation
    metric_cols = ["p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "mean_latency_ms", "throughput_ops_sec"]
    agg = df_sub.groupby(["workload_id", "database"], as_index=False)[metric_cols].median()

    # 4. Derive best_store labels (min p95 latency)
    pivot_p95 = agg.pivot(index="workload_id", columns="database", values="p95_latency_ms")
    best_store = pivot_p95.idxmin(axis=1)
    best_p95 = pivot_p95.min(axis=1)

    labels_df = profiles_df[profiles_df["workload_id"].isin(valid_profiles)].copy()
    labels_df["best_store"] = labels_df["workload_id"].map(best_store)
    labels_df["best_p95_latency_ms"] = labels_df["workload_id"].map(best_p95)

    print(f"\nLabel distribution for {name}:")
    print(labels_df["best_store"].value_counts(dropna=False))

    # 5. Grouped train/test split by base_workload_id
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=RANDOM_STATE)
    train_idx, test_idx = next(gss.split(labels_df, groups=labels_df["base_workload_id"]))

    train_data = labels_df.iloc[train_idx].copy()
    test_data = labels_df.iloc[test_idx].copy()
    print(f"Train set: {len(train_data)} workloads | Test set: {len(test_data)} workloads")

    feature_cols = [c for c in DEFAULT_FEATURE_COLUMNS if c in labels_df.columns]
    X_train = train_data[feature_cols]
    y_train = train_data["best_store"]
    X_test = test_data[feature_cols]
    y_test = test_data["best_store"]

    majority_store = y_train.value_counts().idxmax()
    majority_pred_test = [majority_store] * len(y_test)
    majority_acc = accuracy_score(y_test, majority_pred_test)
    majority_macro_f1 = f1_score(y_test, majority_pred_test, average="macro", zero_division=0)
    print(f"Majority baseline class: {majority_store} | Test Acc: {majority_acc:.4f} | Test Macro-F1: {majority_macro_f1:.4f}")

    # 6. Model definitions
    unique_classes = sorted(y_train.unique().tolist())
    has_single_class = len(unique_classes) == 1

    models = {
        "Decision Tree": DecisionTreeClassifier(max_depth=6, min_samples_leaf=2, random_state=RANDOM_STATE),
        "Random Forest": RandomForestClassifier(n_estimators=100, min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1),
    }
    if not has_single_class:
        models["Gradient Boosting"] = GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=2, random_state=RANDOM_STATE)
    else:
        models["Gradient Boosting"] = DummyClassifier(strategy="most_frequent")

    fitted_pipes = {}
    preds = {}
    model_rows = [
        {
            "dataset": name,
            "model": "Majority Baseline",
            "accuracy": round(majority_acc, 4),
            "macro_f1": round(majority_macro_f1, 4),
        }
    ]

    for m_name, estimator in models.items():
        pipe = Pipeline([("preprocess", build_preprocessor(feature_cols)), ("model", estimator)])
        pipe.fit(X_train, y_train)
        pred = pipe.predict(X_test)
        fitted_pipes[m_name] = pipe
        preds[m_name] = pred

        acc = accuracy_score(y_test, pred)
        f1 = f1_score(y_test, pred, average="macro", zero_division=0)
        print(f"Model: {m_name:<18} | Test Acc: {acc:.4f} | Test Macro-F1: {f1:.4f}")
        model_rows.append({
            "dataset": name,
            "model": m_name,
            "accuracy": round(acc, 4),
            "macro_f1": round(f1, 4),
        })

    model_metrics_df = pd.DataFrame(model_rows)

    # 7. Cross-validation (GroupKFold by base_workload_id)
    n_groups = train_data["base_workload_id"].nunique()
    cv_folds = min(5, n_groups)
    gkf = GroupKFold(n_splits=cv_folds)
    cv_rows = []

    for m_name, estimator in models.items():
        accs, f1s = [], []
        for tr_i, val_i in gkf.split(train_data, groups=train_data["base_workload_id"]):
            y_tr = train_data.iloc[tr_i]["best_store"]
            y_val = train_data.iloc[val_i]["best_store"]
            if m_name == "Gradient Boosting" and y_tr.nunique() < 2:
                cur_est = DummyClassifier(strategy="most_frequent")
            else:
                cur_est = estimator
            pipe = Pipeline([("preprocess", build_preprocessor(feature_cols)), ("model", cur_est)])
            pipe.fit(train_data.iloc[tr_i][feature_cols], y_tr)
            val_p = pipe.predict(train_data.iloc[val_i][feature_cols])
            accs.append(accuracy_score(y_val, val_p))
            f1s.append(f1_score(y_val, val_p, average="macro", zero_division=0))
        cv_rows.append({
            "dataset": name,
            "model": m_name,
            "cv_folds": cv_folds,
            "mean_cv_accuracy": round(float(np.mean(accs)), 4),
            "std_cv_accuracy": round(float(np.std(accs)), 4),
            "mean_cv_macro_f1": round(float(np.mean(f1s)), 4),
            "std_cv_macro_f1": round(float(np.std(f1s)), 4),
        })
    cv_df = pd.DataFrame(cv_rows)

    # 8. Latency Regret Evaluation
    # Latency map: (workload_id, db) -> p95
    latency_map = agg.set_index(["workload_id", "database"])["p95_latency_ms"].to_dict()

    regret_rows = []
    strategies = [
        ("Oracle", lambda wid: best_store[wid]),
        ("Majority Baseline", lambda wid: majority_store),
    ]
    for db in target_databases:
        strategies.append((f"Always-{db}", (lambda d: lambda wid: d)(db)))

    best_pipe_name = "Random Forest"
    best_pipe = fitted_pipes[best_pipe_name]
    strategies.append((f"ML Recommender ({best_pipe_name})", lambda wid: str(best_pipe.predict(labels_df[labels_df["workload_id"] == wid][feature_cols])[0])))

    for wid in test_data["workload_id"]:
        oracle_db = best_store[wid]
        oracle_lat = latency_map.get((wid, oracle_db), np.nan)
        if oracle_lat <= 0 or np.isnan(oracle_lat):
            continue

        for strat_name, strat_fn in strategies:
            chosen_db = strat_fn(wid)
            chosen_lat = latency_map.get((wid, chosen_db), np.nan)
            if np.isnan(chosen_lat):
                regret = np.nan
            else:
                regret = (chosen_lat - oracle_lat) / oracle_lat

            regret_rows.append({
                "dataset": name,
                "workload_id": wid,
                "strategy": strat_name,
                "chosen_store": chosen_db,
                "chosen_p95_ms": chosen_lat,
                "oracle_store": oracle_db,
                "oracle_p95_ms": oracle_lat,
                "relative_regret": regret,
            })

    raw_regret_df = pd.DataFrame(regret_rows)
    regret_summary = raw_regret_df.groupby("strategy").agg(
        mean_regret=("relative_regret", "mean"),
        median_regret=("relative_regret", "median"),
        p95_regret=("relative_regret", lambda s: float(np.percentile(s.dropna(), 95)) if len(s.dropna()) else np.nan),
        evaluated_workloads=("workload_id", "count"),
    ).reset_index()

    print(f"\nLatency Regret Summary for {name}:")
    print(regret_summary.to_string(index=False))

    # 9. SHAP Explainability Plot
    shap_path = output_dir / f"shap_summary_{name.lower().replace(' ', '_')}.png"
    try:
        explain_model_with_shap(
            pipeline=best_pipe,
            X_background=X_train,
            X_explain=X_test,
            output_figure_path=shap_path,
        )
        print(f"Saved SHAP plot to {shap_path}")
    except Exception as e:
        print(f"SHAP explanation note for {name}: {e}")

    # 10. Generate Regret Bar Chart
    plt.figure(figsize=(9, 5))
    valid_strat = regret_summary.dropna(subset=["mean_regret"]).sort_values("mean_regret")
    bars = plt.barh(valid_strat["strategy"], valid_strat["mean_regret"] * 100.0, color="#1f77b4")
    plt.xlabel("Mean Relative Latency Regret (%)", fontsize=11)
    plt.title(f"Mean Latency Regret vs. Oracle ({name})", fontsize=12, fontweight="bold")
    plt.grid(axis="x", linestyle="--", alpha=0.7)
    for bar in bars:
        w = bar.get_width()
        plt.text(w + 0.5, bar.get_y() + bar.get_height() / 2, f"{w:.2f}%", va="center", ha="left", fontsize=9)
    plt.tight_layout()
    regret_fig_path = output_dir / f"latency_regret_{name.lower().replace(' ', '_')}.png"
    plt.savefig(regret_fig_path, dpi=200)
    plt.close()
    print(f"Saved regret chart to {regret_fig_path}")

    return {
        "name": name,
        "labels_df": labels_df,
        "agg_df": agg,
        "model_metrics_df": model_metrics_df,
        "cv_df": cv_df,
        "regret_summary": regret_summary,
        "raw_regret_df": raw_regret_df,
        "best_pipe": best_pipe,
    }


def main():
    raw_df = pd.read_csv("data/raw/crud_benchmark_runs.csv")
    profiles_df = pd.read_csv("data/processed/workload_profiles.csv")
    fig_dir = Path("reports/figures")
    tbl_dir = Path("reports/tables")
    fig_dir.mkdir(parents=True, exist_ok=True)
    tbl_dir.mkdir(parents=True, exist_ok=True)

    # Dataset A: Redis + MongoDB (150 profiles)
    res_a = evaluate_dataset(
        name="2-Engine (Redis + MongoDB, 150 Profiles)",
        raw_df=raw_df,
        profiles_df=profiles_df,
        target_databases=["Redis", "MongoDB"],
        target_profiles=sorted(profiles_df["workload_id"].unique().tolist()),
        output_dir=fig_dir,
    )

    # Dataset B: 4 Engines (76 profiles)
    base_38 = sorted(profiles_df["base_workload_id"].unique())[:38]
    p_76 = sorted(profiles_df[profiles_df["base_workload_id"].isin(base_38)]["workload_id"].unique().tolist())
    res_b = evaluate_dataset(
        name="4-Engine (Redis + MongoDB + Cassandra + Neo4j, 76 Profiles)",
        raw_df=raw_df,
        profiles_df=profiles_df,
        target_databases=["Redis", "MongoDB", "Cassandra", "Neo4j"],
        target_profiles=p_76,
        output_dir=fig_dir,
    )

    # Combine tables and persist
    all_models = pd.concat([res_a["model_metrics_df"], res_b["model_metrics_df"]], ignore_index=True)
    all_models.to_csv(tbl_dir / "model_comparison.csv", index=False)
    print("\nSaved reports/tables/model_comparison.csv")

    all_cv = pd.concat([res_a["cv_df"], res_b["cv_df"]], ignore_index=True)
    all_cv.to_csv(tbl_dir / "cv_metrics.csv", index=False)
    print("Saved reports/tables/cv_metrics.csv")

    all_regret = pd.concat([
        res_a["regret_summary"].assign(dataset=res_a["name"]),
        res_b["regret_summary"].assign(dataset=res_b["name"]),
    ], ignore_index=True)
    all_regret.to_csv(tbl_dir / "latency_regret.csv", index=False)
    print("Saved reports/tables/latency_regret.csv")

    # Save primary aggregated and labelled datasets (2-engine 150-profile is standard benchmark matrix)
    res_a["agg_df"].to_csv("data/processed/aggregated_benchmark_runs.csv", index=False)
    res_a["labels_df"].to_csv("data/processed/labelled_workloads.csv", index=False)
    print("Saved data/processed/aggregated_benchmark_runs.csv & labelled_workloads.csv")

    # Persist best recommender pipeline
    model_path = Path("results/models/best_nosql_recommender.joblib")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(res_a["best_pipe"], model_path)
    print(f"Persisted best model pipeline to {model_path}")


if __name__ == "__main__":
    main()
