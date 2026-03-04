from __future__ import annotations

import json
import re
from typing import Dict, Optional

import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def affordability_estimate(self, payload: Dict) -> Optional[Dict]:
        prompt = (
            "You are a mortgage affordability analyst. "
            "Given the user profile JSON, estimate conservative affordability in USD. "
            "Return strict JSON with keys: "
            "max_affordable_home_price (int), estimated_monthly_payment_limit (int), "
            "debt_to_income_ratio (float), confidence (low|medium|high), rationale (string). "
            f"User profile: {json.dumps(payload)}"
        )

        req_body = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=req_body)
                resp.raise_for_status()
                data = resp.json()

            raw = data.get("response", "{}")
            parsed = self._robust_json_load(raw)
            if parsed is None:
                return None
            required = {
                "max_affordable_home_price",
                "estimated_monthly_payment_limit",
                "debt_to_income_ratio",
                "confidence",
                "rationale",
            }
            if not required.issubset(set(parsed.keys())):
                return None
            parsed["max_affordable_home_price"] = int(parsed["max_affordable_home_price"])
            parsed["estimated_monthly_payment_limit"] = int(parsed["estimated_monthly_payment_limit"])
            parsed["debt_to_income_ratio"] = float(parsed["debt_to_income_ratio"])
            parsed["confidence"] = str(parsed["confidence"]).lower()
            parsed["rationale"] = str(parsed["rationale"])
            return parsed
        except Exception:
            return None

    async def summarize_listings(self, payload: Dict) -> Optional[Dict]:
        prompt = (
            "You are a home buying assistant. "
            "Given affordability context and candidate listings, return strict JSON with key 'homes'. "
            "homes must be an array of objects with keys: "
            "id (string), summary (string, <=30 words), is_good_choice (boolean), reason (string, <=24 words). "
            "Use true/false booleans, no markdown, no extra keys. "
            "Be conservative and budget-aware. "
            f"Input: {json.dumps(payload)}"
        )

        req_body = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=req_body)
                resp.raise_for_status()
                data = resp.json()

            raw = data.get("response", "{}")
            parsed = self._robust_json_load(raw)
            if parsed is None:
                return None
            homes = parsed.get("homes") or parsed.get("listings") or parsed.get("results")
            if not isinstance(homes, list):
                return None

            cleaned = []
            for item in homes:
                if not isinstance(item, dict):
                    continue
                if "id" not in item:
                    continue
                cleaned.append(
                    {
                        "id": str(item.get("id")),
                        "summary": str(item.get("summary") or "").strip(),
                        "is_good_choice": (
                            item.get("is_good_choice")
                            if isinstance(item.get("is_good_choice"), bool)
                            else None
                        ),
                        "reason": str(item.get("reason") or "").strip(),
                    }
                )
            return {"homes": cleaned}
        except Exception:
            return None

    async def assess_listing_details(self, payload: Dict) -> Optional[Dict]:
        prompt = (
            "You are a conservative home buying advisor. "
            "Evaluate one home for this buyer profile and return strict JSON with keys: "
            "is_good_choice (boolean), explanation (string, <=80 words). "
            "Mention pricing pressure and practical fit, not style opinions. "
            f"Input: {json.dumps(payload)}"
        )
        req_body = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=req_body)
                resp.raise_for_status()
                data = resp.json()
            parsed = self._robust_json_load(data.get("response", "{}"))
            if not isinstance(parsed, dict):
                return None
            good = parsed.get("is_good_choice")
            if not isinstance(good, bool):
                return None
            return {
                "is_good_choice": good,
                "explanation": str(parsed.get("explanation") or "").strip() or None,
            }
        except Exception:
            return None

    @staticmethod
    def _robust_json_load(raw: str) -> Optional[Dict]:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            pass
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return None
        try:
            parsed = json.loads(m.group(0))
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
