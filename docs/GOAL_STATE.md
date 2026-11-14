# Goal Execution State

- **T0**: 2026-11-14T16:34:33+05:30
- **Deadline (Benchmarking)**: 2026-11-14T19:19:33+05:30 (T0 + 2h45m)
- **Deadline (Total Completion)**: 2026-11-14T19:49:33+05:30 (T0 + 3h15m)
- **Hardware**: Windows 11, Intel Core i5-12500H, 16 GB RAM, NVMe SSD, Docker Desktop WSL2 (capped at 3GB).
- **Execution Architecture**: In-container client (`nosql-rag-client:1.0` via compose service `benchmark-runner`) on internal compose network `nosql-rag-research_default`. Concurrency at $c=4$ uses Python multiprocessing to prevent GIL bottlenecks.
- **Strict Database Scheduling**: Exactly one database container active at a time. Free RAM verified before container startup.

---

## Benchmark State Matrix

| Database | Target Profiles | Target Reps | Total Target Runs | Genuine Runs Completed | Status | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Redis** | 150 | 3 | 450 | 450 | **COMPLETE** | In-container, 0 errors, median P95: 0.175 ms |
| **MongoDB** | 150 | 3 | 450 | 450 | **COMPLETE** | In-container, 0 errors, median P95: 0.584 ms |
| **Cassandra** | 76 | 3 | 228 | 228 | **COMPLETE** | In-container, 0 errors, median P95: 1.133 ms |
| **Neo4j** | 76 | 3 | 228 | 0 | **PENDING** | Community 5.26, heap 512M, cache 128M, rep-ordered |

---

## Log of Steps

- **T0+00m (16:34:33)**: Initialized goal execution. Verified Redis 450 genuine runs completed. Containers cleanly stopped. Free RAM: 2.96 GB.


- **T0+32m (17:06:23)**: Completed MongoDB 450 genuine runs. Total genuine runs: 900 (Redis: 450, MongoDB: 450). Free RAM: 2.24 GB.
  - **150-Workload Label Flip Finding (Addition #1)**: 64 / 150 labels (42.67%) flipped from MongoDB to Redis.
  - In-container label distribution: Redis = 149 (99.3%), MongoDB = 1 (0.7%). Host port-forwarding bias hypothesis confirmed empirically.

- **T0+57m (17:31:56)**: Completed Cassandra 228 genuine runs (76 profiles x 3 reps).
  - Sanity pilot passed: W0001 P50=0.561 ms, W0002 P50=0.690 ms, nodetool proxyhistograms write 50%=258us, read 50%=179us.
  - Matrix stats: 228 successful runs, 0 errors. P50 median: 0.613 ms, P95 median: 1.133 ms. OOMKilled: false.
  - Container stopped. Free RAM: 2.05 GB. Total genuine runs in CSV: 1,128.
