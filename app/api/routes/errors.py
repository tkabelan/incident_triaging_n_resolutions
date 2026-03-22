from __future__ import annotations

import json
from queue import Queue
from threading import Thread

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.workflows.error_processing import ErrorProcessingWorkflow

router = APIRouter(tags=["errors"])


class SingleErrorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_text: str = Field(min_length=1, description="The full error text to process.")
    row_id: str = Field(default="manual-1")
    source_file: str = Field(default="manual_input")
    force_web_search: bool = Field(
        default=False,
        description="If true, run web search even when verification would otherwise allow stopping.",
    )


class SingleErrorResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    row_id: str
    status: str
    agent_trace: dict
    models: dict[str, str] | None = None
    classification: dict | None = None
    verification: dict | None = None
    kb_update_reference: str | None = None
    error: dict | None = None


def _sse_payload(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/errors/process", response_model=SingleErrorResponse)
def process_single_error(request: SingleErrorRequest) -> SingleErrorResponse:
    settings = get_settings()
    workflow = ErrorProcessingWorkflow(settings)
    result = workflow.run_single_error(
        request.error_text,
        row_id=request.row_id,
        source_file=request.source_file,
        force_web_search=request.force_web_search,
    )
    return SingleErrorResponse(
        row_id=result["row_id"],
        status=result["status"],
        agent_trace=result["agent_trace"],
        models={
            "primary_classification": settings.models.primary_llm,
            "verification": settings.models.verification_llm,
        },
        classification=result.get("classification"),
        verification=result.get("verification"),
        kb_update_reference=result.get("kb_update_reference"),
        error=result.get("error"),
    )


@router.post("/errors/process/stream")
def process_single_error_stream(request: SingleErrorRequest) -> StreamingResponse:
    event_queue: Queue[dict | None] = Queue()
    settings = get_settings()

    def publish(event: dict) -> None:
        event_queue.put(event)

    def worker() -> None:
        workflow = ErrorProcessingWorkflow(settings)
        try:
            result = workflow.run_single_error(
                request.error_text,
                row_id=request.row_id,
                source_file=request.source_file,
                force_web_search=request.force_web_search,
                progress_callback=publish,
            )
            payload = SingleErrorResponse(
                row_id=result["row_id"],
                status=result["status"],
                agent_trace=result["agent_trace"],
                models={
                    "primary_classification": settings.models.primary_llm,
                    "verification": settings.models.verification_llm,
                },
                classification=result.get("classification"),
                verification=result.get("verification"),
                kb_update_reference=result.get("kb_update_reference"),
                error=result.get("error"),
            ).model_dump()
            event_queue.put({"type": "result", "payload": payload})
        except Exception as exc:
            event_queue.put(
                {
                    "type": "error",
                    "payload": {"message": str(exc), "error_type": exc.__class__.__name__},
                }
            )
        finally:
            event_queue.put(None)

    Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            event = event_queue.get()
            if event is None:
                yield _sse_payload({"type": "done"})
                break
            yield _sse_payload(event)

    return StreamingResponse(stream(), media_type="text/event-stream")
