"""Unit tests for request ID tracking and middleware headers."""

def test_request_id_header_generated(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"].startswith("REQ-")
    assert "X-Response-Time-MS" in response.headers


def test_custom_request_id_preserved(client):
    custom_id = "REQ-CUSTOM-TEST-9999"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
