# Implementation Plan

`/implementation` refers to the current execution plan for building this repository.

## Current Scope

Implement current foundation plus selected Phase 2 tasks:

1. Set up the project scaffold
2. Define runtime and development dependencies
3. Add JSON config loading
4. Add centralized logging
5. Implement Task 2.1: CSV error ingestion service
6. Implement Task 2.2: Raw error ingestion through MCP
7. Implement Task 2.4: Normalize errors
8. Implement Step 6: Retrieve KB grounding
9. Implement Step 7: Classify and propose resolution
10. Replace Step 6 with ChromaDB-backed retrieval
11. Replace Step 7 with LangChain structured output
12. Add end-to-end runner for the first three errors
13. Replace remote embeddings with a local embedding backend for Chroma
14. Disable Chroma telemetry in local runs
15. Add graceful per-error handling for 429/rate-limit failures
16. Add single-call OpenAI diagnostic script
17. Implement Step 8 through MCP using the same LLM model for now
18. Implement Step 9 web search through MCP using Tavily
19. Add retrieval-first short-circuit for repeated errors
20. Add KB write-back for verified outcomes
21. Add single-error runner with step trace for manual testing

## Status

- [x] Create implementation tracker
- [x] Step 1: Project scaffold
- [x] Step 2: Dependencies
- [x] Step 3: JSON config
- [x] Step 4: Logging
- [x] Task 2.1: CSV error ingestion service
- [x] Task 2.2: Raw error ingestion through MCP
- [x] Task 2.3: Store raw error records
- [x] Task 2.4: Normalize errors
- [x] Step 6: Retrieve KB grounding
- [x] Step 7: Classify and propose resolution
- [x] Step 6 update: ChromaDB-backed retrieval
- [x] Step 7 update: LangChain LLM structured output
- [x] End-to-end runner for first three errors
- [x] Step 6 update: local embedding backend for Chroma
- [x] Chroma telemetry disabled in config/load path
- [x] Per-error 429 handling in workflow
- [x] Single-call OpenAI diagnostic script
- [x] Step 8: verification via MCP
- [x] Step 9: Tavily web search via MCP
- [x] Retrieval-first short-circuit for strong KB matches
- [x] KB write-back for verified outcomes
- [x] Single-error runner with step trace

## Implemented Files

### Foundation

- App entrypoint: [app/main.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/main.py)
- FastAPI app factory: [app/api/app.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/api/app.py)
- Health route: [app/api/routes/health.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/api/routes/health.py)
- Config loader: [app/core/config.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/core/config.py)
- Logging setup: [app/logging_config.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/logging_config.py)
- Project dependencies: [pyproject.toml](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/pyproject.toml)
- JSON config template: [config/config.json](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/config/config.json)
- Local env template: [.env.example](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/.env.example)

### Task 2.1: CSV Ingestion

- CSV ingestion service: [app/ingestion/csv_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/ingestion/csv_ingestion.py)
- Error schemas: [app/schemas/error_records.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/schemas/error_records.py)

### Task 2.2: MCP Raw Ingestion

- MCP server registry: [app/mcp_server/server.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/server.py)
- MCP raw ingestion handler: [app/mcp_server/raw_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/raw_ingestion.py)
- MCP server bootstrap: [app/mcp_server/bootstrap.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/bootstrap.py)
- LangChain MCP client: [app/mcp_client/client.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_client/client.py)

### Task 2.3: Raw Storage

- Raw storage service: [app/storage/raw_error_storage.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/storage/raw_error_storage.py)
- Updated raw ingestion schema: [app/schemas/error_records.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/schemas/error_records.py)
- MCP raw ingestion now persists accepted records: [app/mcp_server/raw_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/raw_ingestion.py)

### Task 2.4: Normalization

