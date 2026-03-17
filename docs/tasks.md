# Incident Management and Resolution Tasks

This task list reflects the current simplified product direction:

- Input is an error log feed, starting with CSV files
- In production, the same flow may read from a data lake
- The implementation should follow an MCP-style architecture with:
  - an MCP server exposing tools/resources for ingestion, KB lookup, verification, and search
  - a LangChain-based client that uses those MCP capabilities inside the agentic workflow
- The system reads errors and uses agentic RAG to:
  - ground against the knowledge base
  - classify the error with an LLM
  - propose a resolution
  - verify that result with a second LLM
  - fall back to web search if verification is not satisfactory
  - update the knowledge base with approved outcomes

This document is intentionally simple for now. It is sequenced so each task can be built and tested in isolation.

## Delivery Rules

- Use JSON config for all environment-specific settings. No hardcoded paths, URLs, model names, or storage settings.
- Use Python logging only. No `print` statements in application code.
- Preserve raw and processed data separately.
- Keep functions and services modular.
- Build for production from the start: validation, logging, retries, error handling, and testability.
- Keep MCP contracts explicit and typed so the server and client can evolve safely.

## Current End-to-End Workflow

1. Read new error records from CSV.
2. Store raw error input.
3. Normalize the error into processed form.
4. Search the KB for grounding context.
5. The LangChain client calls MCP tools/resources for grounding context.
6. Ask the primary LLM to classify the issue and suggest a resolution.
7. Ask a secondary LLM to verify the classification and resolution.
8. If verification fails or confidence is too low, perform web search for more evidence through MCP.
9. Re-run or refine the result using the new evidence.
10. Store the final answer and update the KB.

## Phase 1: Project Initialization and Core Structure

Goal:

Create the production-ready foundation for config, logging, storage, API, modular services, and the MCP server/client split.

### Task 1.1: Create the backend project structure

Scope:

- Create the base Python package layout.
- Add folders for API, config, logging, ingestion, KB, agents, workflows, verification, web search, storage, and tests.

Acceptance criteria:

- The project imports cleanly.
- The structure supports isolated implementation of each workflow step.

Test in isolation:

- Import a sample module from the new package structure.

### Task 1.2: Define project dependencies for Python 3.11

Scope:

- Add project metadata and dependency management.
- Include FastAPI, LangChain, LangGraph, ChromaDB, test tools, and logging/config dependencies.

Acceptance criteria:

- A clean environment can install the project successfully.

Test in isolation:

- Install dependencies and import the main libraries.

### Task 1.3: Add JSON configuration system

Scope:

- Create `config.json` and typed config loading.
- Support configuration for input paths, vector DB, embeddings, LLMs, web search, and storage.

Acceptance criteria:

- No operational values are hardcoded.
- Invalid config fails fast at startup.

Test in isolation:

- Load valid config and reject invalid config.

### Task 1.4: Add centralized Python logging

Scope:

- Create logging setup for app startup, ingestion, retrieval, LLM calls, verification, web search, and KB updates.

Acceptance criteria:

- All major workflow steps produce logs.
- Logs are structured enough to trace failures in production.

Test in isolation:

- Run the app and verify logs for startup and one sample service call.

### Task 1.5: Create FastAPI app skeleton

Scope:

- Add the FastAPI app factory.
- Add health and readiness endpoints.

Acceptance criteria:

- The service starts and returns health responses.

Test in isolation:

- Call the health endpoint with a test client.

### Task 1.6: Create MCP server skeleton

Scope:

- Add the MCP server package and startup entrypoint.
- Define the initial server structure for tools and resources related to ingestion, KB, verification, and search.

Acceptance criteria:

- The MCP server starts successfully.
- The server structure is cleanly separated from the FastAPI app.

Test in isolation:

- Start the MCP server and verify it initializes without runtime errors.

### Task 1.7: Create LangChain MCP client skeleton

Scope:

