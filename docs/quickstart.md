# Quick Start

## 1. Configure

```bash
cp .env.example .env
```

Set relevant values in `.env`:

- `OLLAMA_URL`
- `OLLAMA_MODEL=llama3.2:latest`
- `SCAPLING_URL`
- `FLARESOLVERR_URL`
- `APIFY_TOKEN` (optional)
- `MLS_API_URL` and `MLS_API_TOKEN` (optional)

## 2. Run

```bash
docker compose up -d --build
```

## 3. Use

Open `http://localhost:8088` (or configured `HOST_PORT`).

## 4. Persisted Data

Saved searches and homes are stored in `./runtime-data/portal.db`.
