from __future__ import annotations

from collections import defaultdict
from threading import Lock
from uuid import UUID

from railcheck.domain.models import OutcomeRecord


class InMemoryOutcomeRepository:
    """Thread-safe in-memory outcome store (dev / tests)."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, OutcomeRecord] = {}
        self._by_request: dict[UUID, list[UUID]] = defaultdict(list)
        self._by_field: dict[str, list[UUID]] = defaultdict(list)
        self._lock = Lock()

    def save(self, record: OutcomeRecord) -> None:
        with self._lock:
            self._by_id[record.id] = record
            self._by_request[record.request_id].append(record.id)
            self._by_field[record.field_key].append(record.id)

    def list_for_field(self, field_key: str) -> list[OutcomeRecord]:
        with self._lock:
            ids = list(self._by_field.get(field_key, []))
            return [self._by_id[i] for i in ids if i in self._by_id]

    def get_for_request(self, request_id: UUID) -> list[OutcomeRecord]:
        with self._lock:
            ids = list(self._by_request.get(request_id, []))
            return [self._by_id[i] for i in ids if i in self._by_id]
