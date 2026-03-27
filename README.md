# Incident Triaging and Resolutions

Agentic error triage app built with:

- Python 3.11
- FastAPI
- LangChain
- LangGraph
- ChromaDB
- MCP-style server/client integration
- React frontend

## Repo Layout

- `app/`: backend API, workflow, agents, MCP server/client, retrieval, normalization
- `frontend/`: local React UI
- `config/`: JSON config and KB seed data
- `docs/`: specification, plan, tasks, implementation tracker
- `tests/`: backend test suite

## Local Python Setup With uv

The repo now uses `uv.lock` for reproducible Python installs.

If you want `uv` to use your active environment:

```bash
source .venv311/bin/activate
UV_CACHE_DIR=/tmp/uv-cache uv sync --active --frozen --extra dev
```

If you want `uv` to manage its own project environment instead:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --frozen --extra dev
```

Note:

- `uv` prefers the project environment at `.venv`
- if you activate `.venv311`, use `--active`

## Environment Variables

Create a local `.env` in the repo root:

```bash
OPENAI_API_KEY=your-openai-key
TAVILY_API_KEY=your-tavily-key
```

Do not commit `.env`.

## Run the Backend

Start the API:

```bash
source .venv311/bin/activate
python -m uvicorn app.main:app --reload --port 8001
```

Production-style backend startup:

```bash
source .venv311/bin/activate
./scripts/start_backend.sh
```

Process one error with `curl`:

```bash
curl -X POST http://127.0.0.1:8001/api/v1/errors/process \
  -H "Content-Type: application/json" \
  -d '{"error_text":"[CANNOT_OPEN_SOCKET] Connection refused on localhost socket"}' | jq
```

## Run the Frontend

In a second terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

The frontend expects the backend on `http://127.0.0.1:8001`.

## Local Quality Checks

These match the Python CI job:

```bash
source .venv311/bin/activate
UV_CACHE_DIR=/tmp/uv-cache uv sync --active --frozen --extra dev
UV_CACHE_DIR=/tmp/uv-cache uv run black --check app tests
UV_CACHE_DIR=/tmp/uv-cache uv run isort --check-only app tests
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check app tests
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```

Frontend build check:

```bash
cd frontend
npm install
npm run build
```

## GitHub Actions

CI is defined in:

- `.github/workflows/workflow.yml`

It runs:

- Python dependency sync from `uv.lock`
- `black --check app tests`
- `isort --check-only app tests`
- `ruff check app tests`
- `pytest -q`
- frontend `npm run build`

## Azure Backend

Backend Azure App Service notes are in:

- `docs/azure_backend.md`
