# Phase A — Machine Preflight Summary

Generated: 2026-11-14T08:08 UTC

## A1. Tool Versions
| Tool | Version | Required | Status |
|------|---------|----------|--------|
| git | 2.51.2.windows.1 | any | ✅ |
| Python | 3.14.0 | ≥ 3.10 | ✅ |
| Docker | 29.9.2 | any | ✅ |
| requires-python (pyproject.toml) | ≥ 3.10 | — | ✅ |

## A2. Secret Leak Check
- Only `.env.example` matched the pattern — contains placeholder values only.
- No real `AstraCS:` token committed. Only `AstraCS:xxxx` and `AstraCS:fake-token` in docs/tests.
- **Result: CLEAN ✅**

## A3. WSL2 Memory Cap
- `.wslconfig` written fresh (no prior file):
  ```
  [wsl2]
  memory=3GB
  processors=6
  swap=4GB
  ```
  (MINIMAL plan — capped at 3 GB because free RAM is 3–5 GB range)

## A4. Docker Desktop
- Launched from `C:\Users\hiten\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe`
- `docker run --rm hello-world` → ✅
- `docker info` → Server version: 29.9.2 ✅

## A5. Power Settings
- standby-timeout-ac = 0 (applied)
- monitor-timeout-ac = 60 (applied)
- High-performance plan set attempted

## A6. Memory at Baseline (WSL + Docker both running)
| Metric | Value |
|--------|-------|
| Free RAM (after WSL shutdown) | 4.16 GB |
| Free RAM (after Docker started) | 1.66 GB |
| Total RAM | 15.69 GB |
| WSL2 (vmmemWSL) | ~1.7 GB |
| Diagnostic: Free GB | 1.66 |
| Diagnostic: Used GB | 11.53 |
| Sum of process working sets | 15.12 GB |
| Pool Nonpaged Bytes | 1.163 GB |
| Pool Paged Bytes | 0.599 GB |

## Plan Selection: **MINIMAL**
- Free RAM (true baseline, WSL+Docker stopped): **4.16 GB**
- Threshold: 3–5 GB → MINIMAL plan
- **Engines: Redis, MongoDB, Qdrant only (one at a time)**
- Cassandra and Neo4j: SKIPPED (see DECISIONS.md)
- WSL2 capped at 3 GB

## Top Memory Consumers (at measurement time)
| Process | MB |
|---------|-----|
| vmmemWSL | 1,705 |
| chrome | 394 |
| agy | 366 |
| Antigravity IDE | 362+ |
| MsMpEng | 357 |

