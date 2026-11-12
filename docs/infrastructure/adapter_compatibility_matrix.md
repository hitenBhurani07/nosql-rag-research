# Adapter Compatibility Matrix and Technical Audit

*Audit Date:* 2026-11-13  
*Scope:* Technical compatibility of `nosql_rag` Python adapters against shortlisted cloud database providers.

---

## 1. Engine-by-Engine Adapter Compatibility

| Database | Shortlisted Provider | Existing Adapter Implementation | Required Connection Protocol | Authentication Method | Special Files / Certificates | Adapter Status |
| --- | --- | --- | --- | --- | --- | --- |
| **Redis** | Redis Cloud Free | `RedisAdapter` (`redis-py`) | `rediss://` or `redis://` over TLS | User/Password in URI | None (standard CA TLS) | **100% Compatible** (no code changes needed) |
| **MongoDB** | MongoDB Atlas M0 | `MongoAdapter` (`pymongo`) | `mongodb+srv://` over TLS | SCRAM User/Password | None (standard CA TLS) | **100% Compatible** (no code changes needed) |
| **Cassandra** | DataStax Astra DB | `CassandraAdapter` (`cassandra-driver`) | mTLS over Secure Connect Bundle | Application Token (`token` / `AstraCS:...`) | **`secure-connect-database.zip`** | **Enhanced in Phase 13** (dual-mode standard + Astra added) |
| **Cassandra** | Self-Hosted / OCI | `CassandraAdapter` (`cassandra-driver`) | CQL native binary port (9042) | PlainText / None | Optional custom TLS cert | **100% Compatible** (standard mode preserved) |
| **Neo4j** | Neo4j AuraDB Free | `Neo4jAdapter` (`neo4j-python-driver`) | Bolt over TLS (`neo4j+s://`) | Basic (`neo4j` / Password) | None (standard CA TLS) | **100% Compatible** (no code changes needed) |
| **Qdrant** | Qdrant Cloud Free | `QdrantAdapter` (`qdrant-client`) | HTTPS REST / gRPC port 6333 | HTTP Header `api-key` | None (standard CA TLS) | **100% Compatible** (no code changes needed) |

---

## 2. Cassandra Astra DB Integration Audit

### 2.1 The Technical Divergence
Standard Apache Cassandra uses direct contact points (`contact_points=['127.0.0.1'], port=9042`).
DataStax Astra DB Serverless operates behind an enterprise mTLS proxy. Direct TCP connections to raw IPs are rejected. Clients must provide a **Secure Connect Bundle (SCB)** `.zip` containing:
- `cqlshrc`
- `config.json`
- `ca.crt`
- `cert` & `key`

### 2.2 Phase 13 Implementation Resolution
In Phase 13, `nosql_rag.adapters.crud.CassandraAdapter` was enhanced to support **both modes seamlessly**:

```python
if self.mode == "astra":
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.cluster import Cluster

    auth = PlainTextAuthProvider("token", application_token)
    cloud_config = {"secure_connect_bundle": secure_connect_bundle_path}
    self.cluster = Cluster(cloud=cloud_config, auth_provider=auth, connect_timeout=15)
else:
    # Standard contact-point cluster connection preserved for self-hosted / Docker / OCI
    ...
```

### 2.3 Python 3.12 `asyncore` Compatibility Fix
In Python 3.12, the standard library deprecated and removed `asyncore`, causing older `cassandra-driver` installations to fail during cluster initialization.
**Resolution:** Added `pyasyncore>=1.0.4` to `pyproject.toml` dependencies under Python 3.12+, fully resolving driver initialization.
