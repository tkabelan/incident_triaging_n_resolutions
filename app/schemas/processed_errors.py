from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProcessedErrorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_id: str
    source_file: str
    raw_storage_reference: str
    error_prefix: str
    error_summary: str
    normalized_prefix: str
    category_hint: str
    keywords: list[str] = Field(default_factory=list)
    error_type: str
    exception_type: str | None
    severity: str
    service_hint: str | None
    retryable: bool
    resolution_type: str


class KnowledgeBaseEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kb_id: str
    title: str
    category: str
    symptoms: list[str]
    resolution: str
    notes: str
    source_type: str = "seed"
    error_type: str | None = None
    exception_type: str | None = None
    severity: str | None = None
    service_hint: str | None = None
    retryable: bool | None = None
    resolution_type: str | None = None


class GroundingEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kb_id: str
    title: str
    category: str
    resolution: str
    notes: str
    score: float
    source_type: str = "seed"
    error_type: str | None = None
    exception_type: str | None = None
    severity: str | None = None
    service_hint: str | None = None
    retryable: bool | None = None
    resolution_type: str | None = None


class KbRetrievalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: list[GroundingEvidence] = Field(default_factory=list)
    direct_match: GroundingEvidence | None = None


class ClassificationResolutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    main_category: str | None = None
    subcategory: str | None = None
    confidence: float
    reasoning: str
    proposed_resolution: str
    evidence: list[GroundingEvidence] = Field(default_factory=list)


class ClassificationResolutionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    main_category: str
    subcategory: str
    confidence: float
    reasoning: str
    proposed_resolution: str


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    confidence: float
    reasoning: str
    needs_web_search: bool


class WebSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    content: str
    score: float | None = None


class RefinementResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    classification: ClassificationResolutionResult
    verification: VerificationResult
