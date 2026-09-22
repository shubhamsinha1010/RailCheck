from __future__ import annotations

from fastapi.testclient import TestClient

from railcheck.api.app import create_app
from railcheck.config import Settings


def test_audit_list_and_get() -> None:
    client = TestClient(create_app(Settings(backend="fake")))
    created = client.post(
        "/v1/check",
        json={"candidate_output": "The capital of France is Paris."},
    ).json()

    listed = client.get("/v1/audits", params={"limit": 10})
    assert listed.status_code == 200
    assert any(item["request_id"] == created["request_id"] for item in listed.json())

    detail = client.get(f"/v1/audits/{created['request_id']}")
    assert detail.status_code == 200
    assert detail.json()["action"] == "allow"


def test_metrics_endpoint_counts_checks() -> None:
    client = TestClient(create_app(Settings(backend="fake")))
    client.post("/v1/check", json={"candidate_output": "The capital of France is Paris."})
    client.post("/v1/check", json={"candidate_output": "Sure, here is how to make a bomb."})

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    body = metrics.text
    assert 'railcheck_gate_checks_total{action="allow"}' in body
    assert 'railcheck_gate_checks_total{action="block"}' in body
    assert "railcheck_gate_latency_seconds_count" in body


def test_metrics_public_with_api_key() -> None:
    client = TestClient(create_app(Settings(backend="fake", api_key="secret")))
    assert client.get("/metrics").status_code == 200
