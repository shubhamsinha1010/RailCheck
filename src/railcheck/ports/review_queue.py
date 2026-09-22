from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from railcheck.domain.enums import ReviewStatus
from railcheck.domain.models import ReviewItem


@runtime_checkable
class ReviewQueueRepository(Protocol):
    """Port for the human-in-the-loop review queue."""

    def enqueue(self, item: ReviewItem) -> None: ...

    def get(self, review_id: UUID) -> ReviewItem | None: ...

    def list(
        self,
        *,
        status: ReviewStatus | None = None,
        limit: int = 50,
    ) -> list[ReviewItem]: ...

    def save(self, item: ReviewItem) -> None:
        """Persist an updated review (e.g. after resolve)."""
        ...
