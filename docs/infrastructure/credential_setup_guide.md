# Credential and Secrets Setup Guide

Step-by-step manual setup instructions for configuring live cloud database endpoints in Google Colab Secrets and local development `.env`.

---

## 1. Actual Provisioned Endpoints (Active in Phase 13.1)

Three live database services have been provisioned for the research environment:

### A. Redis Cloud (Key-Value Engine)
- **Database Name:** `nosql-rag-research`
- **Plan:** Free, 30 MB
- **Cloud & Region:** AWS Mumbai (`ap-south-1`)
- **Host:** `profit-cook-stitch-74158.db.redis.io`
- **Port:** `18690`
- **Username:** `default`
- **Connection URI Format:**
  ```text
  redis://default:<REDIS_PASSWORD>@profit-cook-stitch-74158.db.redis.io:18690
  ```
  *(If your Redis console provides `rediss://` for TLS, use `rediss://` instead).*

### B. MongoDB Atlas (Document Engine)
- **Project:** `NoSQL RAG Research`
- **Cluster:** `Cluster0` (M0 Free Tier)
- **Host:** `cluster0.hqd8wfk.mongodb.net`
- **Dedicated User:** `rag_research`
- **Database Name:** `nosql_rag_research`
- **Connection URI Format:**
  ```text
  mongodb+srv://rag_research:<MONGODB_PASSWORD>@cluster0.hqd8wfk.mongodb.net/nosql_rag_research?retryWrites=true&w=majority
  ```
  *(Ensure special characters in the password are percent-encoded).*
- **Networking Requirement:** Google Colab dynamic egress IP must be allowlisted. Run Cell 13 in the notebook to discover the current IP, then add it in Atlas under **Network Access** as `<COLAB_PUBLIC_IP>/32` (recommended: 1-hour or 6-hour auto-expiry).

### C. DataStax Astra DB (Wide-Column Engine / Cassandra)
- **Database Name:** `nosql_rag_research`
- **Database ID:** `0d4339a2-6863-4ac6-bd99-82ae8c984887`
- **Keyspace:** `nosql_rag_research`
- **Cloud & Region:** AWS `us-east-2`
- **Driver Model:** Standard CQL driver with mutual TLS (mTLS).
- **Secure Connect Bundle Archive:** `secure-connect-nosql-rag-research.zip`.
- **Application Token:** `AstraCS:...` generated from Organization Settings.

### Unprovisioned Services (Safely Skipped)
- **Neo4j AuraDB:** Not yet provisioned. Safely skipped when unconfigured.
- **Qdrant Cloud:** Not yet provisioned. Safely skipped when unconfigured.

---

## 2. Google Colab Secrets Setup (Recommended)

In Google Colab, open the left sidebar, click the **Key icon (Secrets)**, add the keys below, and toggle **Notebook access** to ON:

```text
REDIS_URL                           -> redis://default:<password>@profit-cook-stitch-74158.db.redis.io:18690
MONGODB_URI                         -> mongodb+srv://rag_research:<password>@cluster0.hqd8wfk.mongodb.net/nosql_rag_research?retryWrites=true&w=majority
MONGODB_DATABASE                    -> nosql_rag_research
CASSANDRA_MODE                      -> astra
CASSANDRA_KEYSPACE                  -> nosql_rag_research
CASSANDRA_SECURE_CONNECT_BUNDLE_PATH-> /tmp/astra_scb/secure-connect-bundle.zip
CASSANDRA_APPLICATION_TOKEN         -> AstraCS:<your_token_string>
```

*(Optional unprovisioned secrets: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `QDRANT_URL`, `QDRANT_API_KEY` can be left unset).*

---

## 3. Secure Connect Bundle (SCB) Staging in Colab

In the notebook, execute **Cell 15** (`Stage DataStax Astra DB Secure Connect Bundle`):
1. A file picker dialog will open via `google.colab.files.upload()`.
2. Select your downloaded `secure-connect-nosql-rag-research.zip`.
3. The cell automatically stages it to `/tmp/astra_scb/secure-connect-bundle.zip` with permissions `0600`.
4. It validates that the archive is a readable, uncorrupted ZIP containing Astra configuration markers.
5. The bundle is completely isolated from `/content/nosql-rag-research/` and Google Drive.
6. **Note on Runtime Restart:** `/tmp` is ephemeral. If the runtime is restarted or disconnected, re-run Cell 15 to re-stage the bundle.

---

## 4. Local Development Setup (`.env`)

For local terminal development, copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate the values matching your provisioned endpoints. `.env` and `.env.*` are excluded by `.gitignore`.

Run the automated preflight check:
```bash
python scripts/database_preflight.py
```
This tests configured services, skips unprovisioned ones, and sanitizes all errors.