- Add the LangChain-side client layer that can connect to the MCP server.
- Define how the workflow will invoke MCP tools/resources from application services.

Acceptance criteria:

- The client can connect to the MCP server.
- The interface is modular and reusable by workflow nodes.

Test in isolation:

- Run a simple client connection test against the MCP server.

### Task 1.8: Define initial MCP contracts

Scope:

- Define the first set of MCP-exposed capabilities and their typed request/response contracts.
- Start with KB retrieval, raw error ingestion, verification, and web search interfaces.

Acceptance criteria:

- MCP request and response shapes are explicit and validated.
- Contracts are simple enough for early iteration.

Test in isolation:

- Validate example MCP requests and responses against typed schemas.

### Task 1.9: Add storage scaffolding for raw and processed data

Scope:

- Define where raw error inputs are stored.
- Define where processed normalized records are stored.

Acceptance criteria:

- Raw and processed records are clearly separated.
- The separation works for CSV now and can evolve to a data-lake source later.

Test in isolation:

- Save one raw record and one processed record and retrieve both.

### Task 1.10: Create base schemas for error records and KB entries

Scope:

- Add Pydantic models for raw errors, normalized errors, classification output, resolution output, verification output, and KB records.

Acceptance criteria:

- All workflow steps exchange typed data.

Test in isolation:

- Validate correct and incorrect payload examples.

### Task 1.11: Add database or persistent store scaffolding for audit records

Scope:

- Add the minimum persistence needed for workflow runs, verification results, and KB update tracking.

Acceptance criteria:

- Each processed error can be traced through the workflow.

Test in isolation:

- Persist and retrieve a sample workflow run record.

## Phase 2: Agentic RAG With Verification and Fallback Search

Goal:

Implement the actual error-processing loop: ingest, ground, classify, resolve, verify, search if needed, and update the KB.

### Task 2.1: Build CSV error ingestion service

Scope:

- Read error logs from CSV input.
- Convert each row into a raw error record.

Acceptance criteria:

- CSV ingestion handles expected columns and malformed rows safely.

Test in isolation:

- Ingest a sample CSV and verify the parsed raw records.

### Task 2.2: Expose raw error ingestion through MCP

Scope:

- Add an MCP tool or resource that accepts raw error input for downstream processing.

Acceptance criteria:

- The ingestion capability is available through the MCP server.
- The contract matches the typed raw error schema.

Test in isolation:

- Call the MCP ingestion capability from the client and verify the response.

### Task 2.3: Store raw error records

Scope:

- Persist the untouched input error records before any transformation.

Acceptance criteria:

- Original error data is retained for audit and replay.

Test in isolation:

- Ingest sample data and verify raw storage remains unchanged.

### Task 2.4: Normalize errors into processed records

Scope:

- Clean and standardize the ingested error records.
- Extract useful fields such as timestamp, source system, error message, and identifiers.

Acceptance criteria:

- The processed record is stable and suitable for retrieval and LLM prompting.

Test in isolation:

- Normalize sample rows with missing and complete fields.

### Task 2.5: Create KB schema and ChromaDB collection setup

Scope:

- Define KB document types and metadata.
- Initialize ChromaDB collections for incidents/errors, resolutions, and supporting knowledge.

Acceptance criteria:

- Collections are created or reused idempotently.

Test in isolation:

- Initialize the vector store and verify the required collections exist.

### Task 2.6: Build KB ingestion and indexing pipeline

Scope:

- Add the ability to insert KB documents into ChromaDB with embeddings and metadata.

Acceptance criteria:

- KB items are searchable by similarity and metadata.

Test in isolation:

- Index sample KB entries and retrieve them successfully.

### Task 2.7: Expose KB retrieval through MCP

Scope:

- Add an MCP capability for KB retrieval so the client can request grounding context from the server.

Acceptance criteria:

- The MCP server returns retrieval results with source ids and metadata.

Test in isolation:

