"""Deterministic seed data generation for SolutionBridge."""

import math
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

# ---------------------------------------------------------------------------
# Endpoint weights for realistic API test run distribution.
# POST /orders gets ~22% of traffic; health/ready probes get ~5% each;
# read-heavy endpoints fill the rest.
# ---------------------------------------------------------------------------
_ENDPOINT_WEIGHTS = [
    5,   # Health Check
    5,   # Readiness Probe
    10,  # List Customers
    8,   # Get Customer
    10,  # List Products
    8,   # Get Product
    22,  # Create Order  (highest traffic)
    12,  # Get Order
    8,   # Customer Orders
    7,   # System Metrics
    5,   # Log Explorer
]

# ---------------------------------------------------------------------------
# Endpoint -> service mapping for log generation (mirrors DEMO_ENDPOINTS_DATA)
# ---------------------------------------------------------------------------
_ENDPOINT_SERVICE_MAP: List[Tuple[str, str]] = [
    (ep["endpoint"], ep["service"]) for ep in DEMO_ENDPOINTS_DATA
]

# ---------------------------------------------------------------------------
# Rich, diverse historical incident templates (30 unique scenarios)
# ---------------------------------------------------------------------------
_HISTORICAL_INCIDENT_TEMPLATES = [
    # --- Database (6) ---
    ("Database connection timeout during peak order placement. DB latency rose to 4.8s. Orders failed to commit.",
     "Database",
     "Increased connection pool size from 20 to 60. Added composite index on (customer_id, external_order_id)."),
    ("Deadlock on orders table when customer placed concurrent requests with identical idempotency key.",
     "Database",
     "Implemented distributed Redis locking on (customer_id, external_order_id) to serialize duplicate submissions."),
    ("Read replica fell 45 seconds behind primary during bulk import. Stale reads returned outdated inventory counts.",
     "Database",
     "Switched critical read paths to primary during import windows. Added replica lag monitoring alert at 10s threshold."),
    ("MySQL InnoDB redo log filled up during 300k-row batch upsert causing 60s write stall.",
     "Database",
     "Increased innodb_log_file_size to 2GB and split upserts into 5k-row micro-batches with intermediate commits."),
    ("Foreign key constraint violation when order-service referenced a customer_id deleted by concurrent account cleanup job.",
     "Database",
     "Changed account cleanup to soft-delete with 30-day retention. Added ON DELETE SET NULL for orphan-safe references."),
    ("Connection leak in ORM session factory caused pool exhaustion after 8 hours of continuous traffic.",
     "Database",
     "Wrapped all session usage in context managers. Added pool_pre_ping=True and pool_recycle=1800 to engine config."),

    # --- Authentication (4) ---
    ("401 Unauthorized errors returned to customer. API key hash lookup failed due to malformed header encoding.",
     "Authentication",
     "Advised customer integration team to strip whitespace and verify UTF-8 encoding on X-API-Key header."),
    ("Customer received 403 Forbidden after rotating credentials. Stale cache held revoked key hash.",
     "Authentication",
     "Implemented instant Redis cache invalidation on API key revocation and updated key rotation guide."),
    ("JWT token validation started failing after certificate rotation. New public key not propagated to edge nodes.",
     "Authentication",
     "Implemented JWKS endpoint with 5-minute refresh interval. Added fallback to previous key for 24h grace period."),
    ("Brute-force login attempts from single IP caused temporary account lockouts for legitimate users sharing NAT gateway.",
     "Authentication",
     "Switched rate-limiting from IP-based to compound key (IP + API key prefix). Added CAPTCHA challenge after 5 failures."),

    # --- Performance (5) ---
    ("Elevated 504 gateway timeouts. Backend service CPU reached 98% during batch CSV import.",
     "Performance",
     "Implemented chunked streaming parser with 50-item batch commits instead of single bulk transaction."),
    ("High response times (2500ms+) during morning batch reconciliations. Database buffer pool cache hit ratio dropped below 80%.",
     "Performance",
     "Increased MySQL innodb_buffer_pool_size to 4GB and tuned query cache allocation."),
    ("P99 latency on /api/v1/products spiked to 3.2s when full-text search hit unindexed description column.",
     "Performance",
     "Added FULLTEXT index on products.description. Implemented Elasticsearch sidecar for complex queries."),
    ("Memory usage on order-service grew linearly. GC pauses exceeded 800ms every 15 minutes.",
     "Performance",
     "Identified unbounded in-memory order history cache. Added LRU eviction with max 10k entries and 5-minute TTL."),
    ("Webhook delivery queue backed up to 50k pending messages during Black Friday. Consumer throughput dropped to 12 msg/s.",
     "Performance",
     "Scaled consumer pods from 3 to 12. Partitioned queue by customer_id for parallel processing. Peak throughput reached 450 msg/s."),

    # --- Infrastructure (5) ---
    ("503 Service Unavailable returned across all endpoints. Kubernetes worker node reached OOM killer limit.",
     "Infrastructure",
     "Adjusted memory request/limit ratio from 1:4 to 1:1.5 and increased horizontal pod autoscaler threshold."),
    ("TLS certificate for api.solutionbridge.io expired at 03:00 UTC. All HTTPS traffic rejected for 47 minutes.",
     "Infrastructure",
     "Implemented cert-manager with automatic renewal 30 days before expiry. Added Prometheus alert for certs expiring within 14 days."),
    ("DNS resolution failure for internal service mesh caused cascading 502 errors across all microservices.",
     "Infrastructure",
     "Deployed CoreDNS with redundant upstream resolvers. Added circuit breaker with cached DNS fallback for 60s."),
    ("Docker image pull failed during rolling deployment. Container registry rate limit exceeded.",
     "Infrastructure",
     "Deployed private registry mirror in VPC. Pre-pulled base images on all worker nodes during maintenance window."),
    ("Load balancer health checks passed but application returned 200 on /health while /api/* returned 503 due to uninitialized dependency.",
     "Infrastructure",
     "Changed health check to /ready endpoint that validates DB and Redis connectivity. Added startup probe with 30s initial delay."),

    # --- Data Consistency (3) ---
    ("POST /orders responded 200 OK with order ID, but database SELECT returned 0 rows.",
     "Data Consistency",
     "Fixed asynchronous write acknowledge bug where API returned before database transaction commit completed."),
    ("Customer balance showed negative value after concurrent partial refund and new order processed simultaneously.",
     "Data Consistency",
     "Implemented optimistic locking with version column on customer_balance table. Added retry logic for StaleObjectError."),
    ("Order status stuck in PROCESSING after payment gateway webhook delivered but handler threw unhandled exception.",
     "Data Consistency",
     "Added dead-letter queue for failed webhook processing. Implemented idempotent retry with exponential backoff up to 3 attempts."),

    # --- Integration (4) ---
    ("Invalid payload schema returned 422. Missing required field 'currency_code' in customer request.",
     "Integration",
     "Updated partner API docs with schema validator. Sent customer sample Postman collection with required headers."),
    ("Partner webhook endpoint returned 301 redirect. HTTP client did not follow redirects, causing silent delivery failures.",
     "Integration",
     "Updated HTTP client config to follow up to 3 redirects. Added webhook delivery status dashboard for partners."),
    ("Customer CSV upload contained BOM characters causing first column header mismatch and silent data truncation.",
     "Integration",
     "Added BOM detection and stripping in upload parser. Returned 400 with descriptive error for unsupported encodings."),
    ("Third-party payment gateway changed API version without notice. Charge requests returned 404 for 2 hours.",
     "Integration",
     "Pinned API version in request headers. Added integration health monitor that alerts on unexpected status code patterns."),

    # --- Application (3) ---
    ("Customer reported intermittent 500 errors on product search. Unhandled NullPointerException when product category is null.",
     "Application",
     "Added null-safety guard and default category fallback in product catalog service mapper."),
    ("Background job scheduler ran duplicate cron instances after pod restart. Double-processed 1,200 reconciliation records.",
     "Application",
     "Implemented distributed lock via Redis SETNX with TTL for cron job leader election. Added idempotency checks on record processing."),
    ("File upload endpoint accepted 2GB payload, exhausting container memory. No request size limit configured.",
     "Application",
     "Added 50MB request body limit in nginx ingress. Implemented streaming multipart parser with disk-backed temp storage."),
]

