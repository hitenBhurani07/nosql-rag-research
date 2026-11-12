# Free-Tier Limitations and Operational Boundaries

*Audit Date:* 2026-11-13  
*Scope:* Documenting operational bottlenecks and quotas across free-tier managed cloud databases.

---

## 1. Summary of Hard Quotas by Database

| Provider / Database | Storage Ceiling | Concurrency Ceiling | Throughput Ceiling | Auto-Pause Inactivity Threshold | Permanent Deletion Threshold |
| --- | --- | --- | --- | --- | --- |
| **Redis Cloud** | **30 MB** | **30 concurrent conns** | **100 ops/second** | N/A (stays online unless terminated) | Account idle policy |
| **MongoDB Atlas** | **512 MB** | **500 concurrent conns** | Shared burst throttling | **30 to 60 days idle** | N/A (can be resumed) |
| **DataStax Astra DB** | Free monthly credits | Dynamic serverless | Governed by credit burn | Suspended if credits depleted | Credit resets 1st of month |
| **Neo4j AuraDB** | **200,000 nodes** | Single pool | ~25 req/min burst rate | **3 days no writes** | **30 days paused** |
| **Qdrant Cloud** | **4 GB SSD / 1 GB RAM**| Shared | Governed by 0.5 vCPU | **7 days idle** | **4 weeks suspended** |

---

## 2. Technical Mitigation Strategies in `nosql_rag`

1. **Storage Overfill Prevention (`cleanup=True`):**
   - The benchmarking harness generates transient run IDs (`bench_p0001_redis_r1_...`).
   - After each benchmark execution completes and latency percentiles are persisted to disk, `adapter.cleanup(run_id)` drops the temporary table, collection, or key prefix.
   - At no point does the working dataset exceed 2,000 records (< 2 MB) in any database.
2. **Throughput Throttle Handling on Redis:**
   - Because Redis Cloud caps free instances at 100 ops/sec, the runner executes operations sequentially or with concurrency=1 for pilot runs, avoiding rate-limit dropouts.
3. **Neo4j 3-Day Inactivity Keep-Alive:**
   - Neo4j AuraDB pauses if no write queries arrive within 3 days.
   - `scripts/database_preflight.py` or running the notebook connection check sends a lightweight ping, confirming active state. If paused, the user resumes it in the Aura web console (takes ~20 seconds).
4. **Qdrant 7-Day Inactivity Keep-Alive:**
   - Pre-flight checks verify collection health. If suspended, one-click reactivation in the Qdrant Cloud UI restores the cluster.
