"""Print a read-only audit of the saved Approach B CRUD benchmark CSV."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from nosql_rag.benchmarking import audit_crud_matrix
from nosql_rag.data.persistence import load_raw_runs


def _latest_timestamp(runs: pd.DataFrame, column: str) -> str | None:
    if column not in runs.columns:
        return None
    values = pd.to_datetime(runs[column], utc=True, errors="coerce").dropna()
    return values.max().isoformat() if not values.empty else None


def _missing_key_groups(keys: list[list[Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int, int], set[str]] = defaultdict(set)
    for workload_id, database, concurrency, repetition in keys:
        groups[(database, concurrency, repetition)].add(workload_id)

    summary = []
    for (database, concurrency, repetition), workload_ids in sorted(groups.items()):
        numbered = sorted(
            (int(match.group(1)), workload_id)
            for workload_id in workload_ids
            if (match := re.fullmatch(r"W(\d+)", workload_id))
        )
        sequence: dict[str, Any] | None = None
        if len(numbered) == len(workload_ids) and numbered:
            values = [number for number, _ in numbered]
            step = values[1] - values[0] if len(values) > 1 else 0
            if len(values) <= 2 or all(
                right - left == step for left, right in zip(values, values[1:])
            ):
                sequence = {
                    "first": numbered[0][1],
                    "last": numbered[-1][1],
                    "step": step,
                    "count": len(numbered),
                }

        item: dict[str, Any] = {
            "database": database,
            "concurrency": concurrency,
            "repetition": repetition,
            "missing_workload_count": len(workload_ids),
        }
        if sequence:
            item["workload_id_sequence"] = sequence
        else:
            item["workload_ids"] = sorted(workload_ids)
        summary.append(item)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv",
        nargs="?",
        type=Path,
        default=Path("data/raw/crud_benchmark_runs.csv"),
        help="Existing raw benchmark CSV (read only).",
    )
    parser.add_argument(
        "--include-keys",
        action="store_true",
        help="Include every missing, failed, and repeated run key in the JSON report.",
    )
    args = parser.parse_args()
    if not args.csv.is_file():
        parser.error(f"CSV does not exist: {args.csv}")

    runs = load_raw_runs(args.csv)
    report: dict[str, Any] = audit_crud_matrix(runs)
    report["source_csv"] = str(args.csv.resolve())
    file_stat = args.csv.stat()
    report["source_file_size_bytes"] = file_stat.st_size
    report["source_file_modified_utc"] = datetime.fromtimestamp(
        file_stat.st_mtime, tz=timezone.utc
    ).isoformat()
    report["source_file_sha256"] = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    report["latest_started_utc"] = _latest_timestamp(runs, "started_utc")
    report["latest_finished_utc"] = _latest_timestamp(runs, "finished_utc")
    report["unique_run_ids"] = int(runs["run_id"].nunique()) if "run_id" in runs else None
    report["unique_configuration_ids"] = (
        int(runs["configuration_id"].nunique()) if "configuration_id" in runs else None
    )
    report["database_repetition_row_counts"] = (
        runs.groupby(["database", "repetition"], dropna=False)
        .size()
        .rename("rows")
        .reset_index()
        .to_dict("records")
        if {"database", "repetition"}.issubset(runs.columns)
        else []
    )
    report["missing_keys_by_database_concurrency_repetition"] = _missing_key_groups(
        report["missing_keys"]
    )
    if not args.include_keys:
        for key in (
            "missing_keys",
            "failed_keys",
            "pending_keys",
            "repeated_attempt_keys",
            "duplicate_successful_keys",
        ):
            report.pop(key, None)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
