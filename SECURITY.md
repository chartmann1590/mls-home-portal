# Security Policy

## Reporting a Vulnerability

If you find a security issue, open a private report by contacting the repository owner directly before publishing details.

## Scope

This project handles integrations with external services (Ollama, scraping bridge, optional MLS/APIs). Keep all credentials out of source control.

## Security Practices

- Never commit `.env` or secret files.
- Commit only `.env.example` placeholders.
- Keep production tokens in environment variables or secret managers.
- Rotate exposed tokens immediately.
- Restrict CORS and network exposure in production.
- Run dependency updates regularly.
