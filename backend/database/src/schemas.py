"""
Pydantic schemas for the trading platform database.

These serve dual purposes:
  * Input validation for database writes.
  * Structured output schemas for LLM tool calls.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ------------------------------------------------------------------ types

RegionType = Literal[
    "north_america", "europe", "asia", "latin_america", "africa",
    "middle_east", "oceania", "global", "international",
]

AssetClassType = Literal[
    "equity", "fixed_income", "real_estate", "commodities", "cash", "alternatives",
]

SectorType = Literal[
    "technology", "healthcare", "financials", "consumer_discretionary",
    "consumer_staples", "industrials", "energy", "materials", "utilities",
    "real_estate", "communication", "treasury", "corporate", "mortgage",
    "government_related", "commodities", "diversified", "other",
]

InstrumentType = Literal[
    "etf", "mutual_fund", "stock", "bond", "bond_fund", "commodity", "reit",
]

JobType = Literal[
    "portfolio_analysis", "rebalance_recommendation", "retirement_projection",
    "risk_assessment", "tax_optimization", "instrument_research",
]

JobStatus = Literal["pending", "running", "completed", "failed"]

AccountType = Literal[
    "401k", "roth_ira", "traditional_ira", "taxable", "529", "hsa", "pension", "other",
]

RiskToleranceType = Literal["conservative", "moderate", "aggressive"]
InvestmentExperienceType = Literal["beginner", "intermediate", "advanced"]
KYCStatus = Literal["pending", "approved", "rejected"]
SignalDirection = Literal["BUY", "SELL", "HOLD"]
SignalHorizon = Literal["1d", "1w", "1m", "3m"]
SignalStatus = Literal["active", "expired", "executed", "rejected", "candidate", "validated"]
TradeSide = Literal["buy", "sell"]
TradeStatus = Literal["pending", "filled", "partial", "cancelled", "rejected"]


# ------------------------------------------------------------ original schemas

class RegionAllocation(BaseModel):
    allocations: Dict[RegionType, float] = Field(
        description="Percentage allocation by geographic region. Must sum to 100.",
    )

    @field_validator("allocations")
    def _sum(cls, v):
        if abs(sum(v.values()) - 100) > 3:
            raise ValueError(f"Region allocations must sum to 100, got {sum(v.values())}")
        return v


class AssetClassAllocation(BaseModel):
    allocations: Dict[AssetClassType, float] = Field(
        description="Percentage allocation by asset class. Must sum to 100.",
    )

    @field_validator("allocations")
    def _sum(cls, v):
        if abs(sum(v.values()) - 100) > 3:
            raise ValueError(f"Asset class allocations must sum to 100, got {sum(v.values())}")
        return v


class SectorAllocation(BaseModel):
    allocations: Dict[SectorType, float] = Field(
        description="Percentage allocation by market sector. Must sum to 100.",
    )

    @field_validator("allocations")
    def _sum(cls, v):
        if abs(sum(v.values()) - 100) > 3:
            raise ValueError(f"Sector allocations must sum to 100, got {sum(v.values())}")
        return v


class InstrumentCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=255)
    instrument_type: InstrumentType
    current_price: Optional[Decimal] = Field(None, ge=0, le=999999)
    allocation_regions: Dict[RegionType, float] = Field(example={"north_america": 100})
    allocation_sectors: Dict[SectorType, float] = Field(example={"technology": 100})
    allocation_asset_class: Dict[AssetClassType, float] = Field(example={"equity": 100})
    source: Optional[str] = "seed"
    tickers: Optional[List[str]] = None

    @field_validator("allocation_regions", "allocation_sectors", "allocation_asset_class")
    def _sum(cls, v):
        if not v:
            raise ValueError("Allocation cannot be empty")
        if abs(sum(v.values()) - 100) > 3:
            raise ValueError(f"Allocations must sum to 100, got {sum(v.values())}")
        return v


class InstrumentResponse(InstrumentCreate):
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    clerk_user_id: str
    display_name: Optional[str] = Field(None, max_length=255)
    years_until_retirement: Optional[int] = Field(None, ge=0, le=100)
    target_retirement_income: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    asset_class_targets: Optional[Dict[AssetClassType, float]] = Field(
        default={"equity": 70, "fixed_income": 30},
    )
    region_targets: Optional[Dict[RegionType, float]] = Field(
        default={"north_america": 50, "international": 50},
    )


class AccountCreate(BaseModel):
    account_name: str = Field(min_length=1, max_length=255)
    account_purpose: Optional[str] = None
    cash_balance: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    cash_interest: Decimal = Field(default=Decimal("0"), ge=0, le=1, decimal_places=4)


class PositionCreate(BaseModel):
    account_id: str
    symbol: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Field(gt=0, decimal_places=8)
    as_of_date: Optional[date] = Field(default_factory=date.today)


class JobCreate(BaseModel):
    clerk_user_id: str
    job_type: JobType
    request_payload: Optional[Dict] = None


class JobUpdate(BaseModel):
    status: JobStatus
    result_payload: Optional[Dict] = None
    error_message: Optional[str] = None


class PortfolioAnalysis(BaseModel):
    total_value: Decimal = Field(decimal_places=2)
    asset_allocation: Dict[AssetClassType, float]
    region_allocation: Dict[RegionType, float]
    sector_allocation: Dict[SectorType, float]
    risk_score: int = Field(ge=1, le=10)
    recommendations: List[str]


class RebalanceRecommendation(BaseModel):
    current_allocation: Dict[str, float]
    target_allocation: Dict[str, float]
    trades: List[Dict]
    rationale: str


# ------------------------------------------------------ trading-platform schemas

class TradingProfileCreate(BaseModel):
    """User suitability + KYC (M10-09 evidence)."""
    clerk_user_id: str
    risk_tolerance: RiskToleranceType
    investment_experience: Optional[InvestmentExperienceType] = None
    income_bracket: Optional[str] = None
    max_drawdown_pct: Decimal = Field(default=Decimal("20.0"), ge=0, le=100)
    kyc_status: KYCStatus = "pending"
    kyc_provider_ref: Optional[str] = None
    jurisdiction: Optional[str] = Field(None, min_length=2, max_length=2)


class TradingSignalCreate(BaseModel):
    clerk_user_id: str
    symbol: str = Field(min_length=1, max_length=20)
    direction: SignalDirection
    confidence: Decimal = Field(ge=0, le=1, decimal_places=3)
    horizon: SignalHorizon
    entry_price: Optional[Decimal] = Field(None, ge=0)
    stop_loss: Optional[Decimal] = Field(None, ge=0)
    take_profit: Optional[Decimal] = Field(None, ge=0)
    rationale: Optional[str] = None
    source: Optional[str] = None
    researcher_event_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class TradeCreate(BaseModel):
    clerk_user_id: str
    account_id: str
    signal_id: Optional[str] = None
    symbol: str = Field(min_length=1, max_length=20)
    side: TradeSide
    quantity: Decimal = Field(gt=0, decimal_places=8)
    filled_price: Optional[Decimal] = Field(None, ge=0)
    commission: Decimal = Field(default=Decimal("0"), ge=0)
    slippage: Decimal = Field(default=Decimal("0"), ge=0)
    broker: Optional[str] = None
    broker_order_id: Optional[str] = None
    is_paper: bool = True
    status: TradeStatus = "pending"
    idempotency_key: Optional[str] = None


class ResearcherEventCreate(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    symbol: Optional[str] = Field(None, max_length=20)
    event_type: str = Field(min_length=3, max_length=50)
    direction: SignalDirection
    confidence: Decimal = Field(ge=0, le=1, decimal_places=3)
    horizon: SignalHorizon
    summary: str
    source_urls: List[str] = Field(default_factory=list)
    extracted_facts: Optional[Dict] = None
    discovered_at: datetime
    expires_at: Optional[datetime] = None
    raw_article_hash: Optional[str] = None
    status: SignalStatus = "candidate"


class TradingAuditEntry(BaseModel):
    clerk_user_id: Optional[str] = None
    actor: str = Field(pattern="^(user|agent|system)$")
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    payload: Optional[Dict] = None
    prev_hash: Optional[str] = None
    this_hash: str


__all__ = [
    # Types
    "RegionType", "AssetClassType", "SectorType", "InstrumentType",
    "JobType", "JobStatus", "AccountType", "RiskToleranceType",
    "InvestmentExperienceType", "KYCStatus", "SignalDirection",
    "SignalHorizon", "SignalStatus", "TradeSide", "TradeStatus",
    # Original schemas
    "InstrumentCreate", "InstrumentResponse", "UserCreate", "AccountCreate",
    "PositionCreate", "JobCreate", "JobUpdate",
    "PortfolioAnalysis", "RebalanceRecommendation",
    "RegionAllocation", "AssetClassAllocation", "SectorAllocation",
    # Trading-platform schemas
    "TradingProfileCreate", "TradingSignalCreate", "TradeCreate",
    "ResearcherEventCreate", "TradingAuditEntry",
]