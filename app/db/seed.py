"""Deterministic seed data generation for SolutionBridge."""

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from app.core.security import hash_api_key
from app.db.models import (
    Customer,
    Product,
    ApiEndpoint,
    ApiTestRun,
    Order,
    Log,
    SystemMetric,
    HistoricalIncident,
)
from app.core.logging import logger

# Deterministic Seed for Reproducibility
SEED_VALUE = 42

# Known test credentials (raw keys saved for Postman/Newman & testing, hashes stored in DB)
DEMO_CUSTOMERS_DATA = [
    {
        "id": 1,
        "name": "Acme Retail",
        "email": "integration@acmeretail.com",
        "environment": "production",
        "raw_key": "sb_live_acme_retail_key_9281",
    },
    {
        "id": 2,
        "name": "Nova Commerce",
        "email": "tech@novacommerce.io",
        "environment": "production",
        "raw_key": "sb_live_nova_comm_key_1829",
    },
    {
        "id": 3,
        "name": "Zenith Logistics",
        "email": "api@zenithlogistics.net",
        "environment": "sandbox",
        "raw_key": "sb_test_zenith_log_key_4410",
    },
]

DEMO_PRODUCTS_DATA = [
    {"sku": "PROD-1001", "name": "Enterprise Analytics Suite", "price": Decimal("299.99"), "stock": 500, "desc": "B2B telemetry analysis seat"},
    {"sku": "PROD-1002", "name": "Cloud API Gateway Pro", "price": Decimal("149.50"), "stock": 350, "desc": "Rate-limited API gateway subscription"},
    {"sku": "PROD-1003", "name": "Event Stream Pipeline", "price": Decimal("450.00"), "stock": 200, "desc": "Kafka-compatible managed event broker"},
    {"sku": "PROD-1004", "name": "Edge Cache Accelerator", "price": Decimal("89.00"), "stock": 600, "desc": "Sub-millisecond global CDN cache"},
    {"sku": "PROD-1005", "name": "Audit & Compliance Logger", "price": Decimal("199.00"), "stock": 400, "desc": "Immutable append-only audit trail module"},
    {"sku": "PROD-1006", "name": "Integration Webhook Hub", "price": Decimal("75.00"), "stock": 1000, "desc": "High-throughput webhook delivery cluster"},
    {"sku": "PROD-1007", "name": "ML Anomaly Detector Agent", "price": Decimal("599.00"), "stock": 150, "desc": "Automated telemetry outlier detection engine"},
    {"sku": "PROD-1008", "name": "Secure Vault Tokenizer", "price": Decimal("129.95"), "stock": 800, "desc": "Zero-trust tokenization for sensitive payloads"},
]

DEMO_ENDPOINTS_DATA = [
    {"name": "Health Check", "method": "GET", "endpoint": "/health", "service": "gateway-service", "expected_status": 200, "max_response_time_ms": 100},
    {"name": "Readiness Probe", "method": "GET", "endpoint": "/ready", "service": "gateway-service", "expected_status": 200, "max_response_time_ms": 150},
    {"name": "List Customers", "method": "GET", "endpoint": "/api/v1/customers", "service": "customer-service", "expected_status": 200, "max_response_time_ms": 250},
    {"name": "Get Customer", "method": "GET", "endpoint": "/api/v1/customers/{customer_id}", "service": "customer-service", "expected_status": 200, "max_response_time_ms": 200},
    {"name": "List Products", "method": "GET", "endpoint": "/api/v1/products", "service": "product-service", "expected_status": 200, "max_response_time_ms": 200},
    {"name": "Get Product", "method": "GET", "endpoint": "/api/v1/products/{product_id}", "service": "product-service", "expected_status": 200, "max_response_time_ms": 180},
    {"name": "Create Order", "method": "POST", "endpoint": "/api/v1/orders", "service": "order-service", "expected_status": 201, "max_response_time_ms": 400},
    {"name": "Get Order", "method": "GET", "endpoint": "/api/v1/orders/{order_id}", "service": "order-service", "expected_status": 200, "max_response_time_ms": 200},
    {"name": "Customer Orders", "method": "GET", "endpoint": "/api/v1/customers/{customer_id}/orders", "service": "order-service", "expected_status": 200, "max_response_time_ms": 300},
    {"name": "System Metrics", "method": "GET", "endpoint": "/api/v1/metrics", "service": "telemetry-service", "expected_status": 200, "max_response_time_ms": 250},
    {"name": "Log Explorer", "method": "GET", "endpoint": "/api/v1/logs", "service": "telemetry-service", "expected_status": 200, "max_response_time_ms": 300},
]


