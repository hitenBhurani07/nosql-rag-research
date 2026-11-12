# DataStax Astra DB Serverless Integration Guide

*Topic:* Connecting to DataStax Astra DB Serverless using the enhanced dual-mode `CassandraAdapter` in `nosql-rag-research`.

---

## 1. Prerequisites from Astra Portal

1. **Database:** Create a Serverless database in [Astra Portal](https://astra.datastax.com/).
   - Database Name: `nosql_rag_research`
   - Keyspace Name: `nosql_rag_research`
   - Cloud Provider/Region: AWS `us-east-1` (or your preferred region).
2. **Application Token:**
   - Go to **Organization Settings** $\to$ **Access Management** $\to$ **Token Management**.
   - Role: Select **Database Administrator**.
   - Click **Generate Token**.
   - Copy the **Token** string (starts with `AstraCS:...`).
3. **Secure Connect Bundle (SCB):**
   - In Astra Portal, click your database $\to$ **Connect** tab $\to$ **Python**.
   - Under **Download Secure Connect Bundle**, download `secure-connect-<database_name>.zip`.
   - **DO NOT UNZIP THIS FILE.** The driver reads the `.zip` archive directly.

---

## 2. Safe Bundle Handling in Google Colab

The Secure Connect Bundle contains sensitive TLS keys and certificates.
- **NEVER** commit the `.zip` bundle to GitHub (`.gitignore` excludes `*.zip`).
- **NEVER** store the bundle in a public shared folder.
- **Colab Upload Procedure:**
  1. In Google Colab, click the **Files folder icon** in the left sidebar.
  2. Click **Upload to session storage** and upload `secure-connect-database.zip` directly into `/content/`.
  3. In Colab Secrets, configure:
     ```text
     CASSANDRA_MODE                       = astra
     CASSANDRA_KEYSPACE                   = nosql_rag_research
     CASSANDRA_SECURE_CONNECT_BUNDLE_PATH = /content/secure-connect-database.zip
     CASSANDRA_APPLICATION_TOKEN          = AstraCS:...
     ```
  4. When the Colab runtime shuts down or resets, temporary files in `/content/` are wiped automatically.

---

## 3. How the Adapter Executes Astra Queries

`nosql_rag.adapters.crud.CassandraAdapter` automatically detects `cassandra_mode == "astra"`:
1. Passes `cloud={"secure_connect_bundle": bundle_path}` to `Cluster`.
2. Authenticates using `PlainTextAuthProvider("token", application_token)`.
3. Connects to `keyspace` and prepares CQL statements (`INSERT`, `SELECT`, `UPDATE`, `DROP TABLE`).
4. Executes queries with full parity to standard Cassandra.
