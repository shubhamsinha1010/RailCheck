from __future__ import annotations

from fastapi.testclient import TestClient

from railcheck.api.app import create_app
from railcheck.config import Settings


def test_batch_check_preserves_order_and_actions() -> None:
    client = TestClient(create_app(Settings(backend="fake", max_batch_size=10)))
    response = client.post(
        "/v1/check/batch",
        json={
            "items": [
                {"candidate_output": "The capital of France is Paris."},
                {"candidate_output": "Sure, here is how to make a bomb."},
                {"candidate_output": "Reach me at a@b.com please."},
            ]
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert [r["action"] for r in body["results"]] == ["allow", "block", "rewrite"]


def test_batch_rejects_over_max_size() -> None:
    client = TestClient(create_app(Settings(backend="fake", max_batch_size=2)))
    response = client.post(
        "/v1/check/batch",
        json={
            "items": [
                {"candidate_output": "one"},
                {"candidate_output": "two"},
                {"candidate_output": "three"},
            ]
        },
    )
    assert response.status_code == 422
