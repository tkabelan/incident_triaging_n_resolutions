# Local React Frontend Plan

## Goal

Build a simple local React frontend that lets a user paste one error, run the agent, and view the result in a readable, non-JSON format.

## Runtime Shape

- Frontend stack: React + Vite
- Local backend: FastAPI at `http://127.0.0.1:8000`
- Frontend dev server: `http://127.0.0.1:5173`

## Core User Flow

1. User pastes an error into a text area.
2. User clicks `Analyze Error`.
3. Frontend sends `POST /api/v1/errors/process`.
4. Frontend receives `agent_trace`, classification, verification, and KB update info.
5. Frontend renders the result in sections instead of raw JSON.

## UI Sections

### 1. Input Panel

- Large text area for the error
- `Analyze Error` button
- Loading state while the request is running

### 2. Final Outcome Card

- Final status
- Classification
- Resolution
- Outcome source
- Plain-language branch explanation

### 3. Agent Steps Timeline

- Chroma DB lookup
- Planner decision
- Primary LLM
- Verification LLM
- Web search
- Refinement LLM
- Reflection
- Human review

Each step should show:

- status
- confidence if available
- short reason
- whether it ran or was skipped

### 4. Scores Panel

- Classification confidence
- Verification confidence
- Refinement confidence if present
- Web search result count

### 5. Web Evidence Panel

- Search result title
- URL
- score
- short content excerpt

### 6. KB Update Panel

- KB update triggered: yes or no
- KB update reference
- KB update reason

## API Contract To Use

Use:

- `POST /api/v1/errors/process`

Important response fields:

- `agent_trace.final_status`
- `agent_trace.outcome_source`
- `agent_trace.classification`
- `agent_trace.resolution`
- `agent_trace.branch_explanation`
- `agent_trace.kb_update_triggered`
- `agent_trace.kb_update_reference`
- `agent_trace.kb_update_reason`
- `agent_trace.stages`

## Recommended Component Split

- `ErrorInputForm`
- `OutcomeSummary`
- `AgentTimeline`
- `ScoreCards`
- `WebEvidenceList`
- `KbUpdateStatus`

## Local Development Steps

1. Start FastAPI locally with `uvicorn app.main:app --reload`.
2. Create a Vite React app under `frontend/`.
3. Add a small API client for `POST /api/v1/errors/process`.
4. Build the readable page around the `agent_trace`.
5. Add simple error and loading states.

## Important UX Rules

- Never show raw JSON by default.
- Use labels like `Passed`, `Skipped`, `Needs Human Review`.
- Highlight confidence scores visually.
- Show web links as clickable items.
- Show the branch explanation near the top so non-technical users understand what happened.
