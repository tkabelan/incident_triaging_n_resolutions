# Storage Strategy

This project currently uses local filesystem storage for all persisted state.

## Current Storage Layout

- Raw error records: `data/raw`
- Processed error records: `data/processed`
- SQLite app database: `data/app.db`
- Chroma persistence: `data/chroma`

These paths are configured in [config/config.json](/Users/theivendrankabelan/Documents/python_scripts/incident_triaging_n_resolutions/config/config.json).

## Local Development

Local development uses the filesystem directly and this is the intended default:

- raw records are written as JSON files
- processed records are written as JSON files
- SQLite runs from a local file
- Chroma persists vectors to a local directory

This is appropriate for:

- local feature work
- local debugging
- local demos
- repeatable development runs on one machine

## Azure Demo Deployment

For a single-instance Azure App Service demo, the same storage approach is acceptable with clear limits:

- the app can still write to the local app filesystem
- Chroma can still persist to a local directory
- raw and processed records can still be written locally

This is acceptable only for:

- internal demos
- short-lived evaluation environments
- single-instance deployments where data durability is not critical

## Limitations of Local Filesystem Storage on Azure

This storage model is not production-safe on Azure App Service.

Main reasons:

- multiple app instances do not share local state safely
- instance restarts or redeployments can invalidate local runtime state assumptions
- Chroma local persistence is not a scalable shared vector store
- local JSON record storage is not durable enough for operational workloads
- SQLite is not an appropriate multi-instance production database

## Production-Grade Direction

If this app moves beyond demo scope, storage should be split by responsibility:

- raw records:
  - Azure Blob Storage or ADLS
- processed records:
  - Azure Blob Storage, ADLS, or a transactional database depending on access patterns
- relational app state:
  - Azure SQL Database or PostgreSQL
- vector storage:
  - a managed vector-capable database or a production-grade shared vector store

## Current Recommendation

Use the current storage layout for:

- local development
- local testing
- Azure App Service demos

Do not treat the current storage layout as production-ready for:

- scaled deployments
- high-durability incident workflows
- multi-instance App Service setups

## Operational Guidance

For the current codebase:

- keep `data/` out of git
- treat `data/` as environment-local state
- expect Azure demo data to be environment-specific and disposable
- rebuild or reseed Chroma as needed for demo environments
