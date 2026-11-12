# Network, Security, and IP Access Configuration

*Audit Date:* 2026-11-13  
*Scope:* Inbound IP access rules, dynamic Colab IP handling, and transport layer security (TLS).

---

## 1. The Google Colab Dynamic Outbound IP Challenge

Google Colab instances run on dynamic Google Cloud Compute Engine ephemeral pools.
- **Outbound IP Variability:** A Colab session's outbound public IP changes upon every runtime reconnect or kernel reset.
- **Fixed IP Allowlisting Limitation:** Attempting to restrict cloud database firewalls to a single static IP address will fail whenever Colab reconnects to a different worker host.

---

## 2. Provider-by-Provider Network & IP Rules

| Provider | Inbound IP Configuration | Security Control Mechanism | Is `0.0.0.0/0` Required for Colab? | Security Risk Assessment |
| --- | --- | --- | --- | --- |
| **Redis Cloud** | **Security $\to$ Source IP Allowlist** | Password authentication + optional mTLS | **Yes** (allow all IPs or empty allowlist) | **Low Risk:** Protected by strong random password; public port cannot be accessed without correct credentials. |
| **MongoDB Atlas** | **Network Access $\to$ IP Access List** | SCRAM SHA-256 user authentication + TLS | **Yes** (Add `0.0.0.0/0` - Allow Access From Anywhere) | **Low Risk:** Access requires database user credentials; Atlas enforces TLS 1.2+ encryption in transit. |
| **DataStax Astra DB**| **Settings $\to$ IP Access List** | **mTLS Secure Connect Bundle + Token** | **No allowlist needed** | **Very Low Risk:** Connections require both the valid cryptographic client certificates inside the SCB `.zip` AND the application token. |
| **Neo4j AuraDB** | **Aura Console Network Settings** | TLS encryption (`neo4j+s://`) + Password | **Allowed by default** | **Low Risk:** Strong generated 32-character password required; unauthenticated port scans are rejected. |
| **Qdrant Cloud** | **Cluster Network Settings** | HTTPS TLS + Header `api-key` | **Allowed by default** | **Low Risk:** Every REST and gRPC request must supply a valid `api-key` header. |

---

## 3. Security Best Practices for Research Deployments

1. **Dedicated Database Users:** For MongoDB and Neo4j, create a dedicated application user with permissions restricted solely to the research database/keyspace (`nosql_rag_research`), rather than using root/admin accounts.
2. **Temporary Research Instances:** Free tier instances should contain **zero proprietary, personal, or production data**.
3. **Immediate Post-Experiment Deletion:** When research benchmarks are complete, clusters can be paused or deleted from provider consoles to eliminate lingering exposed endpoints.
