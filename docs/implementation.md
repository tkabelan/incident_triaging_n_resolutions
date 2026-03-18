# Implementation Plan

`/implementation` refers to the current execution plan for building this repository.

## Current Scope

The backend agentic phase is complete.

The agentic backend and the first frontend MVP are complete.

The current scope is LangSmith observability and traceability:

1. Add LangSmith configuration and env wiring
2. Trace LangGraph workflow runs in LangSmith
3. Attach useful run metadata and tags
4. Improve debugging visibility for planner, verification, and fallback branches
5. Surface trace context in a dedicated frontend tab

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
- [x] Step 10: refine final answer after web search
- [x] Task 3.1: Replace the custom workflow with a LangGraph graph
- [x] Task 3.2: Define a first-class graph state model
- [x] Task 3.3: Expose KB retrieval through MCP and use it inside the graph
- [x] Task 3.4: Add a planner/decision node
- [x] Task 3.5: Separate policy from reasoning
- [x] Task 3.6: Add retry and reflection behavior
- [x] Task 3.7: Add a human-review exit path
- [x] Task 3.8: Expand KB memory and learning signals
- [x] Task 3.9: Add frontend-friendly agent trace output
- [x] Task 3.10: Add single-error FastAPI endpoint
- [x] Task 4.1: Create the frontend app scaffold
- [x] Task 4.2: Add a typed API client for the single-error endpoint
- [x] Task 4.3: Build the input and submit flow
- [x] Task 4.4: Build the readable outcome summary
- [x] Task 4.5: Build the agent steps timeline
- [x] Task 4.6: Build score, evidence, and KB panels
- [x] Task 4.7: Add simple UX polish for local demo use
- [x] Task 4.8: Stream live reasoning progress to the frontend
- [x] Task 4.9: Add a frontend-controlled forced web-search option
- [x] Task 5.1: Add LangSmith configuration
- [x] Task 5.2: Enable LangSmith tracing for the workflow
- [ ] Task 5.3: Add run metadata and tags
- [ ] Task 5.4: Trace node-level decisions and failures
- [ ] Task 5.5: Add a frontend Trace tab
- [ ] Task 5.6: Document LangSmith local usage

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
- Graph state model: [app/workflows/state.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/state.py)
- CLI entrypoint: [app/run_first_three_errors.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/run_first_three_errors.py)

### Planner

- Planner node and routing logic: [app/workflows/error_processing.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/error_processing.py)
- Planner state fields: [app/workflows/state.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/state.py)

### Policy

- Workflow policy rules: [app/workflows/policy.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/policy.py)
- Workflow policy config: [app/core/config.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/core/config.py)
- Workflow policy values: [config/config.json](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/config/config.json)

### Retry, Review, and Memory

- Retry/reflection and human-review flow: [app/workflows/error_processing.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/error_processing.py)
- Expanded workflow state: [app/workflows/state.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/state.py)
- KB memory write-back metadata: [app/retrieval/kb_retriever.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/retrieval/kb_retriever.py)
- Reflection-aware classification: [app/agents/classification_service.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/agents/classification_service.py)

### Frontend Trace

- Canonical agent trace builder: [app/workflows/state.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/state.py)
- Single-error trace output: [app/run_single_error.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/run_single_error.py)

### Interactive API

- FastAPI single-error route: [app/api/routes/errors.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/api/routes/errors.py)
- FastAPI app registration: [app/api/app.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/api/app.py)
- Local frontend plan: [docs/frontend-plan.md](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/docs/frontend-plan.md)

### Frontend MVP

- Frontend package manifest: [frontend/package.json](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/package.json)
- Vite config and API proxy: [frontend/vite.config.ts](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/vite.config.ts)
- Frontend env template: [frontend/.env.example](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/.env.example)
- Frontend entry HTML: [frontend/index.html](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/index.html)
- React entrypoint: [frontend/src/main.tsx](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/src/main.tsx)
- App shell, summary, and stage timeline: [frontend/src/App.tsx](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/src/App.tsx)
- Typed API client: [frontend/src/api/processError.ts](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/src/api/processError.ts)
- Frontend response types: [frontend/src/types/agent.ts](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/src/types/agent.ts)
- Frontend styles: [frontend/src/styles.css](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/src/styles.css)
- Streaming progress endpoint: [app/api/routes/errors.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/api/routes/errors.py)
- Workflow progress events: [app/workflows/error_processing.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/error_processing.py)
- Frontend-controlled forced web-search flow: [frontend/src/App.tsx](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/frontend/src/App.tsx), [app/workflows/policy.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/workflows/policy.py), [app/api/routes/errors.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/api/routes/errors.py)

### MCP Retrieval

- MCP KB retrieval handler: [app/mcp_server/kb_retrieval.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/kb_retrieval.py)
- MCP bootstrap registration: [app/mcp_server/bootstrap.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_server/bootstrap.py)
- MCP client retrieval method: [app/mcp_client/client.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/app/mcp_client/client.py)

### Tests

- Config tests: [tests/test_config.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_config.py)
- Health API tests: [tests/test_health.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_health.py)
- CSV ingestion tests: [tests/test_csv_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_csv_ingestion.py)
- MCP raw ingestion tests: [tests/test_mcp_raw_ingestion.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_mcp_raw_ingestion.py)
- MCP KB retrieval tests: [tests/test_mcp_kb_retrieval.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_mcp_kb_retrieval.py)
- Workflow planner tests: [tests/test_workflow_planner.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_workflow_planner.py)
- Workflow policy tests: [tests/test_workflow_policy.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_workflow_policy.py)
- Retry and human-review tests: [tests/test_workflow_retry_and_review.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_workflow_retry_and_review.py)
- Agent trace tests: [tests/test_agent_trace.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_agent_trace.py)
- Workflow state tests: [tests/test_workflow_state.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_workflow_state.py)
- Error endpoint tests: [tests/test_error_endpoint.py](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/tests/test_error_endpoint.py)

## Workflow Map

Current implemented workflow shape:

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
  Status: done

- Step 11: Update KB
  Status: done

## Next Task

The next implementation target is LangSmith instrumentation.

Immediate next tasks:

- Task 5.1: Add LangSmith configuration
- Task 5.2: Enable LangSmith tracing for the workflow
- Task 5.3: Add run metadata and tags
- Task 5.5: Add a frontend Trace tab

Expected result:

- LangGraph runs are visible in LangSmith
- LLM calls, planner branches, retries, and failures are traceable outside the local UI
- The frontend can link the current run to its LangSmith trace context
- developers can debug one run from LangSmith without relying only on console logs or the frontend

## Canonical References

- [docs/specification.md](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/docs/specification.md)
- [docs/technical-plan.md](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/docs/technical-plan.md)
- [docs/tasks.md](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/docs/tasks.md)
