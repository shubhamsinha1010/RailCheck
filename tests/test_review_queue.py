from __future__ import annotations

from uuid import UUID

import pytest

from railcheck.adapters.backends.fake import FakeDecisionEngine
from railcheck.adapters.persistence.memory_audit import InMemoryAuditRepository
from railcheck.adapters.persistence.memory_review_queue import InMemoryReviewQueueRepository
from railcheck.application.gate_service import GateService
from railcheck.application.review_service import (
    ReviewConflictError,
    ReviewNotFoundError,
    ReviewService,
)
from railcheck.domain.enums import GateAction, QuestionType, ReviewResolution, ReviewStatus
from railcheck.domain.models import Answer, GateContext, QuestionSpec
from railcheck.packs.safety import SafetyPack
from railcheck.policy.bands import ConfidenceBands
from railcheck.policy.engine import PolicyEngine
from railcheck.ports.decision_engine import DecisionEngine


class LowConfidenceEngine:
    """Stub that always returns mid-confidence allow → policy HUMAN_REVIEW."""

    @property
    def name(self) -> str:
        return "stub-low-conf"

    def evaluate(self, context: GateContext, questions: list[QuestionSpec]) -> list[Answer]:
        answers: list[Answer] = []
        for q in questions:
            if q.type is QuestionType.CHOICE:
                value: object = "allow"
            elif q.type is QuestionType.SCORE:
                value = 0.0
            else:
                value = 0.1
            answers.append(
                Answer(key=q.key, type=q.type, value=value, confidence=0.4, probabilities=None)
            )
        return answers


def _gate(
    engine: DecisionEngine | None = None,
    queue: InMemoryReviewQueueRepository | None = None,
) -> tuple[GateService, InMemoryReviewQueueRepository]:
    queue = queue or InMemoryReviewQueueRepository()
    service = GateService(
        engine=engine or FakeDecisionEngine(),
        policy=PolicyEngine(ConfidenceBands()),
        pack=SafetyPack(),
        audit=InMemoryAuditRepository(),
        reviews=queue,
    )
    return service, queue


def test_human_review_is_enqueued() -> None:
    gate, queue = _gate(engine=LowConfidenceEngine())
    result = gate.check(GateContext(candidate_output="Ambiguous borderline reply."))
    assert result.action is GateAction.HUMAN_REVIEW
    pending = queue.list(status=ReviewStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].id == result.request_id


def test_rewrite_is_enqueued() -> None:
    gate, queue = _gate()
    result = gate.check(
        GateContext(candidate_output="Email me at jane.doe@example.com for details.")
    )
    assert result.action is GateAction.REWRITE
    assert len(queue.list(status=ReviewStatus.PENDING)) == 1


def test_allow_is_not_enqueued() -> None:
    gate, queue = _gate()
    result = gate.check(GateContext(candidate_output="Paris is the capital of France."))
    assert result.action is GateAction.ALLOW
    assert queue.list() == []


def test_resolve_allow() -> None:
    gate, queue = _gate(engine=LowConfidenceEngine())
    reviews = ReviewService(queue)
    result = gate.check(GateContext(candidate_output="maybe?"))
    resolved = reviews.resolve(
        result.request_id,
        resolution=ReviewResolution.ALLOW,
        resolver="alice",
        note="Looks fine",
    )
    assert resolved.status is ReviewStatus.RESOLVED
    assert resolved.resolution is ReviewResolution.ALLOW
    assert resolved.resolver == "alice"
    assert queue.list(status=ReviewStatus.PENDING) == []


def test_resolve_rewrite_requires_output() -> None:
    gate, queue = _gate(engine=LowConfidenceEngine())
    reviews = ReviewService(queue)
    result = gate.check(GateContext(candidate_output="maybe?"))
    with pytest.raises(ReviewConflictError):
        reviews.resolve(
            result.request_id,
            resolution=ReviewResolution.REWRITE,
            resolver="bob",
        )


def test_double_resolve_conflicts() -> None:
    gate, queue = _gate(engine=LowConfidenceEngine())
    reviews = ReviewService(queue)
    result = gate.check(GateContext(candidate_output="maybe?"))
    reviews.resolve(result.request_id, resolution=ReviewResolution.BLOCK, resolver="carol")
    with pytest.raises(ReviewConflictError):
        reviews.resolve(result.request_id, resolution=ReviewResolution.ALLOW, resolver="dave")


def test_missing_review_raises() -> None:
    reviews = ReviewService(InMemoryReviewQueueRepository())
    with pytest.raises(ReviewNotFoundError):
        reviews.get(UUID("00000000-0000-0000-0000-000000000001"))
