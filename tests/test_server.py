import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.server import app


def test_server_healthz():
    client = app.test_client()
    res = client.get("/healthz")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "healthy"


def test_server_fleet_status():
    client = app.test_client()
    res = client.get("/api/fleet")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "agents" in data
    assert len(data["agents"]) >= 4


def test_server_run_task():
    client = app.test_client()
    res = client.post("/api/run-task", json={"description": "Test task via API"})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "COMPLETED"
    assert "results" in data


def test_server_attack_simulation():
    client = app.test_client()
    res = client.post("/api/run-attack", json={"attack_type": "privilege_escalation"})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["quarantined"]


def test_server_provenance_and_verify():
    client = app.test_client()
    res = client.get("/api/provenance")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "records" in data

    res_verify = client.get("/api/verify-chain")
    assert res_verify.status_code == 200
    verify_data = json.loads(res_verify.data)
    assert "is_integral" in verify_data


def test_server_scope_evaluator_sandbox():
    client = app.test_client()
    # Test allowed
    res_allow = client.post("/api/evaluate-scope", json={
        "caller_agent": "orchestrator",
        "target_agent": "db_query_agent",
        "requested_scopes": ["cloudsql:orders:read"]
    })
    assert res_allow.status_code == 200
    data_allow = json.loads(res_allow.data)
    assert data_allow["allowed"]

    # Test blocked
    res_block = client.post("/api/evaluate-scope", json={
        "caller_agent": "orchestrator",
        "target_agent": "db_query_agent",
        "requested_scopes": ["cloudsql:orders:write"]
    })
    assert res_block.status_code == 200
    data_block = json.loads(res_block.data)
    assert not data_block["allowed"]
    assert data_block["violation_type"] == "CEILING_EXCEEDED"


def test_server_register_dynamic_agent():
    client = app.test_client()
    res = client.post("/api/register-agent", json={
        "name": "invoice_agent",
        "scopes": ["stripe:invoices:read", "stripe:invoices:write"],
        "description": "Invoice generator agent"
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["name"] == "invoice_agent"
    assert "stripe:invoices:read" in data["scope_ceiling"]


def test_server_dashboard_static():
    client = app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    assert b"FORTIFIED AGENT FLEET" in res.data
