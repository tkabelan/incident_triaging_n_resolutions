from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.workflows.error_processing import ErrorProcessingWorkflow


router = APIRouter(tags=["errors"])


class SingleErrorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_text: str = Field(min_length=1, description="The full error text to process.")
    row_id: str = Field(default="manual-1")
    source_file: str = Field(default="manual_input")


class SingleErrorResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    row_id: str
    status: str
    agent_trace: dict
    classification: dict | None = None
    verification: dict | None = None
    kb_update_reference: str | None = None
    error: dict | None = None


@router.post("/errors/process", response_model=SingleErrorResponse)
def process_single_error(request: SingleErrorRequest) -> SingleErrorResponse:
    workflow = ErrorProcessingWorkflow(get_settings())
    result = workflow.run_single_error(
        request.error_text,
        row_id=request.row_id,
        source_file=request.source_file,
    )
    return SingleErrorResponse(
        row_id=result["row_id"],
        status=result["status"],
        agent_trace=result["agent_trace"],
        classification=result.get("classification"),
        verification=result.get("verification"),
        kb_update_reference=result.get("kb_update_reference"),
        error=result.get("error"),
    )
