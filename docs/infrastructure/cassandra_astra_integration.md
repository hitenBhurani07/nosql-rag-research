# DataStax Astra DB Serverless Integration Guide

*Topic:* Connecting to DataStax Astra DB Serverless using the dual-mode `CassandraAdapter` in `nosql-rag-research`.

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
   - **DO NOT UNZIP THIS FILE.** The driver inspects the `.zip` archive directly in memory.

---

## 2. Mandatory Secure Bundle Handling Protocol

The Secure Connect Bundle contains sensitive private cryptographic keys and TLS certificates. To prevent accidental disclosure:

### Strict Security Rules:
1. **Never enter GitHub:** The bundle filename pattern `*.zip` and `secure-connect*.zip` are excluded by `.gitignore`.
2. **Never appear in notebook outputs:** Never print, dump, or display the binary contents or file paths in cell outputs.
3. **Never be included in experiment ZIP exports:** Do not place the bundle inside `/content/nosql-rag-research/`. Keeping the bundle strictly in `/tmp/astra_scb/` ensures repository export scripts (`shutil.make_archive`) will never package the bundle into result archives.
4. **Never copy into ordinary artifact directories:** Do not store the bundle in `outputs/`, `data/`, or `results/`.
5. **Handle in restricted temporary storage:** Use `/tmp/astra_scb/secure-connect-bundle.zip` with restricted file permissions (`chmod 600`).
6. **Post-experiment cleanup:** Remove `/tmp/astra_scb/` once benchmark execution concludes.

### Colab Setup Commands:
In a dedicated setup cell in Google Colab:
```bash
# Create dedicated restricted temporary directory outside project workspace
mkdir -p /tmp/astra_scb
chmod 700 /tmp/astra_scb

# If uploaded to /content/secure-connect-bundle.zip, move to /tmp/astra_scb:
mv /content/secure-connect-*.zip /tmp/astra_scb/secure-connect-bundle.zip 2>/dev/null || true
chmod 600 /tmp/astra_scb/secure-connect-bundle.zip
```

### Colab Secrets Configuration:
Add these keys in Colab Secrets (left sidebar Key icon):
```text
CASSANDRA_MODE                       -> astra
CASSANDRA_KEYSPACE                   = nosql_rag_research
CASSANDRA_SECURE_CONNECT_BUNDLE_PATH -> /tmp/astra_scb/secure-connect-bundle.zip
CASSANDRA_APPLICATION_TOKEN          -> AstraCS:<your_token_string>
```

### Teardown / Cleanup:
When the benchmark completes:
```bash
rm -rf /tmp/astra_scb
```

---

## 3. Dual-Mode Architecture in `nosql_rag`

The `CassandraAdapter` supports both deployment paradigms:

### Mode 1: DataStax Astra DB Serverless (`cassandra_mode="astra"`)
When `cassandra_mode == "astra"` or when bundle/token credentials are provided:
1. Initializes `Cluster(cloud={"secure_connect_bundle": bundle_path}, auth_provider=PlainTextAuthProvider("token", application_token))`.
2. Connects to `keyspace` and prepares CQL statements (`INSERT`, `SELECT`, `UPDATE`, `DROP TABLE`).
3. Executes queries over an encrypted mTLS tunnel.

### Mode 2: Standard Apache Cassandra (`cassandra_mode="standard"`)
When running against standard self-hosted Cassandra, local Docker, or Mode B cloud VMs:
1. Configures `Cluster(contact_points=hosts, port=port, auth_provider=auth, ssl_context=ssl)`.
2. Bypasses SCB requirements completely.