def seed_database(db: Session) -> Dict[str, int]:
    """Populate database with deterministic initial and historical seed data."""
    random.seed(SEED_VALUE)
    now = datetime.now(timezone.utc)

    # 1. Customers
    existing_cust_count = db.query(Customer).count()
    if existing_cust_count == 0:
        for cust in DEMO_CUSTOMERS_DATA:
            customer = Customer(
                id=cust["id"],
                name=cust["name"],
                email=cust["email"],
                environment=cust["environment"],
                api_key_hash=hash_api_key(cust["raw_key"]),
                status="active",
                created_at=now - timedelta(days=60),
            )
            db.add(customer)
        db.commit()

    # 2. Products
    existing_prod_count = db.query(Product).count()
    if existing_prod_count == 0:
        for p in DEMO_PRODUCTS_DATA:
            product = Product(
                sku=p["sku"],
                name=p["name"],
                description=p["desc"],
                price=p["price"],
                stock=p["stock"],
                is_active=True,
                created_at=now - timedelta(days=60),
            )
            db.add(product)
        db.commit()

    # 3. API Endpoints
    existing_ep_count = db.query(ApiEndpoint).count()
    if existing_ep_count == 0:
        for ep in DEMO_ENDPOINTS_DATA:
            endpoint = ApiEndpoint(
                name=ep["name"],
                method=ep["method"],
                endpoint=ep["endpoint"],
                service=ep["service"],
                expected_status=ep["expected_status"],
                max_response_time_ms=ep["max_response_time_ms"],
                active=True,
            )
            db.add(endpoint)
        db.commit()

    endpoints = db.query(ApiEndpoint).all()
    endpoint_ids = [ep.id for ep in endpoints]

    # 4. Orders (120+ orders)
    existing_order_count = db.query(Order).count()
    if existing_order_count < 100:
        orders = []
        statuses = ["COMPLETED", "COMPLETED", "COMPLETED", "PENDING", "PROCESSING", "FAILED"]
        for i in range(1, 131):
            cust_id = random.choice([1, 2, 3])
            order_time = now - timedelta(days=random.randint(0, 30), minutes=random.randint(0, 1440))
            order = Order(
                customer_id=cust_id,
                external_order_id=f"ORD-EXT-{cust_id*1000 + i}",
                status=random.choice(statuses),
                amount=Decimal(str(round(random.uniform(25.0, 1850.0), 2))),
                created_at=order_time,
                updated_at=order_time + timedelta(seconds=random.randint(1, 120)),
            )
            orders.append(order)
        db.bulk_save_objects(orders)
        db.commit()

    # 5. API Test Runs (1050+ records)
    existing_runs_count = db.query(ApiTestRun).count()
    if existing_runs_count < 1000:
        test_runs = []
        for i in range(1, 1051):
            ep_id = random.choice(endpoint_ids)
            cust_id = random.choice([1, 2, 3, None])
            run_time = now - timedelta(days=random.randint(0, 14), minutes=random.randint(0, 1440))
            req_id = f"REQ-TEST-{10000 + i}"

            # 92% pass, 5% failure, 3% timeout/error
            roll = random.random()
            if roll < 0.92:
                status_code = 200
                test_status = "PASSED"
                resp_time = round(random.uniform(25.0, 180.0), 2)
                resp_body = '{"status": "success", "data": "ok"}'
                err_msg = None
            elif roll < 0.97:
                status_code = 400
                test_status = "FAILED"
                resp_time = round(random.uniform(40.0, 220.0), 2)
                resp_body = '{"status": "error", "error_code": "VALIDATION_FAILED"}'
                err_msg = "Payload validation failure: missing required parameter"
            else:
                status_code = 500
                test_status = "ERROR"
                resp_time = round(random.uniform(1200.0, 4800.0), 2)
                resp_body = '{"status": "error", "error_code": "INTERNAL_DB_TIMEOUT"}'
                err_msg = "Connection timed out waiting for backend database response"

            run = ApiTestRun(
                customer_id=cust_id,
                endpoint_id=ep_id,
                request_id=req_id,
                status_code=status_code,
                response_time_ms=resp_time,
                test_status=test_status,
                response_body=resp_body,
                error_message=err_msg,
                created_at=run_time,
            )
            test_runs.append(run)
        db.bulk_save_objects(test_runs)
        db.commit()

    # 6. Structured Logs (3200+ log entries)
    existing_log_count = db.query(Log).count()
    if existing_log_count < 3000:
        logs = []
        services = ["order-service", "gateway-service", "customer-service", "product-service", "database-cluster"]
        log_templates = [
            ("INFO", "order-service", "Order processed successfully", 200, None),
            ("INFO", "gateway-service", "Authorized API key request", 200, None),
            ("INFO", "product-service", "Product inventory checked", 200, None),
            ("WARNING", "order-service", "High payload validation latency", 200, "SLOW_PAYLOAD_PARSER"),
            ("WARNING", "gateway-service", "Client nearing rate limit threshold", 429, "RATE_LIMIT_WARNING"),
            ("ERROR", "order-service", "Database connection pool exhausted", 500, "DB_TIMEOUT"),
            ("ERROR", "gateway-service", "Invalid API key provided in X-API-Key", 401, "AUTH_INVALID"),
            ("ERROR", "product-service", "Deadlock detected during inventory reserve", 500, "DB_DEADLOCK"),
            ("ERROR", "database-cluster", "Query execution exceeded 3000ms threshold", 500, "SLOW_SQL_QUERY"),
            ("ERROR", "order-service", "Order write failed to commit; transaction aborted", 500, "DATA_WRITE_FAILED"),
        ]

        for i in range(1, 3201):
            log_time = now - timedelta(days=random.randint(0, 10), minutes=random.randint(0, 1440), seconds=random.randint(0, 59))
            req_id = f"REQ-LOG-{20000 + i}"
            cust_id = random.choice([1, 2, 3])

            # Select template biased toward normal INFO (85%)
            if random.random() < 0.85:
                tpl = log_templates[random.randint(0, 2)]
            else:
                tpl = log_templates[random.randint(3, len(log_templates) - 1)]

            level, srv, msg, st_code, err_code = tpl
            resp_time = round(random.uniform(15.0, 180.0) if level == "INFO" else random.uniform(850.0, 4900.0), 2)

            log_entry = Log(
                timestamp=log_time,
                level=level,
                service=srv,
                customer_id=cust_id,
                request_id=req_id,
                endpoint=f"/api/v1/orders",
                status_code=st_code,
                message=msg,
                error_code=err_code,
                response_time_ms=resp_time,
                metadata_json=f'{{"attempt": 1, "region": "us-east-1", "service": "{srv}"}}',
            )
            logs.append(log_entry)

        db.bulk_save_objects(logs)
        db.commit()

    # 7. System Metrics (550+ observations)
    existing_metrics_count = db.query(SystemMetric).count()
    if existing_metrics_count < 500:
        metrics_list = []
        for i in range(1, 551):
            m_time = now - timedelta(hours=i * 0.5)
            # 90% normal, 10% spiked
            if random.random() < 0.90:
                cpu = round(random.uniform(15.0, 45.0), 2)
                mem = round(random.uniform(30.0, 60.0), 2)
                db_lat = round(random.uniform(2.5, 12.0), 2)
                conns = random.randint(10, 40)
                req_rate = round(random.uniform(100.0, 450.0), 2)
                err_rate = round(random.uniform(0.0, 1.2), 3)
            else:
                # Spikes
                cpu = round(random.uniform(75.0, 98.0), 2)
                mem = round(random.uniform(78.0, 95.0), 2)
                db_lat = round(random.uniform(45.0, 350.0), 2)
                conns = random.randint(85, 120)
                req_rate = round(random.uniform(700.0, 1500.0), 2)
                err_rate = round(random.uniform(8.0, 35.0), 3)

            metric = SystemMetric(
                timestamp=m_time,
                cpu_percent=cpu,
                memory_percent=mem,
                db_latency_ms=db_lat,
                active_connections=conns,
                request_rate=req_rate,
                error_rate=err_rate,
            )
            metrics_list.append(metric)

        db.bulk_save_objects(metrics_list)
        db.commit()

    # 8. Historical Incidents (105+ records with categorized resolutions)
    existing_hist_count = db.query(HistoricalIncident).count()
    if existing_hist_count < 100:
        historical_templates = [
            ("Database connection timeout during peak order placement. DB latency rose to 4.8s. Orders failed to commit.",
             "Database", "Increased connection pool size from 20 to 60. Added composite index on (customer_id, external_order_id)."),
            ("401 Unauthorized errors returned to customer. API key hash lookup failed due to malformed header encoding.",
             "Authentication", "Advised customer integration team to strip whitespace and verify UTF-8 encoding on X-API-Key header."),
            ("Elevated 504 gateway timeouts. Backend service CPU reached 98% during batch CSV import.",
             "Performance", "Implemented chunked streaming parser with 50-item batch commits instead of single bulk transaction."),
            ("503 Service Unavailable returned across all endpoints. Kubernetes worker node reached OOM killer limit.",
             "Infrastructure", "Adjusted memory request/limit ratio from 1:4 to 1:1.5 and increased horizontal pod autoscaler threshold."),
            ("POST /orders responded 200 OK with order ID, but database SELECT returned 0 rows.",
             "Data Consistency", "Fixed asynchronous write acknowledge bug where API returned before database transaction commit completed."),
            ("Invalid payload schema returned 422. Missing required field 'currency_code' in customer request.",
             "Integration", "Updated partner API docs with schema validator. Sent customer sample Postman collection with required headers."),
            ("Customer reported intermittent 500 errors on product search. Unhandled NullPointerException when product category is null.",
             "Application", "Added null-safety guard and default category fallback in product catalog service mapper."),
            ("Deadlock on orders table when customer placed concurrent requests with identical idempotency key.",
             "Database", "Implemented distributed Redis locking on (customer_id, external_order_id) to serialize duplicate submissions."),
            ("High response times (2500ms+) during morning batch reconciliations. Database buffer pool cache hit ratio dropped below 80%.",
             "Performance", "Increased MySQL innodb_buffer_pool_size to 4GB and tuned query cache allocation."),
            ("Customer received 403 Forbidden after rotating credentials. Stale cache held revoked key hash.",
             "Authentication", "Implemented instant Redis cache invalidation on API key revocation and updated key rotation guide.")
        ]

        historical_records = []
        for i in range(1, 111):
            base_text, cat, resolution = historical_templates[(i - 1) % len(historical_templates)]
            variant_text = f"Incident #{1000 + i}: {base_text} Observed on cluster-{random.choice(['alpha', 'bravo', 'prod-east'])}."
            rec = HistoricalIncident(
                incident_id=f"INC-{1000 + i}",
                text=variant_text,
                embedding_reference=f"emb_ref_{1000 + i}",
                resolution=resolution,
            )
            historical_records.append(rec)

        db.bulk_save_objects(historical_records)
        db.commit()

    final_counts = {
        "customers": db.query(Customer).count(),
        "products": db.query(Product).count(),
        "endpoints": db.query(ApiEndpoint).count(),
        "orders": db.query(Order).count(),
        "api_test_runs": db.query(ApiTestRun).count(),
        "logs": db.query(Log).count(),
        "metrics": db.query(SystemMetric).count(),
        "historical_incidents": db.query(HistoricalIncident).count(),
    }
    logger.info(f"Database seeded successfully: {final_counts}")
    return final_counts
