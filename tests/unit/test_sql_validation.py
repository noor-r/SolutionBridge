"""Unit tests for SQL validation service and diagnostic queries."""

from app.services.sql_validation_service import SQLValidationService


def test_validate_order_persistence(db):
    sql_svc = SQLValidationService(db)
    # Seeded order ORD-EXT-1001 exists or we test non-existent
    res_missing = sql_svc.validate_order_persistence(customer_id=1, external_order_id="NON_EXISTENT_ORD")
    assert res_missing["persisted"] is False
    assert "NOT found" in res_missing["diagnostic_finding"]


def test_check_duplicate_orders(db):
    sql_svc = SQLValidationService(db)
    res = sql_svc.check_duplicate_orders(customer_id=1, external_order_id="UNIQUE-ID-12345")
    assert res["is_duplicate"] is False


def test_aggregate_error_codes_by_request(db):
    sql_svc = SQLValidationService(db)
    res = sql_svc.aggregate_error_codes_by_request("REQ-TEST-NONEXISTENT")
    assert res["total_error_codes"] == 0
    assert "query_id" in res


def test_customer_integration_health(db):
    sql_svc = SQLValidationService(db)
    res = sql_svc.inspect_customer_integration_health(customer_id=1)
    assert res["found"] is True
    assert "pass_rate" in res["data"]
