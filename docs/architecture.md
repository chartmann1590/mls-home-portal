# Architecture

## Services

- `mls-home-portal` (FastAPI + static frontend)
- `scapling-bridge` (Scrapling API wrapper)

## Search Pipeline

`direct MLS -> Scrapling -> FlareSolverr-assisted scrape -> Apify`

## Backend Components

- `backend/app.py`: API routes and orchestration
- `backend/services/listings.py`: provider fallback strategy
- `backend/services/scapling_client.py`: scrape/parsing and detail extraction
- `backend/services/ollama_client.py`: affordability and AI summaries
- `backend/services/saved_data.py`: SQLite persistence

## Frontend

- `frontend/index.html`: UI shell and modal
- `frontend/app.js`: search, save, rerun, detail loading
- `frontend/styles.css`: responsive UI styling
