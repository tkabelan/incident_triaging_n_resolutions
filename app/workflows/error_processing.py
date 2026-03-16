from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.agents.classification_service import PrimaryClassificationService
from app.core.config import Settings
from app.ingestion.csv_ingestion import CsvErrorIngestionService
from app.mcp_client.client import LangChainMcpClient
from app.mcp_server.bootstrap import create_mcp_server
from app.normalization.error_normalizer import ErrorNormalizationService
from app.retrieval.kb_retriever import KnowledgeBaseRetriever
from app.schemas.error_records import RawErrorRecord
from app.storage.processed_error_storage import ProcessedErrorStorageService


logger = logging.getLogger(__name__)
MAX_WEB_SEARCH_QUERY_LENGTH = 380


class ErrorProcessingWorkflow:
    def __init__(
        self,
        settings: Settings,
        *,
        ingestion_service: CsvErrorIngestionService | None = None,
        mcp_client: LangChainMcpClient | None = None,
        normalizer: ErrorNormalizationService | None = None,
        retriever: KnowledgeBaseRetriever | None = None,
        classifier: PrimaryClassificationService | None = None,
    ) -> None:
        self._settings = settings
        self._ingestion_service = ingestion_service or CsvErrorIngestionService()
        self._mcp_client = mcp_client or LangChainMcpClient(create_mcp_server())
        self._normalizer = normalizer or ErrorNormalizationService(
            ProcessedErrorStorageService(settings.storage.processed_data_dir)
        )
        self._retriever = retriever or KnowledgeBaseRetriever.from_settings(settings)
        self._classifier = classifier or PrimaryClassificationService.from_settings(settings)

    def run_first_three_errors(self) -> list[dict]:
        csv_path = Path(self._settings.ingestion.error_data_dir) / self._settings.ingestion.default_csv_file
        logger.info("Starting end-to-end processing for first three errors from %s", csv_path)
        results: list[dict] = []
        for raw_record in self._ingestion_service.read_errors(csv_path):
            results.append(self._process_one_error(raw_record))
        logger.info("Completed end-to-end processing for %s errors", len(results))
        return results

    def run_single_error(
        self,
        error_text: str,
        *,
        row_id: str = "manual-1",
        source_file: str = "manual_input",
    ) -> dict[str, Any]:
        logger.info("Starting end-to-end processing for a single manual error")
        raw_record = RawErrorRecord(
            row_id=row_id,
            error_prefix=self._infer_error_prefix(error_text),
            error_message=error_text,
            source_file=source_file,
        )
        return self._process_one_error(raw_record)

    def _process_one_error(self, raw_record: Any) -> dict[str, Any]:
        result: dict[str, Any] = {
            "row_id": raw_record.row_id,
            "status": "failed",
            "steps": [],
            "stage_details": {
                "chroma_db": {"status": "not_run", "confidence": None, "error": None},
                "primary_llm": {"status": "not_run", "confidence": None, "error": None},
                "verification_llm": {"status": "not_run", "confidence": None, "error": None},
                "web_search": {"status": "not_run", "confidence": None, "error": None},
                "refinement_llm": {"status": "not_run", "confidence": None, "error": None},
            },
            "kb_match_found": False,
            "kb_direct_match": False,
            "evidence_count": 0,
            "raw_storage_reference": None,
            "processed_storage_reference": None,
            "processed_error": None,
            "classification": None,
            "verification": None,
            "web_search_results": [],
            "kb_update_reference": None,
            "error": None,
        }
        try:
            result["steps"].append("raw_ingestion_started")
            raw_response = self._mcp_client.ingest_raw_error(raw_record)
            result["raw_storage_reference"] = raw_response.storage_reference
            result["steps"].append("raw_ingestion_completed")

            result["steps"].append("normalization_started")
            processed_record, processed_storage_reference = self._normalizer.normalize_from_storage(
                raw_response.storage_reference
            )
            result["processed_storage_reference"] = processed_storage_reference
            result["processed_error"] = processed_record.model_dump()
            result["steps"].append("normalization_completed")

            # Agentic decision point 1: prefer a strong prior KB match over new model calls.
            result["steps"].append("kb_retrieval_started")
            evidence = self._retriever.retrieve(processed_record)
            result["steps"].append("kb_retrieval_completed")
            result["evidence_count"] = len(evidence)
            result["kb_match_found"] = bool(evidence)
            result["stage_details"]["chroma_db"]["status"] = "pass" if evidence else "fail"
            direct_match = self._retriever.get_direct_match(evidence)
            if direct_match is not None:
                result["kb_direct_match"] = True
                result["stage_details"]["chroma_db"]["confidence"] = direct_match.score
                classification = self._retriever.build_classification_from_match(
                    processed_record,
                    direct_match,
                    evidence,
                )
                result["classification"] = classification.model_dump()
                result["status"] = "resolved_from_kb"
                result["steps"].append("resolved_from_kb")
                result["stage_details"]["primary_llm"]["status"] = "skipped"
                result["stage_details"]["verification_llm"]["status"] = "skipped"
                result["stage_details"]["web_search"]["status"] = "skipped"
                result["stage_details"]["refinement_llm"]["status"] = "skipped"
                return result

            # Agentic decision point 2: use the primary LLM only when retrieval is not strong enough.
            result["steps"].append("primary_classification_started")
            try:
                classification = self._classifier.classify_and_resolve(processed_record, evidence)
            except Exception as exc:
                result["stage_details"]["primary_llm"]["status"] = "fail"
                result["stage_details"]["primary_llm"]["error"] = self._format_error(exc)
                raise
            result["classification"] = classification.model_dump()
            result["steps"].append("primary_classification_completed")
            result["stage_details"]["primary_llm"]["status"] = "pass"
            result["stage_details"]["primary_llm"]["confidence"] = classification.confidence

            # Agentic decision point 3: verify the proposed answer before treating it as reliable.
            result["steps"].append("verification_started")
            try:
                verification = self._mcp_client.verify_resolution(
                    processed_record,
                    classification,
                    evidence,
                )
            except Exception as exc:
                result["stage_details"]["verification_llm"]["status"] = "fail"
                result["stage_details"]["verification_llm"]["error"] = self._format_error(exc)
                raise
            result["verification"] = verification.model_dump()
            result["steps"].append("verification_completed")
            result["stage_details"]["verification_llm"]["status"] = "pass" if verification.passed else "fail"
            result["stage_details"]["verification_llm"]["confidence"] = verification.confidence

            if verification.passed:
                # Agentic decision point 4: successful outcomes are learned back into the KB.
                result["steps"].append("kb_update_started")
                result["kb_update_reference"] = self._retriever.upsert_verified_resolution(
                    processed_record,
                    classification,
                )
                result["steps"].append("kb_update_completed")
                result["status"] = "success"
                result["stage_details"]["web_search"]["status"] = "skipped"
                result["stage_details"]["refinement_llm"]["status"] = "skipped"
            elif verification.needs_web_search and self._settings.search.enabled:
                # Agentic decision point 5: gather external evidence only when internal evidence is insufficient.
                result["steps"].append("web_search_started")
                query = self._build_web_search_query(processed_record, classification)
                try:
                    web_results = self._mcp_client.web_search(query)
                except Exception as exc:
                    result["stage_details"]["web_search"]["status"] = "fail"
                    result["stage_details"]["web_search"]["error"] = self._format_error(exc)
                    raise
                result["web_search_results"] = [item.model_dump() for item in web_results]
                result["steps"].append("web_search_completed")
                result["stage_details"]["web_search"]["status"] = "pass" if web_results else "fail"
                # Agentic decision point 6: refine the answer using both KB and web evidence.
                result["steps"].append("refinement_started")
                try:
                    refined_classification = self._classifier.refine_with_web_search(
                        processed_record,
                        evidence,
                        web_results,
                    )
                except Exception as exc:
                    result["stage_details"]["refinement_llm"]["status"] = "fail"
                    result["stage_details"]["refinement_llm"]["error"] = self._format_error(exc)
                    raise
                result["classification"] = refined_classification.model_dump()
                result["stage_details"]["refinement_llm"]["status"] = "pass"
                result["stage_details"]["refinement_llm"]["confidence"] = refined_classification.confidence
                result["steps"].append("refinement_completed")

                result["steps"].append("refinement_verification_started")
                try:
                    refined_verification = self._mcp_client.verify_resolution(
                        processed_record,
                        refined_classification,
                        evidence,
                    )
                except Exception as exc:
                    result["stage_details"]["verification_llm"]["error"] = self._format_error(exc)
                    raise
                result["verification"] = refined_verification.model_dump()
                result["steps"].append("refinement_verification_completed")
                result["stage_details"]["verification_llm"]["status"] = "pass" if refined_verification.passed else "fail"
                result["stage_details"]["verification_llm"]["confidence"] = refined_verification.confidence

                if refined_verification.passed:
                    result["steps"].append("kb_update_started")
                    result["kb_update_reference"] = self._retriever.upsert_verified_resolution(
                        processed_record,
                        refined_classification,
                    )
                    result["steps"].append("kb_update_completed")
                    result["status"] = "success_after_refinement"
                else:
                    result["status"] = "refinement_failed"
            else:
                result["stage_details"]["web_search"]["status"] = "skipped"
                result["stage_details"]["refinement_llm"]["status"] = "skipped"
                result["status"] = "verification_failed"
        except Exception as exc:
            logger.exception("Failed processing error row %s", raw_record.row_id)
            result["error"] = self._format_error(exc)
            result["steps"].append("failed")

        return result

    def _build_web_search_query(
        self,
        processed_error: Any,
        classification: Any,
    ) -> str:
        parts = [
            processed_error.error_type,
            processed_error.exception_type or "",
            processed_error.service_hint or "",
            classification.category,
            processed_error.error_summary,
            " ".join(processed_error.keywords[:4]),
        ]
        query = " ".join(part.strip() for part in parts if part and part.strip())
        if len(query) <= MAX_WEB_SEARCH_QUERY_LENGTH:
            return query
        return query[:MAX_WEB_SEARCH_QUERY_LENGTH].rstrip()

    def _format_error(self, exc: Exception) -> dict[str, Any]:
        error_type = exc.__class__.__name__
        message = str(exc)
        is_rate_limited = error_type == "RateLimitError" or "429" in message
        return {
            "type": error_type,
            "message": message,
            "is_rate_limited": is_rate_limited,
            "retryable": is_rate_limited,
        }

    def _infer_error_prefix(self, error_text: str) -> str:
        first_line = error_text.strip().splitlines()[0] if error_text.strip() else "ManualError"
        if ":" in first_line:
            return first_line
        first_token = first_line.split()[0] if first_line.split() else "ManualError"
        return first_token
