from __future__ import annotations

from railcheck.calibration.metrics import compute_brier_score, compute_ece


def test_brier_perfect() -> None:
    assert compute_brier_score([0.0, 1.0], [0, 1]) == 0.0


def test_ece_report_shape() -> None:
    report = compute_ece([0.1, 0.2, 0.9, 0.95], [0, 0, 1, 1], n_bins=5)
    assert report.n == 4
    assert 0.0 <= report.ece <= 1.0
    assert len(report.reliability) == 5
