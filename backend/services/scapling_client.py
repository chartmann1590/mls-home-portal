from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


def _money_to_int(value: str) -> Optional[int]:
    if not value:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    s = str(value).strip()
    m = re.search(r"(\d[\d,]*)", s)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except Exception:
        return None


def _parse_cards_from_html(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    listings: List[Dict[str, Any]] = []

    selectors = [
        "article",
        "li[data-testid*='property-card']",
        "div[data-testid*='property-card']",
        "div.component_property-card",
    ]

    cards = []
    for sel in selectors:
        cards = soup.select(sel)
        if cards:
            break

    for idx, card in enumerate(cards):
        text = card.get_text(" ", strip=True)
        price_match = re.search(r"\$[\d,]+", text)
        if not price_match:
            continue
        beds_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:bd|beds?|bedrooms?)\b", text, re.IGNORECASE)
        baths_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ba|baths?|bathrooms?)\b", text, re.IGNORECASE)
        sqft_match = re.search(r"([\d,]{3,7})\s*(?:sq\s*ft|sqft)\b", text, re.IGNORECASE)

        address = ""
        for s in [
            "[data-testid*='card-address']",
            "address",
            "h3",
            "h2",
        ]:
            node = card.select_one(s)
            if node and node.get_text(strip=True):
                address = node.get_text(" ", strip=True)
                break

        link = card.select_one("a[href]")
        listing_url = link["href"] if link else None
        image = card.select_one("img[src]")

        listings.append(
            {
                "id": f"scapling-{idx}",
                "address": address or f"Listing {idx + 1}",
                "city": "",
                "state": "",
                "zip_code": "",
                "price": _money_to_int(price_match.group(0)) or 0,
                "beds": _to_float(beds_match.group(1)) if beds_match else None,
                "baths": _to_float(baths_match.group(1)) if baths_match else None,
                "sqft": _to_int(sqft_match.group(1)) if sqft_match else None,
                "lot_sqft": None,
                "property_type": "single_family",
                "listing_url": listing_url,
                "image_url": image["src"] if image else None,
                "source": "scapling",
                "broker_name": None,
            }
        )

    return listings


