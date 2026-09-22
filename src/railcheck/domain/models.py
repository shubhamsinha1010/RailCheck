from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from railcheck.domain.enums import GateAction, QuestionType, ReviewResolution, ReviewStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class QuestionSpec:
    """One typed System One question evaluated against a candidate output."""

    key: str
    type: QuestionType
    instructions: str
    criteria: dict[str, str] | list[str] | None = None


@dataclass(frozen=True, slots=True)
class Answer:
    """Structured answer for a single question, including calibrated signal."""

    key: str
    type: QuestionType
    value: Any
    confidence: float
    probabilities: dict[str, float] | None = None


@dataclass(frozen=True, slots=True)
class GateContext:
    """Everything the decision engine needs about one candidate output."""

    candidate_output: str
    user_prompt: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_state(self) -> str:
        """Render a compact state blob for System One backends."""
        parts = [f"Candidate output:\n{self.candidate_output}"]
        if self.user_prompt:
            parts.append(f"User prompt:\n{self.user_prompt}")
        if self.tool_name:
            parts.append(f"Tool: {self.tool_name}")
            if self.tool_args:
                parts.append(f"Tool args: {self.tool_args}")
        if self.metadata:
            parts.append(f"Metadata: {self.metadata}")
        return "\n\n".join(parts)


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    action: GateAction
    reason: str
    triggered_by: str | None = None


@dataclass(frozen=True, slots=True)
class GateResult:
    request_id: UUID
    action: GateAction
    reason: str
    answers: tuple[Answer, ...]
    pack_name: str
    backend: str
    created_at: datetime = field(default_factory=utc_now)
    triggered_by: str | None = None

    @staticmethod
    def new(
        *,
        action: GateAction,
        reason: str,
        answers: list[Answer] | tuple[Answer, ...],
        pack_name: str,
        backend: str,
        triggered_by: str | None = None,
    ) -> GateResult:
        return GateResult(
            request_id=uuid4(),
            action=action,
            reason=reason,
            answers=tuple(answers),
            pack_name=pack_name,
            backend=backend,
            triggered_by=triggered_by,
        )


@dataclass(frozen=True, slots=True)
class AuditRecord:
    result: GateResult
    context: GateContext


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """A mid-confidence (or rewrite) gate result awaiting human judgment."""

    id: UUID
    status: ReviewStatus
    result: GateResult
    context: GateContext
    created_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None
    resolver: str | None = None
    resolution: ReviewResolution | None = None
    note: str | None = None
    rewritten_output: str | None = None

    @staticmethod
    def pending(*, result: GateResult, context: GateContext) -> ReviewItem:
        return ReviewItem(
            id=result.request_id,
            status=ReviewStatus.PENDING,
            result=result,
            context=context,
        )

    def resolve(
        self,
        *,
        resolution: ReviewResolution,
        resolver: str,
        note: str | None = None,
        rewritten_output: str | None = None,
    ) -> ReviewItem:
        if self.status is ReviewStatus.RESOLVED:
            raise ValueError(f"Review {self.id} is already resolved")
        if resolution is ReviewResolution.REWRITE and not rewritten_output:
            raise ValueError("rewritten_output is required when resolution is rewrite")
        return ReviewItem(
            id=self.id,
            status=ReviewStatus.RESOLVED,
            result=self.result,
            context=self.context,
            created_at=self.created_at,
            resolved_at=utc_now(),
            resolver=resolver,
            resolution=resolution,
            note=note,
            rewritten_output=rewritten_output,
        )


@dataclass(frozen=True, slots=True)
class OutcomeRecord:
    """Ground-truth label for a prior gate decision, used for calibration."""

    request_id: UUID
    field_key: str
    label: str
    labeled_by: str
    labeled_at: datetime = field(default_factory=utc_now)
    note: str | None = None
    id: UUID = field(default_factory=uuid4)
