from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional


class SearchRequest(BaseModel):
    area: str = Field(..., min_length=2, max_length=120)
    max_price: int = Field(..., gt=50000)
    annual_income: float = Field(..., gt=0)
    monthly_debt: float = Field(0, ge=0)
    down_payment: float = Field(0, ge=0)
    interest_rate: float = Field(6.75, gt=0, lt=25)
    loan_term_years: int = Field(30, ge=10, le=40)
    provider: str = Field("auto")


class Listing(BaseModel):
    id: str
    address: str
    city: str
    state: str
    zip_code: str
    price: int
    beds: Optional[float] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    lot_sqft: Optional[int] = None
    property_type: str = "single_family"
    listing_url: Optional[str] = None
    image_url: Optional[str] = None
    source: str = "unknown"
    broker_name: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_is_good_choice: Optional[bool] = None
    ai_reason: Optional[str] = None


class AffordabilityResult(BaseModel):
    max_affordable_home_price: int
    estimated_monthly_payment_limit: int
    debt_to_income_ratio: float
    confidence: str
    rationale: str


class SearchResponse(BaseModel):
    area: str
    requested_max_price: int
    ai_affordability: AffordabilityResult
    effective_price_cap: int
    listing_count: int
    listings: List[Listing]
    notes: List[str]


class ListingDetailRequest(BaseModel):
    listing_url: str = Field(..., min_length=8)
    address: str = Field(..., min_length=3)
    city: str = ""
    state: str = ""
    price: int = Field(..., gt=0)
    beds: Optional[float] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    effective_price_cap: int = Field(..., gt=0)
    monthly_payment_limit: int = Field(..., ge=0)
    ai_reason: Optional[str] = None
    broker_name: Optional[str] = None


class RealtorInfo(BaseModel):
    broker_name: Optional[str] = None
    agent_name: Optional[str] = None
    agent_phone: Optional[str] = None
    agent_email: Optional[str] = None
    mls_name: Optional[str] = None
    mls_id: Optional[str] = None


class ListingDetailResponse(BaseModel):
    listing_url: str
    description: Optional[str] = None
    photos: List[str]
    realtor: RealtorInfo
    ai_is_good_choice: Optional[bool] = None
    ai_explanation: Optional[str] = None


class SavedSearchCreate(BaseModel):
    name: Optional[str] = None
    criteria: SearchRequest


class SavedSearch(BaseModel):
    id: int
    name: str
    criteria: SearchRequest
    created_at: datetime
    updated_at: datetime


class SavedSearchListResponse(BaseModel):
    items: List[SavedSearch]


class SavedListingCreate(BaseModel):
    listing: Listing
    effective_price_cap: Optional[int] = None
    monthly_payment_limit: Optional[int] = None


class SavedListing(BaseModel):
    id: int
    listing: Listing
    effective_price_cap: Optional[int] = None
    monthly_payment_limit: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class SavedListingListResponse(BaseModel):
    items: List[SavedListing]
