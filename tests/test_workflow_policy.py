from __future__ import annotations

from app.schemas.processed_errors import GroundingEvidence, VerificationResult
from app.workflows.policy import WorkflowPolicy


def test_policy_can_disable_direct_kb_resolution() -> None:
    policy = WorkflowPolicy(
        allow_direct_kb_resolution=False,
        verification_confidence_threshold=0.6,
        refinement_confidence_threshold=0.7,
        use_web_search_on_low_confidence=True,
        update_kb_on_verified=True,
        max_classification_retries=1,
        max_refinement_retries=1,
        route_failed_verification_to_human_review=True,
        route_failed_refinement_to_human_review=True,
    )
    decision = policy.decide_after_kb_retrieval(
        GroundingEvidence(
            kb_id="kb-1",
            title="Known issue",
            category="access_denied",
            resolution="Check IAM",
            notes="seed note",
            score=0.92,
            source_type="learned",
            error_type="access_denied",
            exception_type="AccessDeniedException",
            severity="high",
            service_hint="s3",
            retryable=False,
            resolution_type="permission_fix",
        )
    )

    assert decision.action == "primary_classification"


def test_policy_uses_web_search_for_low_confidence_verification() -> None:
    policy = WorkflowPolicy(
        allow_direct_kb_resolution=True,
        verification_confidence_threshold=0.6,
        refinement_confidence_threshold=0.7,
        use_web_search_on_low_confidence=True,
        update_kb_on_verified=True,
        max_classification_retries=1,
        max_refinement_retries=1,
        route_failed_verification_to_human_review=True,
        route_failed_refinement_to_human_review=True,
    )
    decision = policy.decide_after_verification(
        VerificationResult(
            passed=True,
            confidence=0.42,
            reasoning="Weakly grounded.",
            needs_web_search=False,
        ),
        search_enabled=True,
    )

    assert decision.action == "web_search"


def test_policy_prevents_kb_update_when_disabled() -> None:
    policy = WorkflowPolicy(
        allow_direct_kb_resolution=True,
        verification_confidence_threshold=0.6,
        refinement_confidence_threshold=0.7,
        use_web_search_on_low_confidence=True,
        update_kb_on_verified=False,
        max_classification_retries=1,
        max_refinement_retries=1,
        route_failed_verification_to_human_review=True,
        route_failed_refinement_to_human_review=True,
    )
    decision = policy.decide_after_refinement_verification(
        VerificationResult(
            passed=True,
            confidence=0.91,
            reasoning="Looks good.",
            needs_web_search=False,
        )
    )

    assert decision.action == "end"
