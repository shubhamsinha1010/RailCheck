from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from uuid import UUID

from railcheck.domain.enums import ReviewStatus
from railcheck.domain.models import ReviewItem


class InMemoryReviewQueueRepository:
    """Thread-safe in-memory review queue (dev / tests)."""

    def __init__(self, max_records: int = 10_000) -> None:
        self._max_records = max_records
        self._items: OrderedDict[UUID, ReviewItem] = OrderedDict()
        self._lock = Lock()

    def enqueue(self, item: ReviewItem) -> None:
        with self._lock:
            self._items[item.id] = item
            while len(self._items) > self._max_records:
                self._items.popitem(last=False)

    def get(self, review_id: UUID) -> ReviewItem | None:
        with self._lock:
            return self._items.get(review_id)

    def list(
        self,
        *,
        status: ReviewStatus | None = None,
        limit: int = 50,
    ) -> list[ReviewItem]:
        with self._lock:
            items = list(self._items.values())
        if status is not None:
            items = [i for i in items if i.status is status]
        return list(reversed(items[-limit:]))

    def save(self, item: ReviewItem) -> None:
        with self._lock:
            if item.id not in self._items:
                raise KeyError(f"Review {item.id} not found")
            self._items[item.id] = item
