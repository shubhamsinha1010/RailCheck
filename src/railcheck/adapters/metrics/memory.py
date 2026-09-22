from __future__ import annotations

from collections import defaultdict
from threading import Lock


class InMemoryMetricsCollector:
    """Process-local counters exposed in Prometheus text format (no extra deps)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._gate_checks: dict[str, int] = defaultdict(int)
        self._latency_sum = 0.0
        self._latency_count = 0
        self._review_pending = 0

    def inc_gate_check(self, action: str) -> None:
        with self._lock:
            self._gate_checks[action] += 1

    def observe_gate_latency_seconds(self, seconds: float) -> None:
        with self._lock:
            self._latency_sum += max(0.0, seconds)
            self._latency_count += 1

    def set_review_pending(self, count: int) -> None:
        with self._lock:
            self._review_pending = max(0, count)

    def render_prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP railcheck_gate_checks_total Gate checks by action",
                "# TYPE railcheck_gate_checks_total counter",
            ]
            for action, value in sorted(self._gate_checks.items()):
                lines.append(f'railcheck_gate_checks_total{{action="{action}"}} {value}')

            lines.extend(
                [
                    "# HELP railcheck_gate_latency_seconds_sum Total gate check latency",
                    "# TYPE railcheck_gate_latency_seconds_sum counter",
                    f"railcheck_gate_latency_seconds_sum {self._latency_sum}",
                    "# HELP railcheck_gate_latency_seconds_count Gate check latency samples",
                    "# TYPE railcheck_gate_latency_seconds_count counter",
                    f"railcheck_gate_latency_seconds_count {self._latency_count}",
                    "# HELP railcheck_review_pending Pending human reviews",
                    "# TYPE railcheck_review_pending gauge",
                    f"railcheck_review_pending {self._review_pending}",
                ]
            )
            return "\n".join(lines) + "\n"
