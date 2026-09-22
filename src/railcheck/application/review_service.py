from __future__ import annotations

from uuid import UUID

from railcheck.application.calibration_service import AuditMissingError, CalibrationService
from railcheck.domain.enums import GATE_ACTION_FIELD, ReviewResolution, ReviewStatus
from railcheck.domain.models import GateContext, GateResult, ReviewItem
from railcheck.ports.review_queue import ReviewQueueRepository


class ReviewNotFoundError(LookupError):
    pass


class ReviewConflictError(ValueError):
    pass


class ReviewService:
    """Human-in-the-loop use cases over the review queue port."""

    def __init__(
        self,
        queue: ReviewQueueRepository,
        *,
        calibration: CalibrationService | None = None,
    ) -> None:
        self._queue = queue
        self._calibration = calibration

    def enqueue_from_gate(self, *, result: GateResult, context: GateContext) -> ReviewItem:
        item = ReviewItem.pending(result=result, context=context)
        self._queue.enqueue(item)
        return item

    def get(self, review_id: UUID) -> ReviewItem:
        item = self._queue.get(review_id)
        if item is None:
            raise ReviewNotFoundError(f"Review {review_id} not found")
        return item

    def list_pending(self, *, limit: int = 50) -> list[ReviewItem]:
        return self._queue.list(status=ReviewStatus.PENDING, limit=limit)

    def list_all(self, *, status: ReviewStatus | None = None, limit: int = 50) -> list[ReviewItem]:
        return self._queue.list(status=status, limit=limit)

    def resolve(
        self,
        review_id: UUID,
        *,
        resolution: ReviewResolution,
        resolver: str,
        note: str | None = None,
        rewritten_output: str | None = None,
    ) -> ReviewItem:
        item = self.get(review_id)
        try:
            resolved = item.resolve(
                resolution=resolution,
                resolver=resolver,
                note=note,
                rewritten_output=rewritten_output,
            )
        except ValueError as exc:
            raise ReviewConflictError(str(exc)) from exc
        self._queue.save(resolved)
        self._record_gate_outcome(resolved, resolver=resolver, note=note)
        return resolved

    def _record_gate_outcome(
        self,
        resolved: ReviewItem,
        *,
        resolver: str,
        note: str | None,
    ) -> None:
        if self._calibration is None or resolved.resolution is None:
            return
        try:
            self._calibration.record(
                request_id=resolved.id,
                field_key=GATE_ACTION_FIELD,
                label=resolved.resolution.value,
                labeled_by=resolver,
                note=note,
            )
        except AuditMissingError:
            # Review without audit should not break resolve.
            return
