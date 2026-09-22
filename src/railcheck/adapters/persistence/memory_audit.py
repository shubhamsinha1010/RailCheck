from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from uuid import UUID

from railcheck.domain.models import AuditRecord


class InMemoryAuditRepository:
    """Thread-safe in-memory audit log (dev / tests). Swap for Postgres in production."""

    def __init__(self, max_records: int = 10_000) -> None:
        self._max_records = max_records
        self._records: OrderedDict[UUID, AuditRecord] = OrderedDict()
        self._lock = Lock()

    def save(self, record: AuditRecord) -> None:
        with self._lock:
            self._records[record.result.request_id] = record
            while len(self._records) > self._max_records:
                self._records.popitem(last=False)

    def get(self, request_id: UUID) -> AuditRecord | None:
        with self._lock:
            return self._records.get(request_id)

    def list_recent(self, limit: int = 50) -> list[AuditRecord]:
        with self._lock:
            items = list(self._records.values())
        return list(reversed(items[-limit:]))
