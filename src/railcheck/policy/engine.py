from __future__ import annotations

from railcheck.domain.enums import GateAction, QuestionType
from railcheck.domain.models import Answer, PolicyDecision
from railcheck.policy.bands import ConfidenceBands


class PolicyEngine:
    """
    Pure policy: maps System One answers + confidence bands → GateAction.

    Single responsibility: no I/O, no backend knowledge (SRP + easy unit tests).
    """

    def __init__(self, bands: ConfidenceBands | None = None) -> None:
        self._bands = bands or ConfidenceBands()

    @property
    def bands(self) -> ConfidenceBands:
        return self._bands

    def decide(self, answers: list[Answer]) -> PolicyDecision:
        by_key = {a.key: a for a in answers}

        # PII is handled via risk_class → rewrite (redact), not hard block.
        block_hit = self._first_high_confidence_noul(
            by_key,
            keys=("jailbreak_success", "policy_violation", "tool_abuse"),
        )
        if block_hit is not None:
            return PolicyDecision(
                action=GateAction.BLOCK,
                reason=f"High-confidence positive signal on '{block_hit.key}'",
                triggered_by=block_hit.key,
            )

        harm = by_key.get("harm_severity")
        if (
            harm is not None
            and harm.type == QuestionType.SCORE
            and float(harm.value) >= self._bands.harm_block_score
            and harm.confidence >= self._bands.block_min_confidence
        ):
            return PolicyDecision(
                action=GateAction.BLOCK,
                reason="Harm severity above block threshold with high confidence",
                triggered_by="harm_severity",
            )

        risk = by_key.get("risk_class")
        if risk is not None and risk.type == QuestionType.CHOICE:
            label = str(risk.value)
            if label == "block" and risk.confidence >= self._bands.block_min_confidence:
                return PolicyDecision(
                    action=GateAction.BLOCK,
                    reason="risk_class chose block with high confidence",
                    triggered_by="risk_class",
                )
            if label == "rewrite":
                return PolicyDecision(
                    action=GateAction.REWRITE,
                    reason="risk_class recommends rewrite",
                    triggered_by="risk_class",
                )
            if label == "human_review":
                return PolicyDecision(
                    action=GateAction.HUMAN_REVIEW,
                    reason="risk_class recommends human review",
                    triggered_by="risk_class",
                )
            if (
                label == "allow"
                and risk.confidence >= self._bands.allow_min_confidence
                and not self._any_elevated_noul(by_key)
            ):
                return PolicyDecision(
                    action=GateAction.ALLOW,
                    reason="risk_class allow with high confidence and no elevated flags",
                    triggered_by="risk_class",
                )

        return PolicyDecision(
            action=GateAction.HUMAN_REVIEW,
            reason="Confidence outside auto-allow / auto-block bands",
            triggered_by=risk.key if risk else None,
        )

    def _first_high_confidence_noul(
        self,
        by_key: dict[str, Answer],
        *,
        keys: tuple[str, ...],
    ) -> Answer | None:
        for key in keys:
            answer = by_key.get(key)
            if answer is None or answer.type != QuestionType.NOUL:
                continue
            probability = float(answer.value)
            if (
                probability >= self._bands.noul_positive_threshold
                and answer.confidence >= self._bands.block_min_confidence
            ):
                return answer
        return None

    def _any_elevated_noul(self, by_key: dict[str, Answer]) -> bool:
        for key in ("jailbreak_success", "policy_violation", "tool_abuse", "contains_pii"):
            answer = by_key.get(key)
            if answer is None or answer.type != QuestionType.NOUL:
                continue
            if float(answer.value) >= self._bands.noul_positive_threshold:
                return True
        return False
