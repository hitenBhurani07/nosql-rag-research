# Provider Comparison and Free-Tier Specifications

*Verification Date:* 2026-11-13  
*Primary Source Documents:* Official vendor documentation and pricing portals.

---

## 1. Provider Comparison Matrix

| Attribute | Redis | MongoDB | Apache Cassandra (Astra DB) | Neo4j | Qdrant |
| --- | --- | --- | --- | --- | --- |
| **Recommended Provider** | **Redis Cloud** | **MongoDB Atlas** | **DataStax Astra DB Serverless** | **Neo4j AuraDB** | **Qdrant Cloud** |
| **Official Pricing URL** | [redis.io/pricing](https://redis.io/pricing/) | [mongodb.com/pricing](https://www.mongodb.com/pricing) | [datastax.com/pricing](https://www.datastax.com/pricing) | [neo4j.com/pricing](https://neo4j.com/pricing/) | [qdrant.tech/pricing](https://qdrant.tech/pricing/) |
| **Documentation URL** | [redis.io/docs](https://redis.io/docs/) | [mongodb.com/docs/atlas](https://www.mongodb.com/docs/atlas/) | [docs.datastax.com/astra](https://docs.datastax.com/en/astra-db-serverless/) | [neo4j.com/docs/aura](https://neo4j.com/docs/aura/) | [qdrant.tech/documentation](https://qdrant.tech/documentation/) |
| **Permanent Free Tier** | Yes (Free Plan) | Yes (M0 Cluster) | Yes (Free Tier Credits) | Yes (AuraDB Free) | Yes (1 Free Cluster) |
| **Credit Card Required?** | **No** | **No** | **No** | **No** | **No** |
| **Storage Quota** | **30 MB** | **512 MB** | Generous (~$25 credit/mo) | **200,000 nodes** / **400,000 rels** | **4 GB SSD** |
| **RAM / vCPU** | Shared RAM | Shared vCPU/RAM | Serverless compute | Shared container | **1 GB RAM, 0.5 vCPU** |
| **Throughput Limit** | **100 ops/sec** | Shared rate limit | Serverless auto-scale | Rate limited (~25 req/min) | Rate limited by 0.5 vCPU |
| **Connection Limit** | **30 connections** | **500 connections** | High (Serverless) | Limited pool | Capped by RAM/HTTP |
| **Region Availability** | AWS/GCP (selected regions) | AWS/GCP/Azure multi-region | AWS/GCP/Azure (e.g. us-east-1) | AWS/GCP (e.g. us-east-1) | AWS/GCP (selected regions) |
| **TLS / Encryption** | Yes (mTLS / TLS) | Yes (TLS 1.2+) | Yes (mTLS via Secure Connect Bundle) | Yes (Bolt over TLS: `neo4j+s://`) | Yes (HTTPS / TLS) |
| **Authentication** | Username / Password | SCRAM (User/Password) | **Application Token (`AstraCS:...`)** | Username / Password (`neo4j`) | **API Key (`Qdrant-Api-Key`)** |
| **Inactivity / Suspension** | Suspended if idle | Auto-pause after 30–60 days idle | Monthly credits reset on 1st | **Auto-pause after 3 days no writes** | **Suspended after 7 days idle** |
| **Data Deletion Policy** | Manual or prolonged idle | Not deleted if resumed | Suspended if credits depleted | **Deleted after 30 days paused** | **Deleted after 4 weeks suspended** |
| **Python Client Driver** | `redis-py` (v5.0+) | `pymongo` (v4.6+) | `cassandra-driver` (v3.29+) | `neo4j` (v5.18+) | `qdrant-client` (v1.9+) |
| **Suitability for Pilot** | **High** (200 records < 1 MB) | **High** (200 records < 2 MB) | **High** (Astra SCB supported) | **High** (200 nodes << 200k cap) | **High** (2k vectors << 4 GB cap) |

---

## 2. In-Depth Provider Profiles

### 2.1 Redis Cloud (Redis, Inc.)
- **Free Allowance:** 1 database, 30 MB fixed in-memory storage, 30 maximum concurrent client connections, 100 ops/sec max throughput.
- **Suitability for Research Pilot:** Fully supports the pre-flight pilot (2 profiles, 200 records of 128B–2048B = ~0.3 MB total memory footprint, single-threaded connection).
- **Hard Constraints:** The 100 ops/sec throughput cap means client benchmarks with high concurrency (e.g., 4 or 8 threads) will encounter request throttling or queue latency. Must be run with controlled request pacing.

### 2.2 MongoDB Atlas (MongoDB, Inc.)
- **Free Allowance:** M0 Shared Cluster with 512 MB combined data and index storage. No expiration date.
- **Suitability for Research Pilot:** Excellent. 500 max concurrent connections and 512 MB capacity easily accommodate the 200-record pilot and 1,000-record full matrix runs.
- **Hard Constraints:** Atlas pauses clusters after 30 to 60 days of inactivity. Resuming requires logging into the web console or issuing a ping.

### 2.3 DataStax Astra DB Serverless (Apache Cassandra)
- **Free Allowance:** $25 free monthly credit that automatically refreshes on the first day of every month. No credit card required.
- **Suitability for Research Pilot:** Native CQL table support with high scalability. Completely covers both pilot and full matrix benchmarks without incurring costs.
- **Hard Constraints:** Authentication requires downloading a **Secure Connect Bundle (SCB)** `.zip` package and generating an **Application Token** (`AstraCS:...`). Contact-point direct IP connections are disabled on Serverless.

### 2.4 Neo4j AuraDB Free (Neo4j, Inc.)
- **Free Allowance:** 1 free instance with capacity up to 200,000 nodes and 400,000 relationships.
- **Suitability for Research Pilot:** Fits both operational CRUD lookups and multi-hop graph traversal benchmarks (which generate ~200 nodes and ~600 edges).
- **Hard Constraints:** Automatically pauses after **3 days of no write queries**. A paused database takes approximately 20–30 seconds to wake up via the Aura Console or client connection. Permanently deletes after 30 consecutive days paused.

### 2.5 Qdrant Cloud (Qdrant Solutions GmbH)
- **Free Allowance:** 1 free single-node cluster provisioned with 1 GB RAM, 0.5 vCPU, and 4 GB disk storage.
- **Suitability for Research Pilot:** Outstanding. 4 GB SSD can hold over 100,000 384-dimensional dense vectors. Easily supports our 2,000-vector ANN benchmark and the 5,183-document BEIR SciFact corpus.
- **Hard Constraints:** Clusters idle for **7 days** are automatically suspended. A suspended cluster can be reactivated with one click in the console, but is permanently deleted if untouched for 4 weeks.