# ---------------------------------------------------------------------------
# Log message templates per endpoint for realistic variety
# ---------------------------------------------------------------------------
_LOG_MESSAGES_BY_ENDPOINT = {
    "/health": {
        "INFO": ["Health check passed", "Service heartbeat OK"],
        "WARNING": ["Health check response slow (>80ms)", "Partial health: Redis latency elevated"],
    },
    "/ready": {
        "INFO": ["Readiness probe passed", "All dependencies healthy"],
        "WARNING": ["Readiness degraded: DB replica lag 8s", "Readiness probe slow (>120ms)"],
    },
    "/api/v1/customers": {
        "INFO": ["Customer list retrieved successfully", "Fetched customer directory (page {page})"],
        "WARNING": ["Customer query took >200ms", "Large result set: 500+ customers returned"],
        "ERROR": ["Failed to query customer table", "Customer service connection refused"],
    },
    "/api/v1/customers/{customer_id}": {
        "INFO": ["Customer profile retrieved", "Customer lookup by ID completed"],
        "WARNING": ["Customer not found, returning 404", "Customer record cache miss"],
        "ERROR": ["Customer lookup query timed out", "Unexpected null in customer record"],
    },
    "/api/v1/products": {
        "INFO": ["Product catalog fetched", "Product inventory checked"],
        "WARNING": ["Product search latency elevated", "Large product result set returned"],
        "ERROR": ["Product service temporarily unavailable", "Full-text search index corrupted"],
    },
    "/api/v1/products/{product_id}": {
        "INFO": ["Product details retrieved", "Product price lookup completed"],
        "WARNING": ["Product not found in cache, fetching from DB", "Product image URL returned 404"],
        "ERROR": ["Product lookup failed: connection pool exhausted", "Deadlock detected during inventory reserve"],
    },
    "/api/v1/orders": {
        "INFO": ["Order processed successfully", "Order created and queued for fulfillment", "Order validation passed"],
        "WARNING": ["High payload validation latency", "Order amount exceeds review threshold"],
        "ERROR": ["Database connection pool exhausted", "Order write failed to commit; transaction aborted", "Payment gateway timeout during order creation"],
    },
    "/api/v1/orders/{order_id}": {
        "INFO": ["Order details retrieved", "Order status lookup completed"],
        "WARNING": ["Order not found, returning 404", "Order status cache stale"],
        "ERROR": ["Order lookup query exceeded timeout", "Unexpected order status inconsistency"],
    },
    "/api/v1/customers/{customer_id}/orders": {
        "INFO": ["Customer order history retrieved", "Customer orders paginated response sent"],
        "WARNING": ["Large order history: 1000+ records", "Customer order query slow (>250ms)"],
        "ERROR": ["Failed to join customer and order tables", "Customer order aggregation timeout"],
    },
    "/api/v1/metrics": {
        "INFO": ["System metrics snapshot collected", "Telemetry data aggregated"],
        "WARNING": ["Metric collection latency >200ms", "Partial metrics: some pods unreachable"],
        "ERROR": ["Metrics aggregation pipeline failed", "Prometheus scrape target unreachable"],
    },
    "/api/v1/logs": {
        "INFO": ["Log query executed successfully", "Log entries filtered and returned"],
        "WARNING": ["Log query returned >10k results, truncating", "Log search index lag detected"],
        "ERROR": ["Log storage backend connection lost", "Elasticsearch cluster health RED"],
    },
}

