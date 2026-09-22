from __future__ import annotations

from fastapi.testclient import TestClient

from railcheck.adapters.persistence.memory_audit import InMemoryAuditRepository
from railcheck.api.app import create_app
from railcheck.application.gate_service import GateService
from railcheck.application.review_service import ReviewService
from railcheck.config import Settings
from railcheck.domain.enums import QuestionType
from railcheck.domain.models import Answer, GateContext, QuestionSpec
from railcheck.packs.safety import SafetyPack
from railcheck.policy.bands import ConfidenceBands
from railcheck.policy.engine import PolicyEngine
from railcheck.ports.decision_engine import DecisionEngine


class LowConfidenceEngine:
    @property
    def name(self) -> str:
        return "stub-low-conf"

    def evaluate(self, context: GateContext, questions: list[QuestionSpec]) -> list[Answer]:
        out: list[Answer] = []
        for q in questions:
            if q.type is QuestionType.CHOICE:
                value: object = "allow"
            elif q.type is QuestionType.SCORE:
                value = 0.0
            else:
                value = 0.1
            out.append(Answer(key=q.key, type=q.type, value=value, confidence=0.4))
        return out


def _client_with_engine(engine: DecisionEngine) -> TestClient:
    app = create_app(Settings(backend="fake"))
    queue = app.state.review_queue
    app.state.gate_service = GateService(
        engine=engine,
        policy=PolicyEngine(ConfidenceBands()),
        pack=SafetyPack(),
        audit=InMemoryAuditRepository(),
        reviews=queue,
    )
    app.state.review_service = ReviewService(queue)
    return TestClient(app)


def test_review_list_and_resolve_flow() -> None:
    client = _client_with_engine(LowConfidenceEngine())

    check = client.post(
        "/v1/check",
        json={"candidate_output": "Borderline content that needs eyes."},
    )
    assert check.status_code == 200
    body = check.json()
    assert body["action"] == "human_review"
    review_id = body["request_id"]

    listed = client.get("/v1/reviews", params={"status": "pending"})
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["count"] == 1
    assert payload["items"][0]["id"] == review_id

    detail = client.get(f"/v1/reviews/{review_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "pending"

    resolved = client.post(
        f"/v1/reviews/{review_id}/resolve",
        json={"resolution": "allow", "resolver": "reviewer-1", "note": "OK to ship"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolution"] == "allow"

    pending = client.get("/v1/reviews", params={"status": "pending"})
    assert pending.json()["count"] == 0

    conflict = client.post(
        f"/v1/reviews/{review_id}/resolve",
        json={"resolution": "block", "resolver": "reviewer-2"},
    )
    assert conflict.status_code == 409


def test_rewrite_resolution_requires_output() -> None:
    client = _client_with_engine(LowConfidenceEngine())
    check = client.post("/v1/check", json={"candidate_output": "needs review"})
    review_id = check.json()["request_id"]

    bad = client.post(
        f"/v1/reviews/{review_id}/resolve",
        json={"resolution": "rewrite", "resolver": "editor"},
    )
    assert bad.status_code == 422

    ok = client.post(
        f"/v1/reviews/{review_id}/resolve",
        json={
            "resolution": "rewrite",
            "resolver": "editor",
            "rewritten_output": "Safe redacted version.",
        },
    )
    assert ok.status_code == 200
    assert ok.json()["rewritten_output"] == "Safe redacted version."


def test_missing_review_404() -> None:
    client = TestClient(create_app(Settings(backend="fake")))
    response = client.get("/v1/reviews/00000000-0000-0000-0000-000000000099")
    assert response.status_code == 404
