# Incident Management and Resolution Technical Plan

## 1. Objective

Build a production-oriented agentic RAG system that:

- reads error logs from CSV first
- can later switch to a data-lake source without major code changes
- grounds errors against a knowledge base
- uses a primary LLM to classify the error and propose a resolution
- uses a secondary LLM to verify that answer
- falls back to web search when verification is not satisfactory
- updates the knowledge base with approved outcomes

The implementation should use:

- Python 3.11
- LangChain
- LangGraph
- ChromaDB
- FastAPI
- MCP-style server/client boundaries

## 2. Technical Principles

These are non-negotiable for the implementation:

1. JSON config
   - No hardcoded paths, URLs, model names, collection names, or environment values.
   - Use config files and validated config models.

2. Python logging
   - No `print` statements.
   - Log ingestion, retrieval, LLM calls, verification, fallback search, and KB update steps.

3. Raw / processed separation
   - Raw layer stores untouched source records and documents.
   - Processed layer stores normalized, validated, workflow-ready artifacts.

4. Modular functions and services
   - Separate config, ingestion, normalization, retrieval, classification, verification, search, and KB update logic.

5. Production-first behavior
   - Typed contracts
   - retries and timeouts
   - structured errors
   - auditable workflow runs

## 3. Architecture Style

Use a modular monolith for the MVP with two internal runtime surfaces:

- FastAPI for application APIs
- MCP server for tool/resource access used by the agent workflow

Why:

- keeps the first version deployable and debuggable
- avoids premature service splitting
- preserves a clean boundary between orchestration logic and operational capabilities

## 4. Proposed Architecture

### Core Components

1. FastAPI Application
   - health/readiness endpoints
   - API endpoints to submit errors and inspect results
   - optional endpoints for manual KB ingestion and workflow replay

2. LangGraph Workflow Layer
   - stateful graph for end-to-end error processing
   - branching for verification pass/fail
   - auditable node execution

3. LangChain Client Layer
   - calls MCP tools/resources
   - wraps LLM invocation and prompt contracts
   - centralizes tool access for workflow nodes

4. MCP Server
   - exposes capabilities for:
     - raw error ingestion
     - KB retrieval
     - verification
     - web search
     - KB update

5. ChromaDB Knowledge Layer
   - stores vectorized KB artifacts
   - supports similarity search and metadata filtering

6. Persistent Storage Layer
   - stores raw errors
   - stores processed errors
   - stores workflow runs and audit records
   - stores KB update history

## 5. MCP Design

The agentic workflow should not directly own every operational integration. It should call an MCP surface through a LangChain client.

### MCP Server Responsibilities

- expose typed tools/resources
- isolate integration logic from workflow nodes
- provide a stable contract for future replacement or extension

### Initial MCP Capabilities

- `error.ingest_raw`
- `kb.retrieve_context`
- `verification.verify_resolution`
- `search.web`
- `kb.update_entry`

### MCP Contract Rules

- every request and response is typed
- every tool/resource call is logged
- failures return structured error objects
- source traceability is preserved in responses

## 6. High-Level Workflow

### End-to-End Flow

1. Read error record from CSV.
2. Save the raw record unchanged.
3. Normalize the error into processed form.
4. Retrieve grounding context from the KB through MCP.
5. Use the primary LLM to classify the error and propose a resolution.
6. Verify the result with a second LLM through MCP.
7. If verification fails or confidence is low, call web search through MCP.
8. Merge KB and web evidence.
9. Re-run or refine the classification and resolution.
10. Persist the final result and update the KB through MCP.

### Verification Branching

- If verification passes:
  - persist result
  - update KB

- If verification fails:
  - run fallback search
  - refine answer
  - persist result with fallback marker
  - update KB only if the final result is approved by policy

## 7. Data Layers

### Raw Layer

Stores:

- original CSV rows
- original uploaded KB documents
- original search results if retention is required

Purpose:

- audit
- replay
- debugging

### Processed Layer

Stores:

- normalized error records
- normalized KB chunks
- verified classification and resolution outputs
- workflow-ready evidence objects

Purpose:

- retrieval
- prompting
- reporting

## 8. Storage Plan

### ChromaDB

Use ChromaDB only for retrieval-oriented knowledge.

Collections:

- `errors`
- `resolutions`
- `kb_articles`
- `runbooks`

Use metadata such as:

- source type
- system name
- service name
- error category
- created date
- verification status
- tags

### Operational Persistence

Use a durable store for:

- workflow runs
- audit records
- raw/processed storage metadata
- KB update records

Recommended choice:

- PostgreSQL for transactional state

Reason:

- ChromaDB should not be the source of truth for workflow state or audits.

## 9. Module Structure

Recommended structure:

- `app/api`
- `app/core`
- `app/config`
- `app/logging`
- `app/ingestion`
- `app/normalization`
- `app/kb`
- `app/retrieval`
- `app/verification`
- `app/search`
- `app/workflows`
- `app/mcp_server`
- `app/mcp_client`
- `app/storage`
- `app/schemas`
- `tests`

### Module Responsibilities

`app/ingestion`
- CSV reading
- raw error capture

`app/normalization`
- error cleaning
- field extraction

`app/kb`
- KB ingestion
- KB update
- ChromaDB indexing

`app/retrieval`
- KB retrieval
- evidence shaping

