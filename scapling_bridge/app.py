from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from scrapling import DynamicFetcher, StealthyFetcher

app = FastAPI(title="Scapling Bridge", version="1.0.0")
logger = logging.getLogger("scapling_bridge")


class ScrapeRequest(BaseModel):
    url: str = Field(..., min_length=8)
    render_js: bool = True
    wait_for: str = "networkidle"
    output: str = "html"


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/v1/scrape")
def scrape(req: ScrapeRequest) -> dict:
    try:
        def _extract_html(resp: object) -> str:
            return (
                (getattr(resp, "html_content", None) or "")
                or (getattr(resp, "text", None) or "")
                or (
                    getattr(resp, "body", b"").decode("utf-8", errors="ignore")
                    if isinstance(getattr(resp, "body", b""), (bytes, bytearray))
                    else ""
                )
            )

        fetchers = [StealthyFetcher.fetch, DynamicFetcher.fetch]
        html = ""
        final_url = req.url
        for fetch_fn in fetchers:
            response = fetch_fn(
                req.url,
                headless=True,
                network_idle=(req.wait_for.lower() == "networkidle"),
                disable_resources=False,
                timeout=60000,
                wait=1500,
            )
            candidate = _extract_html(response)
            blocked = "Your request could not be processed" in candidate
            if candidate and not blocked:
                html = candidate
                final_url = getattr(response, "url", req.url)
                break
            if len(candidate) > len(html):
                html = candidate
                final_url = getattr(response, "url", req.url)

        return {
            "url": final_url,
            "html": html,
            "length": len(html),
        }
    except Exception as exc:
        logger.exception("Scapling fetch failed for %s", req.url)
        raise HTTPException(status_code=502, detail=f"Scraping failed: {exc}")
