"""
Data models for AutoFinder using Pydantic for validation and serialization.

This module defines all data structures used throughout the application:
- Configuration models
- Car inventory models
- Price history tracking
- Finance calculations
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Configuration Models
# ============================================================================

class FinanceConfig(BaseModel):
    """Finance calculation parameters."""
    apr_percent: float = Field(..., description="Annual Percentage Rate")
    term_months: int = Field(..., description="Loan term in months")
    doc_fees: float = Field(..., description="Documentation fees")
    ttl_percent_of_price: float = Field(..., description="Tax, Title, License as % of price")


class Filters(BaseModel):
    """Search filters for vehicle inventory."""
    min_year: int = Field(..., description="Minimum vehicle year")
    max_mileage: int = Field(..., description="Maximum mileage")
    allowed_conditions: List[Literal["new", "used", "certified"]] = Field(..., description="Allowed vehicle conditions")
    include_makes: List[str] = Field(default_factory=list, description="List of makes to include")
    exclude_models: List[str] = Field(default_factory=list, description="List of models to exclude")


class Sources(BaseModel):
    """Data source configuration."""
    ai_meta_search: bool = Field(default=True, description="Enable AI-powered meta search")
    dealers: List[str] = Field(default_factory=list, description="Direct dealer URLs")
    aggregators: List[str] = Field(default_factory=list, description="Aggregator service names")


class AppConfig(BaseModel):
    """Main application configuration loaded from config/app.config.json."""
    zip: str = Field(..., description="ZIP code for search center")
    radius_miles: int = Field(..., description="Search radius in miles")
    max_down_payment: float = Field(..., description="Maximum down payment amount")
    max_monthly_payment: float = Field(..., description="Maximum monthly payment")
    finance: FinanceConfig
    filters: Filters
    sources: Sources


# ============================================================================
# Vehicle Inventory Models
# ============================================================================

class DealerInfo(BaseModel):
    """Dealer contact information."""
    name: str = Field(..., description="Dealer name")
    phone: Optional[str] = Field(None, description="Dealer phone number")
    url: str = Field(..., description="Dealer or listing URL")


class MediaInfo(BaseModel):
    """Vehicle media assets."""
    thumbnail: Optional[str] = Field(None, description="Thumbnail image URL")


class Timestamps(BaseModel):
    """Vehicle listing timestamps."""
    first_seen: str = Field(..., description="ISO 8601 timestamp when first seen")
    last_seen: str = Field(..., description="ISO 8601 timestamp when last seen")


class FinanceAssumptions(BaseModel):
    """Finance calculation assumptions for transparency."""
    apr_percent: float
    term_months: int
    ttl_percent_of_price: float
    doc_fees: float


class FinanceInfo(BaseModel):
    """Calculated finance information for a vehicle."""
    est_down: float = Field(..., description="Estimated down payment")
    est_monthly: float = Field(..., description="Estimated monthly payment")
    assumptions: FinanceAssumptions


class PriceTrend(BaseModel):
    """Price change tracking."""
    direction: Literal["up", "down", "flat", "new"] = Field(..., description="Price movement direction")
    delta: float = Field(default=0, description="Price change amount (absolute)")
    prev_price: Optional[float] = Field(None, description="Previous price")
    last_change_at: Optional[str] = Field(None, description="ISO 8601 timestamp of last price change")


class NormalizedCar(BaseModel):
    """
    Normalized vehicle data structure.

    This is the canonical representation of a vehicle listing,
    normalized from various data sources.
    """
    id: str = Field(..., description="Unique identifier (VIN or generated hash)")
    vin: Optional[str] = Field(None, description="Vehicle Identification Number")
    source: str = Field(..., description="Data source identifier")
    title: str = Field(..., description="Display title (e.g., '2019 Honda Accord EX-L')")
    year: int = Field(..., description="Model year")
    make: str = Field(..., description="Vehicle make")
    model: str = Field(..., description="Vehicle model")
    trim: Optional[str] = Field(None, description="Trim level")
    condition: Literal["new", "used", "certified"] = Field(..., description="Vehicle condition")
    price: float = Field(..., description="Listed price")
    mileage: int = Field(..., description="Odometer reading")
    distance_miles: float = Field(..., description="Distance from search center")
    dealer: DealerInfo
    media: MediaInfo = Field(default_factory=lambda: MediaInfo())
    timestamps: Timestamps
    finance: FinanceInfo
    price_trend: PriceTrend = Field(default_factory=lambda: PriceTrend(direction="new", delta=0))

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Ensure year is reasonable."""
        current_year = datetime.now().year
        if v < 1900 or v > current_year + 2:
            raise ValueError(f"Year must be between 1900 and {current_year + 2}")
        return v

    @field_validator('price', 'mileage')
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """Ensure price and mileage are positive."""
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v


class Inventory(BaseModel):
    """
    Complete inventory snapshot.

    Written to data/inventory.json on each run.
    """
    generated_at: str = Field(..., description="ISO 8601 timestamp of generation")
    zip: str = Field(..., description="Search ZIP code")
    radius_miles: int = Field(..., description="Search radius")
    items: List[NormalizedCar] = Field(default_factory=list, description="Vehicle listings")


# ============================================================================
# History Models
# ============================================================================

class HistoryItem(BaseModel):
    """Compact price tracking for a single vehicle in a run."""
    id: str = Field(..., description="Vehicle ID (VIN or hash)")
    price: float = Field(..., description="Price at this run")


class HistoryRun(BaseModel):
    """Single data collection run snapshot."""
    generated_at: str = Field(..., description="ISO 8601 timestamp of run")
    items: List[HistoryItem] = Field(default_factory=list, description="Vehicle prices in this run")


class History(BaseModel):
    """
    Historical price tracking.

    Append-only structure written to data/history.json.
    """
    runs: List[HistoryRun] = Field(default_factory=list, description="Chronological list of runs")


# ============================================================================
# Raw Source Data Models
# ============================================================================

class RawCarData(BaseModel):
    """
    Raw, unnormalized vehicle data from a source.

    This is an intermediate structure before normalization.
    Fields are optional to accommodate various source formats.
    """
    vin: Optional[str] = None
    source: str
    title: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    trim: Optional[str] = None
    condition: Optional[str] = None
    price: Optional[float] = None
    mileage: Optional[int] = None
    distance_miles: Optional[float] = None
    dealer_name: Optional[str] = None
    dealer_phone: Optional[str] = None
    dealer_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    class Config:
        """Allow extra fields that might come from sources."""
        extra = "allow"
