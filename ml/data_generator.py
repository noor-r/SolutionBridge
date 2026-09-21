"""Synthetic Data Generator for ML Training and Holdout Evaluation.

Generates statistically grounded synthetic datasets for:
1. Telemetry Metric Observations (Normal vs Abnormal) for Isolation Forest.
2. 1,200+ Labeled Incident Examples across 7 distinct PSE incident classes.
3. 110+ Historical Incident Summaries with past engineering resolutions.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

INCIDENT_CLASSES = [
    "Authentication",
    "Database",
    "Application",
    "Infrastructure",
    "Integration",
    "Performance",
    "Data Consistency",
]


def generate_anomaly_data(n_train_normal: int = 1500, n_test_normal: int = 300, n_test_abnormal: int = 150):
    """
    Generate telemetry data for Isolation Forest.
    Features:
    - response_time_ms
    - db_latency_ms
    - cpu_percent
    - memory_percent
    - request_rate
    - error_rate
    - active_connections
    """
    def _sample_normal(n: int) -> pd.DataFrame:
        return pd.DataFrame({
            "response_time_ms": np.clip(np.random.normal(75.0, 25.0, n), 15.0, 250.0),
            "db_latency_ms": np.clip(np.random.normal(6.5, 2.0, n), 1.0, 20.0),
            "cpu_percent": np.clip(np.random.normal(32.0, 8.0, n), 10.0, 55.0),
            "memory_percent": np.clip(np.random.normal(48.0, 7.0, n), 20.0, 65.0),
            "request_rate": np.clip(np.random.normal(180.0, 40.0, n), 50.0, 400.0),
            "error_rate": np.clip(np.random.normal(0.4, 0.2, n), 0.0, 1.5),
            "active_connections": np.clip(np.random.normal(25.0, 5.0, n), 10.0, 45.0),
        })

    def _sample_abnormal(n: int) -> pd.DataFrame:
        records = []
        for _ in range(n):
            mode = random.choice(["db_spike", "cpu_exhaustion", "latency_explosion", "error_storm"])
            if mode == "db_spike":
                records.append({
                    "response_time_ms": np.random.uniform(2500.0, 5200.0),
                    "db_latency_ms": np.random.uniform(150.0, 450.0),
                    "cpu_percent": np.random.uniform(50.0, 75.0),
                    "memory_percent": np.random.uniform(55.0, 75.0),
                    "request_rate": np.random.uniform(150.0, 350.0),
                    "error_rate": np.random.uniform(8.0, 30.0),
                    "active_connections": np.random.uniform(85.0, 120.0),
                })
            elif mode == "cpu_exhaustion":
                records.append({
                    "response_time_ms": np.random.uniform(800.0, 3000.0),
                    "db_latency_ms": np.random.uniform(10.0, 40.0),
                    "cpu_percent": np.random.uniform(92.0, 99.5),
                    "memory_percent": np.random.uniform(88.0, 98.0),
                    "request_rate": np.random.uniform(800.0, 1500.0),
                    "error_rate": np.random.uniform(15.0, 40.0),
                    "active_connections": np.random.uniform(60.0, 95.0),
                })
            elif mode == "latency_explosion":
                records.append({
                    "response_time_ms": np.random.uniform(3500.0, 6000.0),
                    "db_latency_ms": np.random.uniform(80.0, 250.0),
                    "cpu_percent": np.random.uniform(65.0, 85.0),
                    "memory_percent": np.random.uniform(60.0, 80.0),
                    "request_rate": np.random.uniform(300.0, 600.0),
                    "error_rate": np.random.uniform(4.0, 15.0),
                    "active_connections": np.random.uniform(70.0, 110.0),
                })
            else:  # error_storm
                records.append({
                    "response_time_ms": np.random.uniform(100.0, 400.0),
                    "db_latency_ms": np.random.uniform(5.0, 15.0),
                    "cpu_percent": np.random.uniform(40.0, 65.0),
                    "memory_percent": np.random.uniform(45.0, 65.0),
                    "request_rate": np.random.uniform(400.0, 1000.0),
                    "error_rate": np.random.uniform(45.0, 85.0),
                    "active_connections": np.random.uniform(30.0, 60.0),
                })
        return pd.DataFrame(records)

    # 1. Training set: strictly normal data
    df_train = _sample_normal(n_train_normal)

    # 2. Holdout evaluation set: normal (label 0) and abnormal (label 1)
    df_test_norm = _sample_normal(n_test_normal)
    df_test_norm["is_anomaly"] = 0

    df_test_abn = _sample_abnormal(n_test_abnormal)
    df_test_abn["is_anomaly"] = 1

    df_holdout = pd.concat([df_test_norm, df_test_abn], ignore_index=True)
    df_holdout = df_holdout.sample(frac=1.0, random_state=SEED).reset_index(drop=True)

    return df_train, df_holdout


def generate_incident_classifier_data(n_samples: int = 1400) -> pd.DataFrame:
    """Generate 1,200+ realistic labeled incident records across 7 classes."""
    records = []

    templates = {
        "Authentication": [
            ("Invalid API key provided in X-API-Key header", "AUTH_INVALID", 401, "POST /api/v1/orders", 15.0, 3.0),
            ("Customer signature hash mismatch on authorization request", "AUTH_SIGNATURE_MISMATCH", 401, "POST /api/v1/orders", 20.0, 4.0),
            ("Customer API key expired or revoked", "AUTH_KEY_EXPIRED", 403, "GET /api/v1/products", 18.0, 2.0),
            ("Missing required X-API-Key header in request", "AUTH_REQUIRED", 401, "POST /api/v1/orders", 12.0, 1.0),
            ("Bearer token format invalid or truncated", "AUTH_TOKEN_MALFORMED", 401, "GET /api/v1/customers/1", 16.0, 2.0),
        ],
        "Database": [
            ("Database connection pool timeout waiting for connection", "DB_TIMEOUT", 500, "POST /api/v1/orders", 4820.0, 320.0),
            ("Deadlock detected during concurrent row updates", "DB_DEADLOCK", 500, "POST /api/v1/orders", 2100.0, 180.0),
            ("Can't connect to MySQL database server connection refused", "DB_CONN_ERR", 500, "POST /api/v1/orders", 5010.0, 999.0),
            ("Transaction lock wait timeout exceeded on orders table", "DB_LOCK_TIMEOUT", 500, "POST /api/v1/orders", 4500.0, 250.0),
            ("MySQL server has gone away during batch commit", "DB_DISCONNECTED", 500, "POST /api/v1/orders", 3200.0, 400.0),
        ],
        "Application": [
            ("Unhandled NullPointerException in PricingCalculationEngine", "INTERNAL_EXCEPTION", 500, "POST /api/v1/orders", 110.0, 8.0),
            ("KeyError 'currency' missing from customer payload mapping", "UNHANDLED_KEY_ERROR", 500, "POST /api/v1/orders", 95.0, 6.0),
            ("ZeroDivisionError in tax rate calculation module", "MATH_CALC_ERROR", 500, "POST /api/v1/orders", 85.0, 5.0),
            ("RecursionError maximum recursion depth exceeded in mapper", "APP_RECURSION_LIMIT", 500, "GET /api/v1/products", 250.0, 12.0),
            ("AttributeError object has no attribute 'validate_stock'", "APP_ATTRIBUTE_ERROR", 500, "POST /api/v1/orders", 105.0, 7.0),
        ],
        "Infrastructure": [
            ("Circuit breaker 'order-service-breaker' tripped downstream unavailable", "SERVICE_UNAVAILABLE", 503, "POST /api/v1/orders", 520.0, 15.0),
            ("Resource limit exceeded: CPU at 98.5% container throttled", "RESOURCE_EXHAUSTION", 503, "/health", 1800.0, 45.0),
            ("Out of memory OOM killer terminated worker thread", "OOM_KILLED", 503, "POST /api/v1/orders", 2400.0, 35.0),
            ("Kubernetes ingress returned 502 Bad Gateway to upstream", "INGRESS_502_BAD_GATEWAY", 502, "POST /api/v1/orders", 3100.0, 20.0),
            ("Worker socket pool exhausted: too many open files", "SOCKET_EXHAUSTION", 503, "POST /api/v1/orders", 1500.0, 25.0),
        ],
        "Integration": [
            ("Request payload failed Pydantic schema validation missing amount", "VALIDATION_FAILED", 422, "POST /api/v1/orders", 25.0, 4.0),
            ("Customer webhook delivery timed out after 10000ms max retries", "WEBHOOK_TIMEOUT", 504, "POST /webhooks/orders", 10000.0, 10.0),
            ("Unsupported Content-Type header received expected application/json", "UNSUPPORTED_MEDIA_TYPE", 415, "POST /api/v1/orders", 14.0, 2.0),
            ("Client sent malformed JSON body parse syntax error", "JSON_DECODE_ERROR", 400, "POST /api/v1/orders", 18.0, 3.0),
            ("Invalid query parameter 'limit' must be integer between 1 and 500", "INVALID_QUERY_PARAM", 400, "GET /api/v1/logs", 22.0, 5.0),
        ],
        "Performance": [
            ("Query execution exceeded 4000ms full table scan on orders", "SLOW_SQL_QUERY", 200, "GET /api/v1/customers/1/orders", 4550.0, 195.0),
            ("Gateway SLA violated: upstream processing took 3950ms", "HIGH_LATENCY", 200, "POST /api/v1/orders", 3950.0, 120.0),
            ("Thread pool saturation request queue delay exceeded 2000ms", "THREAD_POOL_SATURATION", 200, "POST /api/v1/orders", 2800.0, 85.0),
            ("High response time degradation on catalog search endpoint", "SLOW_CATALOG_SEARCH", 200, "GET /api/v1/products", 3100.0, 140.0),
            ("Database buffer pool thrashing causing high read IOPS latency", "IOPS_SATURATION", 200, "GET /api/v1/customers/2/orders", 3400.0, 210.0),
        ],
        "Data Consistency": [
            ("Order write failed to commit; transaction aborted after 201 response", "DATA_INCONSISTENCY", 201, "POST /api/v1/orders", 90.0, 25.0),
            ("Audit mismatch: API acknowledged $999.00 but database ledger recorded $0.00", "DATA_INCONSISTENCY", 200, "POST /api/v1/orders", 80.0, 22.0),
            ("Phantom record detected: foreign key customer_id not found in customers", "FK_INTEGRITY_VIOLATION", 409, "POST /api/v1/orders", 110.0, 30.0),
            ("Optimistic lock version conflict on inventory SKU reserve", "VERSION_CONFLICT", 409, "POST /api/v1/orders", 130.0, 35.0),
            ("Asynchronous event queue lost order message before database sync", "EVENT_SYNC_FAILURE", 500, "POST /api/v1/orders", 150.0, 40.0),
        ],
    }

    per_class = n_samples // len(INCIDENT_CLASSES)

    for category, tpl_list in templates.items():
        for _ in range(per_class):
            msg_base, err_code, st_code, ep, base_rt, base_db = random.choice(tpl_list)
            # Add realistic random noise to numerical fields
            rt = max(10.0, np.random.normal(base_rt, base_rt * 0.15))
            db_lat = max(1.0, np.random.normal(base_db, base_db * 0.15))
            cpu = np.clip(np.random.normal(70.0 if category == "Infrastructure" else 35.0, 10.0), 10.0, 99.0)
            mem = np.clip(np.random.normal(75.0 if category == "Infrastructure" else 50.0, 8.0), 20.0, 98.0)

            # Natural textual variance
            prefixes = ["Warning: ", "Alert: ", "Critical incident detected: ", "Log event: ", ""]
            text_feature = f"{random.choice(prefixes)}{msg_base}. Error: {err_code} on {ep} with status {st_code}."

            records.append({
                "text": text_feature,
                "message": msg_base,
                "error_code": err_code,
                "status_code": st_code,
                "endpoint": ep,
                "response_time_ms": round(rt, 2),
                "db_latency_ms": round(db_lat, 2),
                "cpu_percent": round(cpu, 2),
                "memory_percent": round(mem, 2),
                "category": category,
            })

    df = pd.DataFrame(records)
    return df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
