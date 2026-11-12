"""Independent preflight connectivity and health checker for all five candidate databases."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from nosql_rag.adapters import (
    build_crud_adapter,
    check_qdrant_connection,
)
from nosql_rag.config import DatabaseConfig


def run_database_preflight(config: DatabaseConfig) -> dict[str, Any]:
    """Inspect configured credentials and execute non-destructive health checks."""
    statuses = {item["database"]: item["configured"] for item in config.safe_status()}
    results: list[dict[str, Any]] = []

    # 1. Operational CRUD engines
    crud_engines = ("Redis", "MongoDB", "Cassandra", "Neo4j")
    for name in crud_engines:
        is_configured = statuses.get(name, False)
        if not is_configured:
            results.append(
                {
                    "database": name,
                    "configured": False,
                    "status": "Skipped",
                    "version": "unknown",
                    "latency_ms": None,
                    "error_category": "MissingCredentials",
                    "error_details": f"Required credentials for {name} are not set in environment or Colab Secrets.",
                }
            )
            continue

        started = time.perf_counter()
        adapter = None
        try:
            adapter = build_crud_adapter(name, config)
            ok = adapter.check()
            elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
            if ok:
                results.append(
                    {
                        "database": name,
                        "configured": True,
                        "status": "Pass",
                        "version": getattr(adapter, "version", "unknown"),
                        "latency_ms": elapsed_ms,
                        "error_category": None,
                        "error_details": None,
                    }
                )
            else:
                results.append(
                    {
                        "database": name,
                        "configured": True,
                        "status": "Fail",
                        "version": getattr(adapter, "version", "unknown"),
                        "latency_ms": elapsed_ms,
                        "error_category": "HealthCheckFailed",
                        "error_details": "Adapter ping/health-check returned False.",
                    }
                )
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
            exc_str = str(exc)
            err_cat = "AuthenticationError" if any(k in exc_str.lower() for k in ["auth", "password", "token", "unauthorized"]) else "NetworkError"
            results.append(
                {
                    "database": name,
                    "configured": True,
                    "status": "Fail",
                    "version": "unknown",
                    "latency_ms": elapsed_ms,
                    "error_category": err_cat,
                    "error_details": f"{type(exc).__name__}: {exc_str[:250]}",
                }
            )
        finally:
            if adapter is not None:
                try:
                    adapter.close()
                except Exception:
                    pass

    # 2. Vector engine: Qdrant
    is_qdrant_configured = statuses.get("Qdrant", False)
    if not is_qdrant_configured:
        results.append(
            {
                "database": "Qdrant",
                "configured": False,
                "status": "Skipped",
                "version": "unknown",
                "latency_ms": None,
                "error_category": "MissingCredentials",
                "error_details": "QDRANT_URL is not set in environment or Colab Secrets.",
            }
        )
    else:
        q_res = check_qdrant_connection(config)
        err = q_res.get("error")
        err_cat = None
        if err:
            err_cat = "AuthenticationError" if any(k in err.lower() for k in ["api_key", "unauthorized", "401"]) else "NetworkError"
        results.append(
            {
                "database": "Qdrant",
                "configured": True,
                "status": "Pass" if q_res["connected"] else "Fail",
                "version": q_res.get("version", "unknown"),
                "latency_ms": q_res.get("connect_check_ms"),
                "error_category": err_cat,
                "error_details": err[:250] if err else None,
            }
        )

    summary = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_databases": len(results),
        "configured_count": sum(1 for r in results if r["configured"]),
        "passed_count": sum(1 for r in results if r["status"] == "Pass"),
        "failed_count": sum(1 for r in results if r["status"] == "Fail"),
        "skipped_count": sum(1 for r in results if r["status"] == "Skipped"),
        "databases": results,
    }
    return summary


def format_table(summary: dict[str, Any]) -> str:
    """Format structured preflight report into a readable console markdown table."""
    lines = [
        "| Database | Configured | Status | Version | Latency (ms) | Error Category |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in summary["databases"]:
        conf = "Yes" if r["configured"] else "No"
        lat = f"{r['latency_ms']:.1f}" if r["latency_ms"] is not None else "N/A"
        err = r["error_category"] or "None"
        lines.append(
            f"| {r['database']:<8} | {conf:<10} | {r['status']:<6} | {str(r['version']):<12} | {lat:<12} | {err:<14} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="NoSQL RAG Research Database Preflight Checker")
    parser.add_argument("--json", action="store_true", help="Output pure JSON")
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format: table or json",
    )
    parser.add_argument("--output", type=Path, default=None, help="Save report to JSON file")
    args = parser.parse_args()

    cfg = DatabaseConfig.from_env()
    report = run_database_preflight(cfg)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    if args.json or args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print("\n" + "=" * 70)
        print("  NoSQL RAG Research — Database Preflight Report")
        print("=" * 70)
        print(format_table(report))
        print("=" * 70)
        print(f"Summary: {report['passed_count']} Passed, {report['failed_count']} Failed, {report['skipped_count']} Skipped.")
        print("Note: Secret values are never displayed or stored in logs.\n")


if __name__ == "__main__":
    main()
