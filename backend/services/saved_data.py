from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models import Listing, SavedListing, SavedListingCreate, SavedSearch, SavedSearchCreate, SearchRequest


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SavedDataStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    criteria_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_json TEXT NOT NULL,
                    effective_price_cap INTEGER,
                    monthly_payment_limit INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _search_from_row(row: sqlite3.Row) -> SavedSearch:
        criteria = SearchRequest(**json.loads(row["criteria_json"]))
        return SavedSearch(
            id=row["id"],
            name=row["name"],
            criteria=criteria,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _listing_from_row(row: sqlite3.Row) -> SavedListing:
        listing = Listing(**json.loads(row["listing_json"]))
        return SavedListing(
            id=row["id"],
            listing=listing,
            effective_price_cap=row["effective_price_cap"],
            monthly_payment_limit=row["monthly_payment_limit"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def list_searches(self) -> List[SavedSearch]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM saved_searches ORDER BY updated_at DESC, id DESC").fetchall()
        return [self._search_from_row(r) for r in rows]

    def create_search(self, req: SavedSearchCreate) -> SavedSearch:
        now = _utc_now()
        name = (req.name or "").strip() or f"{req.criteria.area} up to ${req.criteria.max_price:,}"
        payload = json.dumps(req.criteria.model_dump())
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO saved_searches (name, criteria_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, payload, now, now),
            )
            row_id = int(cur.lastrowid)
            row = conn.execute("SELECT * FROM saved_searches WHERE id = ?", (row_id,)).fetchone()
        return self._search_from_row(row)

    def get_search(self, search_id: int) -> Optional[SavedSearch]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM saved_searches WHERE id = ?", (search_id,)).fetchone()
        return self._search_from_row(row) if row else None

    def delete_search(self, search_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
        return cur.rowcount > 0

    def list_listings(self) -> List[SavedListing]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM saved_listings ORDER BY updated_at DESC, id DESC").fetchall()
        return [self._listing_from_row(r) for r in rows]

    def save_listing(self, req: SavedListingCreate) -> SavedListing:
        now = _utc_now()
        listing_json = json.dumps(req.listing.model_dump())

        with self._conn() as conn:
            existing = None
            if req.listing.listing_url:
                existing = conn.execute(
                    "SELECT * FROM saved_listings WHERE json_extract(listing_json, '$.listing_url') = ? LIMIT 1",
                    (req.listing.listing_url,),
                ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE saved_listings
                    SET listing_json = ?, effective_price_cap = ?, monthly_payment_limit = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        listing_json,
                        req.effective_price_cap,
                        req.monthly_payment_limit,
                        now,
                        existing["id"],
                    ),
                )
                row = conn.execute("SELECT * FROM saved_listings WHERE id = ?", (existing["id"],)).fetchone()
            else:
                cur = conn.execute(
                    """
                    INSERT INTO saved_listings (listing_json, effective_price_cap, monthly_payment_limit, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        listing_json,
                        req.effective_price_cap,
                        req.monthly_payment_limit,
                        now,
                        now,
                    ),
                )
                row = conn.execute("SELECT * FROM saved_listings WHERE id = ?", (int(cur.lastrowid),)).fetchone()
        return self._listing_from_row(row)

    def delete_listing(self, listing_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM saved_listings WHERE id = ?", (listing_id,))
        return cur.rowcount > 0
