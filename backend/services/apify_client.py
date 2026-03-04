from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx


def _to_int(val: Any) -> Optional[int]:
    try:
        if val is None:
            return None
        if isinstance(val, bool):
            return None
        if isinstance(val, (int, float)):
            return int(val)
        s = str(val)
        digits = ''.join(ch for ch in s if ch.isdigit())
        return int(digits) if digits else None
    except Exception:
        return None


class ApifyClient:
    def __init__(
        self,
        token: Optional[str],
        actor: str = "tri_angle/real-estate-aggregator",
        timeout_seconds: int = 120,
    ):
        self.token = (token or "").strip()
        self.actor = actor
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    async def search_single_family(self, area: str, max_price: int) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        run_input = {
            "location": area,
            "maxPrice": max_price,
            "propertyType": "single_family",
            "listingType": "sale",
            "limit": 60,
        }

        run_url = f"https://api.apify.com/v2/acts/{self.actor}/runs"
        params = {
            "token": self.token,
            "waitForFinish": 90,
            "memory": 2048,
            "timeout": 120,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                run_resp = await client.post(run_url, params=params, json=run_input)
                run_resp.raise_for_status()
                run_data = run_resp.json().get("data", {})
                dataset_id = run_data.get("defaultDatasetId")
                if not dataset_id:
                    return []

                ds_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
                ds_resp = await client.get(ds_url, params={"token": self.token, "clean": "true"})
                ds_resp.raise_for_status()
                items = ds_resp.json()

            listings: List[Dict[str, Any]] = []
            for idx, item in enumerate(items if isinstance(items, list) else []):
                if not isinstance(item, dict):
                    continue
                price = _to_int(item.get("price") or item.get("listPrice") or item.get("amount"))
                if not price or price > max_price:
                    continue

                beds = item.get("beds") or item.get("bedrooms")
                baths = item.get("baths") or item.get("bathrooms")
                sqft = _to_int(item.get("sqft") or item.get("livingArea") or item.get("area"))

                listings.append(
                    {
                        "id": str(item.get("id") or item.get("listingId") or f"apify-{idx}"),
                        "address": str(item.get("address") or item.get("street") or "Unknown Address"),
                        "city": str(item.get("city") or ""),
                        "state": str(item.get("state") or ""),
                        "zip_code": str(item.get("zip") or item.get("zipCode") or item.get("postalCode") or ""),
                        "price": price,
                        "beds": float(beds) if isinstance(beds, (int, float, str)) and str(beds).replace('.', '', 1).isdigit() else None,
                        "baths": float(baths) if isinstance(baths, (int, float, str)) and str(baths).replace('.', '', 1).isdigit() else None,
                        "sqft": sqft,
                        "lot_sqft": _to_int(item.get("lotSqft") or item.get("lotSize")),
                        "property_type": "single_family",
                        "listing_url": item.get("listingUrl") or item.get("url"),
                        "image_url": item.get("image") or item.get("imageUrl") or item.get("thumbnail"),
                        "source": "apify",
                        "broker_name": item.get("broker") or item.get("brokerName"),
                    }
                )

            return listings
        except Exception:
            return []