`app/verification`
- second-model verification logic
- verification policy checks

`app/search`
- fallback web search handling
- search result normalization

`app/mcp_server`
- MCP tool/resource registration
- MCP transport and handlers

`app/mcp_client`
- LangChain-integrated MCP client
- reusable wrapper for workflow nodes

`app/workflows`
- LangGraph state
- graph nodes
- branching logic

## 10. LangGraph Design

Use LangGraph for deterministic orchestration.

### Proposed MVP Graph

Nodes:

1. `ingest_error`
2. `normalize_error`
3. `retrieve_kb_context`
4. `classify_and_resolve`
5. `verify_result`
6. `web_search_fallback`
7. `merge_evidence`
8. `refine_result`
9. `persist_result`
10. `update_kb`

### Branching Logic

- `verify_result` decides whether to continue directly to persistence or to fallback search.
- `update_kb` runs only after policy checks and successful finalization.

### Graph State

Include:

- workflow id
- raw error reference
- processed error
- retrieved KB evidence
- primary result
- verification result
- web evidence
- refined result
- final result
- KB update status
- audit references

### Graph Rules

- every node uses typed inputs and outputs
- LLM outputs must be schema-validated
- evidence must carry source references
- workflow state must be persistable for replay/debugging

## 11. LangChain Client Design

LangChain should serve two roles:

- manage LLM interactions
- integrate with MCP capabilities in reusable workflow-friendly wrappers

### Client Responsibilities

- connect to MCP server
- invoke MCP capabilities from workflow nodes
- package evidence for prompts
- parse structured LLM outputs

### Why This Matters

Without this layer, the workflow nodes will become tightly coupled to transport and tool details. The client keeps node logic focused on orchestration.

## 12. API Plan

Expose versioned endpoints under `/api/v1`.

### Initial Endpoints

- `GET /api/v1/health`
- `GET /api/v1/readiness`
- `POST /api/v1/errors/process`
- `GET /api/v1/errors/{workflow_id}`
- `POST /api/v1/kb/documents`

### API Behavior

- return structured results, not free-form text only
- include verification status
- include whether fallback search was used
- include source evidence references where appropriate

## 13. Configuration Plan

Configuration should cover:

- input file locations
- future data-lake settings
- FastAPI host/port
- database settings
- ChromaDB settings
- collection names
- embedding provider settings
- primary LLM settings
- secondary verification LLM settings
- web search settings
- logging settings

All config should be validated on startup.

## 14. Logging and Audit Plan

Log these events at minimum:

- config load
- app startup/shutdown
- CSV ingestion start/end
- raw save success/failure
- normalization success/failure
- KB retrieval requests/results
- primary LLM invocation
- verification invocation and outcome
- web fallback start/end
- KB update start/end
- workflow completion/failure

Audit records should capture:

- raw input reference
- evidence references
- model outputs
- verification outcome
- fallback usage
- final resolution

## 15. Web Search Policy

Web search should only run when:

- verification fails
- verification confidence is below threshold
- evidence from KB is insufficient

Search results must be:

- attributed to source
- stored or referenced for audit as required
- clearly marked as external evidence

## 16. Testing Strategy

### Unit Tests

- config loading
- normalization
- retrieval shaping
- verification decision logic
- MCP request/response validation

### Integration Tests

- FastAPI endpoints
- ChromaDB indexing and retrieval
- MCP server/client interaction
- persistence of workflow and audit data

### Workflow Tests

- verification-pass path
- verification-fail then search path
- KB update success/failure path

## 17. Delivery Phases

### Phase 1

- project structure
- dependencies
- JSON config
- logging
- FastAPI skeleton
- MCP server skeleton
- LangChain MCP client skeleton
- raw/processed storage scaffolding

### Phase 2

- CSV ingestion
- KB indexing
- retrieval
- primary classification/resolution
- verification
- web fallback
- LangGraph workflow
- KB update
- audit and end-to-end tests

## 18. Risks and Mitigations

### Risk: weak KB retrieval

Mitigation:

- enforce metadata quality
- keep KB collections separated by source type
- test retrieval with realistic fixtures early

### Risk: verification model disagreement is noisy

Mitigation:

- use typed verification output
- define explicit pass/fail criteria
- route uncertain cases through fallback search

### Risk: MCP layer adds complexity

Mitigation:

- keep first MCP capability set small
- use typed contracts
- test client/server interaction independently

### Risk: web search introduces low-quality evidence

Mitigation:

- only use it on failed verification paths
- keep source attribution
- treat web evidence as supplemental, not authoritative by default

## 19. Recommended Build Order

1. project scaffold
2. config and logging
3. FastAPI and MCP skeletons
4. raw/processed storage
5. CSV ingestion
6. ChromaDB KB setup
7. retrieval service
8. primary LLM classification/resolution
9. verification service
10. web fallback
11. LangGraph assembly
12. KB update and audit hardening

## 20. Working Summary

The right MVP architecture is a modular monolith with FastAPI for API access, LangGraph for orchestration, LangChain for LLM and MCP client integration, ChromaDB for KB retrieval, PostgreSQL for operational state, and an MCP server exposing retrieval, verification, search, and KB update capabilities.

This shape matches the actual workflow you described and keeps the system simple enough to build step by step while still being suitable for production-oriented operation.
