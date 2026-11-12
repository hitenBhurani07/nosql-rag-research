# Credential and Secrets Setup Guide

Step-by-step manual setup instructions for configuring live cloud database endpoints in Google Colab Secrets and local development `.env`.

---

## 1. Provider Account Registration (Zero Cost / No Credit Card)

Follow these official portals to register zero-cost free-tier accounts:

1. **Redis Cloud:** Sign up at [https://redis.io/try-free/](https://redis.io/try-free/). Create a free subscription (select 30 MB free database on AWS or GCP).
2. **MongoDB Atlas:** Sign up at [https://www.mongodb.com/cloud/atlas/register](https://www.mongodb.com/cloud/atlas/register). Create an **M0 Free Cluster** (select AWS us-east-1 or closest region).
3. **DataStax Astra DB (Cassandra):** Sign up at [https://astra.datastax.com/register](https://astra.datastax.com/register). Create a **Serverless (Vector/CQL)** database named `nosql_rag_research` with keyspace `nosql_rag_research`.
4. **Neo4j AuraDB:** Sign up at [https://neo4j.com/cloud/platform/aura-graph-database/](https://neo4j.com/cloud/platform/aura-graph-database/). Create a **Free Instance** (save the generated password).
5. **Qdrant Cloud:** Sign up at [https://cloud.qdrant.io/](https://cloud.qdrant.io/). Create a **1 GB Free Tier Cluster**.

---

## 2. Google Colab Secrets Setup (Recommended)

In Google Colab, open the left sidebar, click the **Key icon (Secrets)**, add the keys below, and toggle **Notebook access** to ON:

```text
REDIS_URL                           -> rediss://default:<password>@<host>:<port>
MONGODB_URI                         -> mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE                    -> nosql_rag_research
CASSANDRA_MODE                      -> astra
CASSANDRA_KEYSPACE                  -> nosql_rag_research
CASSANDRA_SECURE_CONNECT_BUNDLE_PATH-> /content/secure-connect-database.zip
CASSANDRA_APPLICATION_TOKEN         -> AstraCS:<your_token_string>
NEO4J_URI                           -> neo4j+s://<instance_id>.databases.neo4j.io
NEO4J_USERNAME                      -> neo4j
NEO4J_PASSWORD                      -> <your_neo4j_password>
NEO4J_DATABASE                      -> neo4j
QDRANT_URL                          -> https://<cluster_id>.<region>.cloud.qdrant.io:6333
QDRANT_API_KEY                      -> <your_qdrant_api_key>
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