def _parse_jsonld_from_html(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    listings: List[Dict[str, Any]] = []
    idx = 0

    for script in scripts:
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue

        nodes = payload if isinstance(payload, list) else [payload]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            item_list = node.get("itemListElement")
            if not isinstance(item_list, list):
                continue

            for element in item_list:
                item = element.get("item") if isinstance(element, dict) else None
                if not isinstance(item, dict):
                    continue

                offers = item.get("offers") if isinstance(item.get("offers"), dict) else {}
                price_raw = offers.get("price")
                try:
                    price = int(float(price_raw))
                except Exception:
                    continue

                address_obj = item.get("address") if isinstance(item.get("address"), dict) else {}
                street = str(address_obj.get("streetAddress") or item.get("name") or "").strip()
                city = str(address_obj.get("addressLocality") or "").strip()
                state = str(address_obj.get("addressRegion") or "").strip()
                zip_code = str(address_obj.get("postalCode") or "").strip()
                image = item.get("image")
                if isinstance(image, list):
                    image = image[0] if image else None

                bedrooms = item.get("numberOfBedrooms")
                bathrooms = (
                    item.get("numberOfBathroomsTotal")
                    or item.get("numberOfBathrooms")
                    or item.get("numberofBathroomsTotal")
                )
                floor_size = item.get("floorSize")
                sqft = _to_int(floor_size.get("value")) if isinstance(floor_size, dict) else _to_int(floor_size)

                listings.append(
                    {
                        "id": f"scapling-jsonld-{idx}",
                        "address": street or f"Listing {idx + 1}",
                        "city": city,
                        "state": state,
                        "zip_code": zip_code,
                        "price": price,
                        "beds": _to_float(bedrooms),
                        "baths": _to_float(bathrooms),
                        "sqft": sqft,
                        "lot_sqft": None,
                        "property_type": "single_family",
                        "listing_url": item.get("url"),
                        "image_url": image,
                        "source": "scapling",
                        "broker_name": None,
                    }
                )
                idx += 1

    return listings


def _extract_json_array_after_marker(text: str, marker: str) -> Optional[str]:
    start = text.find(marker)
    if start < 0:
        return None
    arr_start = text.find("[", start)
    if arr_start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for i in range(arr_start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[arr_start : i + 1]
    return None


def _split_us_address(address: str) -> Dict[str, str]:
    # Typical format: "123 Main St, Schenectady, NY 12345"
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 3:
        state_zip = parts[-1].split()
        return {
            "street": ", ".join(parts[:-2] + [parts[-2]]) if len(parts) > 3 else parts[0],
            "city": parts[-2],
            "state": state_zip[0] if state_zip else "",
            "zip_code": state_zip[1] if len(state_zip) > 1 else "",
        }
    return {"street": address, "city": "", "state": "", "zip_code": ""}


def _parse_zillow_results_from_html(html: str) -> List[Dict[str, Any]]:
    marker = '"listResults":'
    raw = _extract_json_array_after_marker(html, marker)
    if not raw:
        return []

    try:
        items = json.loads(raw)
    except Exception:
        return []

    listings: List[Dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        raw_price = item.get("price")
        if isinstance(raw_price, str):
            price = _money_to_int(raw_price)
        elif isinstance(raw_price, (int, float)):
            price = int(raw_price)
        else:
            price = None
        if not price:
            continue

        full_address = str(item.get("address") or "").strip()
        if not full_address:
            street = str(item.get("streetAddress") or "").strip()
            city = str(item.get("city") or "").strip()
            state = str(item.get("state") or "").strip()
            postal = str(item.get("zipcode") or item.get("zip_code") or "").strip()
            full_address = ", ".join([x for x in [street, city, state, postal] if x])

        parsed_addr = _split_us_address(full_address)
        detail = str(item.get("detailUrl") or "").strip()
        if detail and detail.startswith("/"):
            detail = f"https://www.zillow.com{detail}"

        listings.append(
            {
                "id": str(item.get("zpid") or item.get("id") or f"zillow-{idx}"),
                "address": parsed_addr["street"] or full_address or f"Listing {idx + 1}",
                "city": parsed_addr["city"],
                "state": parsed_addr["state"],
                "zip_code": parsed_addr["zip_code"],
                "price": price,
                "beds": _to_float(item.get("beds")),
                "baths": _to_float(item.get("baths")),
                "sqft": _to_int(item.get("area")),
                "lot_sqft": None,
                "property_type": "single_family",
                "listing_url": detail or None,
                "image_url": item.get("imgSrc"),
                "source": "scapling",
                "broker_name": item.get("brokerName"),
            }
        )

    return listings


def _clean_area(area: str) -> str:
    return re.sub(r"\s+", " ", area.replace(",", " ").strip())


def _realtor_search_url(area: str, max_price: int) -> str:
    clean = _clean_area(area)
    if re.fullmatch(r"\d{5}", clean):
        loc = clean
    else:
        parts = clean.split(" ")
        if len(parts) >= 2 and len(parts[-1]) == 2:
            loc = f"{'-'.join(parts[:-1])}_{parts[-1].upper()}"
        else:
            loc = "-".join(parts)
    return f"https://www.realtor.com/realestateandhomes-search/{loc}/type-single-family-home/price-na-{max_price}"


def _zillow_search_url(area: str) -> str:
    clean = _clean_area(area)
    parts = clean.split(" ")
    if len(parts) >= 2 and len(parts[-1]) == 2:
        city = "-".join(parts[:-1])
        state = parts[-1].upper()
        slug = f"{city},-{state}"
    else:
        slug = clean.replace(" ", "-")
    return f"https://www.zillow.com/homes/for_sale/{slug}_rb/"


def _homes_search_url(area: str) -> str:
    clean = _clean_area(area)
    slug = clean.replace(" ", "-")
    return f"https://www.homes.com/homes-for-sale/{slug}/?property_type=single-family-home"


def _trulia_search_url(area: str) -> str:
    clean = _clean_area(area)
    slug = clean.replace(" ", "_")
    return f"https://www.trulia.com/for_sale/{slug}/SINGLE-FAMILY_HOME_type/"


class ScaplingClient:
    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout_seconds: int = 180,
        flaresolverr_url: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.flaresolverr_url = (flaresolverr_url or "").strip()

    @property
    def flaresolverr_enabled(self) -> bool:
        return bool(self.flaresolverr_url)

    @staticmethod
    def _extract_html_from_scrape_response(data: Any) -> str:
        if not isinstance(data, dict):
            return ""
        return (
            data.get("html")
            or data.get("content")
            or (data.get("data") or {}).get("html")
            or (data.get("data") or {}).get("content")
            or (data.get("result") or {}).get("html")
            or (data.get("result") or {}).get("content")
            or ""
        )

    async def _fetch_with_flaresolverr(self, target_url: str) -> str:
        if not self.flaresolverr_enabled:
            return ""
        payload = {"cmd": "request.get", "url": target_url, "maxTimeout": 120000}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(self.flaresolverr_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            if not isinstance(data, dict):
                return ""
            solution = data.get("solution") if isinstance(data.get("solution"), dict) else {}
            html = solution.get("response")
            return html if isinstance(html, str) else ""
        except Exception:
            return ""

    async def search_single_family(self, area: str, max_price: int) -> List[Dict[str, Any]]:
        target_urls = [
            _realtor_search_url(area, max_price),
            _zillow_search_url(area),
            _homes_search_url(area),
            _trulia_search_url(area),
        ]
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

        candidate_paths = ["/v1/scrape", "/scrape", "/api/scrape"]

        for target_url in target_urls:
            html_candidates: List[str] = []
            payload = {"url": target_url, "render_js": True, "wait_for": "networkidle", "output": "html"}
            for path in candidate_paths:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        resp = await client.post(f"{self.base_url}{path}", json=payload, headers=headers)
                        if resp.status_code >= 400:
                            continue
                        html = self._extract_html_from_scrape_response(resp.json())
                        if html:
                            html_candidates.append(html)
                except Exception:
                    continue

            fs_html = await self._fetch_with_flaresolverr(target_url)
            if fs_html:
                html_candidates.append(fs_html)

            for html in html_candidates:
                parser_outputs: List[List[Dict[str, Any]]] = []
                if "zillow.com" in target_url:
                    parser_outputs.append(_parse_zillow_results_from_html(html))
                    parser_outputs.append(_parse_jsonld_from_html(html))
                    parser_outputs.append(_parse_cards_from_html(html))
                else:
                    parser_outputs.append(_parse_cards_from_html(html))
                    parser_outputs.append(_parse_jsonld_from_html(html))

                for parsed in parser_outputs:
                    if not parsed:
                        continue
                    filtered = [x for x in parsed if x.get("price") and x["price"] <= max_price]
                    if filtered:
                        for row in filtered:
                            listing_url = row.get("listing_url")
                            if isinstance(listing_url, str) and listing_url.startswith("/"):
                                row["listing_url"] = urljoin(target_url, listing_url)
                        return filtered

        return []

    async def fetch_listing_details(self, listing_url: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        payload = {
            "url": listing_url,
            "render_js": True,
            "wait_for": "networkidle",
            "output": "html",
        }

        html = ""
        for path in ["/v1/scrape", "/scrape", "/api/scrape"]:
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(f"{self.base_url}{path}", json=payload, headers=headers)
                    if resp.status_code >= 400:
                        continue
                    data = resp.json()
                if isinstance(data, dict):
                    html = (
                        data.get("html")
                        or data.get("content")
                        or (data.get("data") or {}).get("html")
                        or (data.get("result") or {}).get("html")
                        or ""
                    )
                    if html:
                        break
            except Exception:
                continue

        if not html:
            return {"description": None, "photos": [], "realtor": {}}

        host = (urlparse(listing_url).hostname or "").lower()
        if "zillow.com" in host:
            z = self._parse_zillow_detail_html(html)
            if z:
                return z
        return self._parse_generic_detail_html(html)

    def _parse_zillow_detail_html(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", attrs={"id": "__NEXT_DATA__", "type": "application/json"})
        if not script:
            return self._parse_generic_detail_html(html)

        try:
            next_data = json.loads(script.get_text())
            cache_raw = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("componentProps", {})
                .get("gdpClientCache")
            )
            cache = json.loads(cache_raw) if isinstance(cache_raw, str) else {}
            entry = next(iter(cache.values())) if cache else {}
            if isinstance(entry, str):
                entry = json.loads(entry)
            prop = entry.get("property") or entry.get("data", {}).get("property") or {}
            if not isinstance(prop, dict):
                return self._parse_generic_detail_html(html)

            photos: List[str] = []
            responsive = prop.get("responsivePhotos") or []
            for p in responsive:
                if not isinstance(p, dict):
                    continue
                u = p.get("url")
                if isinstance(u, str) and u and u not in photos:
                    photos.append(u)
            if not photos:
                original = prop.get("originalPhotos") or []
                for p in original:
                    if not isinstance(p, dict):
                        continue
                    mixed = (p.get("mixedSources") or {}).get("jpeg") or []
                    for m in mixed:
                        u = m.get("url") if isinstance(m, dict) else None
                        if isinstance(u, str) and u and u not in photos:
                            photos.append(u)

            attr = prop.get("attributionInfo") or {}
            return {
                "description": str(prop.get("description") or "").strip() or None,
                "photos": photos[:60],
                "realtor": {
                    "broker_name": attr.get("brokerName"),
                    "agent_name": attr.get("agentName"),
                    "agent_phone": attr.get("agentPhoneNumber"),
                    "agent_email": attr.get("agentEmail"),
                    "mls_name": attr.get("mlsName"),
                    "mls_id": attr.get("mlsId"),
                },
            }
        except Exception:
            return self._parse_generic_detail_html(html)

    def _parse_generic_detail_html(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        description = None
        for sel in [
            "meta[name='description']",
            "meta[property='og:description']",
            "div[data-testid*='description']",
            "section[data-testid*='description']",
        ]:
            node = soup.select_one(sel)
            if not node:
                continue
            if node.name == "meta":
                txt = (node.get("content") or "").strip()
            else:
                txt = node.get_text(" ", strip=True)
            if txt:
                description = txt
                break

        photos: List[str] = []
        for img in soup.select("img[src]"):
            src = (img.get("src") or "").strip()
            if not src:
                continue
            if src.startswith("data:"):
                continue
            if src not in photos:
                photos.append(src)
            if len(photos) >= 40:
                break

        return {"description": description, "photos": photos, "realtor": {}}
