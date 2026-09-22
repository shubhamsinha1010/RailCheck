from __future__ import annotations

from fastapi.testclient import TestClient

from railcheck.api.app import create_app
from railcheck.config import Settings


def test_demo_page_is_public() -> None:
    client = TestClient(create_app(Settings(backend="fake", api_key="secret")))
    response = client.get("/demo")
    assert response.status_code == 200
    assert "RailCheck" in response.text


def test_api_key_required_when_configured() -> None:
    client = TestClient(create_app(Settings(backend="fake", api_key="secret")))
    denied = client.post("/v1/check", json={"candidate_output": "hi"})
    assert denied.status_code == 401

    allowed = client.post(
        "/v1/check",
        headers={"x-api-key": "secret"},
        json={"candidate_output": "The capital of France is Paris."},
    )
    assert allowed.status_code == 200
    assert allowed.json()["action"] == "allow"


def test_bearer_api_key_works() -> None:
    client = TestClient(create_app(Settings(backend="fake", api_key="secret")))
    response = client.post(
        "/v1/check",
        headers={"Authorization": "Bearer secret"},
        json={"candidate_output": "hello world"},
    )
    assert response.status_code == 200


def test_no_api_key_means_open_access() -> None:
    client = TestClient(create_app(Settings(backend="fake", api_key="")))
    response = client.post("/v1/check", json={"candidate_output": "hello world"})
    assert response.status_code == 200


def test_healthz_stays_public() -> None:
    client = TestClient(create_app(Settings(backend="fake", api_key="secret")))
    assert client.get("/healthz").status_code == 200
