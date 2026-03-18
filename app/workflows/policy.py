from __future__ import annotations

from dataclasses import dataclass

from app.schemas.processed_errors import GroundingEvidence, VerificationResult


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    reason: str


@dataclass(frozen=True)
class WorkflowPolicy:
    allow_direct_kb_resolution: bool
    verification_confidence_threshold: float
    refinement_confidence_threshold: float
    use_web_search_on_low_confidence: bool
    update_kb_on_verified: bool
    max_classification_retries: int
    max_refinement_retries: int
    route_failed_verification_to_human_review: bool
    route_failed_refinement_to_human_review: bool

    @classmethod
    def from_settings(cls, settings) -> "WorkflowPolicy":
        workflow_settings = getattr(settings, "workflow", None)
        return cls(
            allow_direct_kb_resolution=getattr(
                workflow_settings, "allow_direct_kb_resolution", True
            ),
            verification_confidence_threshold=getattr(
                workflow_settings,
                "verification_confidence_threshold",
                0.6,
            ),
            refinement_confidence_threshold=getattr(
                workflow_settings,
                "refinement_confidence_threshold",
                0.7,
            ),
            use_web_search_on_low_confidence=getattr(
                workflow_settings,
                "use_web_search_on_low_confidence",
                True,
            ),
            update_kb_on_verified=getattr(workflow_settings, "update_kb_on_verified", True),
            max_classification_retries=getattr(workflow_settings, "max_classification_retries", 1),
            max_refinement_retries=getattr(workflow_settings, "max_refinement_retries", 1),
            route_failed_verification_to_human_review=getattr(
                workflow_settings,
                "route_failed_verification_to_human_review",
                True,
            ),
            route_failed_refinement_to_human_review=getattr(
                workflow_settings,
                "route_failed_refinement_to_human_review",
                True,
            ),
        )

    def decide_after_kb_retrieval(self, direct_match: GroundingEvidence | None) -> PolicyDecision:
        if direct_match is not None and self.allow_direct_kb_resolution:
            return PolicyDecision(
                action="direct_kb_resolution",
                reason="Policy allows direct KB resolution when a strong match exists.",
            )
        return PolicyDecision(
            action="primary_classification",
            reason="Policy requires model classification when KB resolution is not approved directly.",
        )

    def decide_after_primary_classification(self) -> PolicyDecision:
        return PolicyDecision(
            action="verification",
            reason="Policy requires verification before the answer can be trusted.",
        )

    def decide_after_verification(
        self,
        verification: VerificationResult | None,
        *,
        search_enabled: bool,
        force_web_search: bool = False,
    ) -> PolicyDecision:
        if verification is None:
            return PolicyDecision("end", "Verification result is missing.")
        if search_enabled and force_web_search:
            return PolicyDecision(
                action="web_search",
                reason="User requested web evidence even though verification completed successfully.",
            )
        if (
            verification.passed
            and verification.confidence >= self.verification_confidence_threshold
        ):
            if self.update_kb_on_verified:
                return PolicyDecision(
                    action="kb_update",
                    reason="Verification passed and policy allows writing verified answers back to KB.",
                )
            return PolicyDecision(
                action="end",
                reason="Verification passed, but KB write-back is disabled by policy.",
            )
        low_confidence = verification.confidence < self.verification_confidence_threshold
        if search_enabled and (
            verification.needs_web_search
            or (low_confidence and self.use_web_search_on_low_confidence)
        ):
            return PolicyDecision(
                action="web_search",
                reason="Policy requires external evidence when verification fails or confidence is too low.",
            )
        return PolicyDecision(
            action="verification_failed",
            reason="Verification did not satisfy policy and no fallback search will run.",
        )

    def decide_after_web_search(self) -> PolicyDecision:
        return PolicyDecision(
            action="refinement",
            reason="Policy requires refinement after collecting external evidence.",
        )

    def decide_after_refinement(self) -> PolicyDecision:
        return PolicyDecision(
            action="refinement_verification",
            reason="Policy requires a second verification after refinement.",
        )

    def decide_after_refinement_verification(
        self, verification: VerificationResult | None
    ) -> PolicyDecision:
        if verification is None:
            return PolicyDecision("end", "Refinement verification result is missing.")
        if verification.passed and verification.confidence >= self.refinement_confidence_threshold:
            if self.update_kb_on_verified:
                return PolicyDecision(
                    action="kb_update",
                    reason="Refined answer passed policy thresholds and can be written back to KB.",
                )
            return PolicyDecision(
                action="end",
                reason="Refined answer passed, but KB write-back is disabled by policy.",
            )
        return PolicyDecision(
            action="refinement_failed",
            reason="Refined answer still does not satisfy policy thresholds.",
        )

    def decide_after_primary_classification_failure(self, attempts: int) -> PolicyDecision:
        if attempts <= self.max_classification_retries:
            return PolicyDecision(
                action="reflection",
                reason="Policy allows a reflected retry after a primary classification failure.",
            )
        return PolicyDecision(
            action="human_review",
            reason="Primary classification exhausted the allowed retry budget.",
        )

    def decide_after_refinement_failure(self, attempts: int) -> PolicyDecision:
        if attempts <= self.max_refinement_retries:
            return PolicyDecision(
                action="reflection",
                reason="Policy allows a reflected retry after a refinement failure.",
            )
        return PolicyDecision(
            action="human_review",
            reason="Refinement exhausted the allowed retry budget.",
        )

    def decide_after_verification_terminal_failure(self) -> PolicyDecision:
        if self.route_failed_verification_to_human_review:
            return PolicyDecision(
                action="human_review",
                reason="Verification failed and policy routes unresolved outcomes to human review.",
            )
        return PolicyDecision(
            action="verification_failed",
            reason="Verification failed and policy does not escalate to human review.",
        )

    def decide_after_refinement_terminal_failure(self) -> PolicyDecision:
        if self.route_failed_refinement_to_human_review:
            return PolicyDecision(
                action="human_review",
                reason="Refinement failed and policy routes unresolved outcomes to human review.",
            )
        return PolicyDecision(
            action="refinement_failed",
            reason="Refinement failed and policy does not escalate to human review.",
        )
