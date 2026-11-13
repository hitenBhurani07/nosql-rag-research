# Provider Comparison and Free-Tier Specifications

*Verification Date:* 2026-11-13  
*Primary Source Documents:* Official vendor documentation, terms of service, and billing consoles.

---

## 1. Provider Comparison Matrix

| Attribute | Redis | MongoDB | Apache Cassandra (Astra DB) | Neo4j | Qdrant |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Recommended Provider** | **Redis Cloud** | **MongoDB Atlas** | **DataStax Astra DB Serverless** | **Neo4j AuraDB** | **Qdrant Cloud** |
| **Official Pricing URL** | [redis.io/pricing](https://redis.io/pricing/) | [mongodb.com/pricing](https://www.mongodb.com/pricing) | [datastax.com/pricing](https://www.datastax.com/pricing) | [neo4j.com/pricing](https://neo4j.com/pricing/) | [qdrant.tech/pricing](https://qdrant.tech/pricing/) |
| **Documentation URL** | [redis.io/docs](https://redis.io/docs/) | [mongodb.com/docs/atlas](https://www.mongodb.com/docs/atlas/) | [docs.datastax.com/astra](https://docs.datastax.com/en/astra-db-serverless/) | [neo4j.com/docs/aura](https://neo4j.com/docs/aura/) | [qdrant.tech/documentation](https://qdrant.tech/documentation/) |
| **Plan Classification** | Resource-capped Free Plan | Shared M0 Sandbox Plan | Serverless Pay-As-You-Go with Free Credit Tier | Resource-capped AuraDB Free | Resource-capped Free Tier |
| **Credit Card Required?** | **No** | **No** | **No** (for initial free usage) | **No** | **No** |
| **Storage Quota** | **30 MB RAM** | **512 MB Storage** | Serverless storage quota (capped by credit balance) | **50,000–200,000 nodes** / **100,000–400,000 rels** (varies by console revision) | **4 GB SSD** |
| **Compute / Memory** | Dedicated 30 MB in-memory | Shared burstable vCPU/RAM | Auto-scaling serverless compute | 1 shared instance (1 GB RAM limit) | **0.5 vCPU, 1 GB RAM** |
| **Throughput & Rate Limits** | **100 ops/sec max** | ~100 ops/sec shared pool | Soft threshold on read/write units | Capped rate (~25–50 queries/sec) | Throttled by 0.5 vCPU allocation |
| **Connection Limit** | **30 concurrent connections** | **500 maximum connections** | Managed serverless connection pool | **10 concurrent connections max** | **20 concurrent connections max** |
| **Monthly Bandwidth Limit** | **5 GB network transfer/month** | Subject to fair use (~10 GB/mo) | Included in credit allocation | Unspecified fair use | Subject to 4 GB disk & cloud egress |
| **TLS / Encryption** | TLS / SSL enabled | TLS 1.2+ mandatory | **mTLS mandatory via Secure Connect Bundle** | Bolt with TLS (`neo4j+s://`) | HTTPS / TLS mandatory |
| **Authentication Scheme** | Password / Default user | SCRAM (Username & Password) | **Application Token (`AstraCS:...`)** | Username (`neo4j`) & Password | **API Key (`Qdrant-Api-Key`)** |
| **Inactivity / Suspension** | Unused DBs purged if idle >90 days | **Auto-pauses after 30 days of inactivity** | Compute scales to zero; hibernates if idle | **Auto-pauses after 72 hours (3 days) of inactivity** | **Auto-suspends after 7 days (1 week) of inactivity** |
| **Data Deletion Policy** | Manual or prolonged idle | Retained indefinitely while paused (1-click resume) | Write-suspended if credits depleted; archived if idle >90 days | **Permanently deleted if left paused for 30 consecutive days** | **Permanently deleted if left suspended for 4 weeks (28 days)** |
| **Python Client Driver** | `redis-py` (v5.0+) | `pymongo` (v4.6+) | `cassandra-driver` (v3.29+) + `pyasyncore` (Py 3.12+) | `neo4j` (v5.18+) | `qdrant-client` (v1.9+) |
| **Suitability for Pilot** | **High** (200 records < 1 MB) | **High** (200 records < 2 MB) | **High** (Astra SCB supported) | **High** (200 nodes << 50k cap) | **High** (2k vectors << 4 GB cap) |

---

## 2. In-Depth Provider Profiles & Quota Boundaries

### 2.1 Redis Cloud (Redis, Inc.)
- **Free Allowance:** 1 database, 30 MB maximum in-memory storage, 30 maximum concurrent client connections, 100 ops/sec maximum throughput ceiling.
- **Network Bandwidth:** Strictly capped at **5 GB monthly network data transfer**.
- **Inactivity Policy:** Databases with zero traffic for over 90 days are subject to decommissioning.
- **Suitability for Research Pilot:** Fully supports our pre-flight pilot (2 profiles, 200 records of 128B–2048B = ~0.3 MB total memory footprint, single-threaded connection).
- **Hard Constraints:** The 100 ops/sec throughput cap and 30-connection ceiling require client benchmarks with concurrency levels > 1 to employ paced request dispatching.

### 2.2 MongoDB Atlas (MongoDB, Inc.)
- **Free Allowance:** M0 Shared Cluster with 512 MB combined data and index storage on shared cloud infrastructure (AWS/GCP/Azure).
- **Connection & Throughput:** 500 maximum connections pool; ~100 ops/sec soft rate limit.
- **Inactivity Policy:** **Automatically pauses after 30 consecutive days of inactivity** (no reads or writes). Waking a paused cluster is performed via the Atlas console and takes 2–4 minutes.
- **Network Guidance:** Blanket `0.0.0.0/0` access is **strongly discouraged** for prolonged periods. Use session-specific temporary `/32` IP allowlisting with 1–6 hour auto-expiry or a dedicated client bastion.

### 2.3 DataStax Astra DB Serverless (Apache Cassandra)
- **Free Allowance & Pricing Classification:** DataStax Astra DB operates on a Serverless Pay-As-You-Go model. Free usage is granted via an initial promotional or monthly free credit allowance (historically $25/month for Serverless Cassandra accounts, though newer Astra Vector accounts offer customized credit grants).
- **Credit Policy & Exhaustion:** Do not assume a fixed $25/month allowance without verifying your specific account billing dashboard upon signup. When free credits are exhausted:
  - If no payment method is on file, **all write operations are suspended/throttled** to prevent surprise charges.
  - If a credit card has been provided, consumption beyond credits transitions automatically to pay-as-you-go billing.
- **Inactivity & Archival:** Inactive serverless databases hibernate compute to zero. Extended inactivity (>90 days without queries) may result in database archival.
- **Authentication & Security:** Astra DB Serverless **does not support direct IP contact-points**. It mandates mutual TLS (mTLS) via a downloaded **Secure Connect Bundle (SCB)** `.zip` file and an **Application Token** (`AstraCS:...`). The SCB must never be placed in source control or public directories.

### 2.4 Neo4j AuraDB Free (Neo4j, Inc.)
- **Free Allowance & Quota Discrepancy:**
  - *Documented Discrepancy:* Official Neo4j documentation and web signup portals report conflicting free-tier limits depending on regional availability and account revision. Certain legacy/marketing pages cite up to **200,000 nodes and 400,000 relationships**, whereas active Aura console deployment screens cite **50,000 nodes and 100,000 relationships** (or a 1 instance / 1 GB memory limit).
  - *Methodological Resolution:* The research harness must assume the conservative lower limit (**50,000 nodes and 100,000 relationships**). Our benchmark workloads generate at most 1,000 nodes and 3,000 relationships per run, remaining well below even the lower 50k threshold.
- **Connection Limits:** Maximum 10 concurrent connections.
- **Inactivity & Deletion Policy:**
  - **Auto-pause after 72 hours (3 days)** of inactivity (no queries executed).
  - Paused databases take ~30 seconds to resume via console or client connect.
  - **Permanent Deletion Warning:** If an AuraDB Free database remains in a paused state for **30 consecutive days, it is permanently deleted and all data is unrecoverable**.

### 2.5 Qdrant Cloud (Qdrant Solutions GmbH)
- **Free Allowance:** 1 free single-node cluster allocated with **0.5 vCPU, 1 GB RAM, and 4 GB SSD storage**.
- **Connection Limits:** Maximum 20 concurrent connections.
- **Inactivity & Deletion Policy:**
  - Automatically suspended if inactive for **7 days (1 week)**.
  - Suspended clusters can be reactivated with one click in the web console.
  - **Permanent Deletion Warning:** If a cluster remains suspended for **4 weeks (28 days)** without reactivation, the cluster and all vector collections are permanently wiped.
- **Suitability for Research Pilot:** Outstanding. 4 GB SSD accommodates over 100,000 384-dimensional dense vectors (our 2,000-vector ANN pilot and 5,183-document BEIR SciFact corpus consume < 50 MB combined).

---

## 3. Controlled Unified-Host Options (Mode B)

For scientific benchmarking where cross-cloud WAN latency is eliminated:

### 3.1 Oracle Cloud Infrastructure (OCI) Always Free
- **Official Allowance:** Ampere A1 Compute provides up to **3,000 OCPU hours and 18,000 GB-hours per calendar month** (e.g., a single 4 OCPU, 24 GB RAM instance running continuously within monthly limits: $4 \times 744 = 2,976 \le 3,000$ OCPU-hrs; $24 \times 744 = 17,856 \le 18,000$ GB-hrs).
- **Payment Verification Requirement:** Creating an Oracle Cloud account **requires a valid credit or debit card for identity verification**, which places a temporary authorization hold (~$1.00 USD, or regional equivalent) that is reversed within a few days.
- **Idle Reclamation Policy:** Oracle terminates and reclaims Always Free compute instances if utilization over a 7-day period falls below:
  - 95th percentile CPU utilization < 20%
  - Network utilization < 20%
  - Memory utilization < 20%
- **Capacity Stockout Notice:** ARM Ampere A1 capacity is subject to regional availability and frequently experiences provisioning delays ("Out of capacity") in popular regions.

### 3.2 Google Cloud Platform (GCP) Spot VM
- **Recommended Shape:** `c2-standard-8` (8 vCPU, 32 GB RAM, compute-optimized).
- **Itemized Cost Estimates (us-central1, subject to market fluctuations):**
  - Compute (Spot/Preemptible rate): ~$0.0522 to $0.065 per hour.
  - Persistent Disk (100 GB SSD): ~$17.00/month $\approx$ $0.024 per hour.
  - External Static/In-Use IPv4: $0.005 per hour.
  - Internet Network Egress: $0.12 per GB (after 200 GB free tier).
  - Snapshot & Artifact Storage (GCS): $0.020 per GB/month.
- **Total Operational Estimate:** **~$0.10 to $0.15 per active hour**.
- **Full Matrix Execution (4 hours):** Estimated at **~$0.40 to $0.60 USD total**.
- *All figures are marked as estimates and require active GCP billing authorization.*

---

## 4. Unresolved Provider Uncertainties

1. **DataStax Astra Credit Expiration:** DataStax periodically adjusts free credit allocations between new trial signups and legacy PAYGO accounts. Exact monthly credit longevity must be verified directly on your account billing tab after registration.
2. **Neo4j Aura Node Ceiling:** Whether your specific free instance receives 50k or 200k nodes depends on current deployment cluster capacity in AWS us-east-1.
3. **OCI Always Free Capacity:** Inability to guarantee instant availability of 4 OCPU Ampere A1 instances due to global ARM stockouts.