# Error codes by error type
_ERROR_CODES = {
    "gateway-service": ["AUTH_INVALID", "RATE_LIMIT_EXCEEDED", "GATEWAY_TIMEOUT", "TLS_HANDSHAKE_FAILED"],
    "order-service": ["DB_TIMEOUT", "DATA_WRITE_FAILED", "PAYMENT_GATEWAY_ERROR", "IDEMPOTENCY_CONFLICT"],
    "customer-service": ["DB_TIMEOUT", "CUSTOMER_NOT_FOUND", "CACHE_MISS_CRITICAL"],
    "product-service": ["DB_DEADLOCK", "SEARCH_INDEX_ERROR", "INVENTORY_LOCK_TIMEOUT"],
    "telemetry-service": ["METRICS_PIPELINE_FAIL", "STORAGE_BACKEND_ERROR"],
    "database-cluster": ["SLOW_SQL_QUERY", "POOL_EXHAUSTED", "REPLICATION_LAG", "DEADLOCK_DETECTED"],
}

# CRITICAL-level infrastructure events
_CRITICAL_EVENTS = [
    ("database-cluster", "Primary database node unresponsive. Failover initiated to standby replica.", "PRIMARY_DOWN"),
    ("gateway-service", "TLS certificate expired. All inbound HTTPS connections rejected.", "CERT_EXPIRED"),
    ("database-cluster", "Disk usage exceeded 95% on primary volume. Write operations suspended.", "DISK_FULL"),
    ("gateway-service", "DDoS mitigation activated. Abnormal traffic pattern: 50k req/s from single CIDR block.", "DDOS_DETECTED"),
    ("order-service", "Out of memory: order-service container killed by OOM killer.", "OOM_KILLED"),
    ("database-cluster", "Corruption detected in InnoDB tablespace. Emergency read-only mode activated.", "DATA_CORRUPTION"),
    ("gateway-service", "DNS resolution failure for internal service mesh. Cascading 502 errors.", "DNS_FAILURE"),
    ("order-service", "Message queue broker unreachable. Order processing pipeline halted.", "QUEUE_BROKER_DOWN"),
]


