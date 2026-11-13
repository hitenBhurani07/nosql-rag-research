# Phase 13.1 Infrastructure Correction & Security Hardening Audit

*Execution Date:* 2026-11-13  
*Repository:* [https://github.com/hitenBhurani07/nosql-rag-research](https://github.com/hitenBhurani07/nosql-rag-research)  
*Status:* Verified, Tested, and Audited

---

## 1. Provider Information Corrections

All cloud provider specifications have been verified against current official documentation:

1. **Redis Cloud (Fixed Free Tier):**
   - Corrected to document: **30 MB RAM**, **30 maximum concurrent client connections**, **100 ops/second throughput limit**, and **5 GB monthly network data transfer**.
   - Purged if inactive for >90 days.
   - Source: [https://redis.io/pricing/](https://redis.io/pricing/) (Verified 2026-11-13).

2. **MongoDB Atlas (Shared M0 Sandbox):**
   - Corrected to document: **512 MB data/index storage**, **500 maximum connections**, ~100 ops/sec soft rate limit, and **30-day automatic pause** after 30 consecutive days of inactivity (corrected from previous 60-day notation).
   - Source: [https://www.mongodb.com/pricing](https://www.mongodb.com/pricing) and [Atlas Free Tier Limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limits/) (Verified 2026-11-13).

3. **DataStax Astra DB Serverless (Apache Cassandra):**
   - Removed blanket claim of permanent guaranteed "$25/month free credit".
   - Classified accurately as a **Serverless Pay-As-You-Go plan with promotional / free credit allowance**.
   - Documented: Credit availability is subject to active account tier; when free credits are exhausted, write operations are suspended/throttled to avoid surprise billing if no credit card is on file; idle serverless databases scale compute to zero and hibernate.
   - Source: [https://www.datastax.com/pricing](https://www.datastax.com/pricing) (Verified 2026-11-13).

4. **Neo4j AuraDB Free:**
   - Explicitly resolved documented quota discrepancy between marketing landing pages (reporting up to 200,000 nodes and 400,000 relationships) and newer console deployment screens (reporting **50,000 nodes and 100,000 relationships** or 1 instance / 1 GB RAM).
   - Documented: The research system conservatively plans against the **50k node / 100k relationship ceiling** (our largest benchmark generates ~1,000 nodes and ~3,000 relationships, operating at < 2% of the lower ceiling).
   - Documented: Maximum **10 concurrent connections**, **auto-pause after 72 hours (3 days)** of inactivity, and **permanent deletion after 30 consecutive days in a paused state**.
   - Source: [https://neo4j.com/docs/aura/current/getting-started/aura-free/](https://neo4j.com/docs/aura/current/getting-started/aura-free/) (Verified 2026-11-13).

5. **Qdrant Cloud Free Tier:**
   - Documented: **0.5 vCPU, 1 GB RAM, 4 GB SSD storage, 20 concurrent connections**.
   - Documented: **Auto-suspension after 7 days (1 week)** of inactivity; **permanent deletion after 4 weeks (28 days)** in a suspended state.
   - Source: [https://qdrant.tech/pricing/](https://qdrant.tech/pricing/) (Verified 2026-11-13).

---

## 2. Infrastructure Costing & Host Feasibility

All estimates are explicitly labeled as **estimates**:

1. **Oracle Cloud Infrastructure (OCI) Always Free:**
   - Corrected capacity definition: Up to **3,000 OCPU hours and 18,000 GB-hours per month** for Ampere A1 Compute (`VM.Standard.A1.Flex`).
   - Payment Verification Requirement: Clearly documented that OCI account registration **requires a valid credit/debit card for identity verification** with a temporary authorization hold (~$1.00 USD) that is reversed within days.
   - Idle Reclamation: Documented that OCI reclaims Always Free instances if CPU, memory, and network utilization remain below 20% over 7 days.
   - Stockout Warning: Documented global ARM stockouts in popular availability domains.

2. **Google Cloud Platform (GCP) Spot VM (`c2-standard-8`):**
   - Corrected cost estimation from naive VM-only pricing to an itemized, all-inclusive model:
     - Spot Compute (8 vCPU, 32 GB RAM): ~$0.0522 to $0.065/hr.
     - 100 GB SSD Persistent Disk: ~$0.024/hr ($17.00/month).
     - In-Use IPv4 External IP: $0.005/hr ($3.60/month).
     - Internet Network Egress: $0.12/GB (after 200 GB/month free tier).
     - Snapshot Storage: $0.020/GB/month.
   - **All-Inclusive Estimate:** **~$0.10 to $0.15 USD per active hour** (~₹8.60 to ₹13.00 INR/hr).
   - **Total for 4-Hour Benchmark Matrix:** **~$0.40 to $0.60 USD (~₹35 to ₹52 INR)**.

---

## 3. Astra Secure Connect Bundle (SCB) Security Architecture

1. **Canonical Secure Path:** Standardized on `/tmp/astra_scb/secure-connect-bundle.zip` across all documentation, configuration, and scripts.
2. **Directory Isolation:** Staged outside `/content/nosql-rag-research/`.
3. **Artifact & Archive Protection:**
   - Because `/tmp/astra_scb/` is outside the repository working tree, repository export commands (`shutil.make_archive`) will never package the bundle into public artifact archives.
   - Excluded by `.gitignore` (`*.zip`, `secure-connect*.zip`).
4. **Access Restrictions:** Permissions set to `0700` on `/tmp/astra_scb/` and `0600` on the bundle archive.
5. **Teardown Command:** Documented `rm -rf /tmp/astra_scb` for post-experiment cleanup.
6. **Architecture Parity:** Preserved dual-mode operation (`cassandra_mode="standard"` for local/Docker/OCI vs `cassandra_mode="astra"` for Astra DB Serverless).

---

## 4. Environment Variable Harmonization: Neo4j

- Standardized canonical variable as **`NEO4J_USERNAME`** across:
  - `src/nosql_rag/config.py`
  - `.env.example`
  - `docs/infrastructure/credential_setup_guide.md`
  - `docs/infrastructure/deployment_runbook.md`
  - `docs/colab_execution_guide.md`
- Implemented tested backward-compatibility fallback in `DatabaseConfig.from_env()`:
  ```python
  neo4j_username=_get_secret("NEO4J_USERNAME") or _get_secret("NEO4J_USER")
  ```
- Verified via unit test: `test_neo4j_username_and_user_alias`.

---

## 5. Diagnostic Exception Hardening & Redaction

- Implemented `sanitize_error_message(text: str | None) -> str | None` in `src/nosql_rag/adapters/base.py`.
- Integrated across:
  - `scripts/database_preflight.py` (both CRUD and Qdrant diagnostics).
  - `src/nosql_rag/adapters/qdrant_adapter.py` (`check_qdrant_connection`).
- **Redaction Capabilities Verified:**
  - Redacts URI credentials: `://user:password@host` $\to$ `://user:[REDACTED]@host`.
  - Redacts empty-user passwords: `://:password@host` $\to$ `://:[REDACTED]@host`.
  - Redacts single-token passwords: `://password@host` $\to$ `://[REDACTED]@host`.
  - Redacts DataStax Astra tokens: `AstraCS:...` $\to$ `AstraCS:[REDACTED]`.
  - Redacts Authorization Bearer tokens: `Authorization: Bearer ...` $\to$ `Authorization: Bearer [REDACTED]`.
  - Redacts Query-string parameters: `?api_key=...` $\to$ `?api_key=[REDACTED]`.
  - Redacts Assignment strings: `token=...`, `password=...`, `secret=...`.
- Verified via unit tests:
  - `test_sanitize_error_message_removes_all_secret_patterns`
  - `test_preflight_redacts_credentials_in_exception`
  - `test_preflight_redacts_qdrant_api_key_in_exception`

---

## 6. MongoDB Network Security Hardening

- Removed all blanket recommendations advising `0.0.0.0/0` as default configuration.
- Evaluated and documented 4 network access strategies:
  - **Option A (Session-Specific Temporary `/32` IP):** Recommended for Colab interactive testing; auto-expires in 1–6 hours.
  - **Option B (Dedicated Client VM with Static IP):** Recommended for Mode B controlled research benchmarking.
  - **Option C (Encrypted Tunnels):** Evaluated for relaying traffic.
  - **Option D (VPC Peering / PrivateLink):** Documented as unavailable on Atlas M0 Sandbox and standard Colab.
- Documented strict mandatory mitigations (dedicated `readWrite` non-admin user, 32-character randomized password, zero production data) if temporary ingress is utilized.

---

## 7. Engineering Quality & Verification Evidence

- Python compilation (`python -m compileall src tests scripts`): **Passed with 0 errors**.
- Linter (`ruff check src tests scripts`): **All checks passed (0 errors)**.
- Unit Test Suite (`pytest -v -m "not integration"`):
  - **Total Tests:** 28 selected, 2 deselected (live integration).
  - **Pass Rate:** **100% (28 passed in 26.46s)**.
  - Mocked Astra adapter tests: **Passed**.
  - Mocked Standard Cassandra adapter tests: **Passed**.
  - Redaction and credential leak prevention tests: **Passed**.
  - Integration skip behavior: **Passed**.
