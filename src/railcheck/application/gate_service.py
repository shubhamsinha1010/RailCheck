from __future__ import annotations

from railcheck.domain.models import AuditRecord, GateContext, GateResult
from railcheck.packs.base import DecisionPack
from railcheck.policy.engine import PolicyEngine
from railcheck.ports.audit_repository import AuditRepository
from railcheck.ports.decision_engine import DecisionEngine


class GateService:
    """
    Application use-case: evaluate a candidate output and return a gate verdict.

    Depends only on ports + pack/policy abstractions (Dependency Inversion).
    """

    def __init__(
        self,
        *,
        engine: DecisionEngine,
        policy: PolicyEngine,
        pack: DecisionPack,
        audit: AuditRepository,
    ) -> None:
        self._engine = engine
        self._policy = policy
        self._pack = pack
        self._audit = audit

    @property
    def pack_name(self) -> str:
        return self._pack.name

    @property
    def backend_name(self) -> str:
        return self._engine.name

    def check(self, context: GateContext) -> GateResult:
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
        return result
