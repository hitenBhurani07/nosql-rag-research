# Cost and Resource Feasibility Analysis

*Audit Date:* 2026-11-13
*Currency Conversions:* USD $1.00 $\approx$ INR 86.50 (estimated).
*Notice:* All figures in this document are **estimates** based on public vendor pricing pages and are subject to change by cloud providers.

---

## 1. Provider Plan Classification & Billing Categorization

To avoid misleading assumptions, hosting resources are categorized by their financial and operational commitment:

| Resource | Provider | Plan Classification | Payment Verification Needed? | Auto-Conversion to Paid? | Cost Risk / Overage Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Redis** | Redis Cloud | Resource-capped Free Plan | **No** | No | 30 MB / 5 GB monthly bandwidth limit. Throttled/rejected at ceiling. |
| **MongoDB** | MongoDB Atlas | Resource-capped M0 Sandbox | **No** | No | 512 MB storage limit. 500 connections. Auto-pauses after 30 days idle. |
| **Cassandra** | DataStax Astra DB | Serverless Free Credit Allowance | **No** (initial usage) | Only if CC added by user | Throttles/suspends writes when credit depleted. |
| **Neo4j** | Neo4j AuraDB | Resource-capped AuraDB Free | **No** | No | 50k–200k nodes. Auto-pauses after 72 hours; deleted after 30 days paused. |
| **Qdrant** | Qdrant Cloud | Resource-capped Free Tier | **No** | No | 4 GB SSD / 1 GB RAM. Auto-suspends after 7 days; deleted after 28 days. |
| **Host VM** | OCI Always Free | Monthly Allowance (ARM A1) | **Yes (Credit/Debit Card ~$1 hold)** | No (unless upgraded) | 3,000 OCPU-hrs / 18,000 GB-hrs per month. Subject to capacity stockouts. |
| **Host VM** | GCP Spot VM | Paid Preemptible Compute | **Yes (GCP Billing Account)** | Yes (billed per second) | ~$0.10–$0.15/hr all-inclusive. Subject to preemption. |

---

## 2. Projected Expense by Operational Scenario

### Scenario 1: One Day of Connection Testing & Pre-Flight Validation
- **Workload:** Health checks, schema generation, 8 pilot benchmark executions (< 2,000 total operations).
- **Resource Footprint:** < 5 MB storage across all 5 databases.

| Service / Resource | Provider Tier | Billed Metric | Estimated Cost (USD) | Estimated Cost (INR) | Payment Card Needed? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Redis** | Redis Cloud Free | 30 MB quota | **$0.00** | **₹0.00** | No |
| **MongoDB** | MongoDB Atlas M0 | 512 MB quota | **$0.00** | **₹0.00** | No |
| **Cassandra** | DataStax Astra DB | Covered by free credit allowance | **$0.00** | **₹0.00** | No |
| **Neo4j** | Neo4j AuraDB Free | 50k–200k node quota | **$0.00** | **₹0.00** | No |
| **Qdrant** | Qdrant Cloud Free | 4 GB SSD / 1 GB RAM | **$0.00** | **₹0.00** | No |
| **Compute** | Google Colab Standard | Standard CPU runtime | **$0.00** | **₹0.00** | No |
| **Total Scenario 1** | | | **$0.00 (Estimated)** | **₹0.00 (Estimated)** | **Zero Cost** |

---

### Scenario 2: One-Week Pilot & Experiment Iteration
- **Workload:** Daily connection checks, 5 pilot matrix runs, 2 Qdrant ANN benchmarks, 1 BEIR SciFact run.
- **Resource Footprint:** ~15 MB storage, ~50,000 total database operations, ~50 MB network egress.

| Service / Resource | Provider Tier | Billed Metric | Estimated Cost (USD) | Estimated Cost (INR) | Payment Card Needed? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Redis** | Redis Cloud Free | Within 30 MB / 5 GB monthly bandwidth | **$0.00** | **₹0.00** | No |
| **MongoDB** | MongoDB Atlas M0 | Within 512 MB quota | **$0.00** | **₹0.00** | No |
| **Cassandra** | DataStax Astra DB | Covered by free credit allowance | **$0.00** | **₹0.00** | No |
| **Neo4j** | Neo4j AuraDB Free | Within node/rel limit | **$0.00** | **₹0.00** | No |
| **Qdrant** | Qdrant Cloud Free | Within 4 GB / 1 GB RAM | **$0.00** | **₹0.00** | No |
| **Compute** | Google Colab Standard | Standard CPU runtime | **$0.00** | **₹0.00** | No |
| **Total Scenario 2** | | | **$0.00 (Estimated)** | **₹0.00 (Estimated)** | **Zero Cost** |

---

### Scenario 3: Full Experiment Matrix Execution (Mode A vs. Mode B)

#### Under Architecture Mode A (Cloud Free Tiers):
- **Workload:** 75 profiles $\times$ 4 engines $\times$ 3 repetitions = 900 CRUD runs + Qdrant ANN + BEIR SciFact.
- **Storage:** ~25 MB max across databases (records cleaned after each batch).
- **Estimated Cost:** **$0.00 (₹0.00)**.
- **Methodological Trade-Off:** WAN latency jitter across multi-cloud regions confounds store ranking. Suitable for pipeline verification, not publishable performance rankings.

#### Under Architecture Mode B (Dedicated Controlled Research VM):
- **Workload:** Co-located benchmark client + sequential Docker containers for Redis, MongoDB, Cassandra, Neo4j, Qdrant.
- **Option 1 (Oracle Cloud Always Free Ampere A1):**
  - Allowance: 4 OCPU, 24 GB RAM (within 3,000 OCPU-hrs / 18,000 GB-hrs monthly ceiling).
  - Estimated Cost: **$0.00 (₹0.00)**.
  - Requirement: Valid payment card for initial ~$1 identity verification hold (reversed).
  - Risk: ARM capacity stockouts in high-demand regions.
- **Option 2 (GCP Spot VM `c2-standard-8` — Compute-Optimized 8 vCPU, 32 GB RAM):**
  - Compute (Spot rate in `us-central1`): ~$0.0522 to $0.065/hr.
  - Storage (100 GB SSD persistent disk): ~$0.024/hr ($17.00/month).
  - Network (In-use IPv4 address): ~$0.005/hr ($3.60/month).
  - Egress Bandwidth: $0.12/GB (negligible for benchmark control traffic).
  - Artifact Storage: $0.020/GB/month.
  - All-Inclusive Hourly Estimate: **~$0.10 to $0.15 USD per hour** (~₹8.60 to ₹13.00/hr).
  - Total for 4-Hour Matrix Run: **~$0.40 to $0.60 USD (₹35.00 to ₹52.00 INR)**.

---

## 3. Cost Control Safeguards & Risk Summary

1. **No Automatic Card Charges:** The 5 shortlisted database providers do not request credit card details for free tier provisioning and cannot bill unforeseen overages.
2. **Hard Inactivity Caps:** When quotas are reached, free-tier services reject writes or throttle connections rather than billing overages.
3. **No Autonomous Deployment:** The repository contains no Terraform scripts, payment credentials, or autonomous cloud provisioning logic.
4. **Card Hold Transparency:** Oracle Cloud's temporary authorization hold is clearly documented before the user initiates registration.
