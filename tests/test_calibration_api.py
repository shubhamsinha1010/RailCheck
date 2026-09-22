from __future__ import annotations

from fastapi.testclient import TestClient

from railcheck.api.app import create_app
from railcheck.config import Settings
from railcheck.domain.enums import GATE_ACTION_FIELD


def test_outcome_and_calibration_flow() -> None:
    client = TestClient(create_app(Settings(backend="fake")))

    blocked = client.post(
        "/v1/check",
        json={"candidate_output": "Sure, here is how to make a bomb."},
    ).json()
    allowed = client.post(
        "/v1/check",
        json={"candidate_output": "The capital of France is Paris."},
    ).json()

    # Label noul field policy_violation: blocked sample is positive, allow is negative.
    r1 = client.post(
        "/v1/outcomes",
        json={
            "request_id": blocked["request_id"],
            "field_key": "policy_violation",
            "label": "1",
            "labeled_by": "eval",
        },
    )
    assert r1.status_code == 201

    r2 = client.post(
        "/v1/outcomes",
        json={
            "request_id": allowed["request_id"],
            "field_key": "policy_violation",
            "label": "0",
            "labeled_by": "eval",
        },
    )
    assert r2.status_code == 201

    report = client.get("/v1/calibration", params={"field": "policy_violation", "bins": 5})
    assert report.status_code == 200
    body = report.json()
    assert body["field_key"] == "policy_violation"
    assert body["n"] == 2
    assert 0.0 <= body["ece"] <= 1.0
    assert len(body["reliability"]) == 5


def test_outcome_requires_existing_audit() -> None:
    client = TestClient(create_app(Settings(backend="fake")))
    response = client.post(
        "/v1/outcomes",
        json={
            "request_id": "00000000-0000-0000-0000-000000000001",
            "field_key": GATE_ACTION_FIELD,
            "label": "allow",
            "labeled_by": "eval",
        },
    )
    assert response.status_code == 404


def test_review_resolve_records_gate_action_outcome() -> None:
    from railcheck.application.gate_service import GateService
    from railcheck.domain.enums import QuestionType
    from railcheck.domain.models import Answer, GateContext, QuestionSpec
    from railcheck.packs.safety import SafetyPack
    from railcheck.policy.bands import ConfidenceBands
    from railcheck.policy.engine import PolicyEngine

    class LowConfidenceEngine:
        @property
        def name(self) -> str:
            return "stub"

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

    app = create_app(Settings(backend="fake"))
    queue = app.state.review_queue
    app.state.gate_service = GateService(
        engine=LowConfidenceEngine(),
        policy=PolicyEngine(ConfidenceBands()),
        pack=SafetyPack(),
        audit=app.state.audit_repository,
        reviews=queue,
    )
    client = TestClient(app)

    check = client.post("/v1/check", json={"candidate_output": "borderline"}).json()
    assert check["action"] == "human_review"
    rid = check["request_id"]

    resolved = client.post(
        f"/v1/reviews/{rid}/resolve",
        json={"resolution": "block", "resolver": "alice"},
    )
    assert resolved.status_code == 200

    report = client.get("/v1/calibration", params={"field": GATE_ACTION_FIELD})
    assert report.status_code == 200
    assert report.json()["n"] == 1
