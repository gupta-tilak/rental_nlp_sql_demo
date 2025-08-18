from __future__ import annotations
from fastapi.testclient import TestClient
from src.app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_query_endpoint_known():
    r = client.post("/query", json={"query": "Top 10 tenants by rent paid"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in {"ok", "fallback"}
    if data["status"] == "ok":
        assert "sql" in data
        assert "result" in data


def test_query_endpoint_fallback():
    r = client.post("/query", json={"query": "Explain the meaning of life"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "fallback"