- Request grounding context through the client and verify the result contract.

### Task 2.8: Implement grounding retrieval service

Scope:

- Given a normalized error, retrieve relevant KB entries from ChromaDB.

Acceptance criteria:

- Retrieval returns evidence with source ids, metadata, and similarity scores.

Test in isolation:

- Query the KB with a sample error and verify relevant grounding results.

### Task 2.9: Implement primary LLM classification and resolution service

Scope:

- Use the normalized error plus retrieved KB context to classify the issue and propose a resolution.

Acceptance criteria:

- Output is structured.
- The response clearly includes classification, reasoning, resolution, and evidence references.

Test in isolation:

- Mock the LLM and verify structured output parsing.

### Task 2.10: Expose verification through MCP

Scope:

- Add an MCP capability for secondary verification so the workflow can call it through the shared protocol layer.

Acceptance criteria:

- Verification can be invoked through the MCP client.
- The response includes pass/fail, confidence, and explanation fields.

Test in isolation:

- Trigger verification through the client with mocked server behavior.

### Task 2.11: Implement secondary LLM verification service

Scope:

- Send the primary result and evidence to a second LLM for verification.
- Return pass/fail, confidence, and disagreement reasons.

Acceptance criteria:

- Verification is explicit and schema-validated.
- Low-confidence or conflicting results are surfaced clearly.

Test in isolation:

- Mock verification responses for pass and fail cases.

### Task 2.12: Expose web search through MCP

Scope:

- Add an MCP capability that performs web search when verification is not satisfactory.

Acceptance criteria:

- Search is available through the shared MCP server instead of being embedded directly in workflow logic.

Test in isolation:

- Call the search capability through the client with a sample query.

### Task 2.13: Add web search fallback service

Scope:

- If verification fails, run web search to gather additional supporting evidence.

Acceptance criteria:

- Search is triggered only when verification criteria are not met.
- Search results are logged and attached to the workflow.

Test in isolation:

- Force verification failure and verify the search path is executed.

### Task 2.14: Add evidence merge step after web search

Scope:

- Merge KB grounding and web search evidence into one context package for a refined answer.

Acceptance criteria:

- The merged evidence remains traceable by source.

Test in isolation:

- Combine retrieved KB results and web results into one structured evidence object.

### Task 2.15: Re-run or refine classification and resolution after fallback search

Scope:

- Use the expanded evidence set to produce a better final answer when the first attempt was not verified.

Acceptance criteria:

- The workflow can produce a revised result after search.
- The system records whether the answer came from direct KB grounding or fallback refinement.

Test in isolation:

- Simulate failed verification followed by successful refinement.

### Task 2.16: Expose KB update through MCP

Scope:

- Add an MCP capability for writing approved outcomes back to the knowledge base.

Acceptance criteria:

- KB update requests and responses are typed and auditable.

Test in isolation:

- Send a KB update request through the client and verify a successful write path.

### Task 2.17: Implement KB update service

Scope:

- Save approved final classifications and resolutions back into the KB.

Acceptance criteria:

- KB updates include metadata, source traceability, and timestamps.
- The update path supports future reuse during retrieval.

Test in isolation:

- Insert a finalized resolution into the KB and retrieve it later.

### Task 2.18: Build the LangGraph workflow

Scope:

- Connect ingestion context, MCP-based KB retrieval, primary LLM, MCP-based verification, MCP-based fallback search, refinement, and MCP-based KB update into one graph.

Acceptance criteria:

- The graph can run end-to-end for one error record.
- Each node has typed input/output.

Test in isolation:

- Execute the workflow with fixture data through pass and fail paths.

### Task 2.19: Integrate the LangChain client with the workflow

Scope:

- Use the LangChain client layer inside the workflow nodes so MCP interactions are centralized and reusable.

Acceptance criteria:

- Workflow nodes do not duplicate direct MCP connection logic.

Test in isolation:

- Execute a workflow node that retrieves KB context via the shared client.

