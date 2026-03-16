from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TaxonomyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_type: str
    exception_type: str | None
    severity: str
    service_hint: str | None
    retryable: bool
    resolution_type: str


def classify_taxonomy(error_prefix: str, error_summary: str) -> TaxonomyResult:
    text = f"{error_prefix} {error_summary}".lower()
    prefix = error_prefix.split(":")[0].strip()

    if "accessdenied" in text or "403 forbidden" in text or "forbidden" in text:
        return TaxonomyResult(
            error_type="access_denied",
            exception_type="AccessDeniedException",
            severity="high",
            service_hint="s3",
            retryable=False,
            resolution_type="permission_fix",
        )
    if "filenotfound" in text or "no such file or directory" in text:
        return TaxonomyResult(
            error_type="file_not_found",
            exception_type="FileNotFoundException",
            severity="medium",
            service_hint="storage",
            retryable=True,
            resolution_type="path_fix",
        )
    if "concurrentappendexception" in text or "conflicting commit" in text or "concurrency control" in text:
        return TaxonomyResult(
            error_type="concurrency_conflict",
            exception_type="ConcurrentAppendException",
            severity="medium",
            service_hint="delta_lake",
            retryable=True,
            resolution_type="retry_or_reschedule",
        )
    if "executionerror" in text or "brickflow" in text:
        return TaxonomyResult(
            error_type="application_error",
            exception_type=prefix or "ExecutionError",
            severity="medium",
            service_hint="application",
            retryable=False,
            resolution_type="code_fix",
        )
    return TaxonomyResult(
        error_type="unknown",
        exception_type=prefix or None,
        severity="medium",
        service_hint=None,
        retryable=False,
        resolution_type="manual_investigation",
    )
