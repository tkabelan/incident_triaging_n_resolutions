from app.agents.classification_service import PrimaryClassificationService
from app.schemas.processed_errors import (
    ClassificationResolutionDraft,
    GroundingEvidence,
    ProcessedErrorRecord,
)


class FakeStructuredLlm:
    def invoke(self, payload):
        assert "processed_error" in payload
        assert "evidence" in payload
        return ClassificationResolutionDraft(
            category="access_denied",
            main_category="PLATFORM",
            subcategory="Authentication & Permissions",
            confidence=0.88,
            reasoning="The evidence matches an S3 permission failure.",
            proposed_resolution="Check IAM and bucket policy.",
        )


def test_classification_service_uses_structured_llm_output() -> None:
    service = PrimaryClassificationService(structured_llm=FakeStructuredLlm())
    processed_error = ProcessedErrorRecord(
        row_id="1",
        source_file="errors.csv",
        raw_storage_reference="raw-ref",
        error_prefix="ValueError",
        error_summary="Forbidden while loading S3 object",
        normalized_prefix="valueerror",
        category_hint="access_denied",
        keywords=["forbidden", "s3"],
        error_type="access_denied",
        exception_type="AccessDeniedException",
        severity="high",
        service_hint="s3",
        retryable=False,
        resolution_type="permission_fix",
    )
    evidence = [
        GroundingEvidence(
            kb_id="kb-access-denied-s3",
            title="S3 access denied during file load",
            category="access_denied",
            resolution="Check IAM and bucket policy.",
            notes="Permissions issue",
            score=0.91,
            source_type="seed",
            error_type="access_denied",
            exception_type="AccessDeniedException",
            severity="high",
            service_hint="s3",
            retryable=False,
            resolution_type="permission_fix",
        )
    ]

    result = service.classify_and_resolve(processed_error, evidence)

    assert result.category == "access_denied"
    assert result.main_category == "PLATFORM"
    assert result.subcategory == "Authentication & Permissions"
    assert result.confidence == 0.88
    assert result.proposed_resolution == "Check IAM and bucket policy."
