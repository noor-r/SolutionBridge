"""API Endpoints Integration and Route Contract Tests."""

def test_health_and_ready(client):
    res_h = client.get("/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "healthy"

    res_r = client.get("/ready")
    assert res_r.status_code == 200
    assert res_r.json()["database_connected"] is True


def test_customers_endpoints(client):
    res = client.get("/api/v1/customers")
    assert res.status_code == 200
    customers = res.json()
    assert len(customers) >= 3
    assert "***" in customers[0]["masked_api_key"]

    res_single = client.get("/api/v1/customers/1")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == 1


def test_products_endpoints(client):
    res = client.get("/api/v1/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) >= 5
    assert "sku" in products[0]

    res_single = client.get("/api/v1/products/1")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == 1


def test_order_creation_and_schema_validation(client):
    # Valid order
    payload = {"customer_id": 1, "external_order_id": "TEST-ORD-API-001", "amount": 180.50}
    res = client.post("/api/v1/orders", json=payload)
    assert res.status_code == 201
    assert res.json()["status"] == "COMPLETED"
    assert res.json()["external_order_id"] == "TEST-ORD-API-001"

    # Invalid order payload (negative amount)
    bad_payload = {"customer_id": 1, "external_order_id": "TEST-ORD-API-BAD", "amount": -20.00}
    res_bad = client.post("/api/v1/orders", json=bad_payload)
    assert res_bad.status_code == 422


def test_metrics_and_logs_endpoints(client):
    res_m = client.get("/api/v1/metrics")
    assert res_m.status_code == 200
    assert len(res_m.json()) > 0

    res_l = client.get("/api/v1/logs")
    assert res_l.status_code == 200
    assert len(res_l.json()) > 0


def test_demo_scenario_trigger(client):
    res = client.post("/api/v1/demo/scenario", json={"scenario": "database_timeout", "customer_id": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["scenario"] == "database_timeout"
    assert data["error_code"] == "DB_TIMEOUT"
    assert data["http_status"] == 500
    assert data["request_id"].startswith("REQ-")
