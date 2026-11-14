# Phase B — Codebase Audit

Generated: 2026-11-14 (Windows local execution run)

## 1. Verified Known Problems

| # | Problem | Verified? | Status |
|---|---------|-----------|--------|
| 1 | Only 8 real measurements, full matrix never ran | ✅ Confirmed | 8 pilot rows in `data/raw/crud_benchmark_runs.csv`. `audit_crud_matrix` reports 0/1800 genuine. |
| 2 | Colab/cloud latencies are network RTT, not engine perf (~175–235ms) | ✅ Confirmed | pilot rows show flat 59–236ms. `hosting_region=local` is false for those rows (they were remote runs). |
| 3 | ~100-hour runtime at 4ops/sec on Colab — cannot finish | ✅ Confirmed | 1800 runs × 1500 ops = 2.7M ops. 4ops/sec → 189h. |
| 4 | Notebook depends on Colab state (Drive mount, in-memory globals) | ✅ Confirmed | Cell 4 defines `RANDOM_SEED`, `FULL_CONCURRENCY_LEVELS`, etc. but cells 5+ can run first in Colab. Package `config.py` has `_get_secret` Colab import. |
| 5 | Full-matrix cell excluded MongoDB | ✅ Confirmed | Colab session screenshot showed `['Redis', 'Cassandra', 'Neo4j']`. Fixed in Codex's work. |
| 6 | `PROJECT_STATUS.json` and `artifact_manifest.csv` stale (0 rows) | ✅ Confirmed | Not found on disk. |
| 7 | No Neo4j graph-traversal invocation in notebook | ✅ Confirmed | No cell calls `benchmark_neo4j_graph_traversal` despite it existing in runner.py. |

## 2. Other AI Notebook Audit — Claim Verification

| Claim | Verified? | Assessment |
|-------|-----------|------------|
| MongoDB excluded via `[db for db in ... if db != 'MongoDB']` | ✅ Confirmed from Colab screenshot | Fixed by updating Cell 37 |
| Drive failure silently redirected to ephemeral storage | ✅ Confirmed in original notebook | N/A for local run; no Drive used |
| Dangerous defaults: `RUN_PILOT=True`, `RUN_FULL_MATRIX=True` | ✅ Confirmed | Current Cell 4 has all flags OFF by default ✅ |
| Undefined globals (sys, platform, etc.) before import | ✅ Confirmed | Cell 4 source imports `os, sys, json, time, platform` etc. ✅ Fixed |
| `train_and_compare_models` argument order: `(X_train, y_train, X_test, y_test)` | ✅ VERIFIED CORRECT | Actual signature on line 104-110 of `training.py`: `X_train, y_train, X_test, y_test`. Fixed notebook calls it correctly. |
| Missing sklearn imports (classification_report, ConfusionMatrixDisplay) | Plausible | Not checked in notebook but package code imports them in `cli.py` correctly. |
| Stale Astra cell ID `ff5046ea` | Cannot verify without original Colab | Low-risk. |
| Legacy Drive scan helper unsafe | Colab-only. N/A for local run | N/A |
| Status reporting reported false zeros | ✅ Confirmed | `PROJECT_STATUS.json` missing |
| Export ZIP could include secrets | ✅ Confirmed | Not relevant for local run with Docker |
| Neo4j graph traversal section missing | ✅ Confirmed | No cell calls the function |
| Matrix plan inconsistency (900 vs 1800 runs) | ✅ Confirmed | Fixed in notebook update |

## 3. Bugs Found in Source Code

### B1. `config.py` — Stale Colab-only phase notes in comments
- Lines 342–344: `"unconfigured (skipped in Phase 13.1)"` for Neo4j/Qdrant
- **Fix**: Remove phase references, use neutral language.

### B2. `config.py` — `MLConfig.group_column = "workload_id"` 
- Should be `"base_workload_id"` for Approach B to prevent matched-concurrency leakage.
- **Fix**: Change default and update `prepare_ml_dataset` accordingly.

### B3. `cli.py` — Missing subcommands
- Current: `check-connections, generate-profiles, validate-data, train, recommend, generate-synthetic-demo`
- Missing per prompt: `benchmark, label, evaluate, explain, qdrant, beir, status`
- **Fix**: Add all 7 missing subcommands.

### B4. `runner.py` — No engine-version capture for local Docker
- `database_version` defaults to `"unknown"` even after connecting.
- **Fix**: Each adapter's `check()` or `version()` should return server version string.

### B5. `data/persistence.py` — `drop_duplicates(run_id, keep='first')` removed (Codex fix applied)  
- Current code uses true append mode (open 'a'). ✅ Already fixed.

### B6. `benchmarking/runner.py` — `run_crud_matrix` resume key uses 4-tuple including concurrency
- Changed by Codex. ✅ Already fixed.

### B7. `features/pipeline.py` — `prepare_ml_dataset` group_column defaults to `"workload_id"`
- Not updated to `"base_workload_id"` by default. Only auto-detects if `base_workload_id` column present.
- **Assessment**: Acceptable — auto-detect logic is there.

### B8. `.gitignore` — does NOT ignore `astra_b64.txt`, `chunk*.txt`, `stage_snippet.py`
- These are untracked scratch files. Must be added to `.gitignore`.

## 4. Hard-Coded Paths / Colab Dependencies

| File | Hard-coded path | Fix |
|------|-----------------|-----|
| `config.py` | Tries `from google.colab import userdata` (silently fails outside Colab) | Already wrapped in try/except ✅ |
| `runner.py` | No hard-coded Drive paths | ✅ OK |
| `cli.py` | Uses `Path("data/raw/...")` relative to CWD | Add `--project-root` flag |
| Old notebook cells | `/content/drive/MyDrive/...` | Fixed in updated notebook |

## 5. Stale / Dead Files

| File | Issue |
|------|-------|
| `astra_b64.txt` | Encoded credential staging scratch — must be gitignored |
| `chunk1-4.txt` | Colab staging scratch — must be gitignored |
| `stage_snippet.py` | Colab staging scratch — must be gitignored |
| `full_send_msg.json` | Agent communication scratch — must be gitignored |
| `send_to_subagent.txt` | Agent scratch — must be gitignored |
| `PROJECT_STATUS.json` | Missing / stale — regenerate from actual artifacts |
| `artifact_manifest.csv` | Missing / stale — regenerate from actual artifacts |
| `results/benchmarks/*.json` | Colab-generated remote benchmarks (Qdrant ANN, BEIR, Neo4j graph) — provenance gap |

## 6. Test Coverage Gaps

- No test for `benchmark_common_crud` with a real (mocked) adapter
- No test for `grouped_train_test_split` with insufficient groups
- No test for `run_crud_matrix` resume with the new 4-tuple key
- `test_matrix_audit.py` exists (untracked)

## 7. Summary

**Existing passing tests**: 44 passed, 2 skipped  
**CLI subcommands present**: 6 (missing: benchmark, label, evaluate, explain, qdrant, beir, status)  
**Primary work for Phases C–I**: Write docker-compose, .env for local Docker, add CLI subcommands, run engines one-at-a-time, collect genuine local measurements, run ML + SHAP + regret.

