# Cost and Resource Feasibility Analysis

*Audit Date:* 2026-11-13  
*Currency Conversions:* USD $1.00 $\approx$ INR 86.50 (estimated).

---

## 1. Projected Expense by Operational Scenario

### Scenario 1: One Day of Connection Testing & Pre-Flight Validation
- **Workload:** Health checks, schema generation, 8 pilot benchmark executions (< 2,000 total operations).
- **Resource Footprint:** < 5 MB storage across all 5 databases.

| Service / Resource | Provider Tier | Billed Metric | Estimated Cost (USD) | Estimated Cost (INR) | Payment Card Needed? |
| --- | --- | --- | --- | --- | --- |
| **Redis** | Redis Cloud Free | 30 MB quota | **$0.00** | **₹0.00** | No |
| **MongoDB** | MongoDB Atlas M0 | 512 MB quota | **$0.00** | **₹0.00** | No |
| **Cassandra** | DataStax Astra DB | $25 monthly free credit | **$0.00** | **₹0.00** | No |
| **Neo4j** | Neo4j AuraDB Free | 200k node quota | **$0.00** | **₹0.00** | No |
| **Qdrant** | Qdrant Cloud Free | 4 GB SSD / 1 GB RAM | **$0.00** | **₹0.00** | No |
| **Compute** | Google Colab Standard | Standard CPU runtime | **$0.00** | **₹0.00** | No |
| **Total Scenario 1** | | | **$0.00** | **₹0.00** | Zero Cost |

---

### Scenario 2: One-Week Pilot & Experiment Iteration
- **Workload:** Daily connection checks, 5 pilot matrix runs, 2 Qdrant ANN benchmarks, 1 BEIR SciFact run.
- **Resource Footprint:** ~15 MB storage, ~50,000 total database operations, ~50 MB network egress.

| Service / Resource | Provider Tier | Billed Metric | Estimated Cost (USD) | Estimated Cost (INR) | Payment Card Needed? |
| --- | --- | --- | --- | --- | --- |
| **Redis** | Redis Cloud Free | Inside 30 MB / 5 GB bandwidth | **$0.00** | **₹0.00** | No |
| **MongoDB** | MongoDB Atlas M0 | Inside 512 MB quota | **$0.00** | **₹0.00** | No |
| **Cassandra** | DataStax Astra DB | Covered by $25 monthly credit | **$0.00** | **₹0.00** | No |
| **Neo4j** | Neo4j AuraDB Free | Inside 200k nodes limit | **$0.00** | **₹0.00** | No |
| **Qdrant** | Qdrant Cloud Free | Inside 4 GB / 1 GB RAM | **$0.00** | **₹0.00** | No |
| **Compute** | Google Colab Standard | Standard CPU runtime | **$0.00** | **₹0.00** | No |
| **Total Scenario 2** | | | **$0.00** | **₹0.00** | Zero Cost |

---

### Scenario 3: Full Experiment Matrix Execution (Mode A vs. Mode B)

#### Under Architecture Mode A (Cloud Free Tiers):
- **Workload:** 75 profiles $\times$ 4 engines $\times$ 3 repetitions = 900 CRUD runs + Qdrant ANN + BEIR SciFact.
- **Storage:** ~25 MB max across databases (records cleaned after each batch).
- **Cost:** **$0.00 (₹0.00)**.
- **Limitations:** Redis throughput capped at 100 ops/s; heterogenous network latency.

#### Under Architecture Mode B (Dedicated Research Cloud VM — e.g. Oracle / GCP / AWS):
- **Workload:** Co-located benchmark client + sequential Docker containers for Redis, MongoDB, Cassandra, Neo4j, Qdrant.
- **Option 1 (OCI Always Free Ampere A1):** 4 OCPU, 24 GB RAM, 200 GB block storage $\to$ **$0.00 (₹0.00)** (Requires credit card for initial identity verification).
- **Option 2 (Hourly Spot Cloud VM — e.g. GCP `e2-standard-4` or AWS `t4g.xlarge`):**
  - Compute: 4 vCPU, 16 GB RAM at ~$0.04/hour.
  - Duration for 900 runs: ~3.5 hours.
  - Compute cost: $3.5 \times \$0.04 = \mathbf{\$0.14}$ (~**₹12.00**).
  - Storage & Network: ~$0.05 (~**₹4.30**).
  - Total Estimated Cost: **~$0.20 (₹17.00)**.

---

## 2. Cost Control Safeguards & Risk Summary
1. **Zero Auto-Conversion:** None of the 5 shortlisted free-tier services auto-convert to paid tiers without manual credit card addition.
2. **Hard Inactivity Caps:** If usage exceeds free tier limits, services suspend connections rather than billing overages.
3. **No Automatic Scaling:** The repository contains no API keys or terraform scripts capable of auto-scaling paid infrastructure.