### Task 2.20: Add API endpoint to process errors

Scope:

- Expose an API that triggers processing of one or more error records.

Acceptance criteria:

- The API returns structured workflow results.
- The response shows whether web fallback was required.

Test in isolation:

- Submit sample error input and verify the response contract.

### Task 2.21: Add audit trail for each workflow run

Scope:

- Record inputs, retrieved evidence, primary output, verification output, fallback activity, and final KB update status.

Acceptance criteria:

- Every final resolution is fully traceable.

Test in isolation:

- Run the workflow and verify a complete audit record exists.

### Task 2.22: Add baseline end-to-end tests

Scope:

- Create tests for the main happy path and the verification-failure fallback path.

Acceptance criteria:

- The core workflow is regression-testable.

Test in isolation:

- Run both end-to-end scenarios with fixtures.

## Suggested Starting Point

Start with these tasks first:

1. Task 1.1: Create the backend project structure
2. Task 1.2: Define project dependencies for Python 3.11
3. Task 1.3: Add JSON configuration system
4. Task 1.4: Add centralized Python logging

These create the base needed for the rest of the workflow.

## Definition of Done

A task is done only when:

- the code is implemented
- config is externalized
- logging is present
- raw and processed separation is preserved where relevant
- the task can be tested in isolation
- failure behavior is explicit

## Phase 3: Full Agentic App

Goal:

Move from a workflow-driven prototype to a truly agentic app where planning, tool choice, branching, retries, and learning are explicit and stateful.

### Task 3.1: Replace the custom workflow with a LangGraph graph

Scope:

- Move the orchestration in `app/workflows/error_processing.py` into LangGraph nodes and edges.
- Preserve the existing end-to-end behavior while making state transitions explicit.

Acceptance criteria:

- The flow runs as a LangGraph graph, not only as custom Python branching.
- Node transitions are traceable and testable.

Test in isolation:

- Execute the graph for a single error and verify node order and transitions.

### Task 3.2: Define a first-class graph state model

Scope:

- Create a single state object for raw input, normalization, taxonomy, retrieval evidence, classification, verification, web search, refinement, KB updates, and audit data.

Acceptance criteria:

- All nodes read and write through the shared state model.

Test in isolation:

- Validate state transitions across multiple graph nodes.

### Task 3.3: Expose KB retrieval through MCP and use it inside the graph

Scope:

- Remove direct retrieval calls from the workflow layer.
- Use MCP for KB retrieval in the same way as verification and web search.

Acceptance criteria:

- The graph uses MCP tools consistently for tool-backed operations.

Test in isolation:

- Retrieve KB evidence through the MCP client inside a graph run.

### Task 3.4: Add a planner/decision node

Scope:

- Introduce a decision node that decides the next action based on graph state.
- Decisions include:
  - resolve from KB
  - classify with LLM
  - verify
  - web search
  - refine
  - escalate to human review

Acceptance criteria:

- Decisioning is explicit and not spread across unrelated code branches.

Test in isolation:

- Run different states through the planner and verify the chosen next action.

### Task 3.5: Separate policy from reasoning

Scope:

- Move thresholds and operational rules into config/policy functions.
- Examples:
  - direct KB match threshold
  - verification confidence threshold
  - max retry count
  - web-search trigger rules

Acceptance criteria:

- Policy can be changed without rewriting core reasoning code.

Test in isolation:

- Verify that threshold changes alter graph behavior correctly.

### Task 3.6: Add retry and reflection behavior

Scope:

- Add one retry path for failed classification/verification where appropriate.
- Add a reflection step that can simplify prompts or alter search strategy on failure.

Acceptance criteria:

- The graph can recover from transient or weak-result scenarios without hard-failing immediately.

Test in isolation:

- Simulate a first-pass failure and verify the retry/reflection branch runs.

### Task 3.7: Add a human-review exit path

Scope:

