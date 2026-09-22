from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReliabilityBin:
    lower: float
    upper: float
    count: int
    avg_confidence: float
    accuracy: float


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    n: int
    ece: float
    brier: float
    reliability: tuple[ReliabilityBin, ...]


def compute_brier_score(probabilities: list[float], outcomes: list[int]) -> float:
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must be the same length")
    if not probabilities:
        return 0.0
    return sum((p - y) ** 2 for p, y in zip(probabilities, outcomes, strict=True)) / len(
        probabilities
    )


def compute_ece(
    probabilities: list[float],
    outcomes: list[int],
    *,
    n_bins: int = 10,
) -> CalibrationReport:
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must be the same length")
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")
    if not probabilities:
        return CalibrationReport(n=0, ece=0.0, brier=0.0, reliability=())

    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for p, y in zip(probabilities, outcomes, strict=True):
        idx = min(n_bins - 1, int(p * n_bins))
        bins[idx].append((p, y))

    reliability: list[ReliabilityBin] = []
    ece = 0.0
    n = len(probabilities)
    for i, bucket in enumerate(bins):
        lower, upper = i / n_bins, (i + 1) / n_bins
        if not bucket:
            reliability.append(
                ReliabilityBin(lower=lower, upper=upper, count=0, avg_confidence=0.0, accuracy=0.0)
            )
            continue
        avg_conf = sum(p for p, _ in bucket) / len(bucket)
        acc = sum(y for _, y in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(avg_conf - acc)
        reliability.append(
            ReliabilityBin(
                lower=lower,
                upper=upper,
                count=len(bucket),
                avg_confidence=avg_conf,
                accuracy=acc,
            )
        )

    return CalibrationReport(
        n=n,
        ece=ece,
        brier=compute_brier_score(probabilities, outcomes),
        reliability=tuple(reliability),
    )
