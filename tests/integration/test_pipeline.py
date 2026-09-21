"""Integration tests for the complete Product Solutions Engineer investigation workflow."""

def test_full_investigation_pipeline(client):
    # 1. Trigger controlled database timeout fault
    sim_res = client.post("/api/v1/demo/scenario", json={"scenario": "database_timeout", "customer_id": 1})
    assert sim_res.status_code == 200
    req_id = sim_res.json()["request_id"]

    # 2. Trigger multi-source analysis
    analysis_res = client.post(f"/api/v1/incidents/analyze/{req_id}")
    assert analysis_res.status_code == 200
    diag = analysis_res.json()

    assert diag["category"] == "Database"
    assert diag["confidence"] >= 0.90
    assert len(diag["deterministic_evidence"]) >= 2
    assert "similar_incidents" in diag
    assert len(diag["similar_incidents"]) == 3
    assert "engineer_summary" in diag
    assert "customer_summary" in diag

    # 3. Check incident persistence in incidents table
    inc_id = diag["incident_id"]
    get_inc_res = client.get(f"/api/v1/incidents/{inc_id}")
    assert get_inc_res.status_code == 200
    inc_data = get_inc_res.json()
    assert inc_data["status"] == "OPEN"
    assert inc_data["request_id"] == req_id
    assert len(inc_data["evidence_items"]) > 0
    assert len(inc_data["actions"]) > 0

    # 4. Update incident status to RESOLVED
    patch_res = client.patch(f"/api/v1/incidents/{inc_id}/status", json={"status": "RESOLVED", "resolution_notes": "Pool size increased"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "RESOLVED"
    assert patch_res.json()["resolved_at"] is not None
