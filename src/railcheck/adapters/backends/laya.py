from __future__ import annotations

from typing import Any

from railcheck.domain.enums import QuestionType
from railcheck.domain.models import Answer, GateContext, QuestionSpec


class LayaDecisionEngine:
    """Adapter: wraps the open-source Laya System One model behind DecisionEngine."""

    def __init__(self, model_id: str = "convaiinnovations/laya", device: str | None = None) -> None:
        try:
            import laya  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - exercised when extra missing
            raise RuntimeError(
                "Laya backend requires the optional dependency: pip install 'railcheck[laya]'"
            ) from exc

        kwargs: dict[str, Any] = {}
        if device:
            kwargs["device"] = device
        self._agent = laya.load(model_id, **kwargs) if kwargs else laya.load(model_id)
        self._model_id = model_id

    @property
    def name(self) -> str:
        return f"laya:{self._model_id}"

    def evaluate(self, context: GateContext, questions: list[QuestionSpec]) -> list[Answer]:
        payload = {q.key: self._to_laya_question(q) for q in questions}
        raw = self._agent.predict(context.as_state(), payload)
        answers_raw = raw.get("answers", raw)
        return [self._from_laya_answer(q, answers_raw[q.key]) for q in questions]

    @staticmethod
    def _to_laya_question(question: QuestionSpec) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": question.type.value,
            "instructions": question.instructions,
        }
        if question.criteria is not None:
            body["criteria"] = question.criteria
        return body

    @staticmethod
    def _from_laya_answer(question: QuestionSpec, raw: dict[str, Any]) -> Answer:
        if question.type == QuestionType.CHOICE:
            value = raw.get("choice", raw.get("value"))
            probabilities = raw.get("probabilities")
        elif question.type == QuestionType.SCORE:
            value = float(raw.get("score", raw.get("value", 0.0)))
            probabilities = raw.get("probabilities")
        else:
            value = float(raw.get("noul", raw.get("value", 0.0)))
            probabilities = None

        confidence = float(raw.get("confidence", 0.0))
        return Answer(
            key=question.key,
            type=question.type,
            value=value,
            confidence=confidence,
            probabilities=probabilities,
        )
