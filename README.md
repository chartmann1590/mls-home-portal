# MLS AI Home Search Portal

Web portal for single-family home discovery using:
- Area + max budget input
- AI affordability analysis via Ollama on `bhumc-av`
- Listing pipeline: direct MLS API first, then Scapling (with optional FlareSolverr), then Apify fallback
- Saved searches (criteria-only) and saved homes bookmarks

## Documentation
- `docs/` for full project docs
- GitHub Pages is published from `mkdocs.yml` via `.github/workflows/pages.yml`

## Run in Docker
```bash
cd /home/chartmann/mls-home-portal
cp .env.example .env
docker-compose up -d --build
```

Open `http://localhost:8088`.
Saved searches and saved homes are persisted in `./runtime-data/portal.db` via Docker volume.

## Environment
Set in `.env`:
- `OLLAMA_URL` default: `http://bhumc-av:11434`
- `OLLAMA_MODEL` default: `llama3.2:latest`
- `SCAPLING_URL` default: `http://bhumc-av:3000`
- `SCAPLING_TOKEN` optional
- `FLARESOLVERR_URL` default: `http://host.docker.internal:8191/v1` (optional anti-bot fallback)
- `MLS_API_URL` optional direct MLS/IDX API base URL
- `MLS_API_TOKEN` optional
- `APIFY_TOKEN` optional (recommended for reliable fallback; free tier available)
- `APIFY_ACTOR` default `tri_angle/real-estate-aggregator`
- `ENABLE_MOCK_FALLBACK` default `false` (for testing only)

## Provider behavior
- `auto` (default): Direct MLS -> Scapling -> FlareSolverr-assisted scrape -> Apify
- `mls`: Direct MLS, then Scapling, then Apify if needed
- `scapling`: Scapling only
- `apify`: Apify only
- `mock`: only if `ENABLE_MOCK_FALLBACK=true`

## API example
```bash
curl -X POST http://localhost:8088/api/search \
  -H 'Content-Type: application/json' \
  -d '{
    "area": "Raleigh NC",
    "max_price": 450000,
    "annual_income": 120000,
    "monthly_debt": 650,
    "down_payment": 30000,
    "interest_rate": 6.75,
    "loan_term_years": 30,
    "provider": "auto"
  }'
```

## MLS note
Direct MLS access usually requires provider agreements (RETS/RESO/IDX) and most public portals actively block scraping (429/403/CAPTCHA). If direct API access is unavailable, this app uses Scapling plus optional Apify fallback for better reliability.

## Public Repo Safety
- Do not commit `.env` or any tokens.
- Use `.env.example` placeholders only.
- Runtime state stays in `runtime-data/` and is gitignored.
