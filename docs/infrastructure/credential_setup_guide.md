# Credential and Secrets Setup Guide

Step-by-step manual setup instructions for configuring live cloud database endpoints in Google Colab Secrets and local development `.env`.

---

## 1. Provider Account Registration (Zero Cost / No Credit Card Required)

Follow these official portals to register zero-cost free-tier accounts:

1. **Redis Cloud:** Sign up at [https://redis.io/try-free/](https://redis.io/try-free/). Create a free subscription (select 30 MB free database on AWS or GCP). Copy the connection URL (`redis://...` or `rediss://...`).
2. **MongoDB Atlas:** Sign up at [https://www.mongodb.com/cloud/atlas/register](https://www.mongodb.com/cloud/atlas/register). Create an **M0 Free Cluster**.
   - Create a dedicated database user with `readWrite` access to `nosql_rag_research`.
   - In **Network Access**, add your current session IP (`<CURRENT_IP>/32`) with a 1-6 hour auto-expiry timer, or temporary access for testing.
   - Copy the SRV connection URI.
3. **DataStax Astra DB (Cassandra):** Sign up at [https://astra.datastax.com/register](https://astra.datastax.com/register).
   - Create a **Serverless** database named `nosql_rag_research` with keyspace `nosql_rag_research`.
   - In **Access Management**, generate an Application Token (role: Database Administrator).
   - In **Connect $\to$ Python**, download the **Secure Connect Bundle (`.zip`)**. Do NOT extract it.
4. **Neo4j AuraDB:** Sign up at [https://neo4j.com/cloud/platform/aura-graph-database/](https://neo4j.com/cloud/platform/aura-graph-database/).
   - Create a **Free Instance**.
   - Save the generated 32-character password and copy the connection URI (`neo4j+s://...`).
5. **Qdrant Cloud:** Sign up at [https://cloud.qdrant.io/](https://cloud.qdrant.io/).
   - Create a **1 GB Free Tier Cluster**.
   - In **Data Access Control**, generate an API key and copy the HTTPS cluster URL (`https://...:6333`).

---

## 2. Google Colab Secrets Setup (Recommended)

In Google Colab, open the left sidebar, click the **Key icon (Secrets)**, add the keys below, and toggle **Notebook access** to ON:

```text
REDIS_URL                           -> rediss://default:<password>@<host>:<port>
MONGODB_URI                         -> mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE                    -> nosql_rag_research
CASSANDRA_MODE                      -> astra
CASSANDRA_KEYSPACE                  -> nosql_rag_research
CASSANDRA_SECURE_CONNECT_BUNDLE_PATH-> /tmp/astra_scb/secure-connect-bundle.zip
CASSANDRA_APPLICATION_TOKEN         -> AstraCS:<your_token_string>
NEO4J_URI                           -> neo4j+s://<instance_id>.databases.neo4j.io
NEO4J_USERNAME                      -> neo4j
NEO4J_PASSWORD                      -> <your_neo4j_password>
NEO4J_DATABASE                      -> neo4j
QDRANT_URL                          -> https://<cluster_id>.<region>.cloud.qdrant.io:6333
QDRANT_API_KEY                      -> <your_qdrant_api_key>
```
*Note on Neo4j:* `NEO4J_USERNAME` is canonical. If `NEO4J_USER` is configured instead, `DatabaseConfig` will automatically map it as a fallback alias.

### Secure Connect Bundle Staging in Colab:
In a notebook cell before running connection checks, stage the bundle outside the project workspace:
```bash
!mkdir -p /tmp/astra_scb && chmod 700 /tmp/astra_scb
# If uploaded to /content/, move to restricted location:
!mv /content/secure-connect-*.zip /tmp/astra_scb/secure-connect-bundle.zip 2>/dev/null || true
!chmod 600 /tmp/astra_scb/secure-connect-bundle.zip
```

---

## 3. Local Development Setup (`.env`)

For testing on your local machine, copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate the values matching your provider instances. `.env` and `.env.*` are excluded by `.gitignore`.

Run the automated preflight check:
```bash
python scripts/database_preflight.py
```
Outputs a clean Markdown table and redacts all secrets from diagnostic logs.