def _business_hour_weight(hour: int) -> float:
    """Return a weight multiplier based on hour-of-day (0-23) to simulate
    business-hours traffic patterns.  Peak is 10-14 UTC, trough is 2-5 UTC."""
    # Sine-based curve peaking around hour 12
    return 0.3 + 0.7 * max(0.0, math.sin(math.pi * (hour - 4) / 16))


def _is_weekend(dt: datetime) -> bool:
    """Return True if the given datetime falls on Saturday or Sunday."""
    return dt.weekday() >= 5


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
    endpoint_map = {ep.id: ep for ep in endpoints}

    # 4. Orders (130 orders with realistic time-of-day and weekend patterns)
    existing_order_count = db.query(Order).count()
    if existing_order_count < 100:
        orders: List[Order] = []
        statuses = ["COMPLETED", "COMPLETED", "COMPLETED", "PENDING", "PROCESSING", "FAILED"]
        # Customer order volume weights: Acme (high-volume), Nova (medium), Zenith (low/sandbox)
        customer_weights = [1, 2, 3]
        customer_probs = [0.50, 0.35, 0.15]

        for i in range(1, 131):
            cust_id = random.choices(customer_weights, weights=customer_probs, k=1)[0]
            day_offset = random.randint(0, 30)
            candidate_time = now - timedelta(days=day_offset)

            # Business-hour bias: pick hour weighted toward daytime
            hour = random.choices(
                range(24),
                weights=[_business_hour_weight(h) for h in range(24)],
                k=1,
            )[0]
            minute = random.randint(0, 59)
            order_time = candidate_time.replace(hour=hour, minute=minute, second=random.randint(0, 59))

            # Weekend dip: 30% chance to skip (reduce weekend orders)
            if _is_weekend(order_time) and random.random() < 0.30:
                # Shift to nearest weekday
                order_time -= timedelta(days=order_time.weekday() - 4)

            status = random.choice(statuses)
            # Realistic amount ranges by customer type
            if cust_id == 1:  # Acme Retail: higher-value enterprise orders
                amount = Decimal(str(round(random.uniform(150.0, 2500.0), 2)))
            elif cust_id == 2:  # Nova Commerce: mid-range
                amount = Decimal(str(round(random.uniform(50.0, 1200.0), 2)))
            else:  # Zenith Logistics: sandbox testing, smaller amounts
                amount = Decimal(str(round(random.uniform(10.0, 300.0), 2)))

            order = Order(
                customer_id=cust_id,
                external_order_id=f"ORD-EXT-{cust_id * 1000 + i}",
                status=status,
                amount=amount,
                created_at=order_time,
                updated_at=order_time + timedelta(seconds=random.randint(1, 120)),
            )
            orders.append(order)
        db.bulk_save_objects(orders)
        db.commit()

    # 5. API Test Runs (1050+ records with realistic endpoint distribution)
    existing_runs_count = db.query(ApiTestRun).count()
    if existing_runs_count < 1000:
        test_runs: List[ApiTestRun] = []
        for i in range(1, 1051):
            # Weighted endpoint selection
            ep_id = random.choices(endpoint_ids, weights=_ENDPOINT_WEIGHTS[:len(endpoint_ids)], k=1)[0]
            cust_id = random.choice([1, 2, 3, None])
            run_time = now - timedelta(days=random.randint(0, 14), minutes=random.randint(0, 1440))
            req_id = f"REQ-TEST-{10000 + i}"

            ep_obj = endpoint_map.get(ep_id)
            max_rt = ep_obj.max_response_time_ms if ep_obj else 300

            # 92% pass, 5% failure, 3% timeout/error
            roll = random.random()
            if roll < 0.92:
                status_code = ep_obj.expected_status if ep_obj else 200
                test_status = "PASSED"
                resp_time = round(random.uniform(max_rt * 0.1, max_rt * 0.7), 2)
                resp_body = '{"status": "success", "data": "ok"}'
                err_msg = None
            elif roll < 0.97:
                status_code = random.choice([400, 422, 404])
                test_status = "FAILED"
                resp_time = round(random.uniform(max_rt * 0.3, max_rt * 1.2), 2)
                resp_body = '{"status": "error", "error_code": "VALIDATION_FAILED"}'
                err_msg = "Payload validation failure: missing required parameter"
            else:
                status_code = random.choice([500, 502, 503, 504])
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

    # 6. Structured Logs (3200+ entries distributed across ALL endpoints with
    #    correlated request lifecycle and CRITICAL events)
    existing_log_count = db.query(Log).count()
    if existing_log_count < 3000:
        logs: List[Log] = []
        all_endpoint_paths = [ep["endpoint"] for ep in DEMO_ENDPOINTS_DATA]
        all_endpoint_services = [ep["service"] for ep in DEMO_ENDPOINTS_DATA]
        regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]

        req_counter = 20000

        # --- Generate ~3000 correlated log groups ---------------------------
        while len(logs) < 3200:
            req_counter += 1
            req_id = f"REQ-LOG-{req_counter}"
            cust_id = random.choice([1, 2, 3])
            region = random.choice(regions)

            # Pick endpoint with realistic distribution
            ep_idx = random.choices(range(len(all_endpoint_paths)), weights=_ENDPOINT_WEIGHTS, k=1)[0]
            ep_path = all_endpoint_paths[ep_idx]
            ep_service = all_endpoint_services[ep_idx]

            # Time with business-hour bias
            day_offset = random.randint(0, 10)
            hour = random.choices(
                range(24),
                weights=[_business_hour_weight(h) for h in range(24)],
                k=1,
            )[0]
            base_time = now - timedelta(
                days=day_offset,
                hours=now.hour - hour,
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59),
            )

            # Determine outcome for this request
            outcome_roll = random.random()

            if outcome_roll < 0.82:
                # --- Happy path: 1 INFO log ---
                msg_options = _LOG_MESSAGES_BY_ENDPOINT.get(ep_path, {}).get("INFO", ["Request processed successfully"])
                msg = random.choice(msg_options).format(page=random.randint(1, 20))
                resp_time = round(random.uniform(15.0, 180.0), 2)
                logs.append(Log(
                    timestamp=base_time,
                    level="INFO",
                    service=ep_service,
                    customer_id=cust_id,
                    request_id=req_id,
                    endpoint=ep_path,
                    status_code=200,
                    message=msg,
                    error_code=None,
                    response_time_ms=resp_time,
                    metadata_json=f'{{"attempt": 1, "region": "{region}", "service": "{ep_service}"}}',
                ))

            elif outcome_roll < 0.90:
                # --- Warning path: 1 INFO + 1 WARNING ---
                info_msg_options = _LOG_MESSAGES_BY_ENDPOINT.get(ep_path, {}).get("INFO", ["Request received"])
                info_msg = random.choice(info_msg_options).format(page=random.randint(1, 20))
                logs.append(Log(
                    timestamp=base_time,
                    level="INFO",
                    service=ep_service,
                    customer_id=cust_id,
                    request_id=req_id,
                    endpoint=ep_path,
                    status_code=200,
                    message=info_msg,
                    error_code=None,
                    response_time_ms=round(random.uniform(15.0, 80.0), 2),
                    metadata_json=f'{{"attempt": 1, "region": "{region}", "service": "{ep_service}"}}',
                ))

                warn_msg_options = _LOG_MESSAGES_BY_ENDPOINT.get(ep_path, {}).get("WARNING", ["Elevated latency detected"])
                warn_msg = random.choice(warn_msg_options)
                warn_codes = ["SLOW_PAYLOAD_PARSER", "RATE_LIMIT_WARNING", "CACHE_MISS", "HIGH_LATENCY"]
                logs.append(Log(
                    timestamp=base_time + timedelta(milliseconds=random.randint(50, 500)),
                    level="WARNING",
                    service=ep_service,
                    customer_id=cust_id,
                    request_id=req_id,
                    endpoint=ep_path,
                    status_code=200,
                    message=warn_msg,
                    error_code=random.choice(warn_codes),
                    response_time_ms=round(random.uniform(200.0, 900.0), 2),
                    metadata_json=f'{{"attempt": 1, "region": "{region}", "service": "{ep_service}"}}',
                ))

            elif outcome_roll < 0.98:
                # --- Error path: 1 INFO (request received) + 1 ERROR ---
                logs.append(Log(
                    timestamp=base_time,
                    level="INFO",
                    service="gateway-service",
                    customer_id=cust_id,
                    request_id=req_id,
                    endpoint=ep_path,
                    status_code=None,
                    message=f"Incoming request {ep_path}",
                    error_code=None,
                    response_time_ms=round(random.uniform(1.0, 10.0), 2),
                    metadata_json=f'{{"attempt": 1, "region": "{region}", "service": "gateway-service"}}',
                ))

                err_msg_options = _LOG_MESSAGES_BY_ENDPOINT.get(ep_path, {}).get("ERROR", ["Internal server error"])
                err_msg = random.choice(err_msg_options)
                service_err_codes = _ERROR_CODES.get(ep_service, ["UNKNOWN_ERROR"])
                status_code = random.choice([500, 502, 503, 504])
                logs.append(Log(
                    timestamp=base_time + timedelta(milliseconds=random.randint(200, 3000)),
                    level="ERROR",
                    service=ep_service,
                    customer_id=cust_id,
                    request_id=req_id,
                    endpoint=ep_path,
                    status_code=status_code,
                    message=err_msg,
                    error_code=random.choice(service_err_codes),
                    response_time_ms=round(random.uniform(850.0, 4900.0), 2),
                    metadata_json=f'{{"attempt": 1, "region": "{region}", "service": "{ep_service}", "status_code": {status_code}}}',
                ))

            else:
                # --- CRITICAL path: 1 INFO + 1 ERROR + 1 CRITICAL ---
                logs.append(Log(
                    timestamp=base_time,
                    level="INFO",
                    service="gateway-service",
                    customer_id=cust_id,
                    request_id=req_id,
                    endpoint=ep_path,
                    status_code=None,
                    message=f"Incoming request {ep_path}",
                    error_code=None,
                    response_time_ms=round(random.uniform(1.0, 5.0), 2),
                    metadata_json=f'{{"attempt": 1, "region": "{region}", "service": "gateway-service"}}',
                ))

                crit_event = random.choice(_CRITICAL_EVENTS)
                crit_service, crit_msg, crit_code = crit_event

                # Preceding ERROR from the service
                logs.append(Log(
                    timestamp=base_time + timedelta(milliseconds=random.randint(100, 500)),
                    level="ERROR",
                    service=crit_service,
                    customer_id=cust_id,
                    request_id=req_id,
                    endpoint=ep_path,
                    status_code=503,
                    message=f"Service degraded: upstream {crit_service} not responding",
                    error_code=crit_code,
                    response_time_ms=round(random.uniform(3000.0, 5000.0), 2),
                    metadata_json=f'{{"attempt": 1, "region": "{region}", "service": "{crit_service}", "escalated": true}}',
                ))

                # CRITICAL infrastructure alert
                logs.append(Log(
                    timestamp=base_time + timedelta(milliseconds=random.randint(500, 2000)),
                    level="CRITICAL",
                    service=crit_service,
                    customer_id=None,  # Infrastructure events are not customer-specific
                    request_id=req_id,
                    endpoint=None,
                    status_code=None,
                    message=crit_msg,
                    error_code=crit_code,
                    response_time_ms=None,
                    metadata_json=f'{{"region": "{region}", "service": "{crit_service}", "severity": "CRITICAL", "pager_notified": true}}',
                ))

        db.bulk_save_objects(logs)
        db.commit()

    # 7. System Metrics (550+ observations with realistic daily patterns)
    existing_metrics_count = db.query(SystemMetric).count()
    if existing_metrics_count < 500:
        metrics_list: List[SystemMetric] = []
        for i in range(1, 551):
            m_time = now - timedelta(hours=i * 0.5)
            hour = m_time.hour
            is_wknd = _is_weekend(m_time)

            # Daily pattern multiplier
            biz_weight = _business_hour_weight(hour)
            if is_wknd:
                biz_weight *= 0.4  # Weekend traffic ~40% of weekday

            # 90% normal, 10% spiked
            if random.random() < 0.90:
                # Scale CPU/connections/request_rate by time-of-day
                base_cpu = 12.0 + 35.0 * biz_weight
                cpu = round(base_cpu + random.uniform(-5.0, 8.0), 2)
                cpu = max(5.0, min(cpu, 70.0))

                mem = round(30.0 + 25.0 * biz_weight + random.uniform(-3.0, 5.0), 2)
                mem = max(20.0, min(mem, 72.0))

                db_lat = round(2.5 + 8.0 * biz_weight + random.uniform(-1.0, 3.0), 2)
                db_lat = max(1.5, db_lat)

                conns = int(8 + 35 * biz_weight + random.randint(-3, 5))
                conns = max(3, conns)

                req_rate = round(80.0 + 400.0 * biz_weight + random.uniform(-30.0, 50.0), 2)
                req_rate = max(20.0, req_rate)

                err_rate = round(random.uniform(0.0, 1.2), 3)
            else:
                # Spikes — still realistic: error_rate capped at 5-15%
                cpu = round(random.uniform(75.0, 98.0), 2)
                mem = round(random.uniform(78.0, 95.0), 2)
                db_lat = round(random.uniform(45.0, 350.0), 2)
                conns = random.randint(85, 150)
                req_rate = round(random.uniform(700.0, 1500.0), 2)
                err_rate = round(random.uniform(5.0, 15.0), 3)

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

    # 8. Historical Incidents (110 records from 30 diverse templates)
    existing_hist_count = db.query(HistoricalIncident).count()
    if existing_hist_count < 100:
        clusters = ["prod-east", "prod-west", "staging-central", "dr-south"]
        severity_labels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        historical_records: List[HistoricalIncident] = []

        for i in range(1, 111):
            tpl_idx = (i - 1) % len(_HISTORICAL_INCIDENT_TEMPLATES)
            base_text, cat, resolution = _HISTORICAL_INCIDENT_TEMPLATES[tpl_idx]
            cluster = random.choice(clusters)
            severity = random.choice(severity_labels)

            # Build unique, rich narrative for each record
            days_ago = random.randint(7, 365)
            duration_min = random.randint(5, 180)
            affected_customers = random.randint(1, 50)

            variant_text = (
                f"Incident #{1000 + i} [{severity}]: {base_text} "
                f"Observed on cluster-{cluster} approximately {days_ago} days ago. "
                f"Duration: {duration_min} minutes. Affected ~{affected_customers} customer(s). "
                f"Category: {cat}."
            )

            variant_resolution = (
                f"{resolution} "
                f"Post-incident review completed. Monitoring rule added to prevent recurrence."
            )

            rec = HistoricalIncident(
                incident_id=f"INC-{1000 + i}",
                text=variant_text,
                embedding_reference=f"emb_ref_{1000 + i}",
                resolution=variant_resolution,
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
