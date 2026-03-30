# Azure Frontend Deployment

This frontend is designed to run on Azure App Service as a separate static React app.

## Runtime Contract

- Node runtime: `20` or newer
- Build command: `npm install && npm run build`
- Production startup: `./frontend/scripts/start_frontend.sh`
- Static output directory: `frontend/dist`

## Required Build-Time Setting

Set the backend origin before building the frontend:

```text
VITE_BACKEND_ORIGIN=https://your-backend-app.azurewebsites.net
```

The production build uses this value directly for API requests.

## Local Azure-Like Check

Build the frontend against a non-local backend origin:

```bash
cd frontend
VITE_BACKEND_ORIGIN=https://example-backend.azurewebsites.net npm run build
```

Serve the built app locally:

```bash
cd frontend
./scripts/start_frontend.sh
```

Defaults:

- `PORT=8080`

## Notes

- During local development, `npm run dev` still uses the Vite dev proxy.
- In production, the frontend calls the configured backend origin directly and does not rely on a local proxy.
