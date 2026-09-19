"""JSON Schema definition and strict local validation for RAG answers."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidatedAnswer:
    """A response that passed both JSON and citation validation."""

    answer: str
    citations: tuple[str, ...]
    abstained: bool
    confidence: float


@dataclass(frozen=True)
class ValidationResult:
    """Validation outcome kept alongside every model sample."""

    value: ValidatedAnswer | None
    error: str | None

    @property
    def valid(self) -> bool:
        return self.value is not None


def answer_schema(allowed_citations: list[str]) -> dict[str, Any]:
    """Build the exact JSON Schema sent to the model backend."""

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "answer": {"type": "string", "minLength": 1},
            "citations": {
                "type": "array",
                "items": {"type": "string", "enum": allowed_citations},
                "uniqueItems": True,
            },
            "abstained": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "required": ["answer", "citations", "abstained", "confidence"],
    }


def validate_answer(raw: str, allowed_citations: set[str]) -> ValidationResult:
    """Validate provider output without trusting provider-side schema support."""

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        return ValidationResult(None, f"invalid JSON: {error.msg}")
    if not isinstance(data, dict):
        return ValidationResult(None, "response must be a JSON object")
    expected_keys = {"answer", "citations", "abstained", "confidence"}
    if set(data) != expected_keys:
        return ValidationResult(None, "response keys do not match the schema")
    answer = data["answer"]
    citations = data["citations"]
    abstained = data["abstained"]
    confidence = data["confidence"]
    if not isinstance(answer, str) or not answer.strip():
        return ValidationResult(None, "answer must be a non-empty string")
    if not isinstance(citations, list) or not all(isinstance(item, str) for item in citations):
        return ValidationResult(None, "citations must be an array of strings")
    if len(set(citations)) != len(citations):
        return ValidationResult(None, "citations must be unique")
    if not set(citations).issubset(allowed_citations):
        return ValidationResult(None, "response cites a chunk that was not retrieved")
    if not isinstance(abstained, bool):
        return ValidationResult(None, "abstained must be a boolean")
    if isinstance(confidence, bool) or not isinstance(confidence, int | float):
        return ValidationResult(None, "confidence must be a number")
    normalized_confidence = float(confidence)
    if not math.isfinite(normalized_confidence) or not 0 <= normalized_confidence <= 1:
        return ValidationResult(None, "confidence must be between 0 and 1")
    if not abstained and not citations:
        return ValidationResult(None, "a non-abstaining answer must cite retrieved evidence")
    return ValidationResult(
        ValidatedAnswer(
            answer=answer.strip(),
            citations=tuple(citations),
            abstained=abstained,
            confidence=normalized_confidence,
        ),
        None,
    )
