# Deployment Guide

This guide covers both local development and Azure App Service deployment for the current repository.

## 1. Local Development

### 1.1 Python environment

From the repo root:

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -e ".[dev]"
```

If you use `uv` instead:

```bash
source .venv311/bin/activate
UV_CACHE_DIR=/tmp/uv-cache uv sync --active --frozen --extra dev
```

### 1.2 Local environment variables

Create a local `.env` file in the repo root:

```bash
cp .env.example .env
```

Set at least:

```text
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
TAVILY_API_KEY=...
```

Optional:

```text
LANGSMITH_API_KEY=...
```

### 1.3 Local backend

Development mode:

```bash
source .venv311/bin/activate
python -m uvicorn app.main:app --reload --port 8001
```

Production-style local mode:

```bash
source .venv311/bin/activate
PORT=8001 ./scripts/start_backend.sh
```

Health check:

```bash
curl http://127.0.0.1:8001/api/v1/health
```

### 1.4 Local frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

This uses the Vite proxy and expects the backend on:

```text
http://127.0.0.1:8001
```

### 1.5 Local production-style frontend

Build and serve the frontend without the Vite dev server:

```bash
cd frontend
VITE_BACKEND_ORIGIN=http://127.0.0.1:8001 npm run build
./scripts/start_frontend.sh
```

Default production-style frontend URL:

```text
http://localhost:8080
```

If you use this mode, ensure backend CORS allows `http://localhost:8080` if the frontend is calling the backend directly.

### 1.6 Local quality checks

Python:

```bash
source .venv311/bin/activate
UV_CACHE_DIR=/tmp/uv-cache uv run black --check app tests
UV_CACHE_DIR=/tmp/uv-cache uv run isort --check-only app tests
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check app tests
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```

Frontend:

```bash
cd frontend
npm run build
```

## 2. Azure App Service Deployment Model

The current repository is designed for:

- one Azure App Service for the backend
- one Azure App Service for the frontend

The codebase remains shared. Runtime behavior changes only through environment variables and build settings.

## 3. Azure Backend Deployment

### 3.1 Azure backend app

Create a Linux Python App Service using:

- Python `3.11`

### 3.2 Backend startup command

Use this startup command in the Azure backend app:

```bash
./scripts/start_backend.sh
```

### 3.3 Backend Azure app settings

Set these in Azure App Service Application Settings:

Required:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `TAVILY_API_KEY`

Optional:

- `LANGSMITH_API_KEY`
- `INCIDENT_APP_CONFIG`
- `INCIDENT_APP_CONFIG_OVERRIDE`
- `WEB_CONCURRENCY`
- `WORKER_TIMEOUT`

Recommended override:

```text
INCIDENT_APP_CONFIG_OVERRIDE={"app":{"environment":"azure"},"deployment":{"cors_allowed_origins":["https://your-frontend-app.azurewebsites.net"]}}
```

### 3.4 Backend deployment workflow

The backend Azure workflow is:

- [.github/workflows/azure-backend-deploy.yml](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/.github/workflows/azure-backend-deploy.yml)

Required GitHub secrets:

- `AZURE_BACKEND_WEBAPP_NAME`
- `AZURE_BACKEND_WEBAPP_PUBLISH_PROFILE`

### 3.5 Backend verification

After deployment:

```text
https://<backend-app>.azurewebsites.net/api/v1/health
```

Then test:

```text
POST https://<backend-app>.azurewebsites.net/api/v1/errors/process
```

## 4. Azure Frontend Deployment

### 4.1 Azure frontend app

Create a Linux Node App Service using:

- Node `20`

### 4.2 Frontend build-time setting

Set the backend origin used at build time:

```text
VITE_BACKEND_ORIGIN=https://<backend-app>.azurewebsites.net
```

### 4.3 Frontend startup command

Use this startup command in the Azure frontend app:

```bash
./frontend/scripts/start_frontend.sh
```

### 4.4 Frontend deployment workflow

The frontend Azure workflow is:

- [.github/workflows/azure-frontend-deploy.yml](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/.github/workflows/azure-frontend-deploy.yml)

Required GitHub configuration:

Secrets:

- `AZURE_FRONTEND_WEBAPP_NAME`
- `AZURE_FRONTEND_WEBAPP_PUBLISH_PROFILE`

Repo variable:

- `AZURE_FRONTEND_BACKEND_ORIGIN`

### 4.5 Frontend verification

After deployment:

- open the frontend URL
- submit one error
- confirm browser requests go to the deployed backend URL

## 5. Storage Expectations

Current storage is documented in:

- [docs/storage_strategy.md](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/docs/storage_strategy.md)

Current reality:

- local filesystem storage is fine for local development
- local filesystem storage is acceptable for a single-instance Azure demo
- it is not production-safe for a scaled or durable Azure deployment

## 6. Recommended First Azure Rollout

Use this order:

1. Deploy backend App Service first.
2. Set backend application settings.
3. Verify `/api/v1/health`.
4. Deploy frontend App Service with the backend origin variable.
5. Open the frontend and run one end-to-end workflow.
6. Confirm CORS, API connectivity, and streaming behavior.

## 7. Current Limits

The app is Azure-ready for demo deployment, not yet hardened for production.

Main limits:

- local Chroma persistence
- local JSON raw and processed storage
- SQLite
- no shared durable storage across multiple app instances
