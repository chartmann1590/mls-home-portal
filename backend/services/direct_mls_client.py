from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


class DirectMLSClient:
    def __init__(self, base_url: str, token: Optional[str] = None, timeout_seconds: int = 30):
        self.base_url = (base_url or "").rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    async def search_single_family(self, area: str, max_price: int) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        payload = {
            "area": area,
            "max_price": max_price,
            "property_type": "single_family",
        }

        # Support common API patterns for MLS/IDX proxy services.
        candidate = [
            ("POST", "/search", payload),
            ("POST", "/api/search", payload),
            ("GET", f"/search?area={area}&max_price={max_price}&property_type=single_family", None),
            ("GET", f"/api/search?area={area}&max_price={max_price}&property_type=single_family", None),
        ]

        for method, path, body in candidate:
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    if method == "POST":
                        resp = await client.post(f"{self.base_url}{path}", json=body, headers=headers)
                    else:
                        resp = await client.get(f"{self.base_url}{path}", headers=headers)

                if resp.status_code >= 400:
                    continue

                data = resp.json()
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("listings") or data.get("results") or data.get("data") or []
                else:
                    items = []

                normalized = []
                for idx, item in enumerate(items):
                    if not isinstance(item, dict):
                        continue
                    price = item.get("price") or item.get("list_price") or 0
                    try:
                        price = int(float(price))
                    except Exception:
                        continue
                    if price <= 0 or price > max_price:
                        continue

                    normalized.append(
                        {
                            "id": str(item.get("id") or item.get("listing_id") or f"mls-{idx}"),
                            "address": str(item.get("address") or item.get("street") or "Unknown Address"),
                            "city": str(item.get("city") or ""),
                            "state": str(item.get("state") or ""),
                            "zip_code": str(item.get("zip_code") or item.get("postal_code") or ""),
                            "price": price,
                            "beds": item.get("beds") or item.get("bedrooms"),
                            "baths": item.get("baths") or item.get("bathrooms"),
                            "sqft": item.get("sqft") or item.get("living_area"),
                            "lot_sqft": item.get("lot_sqft") or item.get("lot_size"),
                            "property_type": "single_family",
                            "listing_url": item.get("listing_url") or item.get("url"),
                            "image_url": item.get("image_url") or item.get("photo"),
                            "source": "direct_mls",
                        }
                    )

                if normalized:
                    return normalized
            except Exception:
                continue

        return []
