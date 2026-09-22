from __future__ import annotations

import time

from railcheck.domain.enums import GateAction, ReviewStatus
from railcheck.domain.models import AuditRecord, GateContext, GateResult, ReviewItem
from railcheck.packs.base import DecisionPack
from railcheck.policy.engine import PolicyEngine
from railcheck.ports.audit_repository import AuditRepository
from railcheck.ports.decision_engine import DecisionEngine
from railcheck.ports.metrics import MetricsCollector
from railcheck.ports.review_queue import ReviewQueueRepository

_QUEUEABLE_ACTIONS = frozenset({GateAction.HUMAN_REVIEW, GateAction.REWRITE})


class GateService:
    """
    Application use-case: evaluate a candidate output and return a gate verdict.

    Depends only on ports + pack/policy abstractions (Dependency Inversion).
    Mid-band and rewrite dispositions are optionally enqueued for review.
    """

    def __init__(
        self,
        *,
        engine: DecisionEngine,
        policy: PolicyEngine,
        pack: DecisionPack,
        audit: AuditRepository,
        reviews: ReviewQueueRepository | None = None,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self._engine = engine
        self._policy = policy
        self._pack = pack
        self._audit = audit
        self._reviews = reviews
        self._metrics = metrics

    @property
    def pack_name(self) -> str:
        return self._pack.name

    @property
    def backend_name(self) -> str:
        return self._engine.name

    def check(self, context: GateContext) -> GateResult:
        started = time.perf_counter()
        questions = self._pack.questions()
        answers = self._engine.evaluate(context, questions)
        decision = self._policy.decide(answers)
        result = GateResult.new(
            action=decision.action,
            reason=decision.reason,
            answers=answers,
            pack_name=self._pack.name,
            backend=self._engine.name,
            triggered_by=decision.triggered_by,
        )
        self._audit.save(AuditRecord(result=result, context=context))
        if self._reviews is not None and result.action in _QUEUEABLE_ACTIONS:
            self._reviews.enqueue(ReviewItem.pending(result=result, context=context))
            if self._metrics is not None:
                pending = len(self._reviews.list(status=ReviewStatus.PENDING, limit=10_000))
                self._metrics.set_review_pending(pending)
        if self._metrics is not None:
            self._metrics.inc_gate_check(result.action.value)
            self._metrics.observe_gate_latency_seconds(time.perf_counter() - started)
        return result

    def check_batch(self, contexts: list[GateContext]) -> list[GateResult]:
        """Evaluate many candidates; order of results matches the input order."""
        return [self.check(context) for context in contexts]
