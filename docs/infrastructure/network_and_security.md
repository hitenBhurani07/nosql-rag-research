# Network, Security, and IP Access Configuration

*Audit Date:* 2026-11-13  
*Scope:* Inbound IP access rules, dynamic Colab IP handling, secure connectivity alternatives, and transport layer security (TLS).

---

## 1. The Google Colab Dynamic Outbound IP Challenge

Google Colab instances execute on ephemeral Google Cloud Compute Engine VM pools:
- **Outbound IP Variability:** A Colab session's outbound public IP is assigned dynamically from large Google Cloud CIDR blocks. Every runtime restart, disconnect, or timeout allocates a different public IP.
- **Why Blanket `0.0.0.0/0` is Deficient:** Granting universal internet access (`0.0.0.0/0`) exposes database listening ports to global port scanners and brute-force attempts. While transport encryption (TLS) and SCRAM/password authentication remain active, blanket open ingress increases attack surfaces.
- **Core Principle:** Automatic deployment of networking daemons or opening ports automatically by the agent is forbidden. The options below provide secure, documented alternatives.

---

## 2. Technical Investigation of Network Access Alternatives

We evaluated four candidate architectures for connecting client runtimes to remote databases:

### Option A: Session-Specific Temporary IP Allowlisting with Auto-Expiry (Recommended for Colab Development)
- **Mechanism:** At runtime startup, determine the Colab instance's exact current public egress IP using an external lookup:
  ```bash
  curl -s https://api.ipify.org
  ```
- **Atlas Configuration:** In MongoDB Atlas **Network Access $\to$ Add IP Address**, enter `<COLAB_CURRENT_IP>/32` and enable the built-in Atlas feature: **"This IP address will be temporarily added for 1 hour / 6 hours"**.
- **Assessment:**
  - *Security:* High. Access is restricted exclusively to the active Colab worker and auto-terminates after the session.
  - *Colab Compatibility:* Excellent. Fully compatible with zero external proxies or cost.
  - *Operational Burden:* Requires updating the entry when Colab reconnects to a fresh runtime.

### Option B: Controlled Benchmark-Client VM with Stable Egress (Recommended for Mode B Benchmarking)
- **Mechanism:** Run benchmarking on a dedicated VM (such as an OCI Always Free instance or GCP Spot VM) assigned a single static external IPv4 address (`<STATIC_VM_IP>`).
- **Atlas / Provider Configuration:** Allowlist strictly `<STATIC_VM_IP>/32`.
- **Assessment:**
  - *Security:* Highest. Ingress is locked to one verified host.
  - *Colab Compatibility:* Bypasses Colab entirely for publishable benchmarks, simultaneously eliminating WAN routing variance.

### Option C: Secure Network Tunnels (SSH / Cloudflare Tunnel / ngrok)
- **Mechanism:** Establish an encrypted egress tunnel from the Colab notebook to a secure intermediary proxy or jump host.
- **Assessment:**
  - *Security:* High. Outbound-only tunnel eliminates public ingress requirements.
  - *Colab Compatibility:* Moderate. Requires running background tunnel daemons and configuring port-forwarding inside the notebook, which adds fragile operational dependencies.

### Option D: Provider-Supported Private Connectivity (VPC Peering / PrivateLink / PSC)
- **Mechanism:** Direct private IP routing over cloud provider internal networks.
- **Assessment:**
  - *Free Tier Incompatibility:* **Unavailable on MongoDB Atlas M0**. Atlas restricts VPC Peering and AWS PrivateLink / GCP Private Service Connect to dedicated clusters (M10+). Furthermore, standard Google Colab runtimes cannot be attached to a customer VPC (only managed GCP Vertex AI Workbench enterprise runtimes support VPC attachment).

---

## 3. Provider-by-Provider Network & Inbound Access Rules

| Provider | Inbound IP Configuration | Security Control Mechanism | Recommended Inbound Access Policy |
| :--- | :--- | :--- | :--- |
| **Redis Cloud** | Security $\to$ Source IP Allowlist | TLS/SSL + strong generated password | Restrict to current Colab session `/32` IP, or dedicated VM IP. |
| **MongoDB Atlas** | Network Access $\to$ IP Access List | TLS 1.2+ mandatory + SCRAM SHA-256 user authentication | **Temporary session IP (`<COLAB_IP>/32`) with 1–6 hour auto-expiry**. If `0.0.0.0/0` is used for brief initial testing, apply strict mitigations below. |
| **DataStax Astra DB** | Settings $\to$ IP Access List | **Mutual TLS (mTLS) via Secure Connect Bundle + Token** | **No firewall allowlist required**. mTLS cryptographic verification rejects all traffic lacking client certificates, regardless of source IP. |
| **Neo4j AuraDB** | Aura Console Security Settings | TLS encrypted transport (`neo4j+s://`) + 32-char generated password | Public endpoint secured by TLS and credentials; unauthenticated requests rejected at gateway. |
| **Qdrant Cloud** | Cluster Network Settings | HTTPS TLS + mandatory `api-key` header | Public endpoint secured by API key authentication; non-matching headers rejected immediately. |

---

## 4. Mandatory Security Mitigations If Using Temporary Ingress

If temporary broad ingress (`0.0.0.0/0`) is utilized during preliminary connection testing, the following mandatory hardening rules apply:
1. **Dedicated Non-Admin User:** Create a MongoDB user restricted strictly to `readWrite` on the `nosql_rag_research` database. Never use cluster administrative accounts (`atlasAdmin`).
2. **High-Entropy Credentials:** Generate a randomized 32-character alphanumeric password with special symbols.
3. **Empty Research Database:** The instance must never house personal, proprietary, or production data.
4. **Immediate Rule Deletion:** Delete the IP allowlist rule or pause the cluster immediately upon experiment completion.
