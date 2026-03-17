from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.schemas.processed_errors import (
    ClassificationResolutionResult,
    GroundingEvidence,
    ProcessedErrorRecord,
)
from app.verification.service import VerificationService

VERIFICATION_TOOL = "verification.verify_resolution"


def create_verification_handler(
    verification_service: VerificationService,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def verify(payload: dict[str, Any]) -> dict[str, Any]:
        processed_error = ProcessedErrorRecord.model_validate(payload["processed_error"])
        classification = ClassificationResolutionResult.model_validate(payload["classification"])
        evidence = [GroundingEvidence.model_validate(item) for item in payload.get("evidence", [])]
        result = verification_service.verify(processed_error, classification, evidence)
        return result.model_dump()

    return verify
