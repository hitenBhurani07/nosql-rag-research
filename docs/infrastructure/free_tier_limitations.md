# Free-Tier Limitations and Operational Boundaries

*Audit Date:* 2026-11-13  
*Scope:* Documenting operational bottlenecks and quotas across free-tier managed cloud databases.

---

## 1. Summary of Hard Quotas by Database

| Provider / Database | Storage Ceiling | Concurrency Ceiling | Throughput Ceiling | Bandwidth Ceiling | Auto-Pause Inactivity Threshold | Permanent Deletion Threshold |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Redis Cloud** | **30 MB RAM** | **30 concurrent conns** | **100 ops/second** | **5 GB network transfer/month** | N/A (stays online) | Purged after >90 days inactive |
| **MongoDB Atlas** | **512 MB** | **500 concurrent conns** | ~100 ops/second | Fair use (~10 GB/month) | **30 days idle** | N/A (retained while paused) |
| **DataStax Astra DB** | Capped by credit balance | Dynamic serverless | Governed by credit burn | Fair use | Compute scales to zero (hibernates) | Write-suspended if credits depleted |
| **Neo4j AuraDB** | **50,000–200,000 nodes** | **10 concurrent conns** | ~25–50 queries/sec | Fair use | **72 hours (3 days) no writes** | **30 consecutive days paused** |
| **Qdrant Cloud** | **4 GB SSD / 1 GB RAM** | **20 concurrent conns** | Capped by 0.5 vCPU | Cloud egress fair use | **7 days (1 week) idle** | **4 weeks (28 days) suspended** |

---

## 2. Technical Mitigation Strategies in `nosql_rag`

1. **Storage Overfill Prevention (`cleanup=True`):**
   - The benchmarking harness generates transient run IDs (`bench_p0001_redis_r1_...`).
   - After each benchmark execution completes and latency percentiles are persisted to disk, `adapter.cleanup(run_id)` drops the temporary table, collection, or key prefix.
   - At no point does the working dataset exceed 2,000 records (< 2 MB) in any database.
2. **Throughput Throttle Handling on Redis (100 ops/s):**
   - Because Redis Cloud caps free instances at 100 ops/sec, the runner executes operations sequentially or with concurrency=1 for pilot runs, avoiding rate-limit dropouts or connection drops.
3. **MongoDB 30-Day Inactivity Auto-Pause:**
   - Atlas pauses instances after 30 days of no reads/writes.
   - Resuming requires logging into the MongoDB Atlas web console and clicking **Resume** (takes ~2–4 minutes).
4. **Neo4j 72-Hour Inactivity Keep-Alive & 30-Day Deletion Guard:**
   - Neo4j AuraDB pauses if no write queries arrive within 72 hours.
   - `scripts/database_preflight.py` or running the notebook connection check verifies instance readiness.
   - **Critical Warning:** If left paused for 30 days, Neo4j deletes the database permanently. Ensure periodic preflight checks or resume via the Aura Console if paused.
5. **Qdrant 7-Day Inactivity Keep-Alive & 28-Day Deletion Guard:**
   - Pre-flight checks verify collection health. If suspended, one-click reactivation in the Qdrant Cloud UI restores the cluster.
   - If left suspended for 28 days, Qdrant wipes the cluster.
