# MLS Home Portal

AI-assisted single-family home search portal that integrates:

- `llama3.2` via Ollama for affordability and listing summaries
- direct MLS API (optional)
- Scrapling bridge scraping fallback
- FlareSolverr fallback for anti-bot pages
- Apify fallback (optional)

## Core Features

- Search by area/ZIP + budget and affordability profile
- Per-listing AI summaries and fit analysis
- Listing detail modal data API (photos, description, realtor info)
- Saved searches (criteria-only, reruns live)
- Saved homes bookmarks

## Default Local Access

- App URL: `http://localhost:8088`
- Health: `http://localhost:8088/health`
