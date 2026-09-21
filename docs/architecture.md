# SolutionBridge Architecture Specification

SolutionBridge is an enterprise-grade platform built specifically for **Product Solutions Engineers (PSE)**. It automates and unifies the end-to-end investigation lifecycle:
**Customer Integration → API Testing → SQL Validation → Log Analysis → System Monitoring → ML-Assisted Diagnosis → Troubleshooting Actions**.

```text
                    +-------------------------------------------+
                    |        Streamlit Operations Portal        |
                    | (Overview, SQL, Logs, ML, Incidents, etc) |
                    +---------------------+---------------------+
                                          | HTTP
                                          v
                    +-------------------------------------------+
                    |          FastAPI Gateway & Auth           |
                    |   (Request-ID Tracking, Masked Keys)      |
                    +----+----------------+----------------+----+
                         |                |                |
                         v                v                v
                 Integration APIs    Incident APIs   Telemetry APIs
                         |                |                |
                         +--------+       |       +--------+
                                  |       |       |
                                  v       v       v
+-----------------------+   +-------------------------------+   +------------------------+
|    MySQL 8 / SQLite   |   |   Diagnostic Evidence Engine  |   | System Metric Stream   |
| (Orders, Customers,   |<--+ (Raw SQL, Logs, Metrics, ML)  +-->| (CPU, RAM, DB Latency, |
|  Endpoints, Runs)     |   +---------------+---------------+   |  Active Connections)   |
+-----------------------+                   |                   +------------------------+
                                            v
                            +---------------+---------------+
                            |   Machine Learning Pipelines  |
                            +-------+-------+-------+-------+
                                    |       |       |
                 +------------------+       |       +------------------+
                 v                          v                          v
      Isolation Forest             TF-IDF + Logistic           FAISS Vector Index
    (Telemetry Outliers)          (7-Class Classifier)         (Semantic Search)
                 |                          |                          |
                 +------------------+       |       +------------------+
                                    |       |       |
                                    v       v       v
                            +-------------------------------+
                            |    Root Cause & Remediation   |
                            | (Evidence-Weighted Reasoning) |
                            +---------------+---------------+
                                            |
                                            v
                            +-------------------------------+
                            |  Engineer & Customer Dossiers |
                            +-------------------------------+
```

---

## 1. Core Architectural Pillars

### 1.1 Dual Database Architecture (Explicit Mode)
- **Primary / Production Engine**: MySQL 8.0 accessed via `mysql+pymysql://` with connection pooling, pool pre-ping, and recycling.
- **Development & In-Memory Engine**: SQLite (`sqlite:///./solutionbridge_dev.db` or `:memory:`) supported explicitly through `DATABASE_URL` for rapid local developer iteration and isolated unit testing.
- **Migrations**: Alembic handles schema versioning across all 11 tables with bidirectional upgrade/downgrade logic.

### 1.2 Dedicated Raw SQL Troubleshooting Layer
Standard application operations (CRUD, customer onboarding, order placing) utilize SQLAlchemy ORM.
In contrast, forensic diagnostic operations bypass ORM abstractions and execute real, parameterized ANSI-compliant SQL via `app/services/sql_validation_service.py`:
1. `validate_order_persistence`: Proves whether an order was written to disk or aborted.
2. `check_duplicate_orders`: Detects non-idempotent submissions from customer retry storms.
3. `inspect_endpoint_latency_stats`: Calculates `AVG`, `MIN`, `MAX` response times over specified time windows.
4. `aggregate_error_codes_by_request`: Correlates distributed error codes across microservices.
5. `check_customer_failure_rate`: Differentiates tenant-isolated bugs from platform-wide outages.
6. `detect_status_mismatches`: Finds stalled transactions stuck in `PENDING` states.
7. `inspect_db_contention_metrics`: Tracks DB latency spikes and pool exhaustion.
8. `find_unhandled_exceptions`: Isolates unhandled 5xx server exceptions.
9. `detect_silent_order_rollbacks`: Reconciles API 201 responses against missing DB rows.
10. `inspect_customer_integration_health`: Aggregates 24-hour SLA scorecards for client syncs.
11. `get_top_failing_endpoints`: Ranks brittle endpoints across all test runs.

### 1.3 Machine Learning Intelligence Layer
The ML layer operates as an advisory diagnostic signal, never inventing facts:
- **Anomaly Detection (`IsolationForest`)**: Trained strictly on normal telemetry baseline; evaluated on holdout datasets with labeled anomalies. Computes real-time decision function scores.
- **Incident Classification (`TF-IDF + LogisticRegression`)**: Predicts likely incident categories across 7 classes: `Authentication`, `Database`, `Application`, `Infrastructure`, `Integration`, `Performance`, and `Data Consistency`. Evaluated with confusion matrices and weighted F1 metrics.
- **Semantic Retrieval (`Sentence-Transformers + FAISS`)**: Embeds incident signatures using `all-MiniLM-L6-v2` and retrieves top-3 historical postmortems and past engineering resolutions using inner-product cosine similarity.

---

## 2. Multi-Evidence Synthesis Sequence

When a partner API fails, the platform executes a deterministic investigation pipeline:

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Partner System
    participant Gateway as SolutionBridge API
    participant Logs as Structured Logger
    participant SQL as SQL Validation Service
    participant Metrics as System Metrics
    participant ML as ML Pipeline (IsoForest, TF-IDF, FAISS)
    participant Engine as Root Cause Engine
    participant Remediation as Troubleshooting Engine

    Customer->>Gateway: POST /api/v1/orders (Payload + X-API-Key)
    Gateway-->>Logs: Emit JSON log (REQ-ID, latency, error_code)
    Gateway-->>Customer: HTTP Error (e.g. 500 DB_TIMEOUT)
    
    Note over Gateway,Remediation: Automated Solutions Engineering Analysis Triggered
    
    Gateway->>Logs: Query correlated logs for REQ-ID
    Logs-->>Engine: Chronological timeline & error codes
    
    Gateway->>SQL: Execute Query 01 & 09 (Persistence & Rollback Check)
    SQL-->>Engine: Row missing; persistence failed
    
    Gateway->>Metrics: Query telemetry vector around REQ-ID timestamp
    Metrics-->>Engine: DB Latency = 280ms, Active Conns = 98
    
    Gateway->>ML: Evaluate Anomaly Score & Incident Class
    ML-->>Engine: Anomaly = True (-0.420), Category = Database (96%)
    
    Gateway->>ML: FAISS Search historical corpus
    ML-->>Engine: Top match INC-421 (82.8% match, pool exhaustion)
    
    Engine->>Remediation: Synthesize facts & trigger rules
    Remediation-->>Gateway: Prioritized Actions (1. Pool, 2. Locks, 3. Health)
    Gateway-->>Customer: Issue Customer-Facing Communication & Internal Postmortem
```

---

## 3. Security & Masked Credentials

- **Raw Key Ingestion**: Generated API keys (e.g. `sb_live_acme_retail_key_9281`) are displayed to the user only once upon creation.
- **Database Storage**: Only HMAC-SHA256 hashes are persisted in the `api_key_hash` column.
- **Display Layer**: All endpoints and Streamlit dashboards mask keys (e.g. `sb_live_***9281`), completely preventing credential leakage in logs and screenshots.
- **Authentication**: Constant-time HMAC comparison prevents timing attacks during header validation.
