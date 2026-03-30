# Azure Backend Deployment

This backend is designed to run on Azure App Service as a Linux Python web app.

## Runtime Contract

- Python runtime: `3.11`
- App entrypoint: `app.main:app`
- Production server: `gunicorn` with `uvicorn.workers.UvicornWorker`
- Health endpoint: `/api/v1/health`

## Startup Command

Use this startup command in Azure App Service:

```bash
./scripts/start_backend.sh
```

The script reads these optional environment variables:

- `HOST`
- `PORT`
- `WEB_CONCURRENCY`
- `WORKER_TIMEOUT`
- `GRACEFUL_TIMEOUT`
- `KEEP_ALIVE`

Defaults:

- `HOST=0.0.0.0`
- `PORT=8000`
- `WEB_CONCURRENCY=2`
- `WORKER_TIMEOUT=300`
- `GRACEFUL_TIMEOUT=30`
- `KEEP_ALIVE=5`

## Required App Settings

Set these in Azure App Service Application Settings, not in tracked files:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `TAVILY_API_KEY`

Optional:

- `LANGSMITH_API_KEY`
- `INCIDENT_APP_CONFIG`
- `INCIDENT_APP_CONFIG_OVERRIDE`

## Example Azure Override

This keeps the same codebase and adjusts only runtime settings:

```text
INCIDENT_APP_CONFIG_OVERRIDE={"app":{"environment":"azure"},"deployment":{"cors_allowed_origins":["https://your-ui.azurewebsites.net"]}}
```

## Local Production-Style Check

Run the backend locally with the same production server used by Azure:

```bash
source .venv311/bin/activate
./scripts/start_backend.sh
```

Then verify the health endpoint:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Notes

- The streaming workflow endpoint can run for longer than Gunicorn's default timeout. The startup script sets a longer worker timeout so the request can finish under App Service and local production-style runs.
- Local filesystem storage is acceptable for a demo deployment but is not a production-grade scaling strategy for Chroma, raw records, or processed records.
- Azure frontend deployment is handled separately from the backend.
