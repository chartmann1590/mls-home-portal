# Security

## Public Repo Safety Rules

- Never commit `.env` files or API keys.
- Keep tokens only in runtime environment variables.
- Use `.env.example` with empty placeholders.
- Persist local DB in ignored `runtime-data/` directory.

## Scraping / Data Source Notes

- Public listing portals may block scraping (403/429/CAPTCHA).
- Use fallback providers and respect source terms and robots policies.

## Recommended Hardening

- Restrict CORS in production.
- Use HTTPS + reverse proxy.
- Put portal behind auth if exposed publicly.
- Rotate all tokens periodically.
