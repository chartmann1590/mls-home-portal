from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from .apify_client import ApifyClient
from .direct_mls_client import DirectMLSClient
from .scapling_client import ScaplingClient


class ListingService:
    def __init__(
        self,
        data_dir: Path,
        scapling_client: ScaplingClient,
        direct_mls_client: DirectMLSClient,
        apify_client: ApifyClient,
        enable_mock_fallback: bool = False,
    ):
        self.data_dir = data_dir
        self.scapling_client = scapling_client
        self.direct_mls_client = direct_mls_client
        self.apify_client = apify_client
        self.enable_mock_fallback = enable_mock_fallback

    def _mock_listings(self, area: str, max_price: int) -> List[Dict]:
        fp = self.data_dir / "sample_listings.json"
        with fp.open("r", encoding="utf-8") as f:
            items = json.load(f)

        area_l = area.lower()
        results = []
        for item in items:
            location = f"{item.get('city', '')} {item.get('state', '')} {item.get('zip_code', '')}".lower()
            if area_l in location and item.get("price", 10**9) <= max_price:
                results.append(item)
        if results:
            return results

        return [x for x in items if x.get("price", 10**9) <= max_price]

    async def search(self, area: str, max_price: int, provider: str) -> Tuple[List[Dict], List[str]]:
        provider = (provider or "auto").lower()
        notes: List[str] = []

        if provider in {"mls", "auto"}:
            mls = await self.direct_mls_client.search_single_family(area, max_price)
            if mls:
                notes.append("Used direct MLS provider.")
                return mls, notes
            notes.append("Direct MLS unavailable or no matches; falling back to Scapling.")

        if provider in {"scapling", "auto", "mls"}:
            sc = await self.scapling_client.search_single_family(area, max_price)
            if sc:
                notes.append("Used Scapling listing provider.")
                return sc, notes
            notes.append("Scapling returned no matching listings.")

        if provider in {"apify", "auto", "mls", "scapling"}:
            ap = await self.apify_client.search_single_family(area, max_price)
            if ap:
                notes.append("Used Apify fallback listing provider.")
                return ap, notes
            if self.apify_client.enabled:
                notes.append("Apify returned no matching listings.")
            else:
                notes.append("Apify fallback is not configured (missing APIFY_TOKEN).")

        if provider == "mock" and self.enable_mock_fallback:
            notes.append("Using mock listings (testing mode).")
            return self._mock_listings(area, max_price), notes

        if self.enable_mock_fallback and provider in {"auto", "mls", "scapling"}:
            notes.append("Using mock fallback because enabled and no live listings were returned.")
            return self._mock_listings(area, max_price), notes

        return [], notes
