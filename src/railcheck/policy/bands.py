from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConfidenceBands:
    """
    Thresholds for confidence-gated dispositions.

    High-confidence block signals → BLOCK.
    High-confidence allow with no elevated risk → ALLOW.
    Everything else → HUMAN_REVIEW (or REWRITE when risk_class says so).
    """

    allow_min_confidence: float = 0.85
    block_min_confidence: float = 0.85
    noul_positive_threshold: float = 0.5
    harm_block_score: float = 2.0

    def __post_init__(self) -> None:
        for name in (
            "allow_min_confidence",
            "block_min_confidence",
            "noul_positive_threshold",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value}")
        if not 0.0 <= self.harm_block_score <= 3.0:
            raise ValueError("harm_block_score must be in [0, 3]")
