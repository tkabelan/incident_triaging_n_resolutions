from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RawErrorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_id: str
    error_prefix: str
    error_message: str
    source_file: str


class RawErrorIngestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record: RawErrorRecord


class RawErrorIngestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accepted: bool
    record: RawErrorRecord
    storage_reference: str
    message: str
