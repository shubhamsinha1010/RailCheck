from __future__ import annotations

from uuid import UUID

from railcheck.calibration.metrics import CalibrationReport, compute_ece
from railcheck.domain.enums import GATE_ACTION_FIELD, QuestionType
from railcheck.domain.models import OutcomeRecord
from railcheck.ports.audit_repository import AuditRepository
from railcheck.ports.outcome_repository import OutcomeRepository


class OutcomeNotFoundError(LookupError):
    pass


class AuditMissingError(LookupError):
    pass


class CalibrationService:
    """
    Join audit predictions with labeled outcomes and compute ECE / Brier.

    Supports noul fields (probability vs 0/1), choice fields (predicted==label),
    and the special gate_action field (predicted action vs labeled action).
    """

    def __init__(self, *, audits: AuditRepository, outcomes: OutcomeRepository) -> None:
        self._audits = audits
        self._outcomes = outcomes

    def record(
        self,
        *,
        request_id: UUID,
        field_key: str,
        label: str,
        labeled_by: str,
        note: str | None = None,
    ) -> OutcomeRecord:
        if self._audits.get(request_id) is None:
            raise AuditMissingError(f"No audit record for request {request_id}")
        record = OutcomeRecord(
            request_id=request_id,
            field_key=field_key,
            label=label,
            labeled_by=labeled_by,
            note=note,
        )
        self._outcomes.save(record)
        return record

    def report(self, field_key: str, *, n_bins: int = 10) -> CalibrationReport:
        pairs = self._probability_outcome_pairs(field_key)
        if not pairs:
            return CalibrationReport(n=0, ece=0.0, brier=0.0, reliability=())
        probabilities, outcomes = zip(*pairs, strict=True)
        return compute_ece(list(probabilities), list(outcomes), n_bins=n_bins)

    def _probability_outcome_pairs(self, field_key: str) -> list[tuple[float, int]]:
        pairs: list[tuple[float, int]] = []
        for outcome in self._outcomes.list_for_field(field_key):
            audit = self._audits.get(outcome.request_id)
            if audit is None:
                continue
            pair = self._pair_for(field_key, audit, outcome.label)
            if pair is not None:
                pairs.append(pair)
        return pairs

    def _pair_for(
        self,
        field_key: str,
        audit,
        label: str,
    ) -> tuple[float, int] | None:
        if field_key == GATE_ACTION_FIELD:
            predicted = audit.result.action.value
            # Use mean confidence across answers as a coarse gate-level signal.
            confidences = [a.confidence for a in audit.result.answers]
            probability = sum(confidences) / len(confidences) if confidences else 0.5
            return probability, int(predicted == label)

        answer = next((a for a in audit.result.answers if a.key == field_key), None)
        if answer is None:
            return None

        if answer.type is QuestionType.NOUL:
            try:
                truth = int(label)
            except ValueError:
                truth = 1 if label.lower() in {"true", "yes", "1"} else 0
            return float(answer.value), truth

        if answer.type is QuestionType.CHOICE:
            predicted = str(answer.value)
            if answer.probabilities and predicted in answer.probabilities:
                probability = float(answer.probabilities[predicted])
            else:
                probability = float(answer.confidence)
            return probability, int(predicted == label)

        if answer.type is QuestionType.SCORE:
            # Treat as correct when rounded prediction matches rounded label.
            try:
                truth_score = float(label)
            except ValueError:
                return None
            predicted = float(answer.value)
            return float(answer.confidence), int(round(predicted) == round(truth_score))

        return None