- Define a terminal state for low-confidence or conflicting outcomes.
- Return the best current answer plus explicit uncertainty and recommended human action.

Acceptance criteria:

- The system can stop safely when it should not continue autonomously.

Test in isolation:

- Feed a low-confidence state and verify the graph exits to review.

### Task 3.8: Expand KB memory and learning signals

Scope:

- Store not only final resolutions but also:
  - failed hypotheses
  - verification outcomes
  - useful web evidence
  - whether the answer came from KB, LLM, or refined search

Acceptance criteria:

- The KB becomes a reusable memory surface, not just a resolution store.

Test in isolation:

- Verify learned metadata is written and retrievable later.

### Task 3.9: Add agent trace output for frontend consumption

Scope:

- Return a clean frontend-friendly trace of what the agent did:
  - which tools were used
  - what was skipped
  - what confidence each stage produced
  - final answer source

Acceptance criteria:

- A frontend can display the agent reasoning path without parsing raw logs.

Test in isolation:

- Run a single error and verify the response includes a structured agent trace.

### Task 3.10: Add FastAPI endpoint for single-error interactive use

Scope:

- Add an API endpoint that accepts one error text and returns the agent trace plus classification and resolution.

Acceptance criteria:

- The endpoint is suitable for wiring into the future frontend input field.

Test in isolation:

- Call the endpoint with one error and verify the response contract.

## Next Focus

The backend agentic phase is now in place. The next implementation phase should be a simple frontend MVP.

## Phase 4: Frontend MVP

Goal:

Build a simple local React frontend that lets a user paste one error, run the existing backend agent, and understand the result without reading raw JSON.

### Task 4.1: Create the frontend app scaffold

Scope:

- Create a React app under `frontend/`.
- Use a local dev setup that runs beside the FastAPI backend.

Acceptance criteria:

- The frontend starts locally.
- A basic page shell renders.

Test in isolation:

- Start the frontend dev server and load the home page.

### Task 4.2: Add a small typed API client

Scope:

- Add a frontend API module for `POST /api/v1/errors/process`.
- Keep request and response handling isolated from components.

Acceptance criteria:

- The frontend can call the backend endpoint successfully.
- API errors are surfaced clearly.

Test in isolation:

- Submit a sample error and verify the parsed response shape.

### Task 4.3: Build the input and submit flow

Scope:

- Add a large error text area.
- Add an `Analyze Error` button and loading state.

Acceptance criteria:

- A user can submit one error from the UI.
- Duplicate submits are prevented while the request is in flight.

Test in isolation:

- Submit a sample error and verify loading, success, and failure states.

### Task 4.4: Build the readable outcome summary

Scope:

- Render final status, classification, resolution, outcome source, and branch explanation.
- Keep the layout readable for non-technical users.

Acceptance criteria:

- A user can understand the final result without opening raw JSON.

Test in isolation:

- Render a mocked successful response and verify the visible summary fields.

### Task 4.5: Build the agent steps timeline

Scope:

- Render the main agent stages in order.
- Show pass, fail, skipped, or not-run clearly.

Acceptance criteria:

- A user can tell which stages ran and why.
- Confidence and reason fields are shown when present.

Test in isolation:

- Render mocked traces for direct-KB, verified, and human-review paths.

### Task 4.6: Build score, evidence, and KB panels

Scope:

- Render classification and verification confidence.
- Render web-search results with title, score, snippet, and link.
- Render KB update status and reference.

Acceptance criteria:

- Scores and supporting evidence are visible in a readable format.

Test in isolation:

- Render mocked traces with web results and KB update details.

### Task 4.7: Add simple UX polish for local demo use

Scope:

- Add lightweight styling, spacing, and status colors.
- Add empty, loading, and API error states.

Acceptance criteria:

- The page is readable on desktop and mobile.
- The frontend feels coherent enough for local demo use.

Test in isolation:

- Manually verify success, loading, error, and human-review states.