- Processed error schemas: [app/schemas/processed_errors.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/schemas/processed_errors.py)
- Normalization service: [app/normalization/error_normalizer.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/normalization/error_normalizer.py)
- Processed storage service: [app/storage/processed_error_storage.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/storage/processed_error_storage.py)

### Step 6: KB Grounding

- KB seed data for Chroma bootstrap: [config/knowledge_base.json](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/config/knowledge_base.json)
- KB retrieval service: [app/retrieval/kb_retriever.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/retrieval/kb_retriever.py)
- Local embedding backend: [app/retrieval/local_embeddings.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/retrieval/local_embeddings.py)

### Step 7: Classification and Resolution

- Primary classification service: [app/agents/classification_service.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/agents/classification_service.py)

### End-to-End Runner

- Workflow runner: [app/workflows/error_processing.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/error_processing.py)
- CLI entrypoint: [app/run_first_three_errors.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/run_first_three_errors.py)

### Tests

- Config tests: [tests/test_config.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_config.py)
- Health API tests: [tests/test_health.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_health.py)
- CSV ingestion tests: [tests/test_csv_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_csv_ingestion.py)
- MCP raw ingestion tests: [tests/test_mcp_raw_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_mcp_raw_ingestion.py)

## Workflow Map

Current workflow shape:

1. Read CSV errors
2. Convert rows into raw error records
3. Send raw error records through MCP
4. Store raw error records
5. Normalize errors
6. Retrieve KB grounding
7. Classify and propose resolution
8. Verify with second LLM
9. Run web search if verification fails
10. Refine final answer
11. Update KB

### Status Against Workflow

- Step 1: Read CSV errors
  Status: done
  Implementation: [app/ingestion/csv_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/ingestion/csv_ingestion.py)

- Step 2: Convert rows into raw error records
  Status: done
  Implementation: [app/ingestion/csv_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/ingestion/csv_ingestion.py), [app/schemas/error_records.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/schemas/error_records.py)

- Step 3: Send raw error records through MCP
  Status: done
  Implementation: [app/mcp_server/server.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/server.py), [app/mcp_server/raw_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/raw_ingestion.py), [app/mcp_server/bootstrap.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/bootstrap.py), [app/mcp_client/client.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_client/client.py)

- Step 4: Store raw error records
  Status: done
  Task mapping: Task 2.3
  Implementation: [app/storage/raw_error_storage.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/storage/raw_error_storage.py), [app/mcp_server/raw_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/raw_ingestion.py)

- Step 5: Normalize errors
  Status: done
  Implementation: [app/normalization/error_normalizer.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/normalization/error_normalizer.py), [app/storage/processed_error_storage.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/storage/processed_error_storage.py)

- Step 6: Retrieve KB grounding
  Status: done
  Implementation: [app/retrieval/kb_retriever.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/retrieval/kb_retriever.py), [config/knowledge_base.json](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/config/knowledge_base.json)
  Note: retrieval now targets ChromaDB with a local hash-based embedding backend. The JSON file is seed data used to bootstrap the collection.

- Step 7: Classify and propose resolution
  Status: done
  Implementation: [app/agents/classification_service.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/agents/classification_service.py)
  Note: classification now uses LangChain structured output with the configured primary LLM.

- Step 8: Verify with second LLM
  Status: done

- Step 9: Run web search if verification fails
  Status: done

- Step 10: Refine final answer
  Status: not started

- Step 11: Update KB
  Status: done

## Next Task: Verification

The next step is verification with a second model or verification service.

What it should do:

- take the structured classification and proposed resolution
- verify whether the grounded answer is acceptable
- return pass/fail, confidence, and disagreement reasons
- decide whether fallback web search is needed

Expected implementation area:

- verification schemas and service under `app/verification`
- optional MCP exposure for verification
- tests for pass/fail verification paths

## Canonical References

- [docs/specification.md](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/docs/specification.md)
- [docs/technical-plan.md](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/docs/technical-plan.md)
- [docs/tasks.md](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/docs/tasks.md)
