import datetime
from enum import Enum
from typing import Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Float,
    JSON,
    Text,
    Date,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field, field_validator, model_validator
from backend.shared.database import Base


def _normalize_symbol(value: str) -> str:
    symbol = value.strip().upper()
    allowed_punctuation = {"-", ".", "/", "_"}
    if not symbol or not any(character.isalnum() for character in symbol):
        raise ValueError("symbol must contain at least one alphanumeric character")
    if any(not (character.isalnum() or character in allowed_punctuation) for character in symbol):
        raise ValueError("symbol contains unsupported characters")
    return symbol


def _validate_probability_map(value: dict[str, Any]) -> dict[str, Any]:
    for key, raw_score in value.items():
        if not isinstance(raw_score, int | float):
            raise ValueError(f"probability value for {key} must be numeric")
        if any(token in key.lower() for token in ("prob", "up", "down", "tail", "win", "loss")):
            if raw_score < 0 or raw_score > 1:
                raise ValueError(f"probability value for {key} must be between 0 and 1")
    return value


class AssetType(str, Enum):
    EQUITY = "equity"
    ETF = "etf"
    OPTION = "option"
    FUTURE = "future"
    CRYPTO = "crypto"
    FOREX = "forex"
    BOND = "bond"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TWAP = "twap"
    VWAP = "vwap"
    ICEBERG = "iceberg"


class OrderStatus(str, Enum):
    CREATED = "created"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


class RecommendationAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ModelStage(str, Enum):
    CANDIDATE = "candidate"
    CHALLENGER = "challenger"
    CHAMPION = "champion"
    RETIRED = "retired"


class DomainModel(PydanticBaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class AuditMetadataDTO(DomainModel):
    request_id: str | None = None
    source: str = "system"
    reproducible: bool = True
    generated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    model_version_id: int | str | None = None
    data_snapshot_id: int | str | None = None


class UserDTO(DomainModel):
    id: int | None = None
    email: str = Field(min_length=3, max_length=320)
    is_active: bool = True
    is_superuser: bool = False
    risk_profile_completed: bool = False
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("email must be a valid address")
        return email


class InstrumentDTO(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    name: str | None = None
    exchange: str | None = None
    asset_type: AssetType = AssetType.EQUITY
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_active: bool = True
    listing_date: datetime.date | None = None
    delisting_date: datetime.date | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_listing_window(self) -> "InstrumentDTO":
        if self.listing_date and self.delisting_date and self.delisting_date < self.listing_date:
            raise ValueError("delisting_date cannot be earlier than listing_date")
        return self


class SignalDTO(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    signal: RecommendationAction
    confidence: float = Field(ge=0.0, le=1.0)
    probability_distribution: dict[str, Any] = Field(default_factory=dict)
    factor_exposures: dict[str, float] = Field(default_factory=dict)
    tail_risk_summary: dict[str, Any] = Field(default_factory=dict)
    freshness_score: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: list[str] = Field(default_factory=list)
    audit_metadata: AuditMetadataDTO = Field(default_factory=AuditMetadataDTO)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("signal", mode="before")
    @classmethod
    def normalize_signal(cls, value: str | RecommendationAction) -> str | RecommendationAction:
        return value.upper() if isinstance(value, str) else value

    @field_validator("probability_distribution")
    @classmethod
    def validate_probability_distribution(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_probability_map(value)


class RecommendationDTO(SignalDTO):
    signal: RecommendationAction | None = None
    recommendation: RecommendationAction = RecommendationAction.HOLD
    entry_zone: dict[str, float] = Field(default_factory=dict)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    position_size: float | None = Field(default=None, ge=0)

    @field_validator("recommendation", mode="before")
    @classmethod
    def normalize_recommendation(cls, value: str | RecommendationAction) -> str | RecommendationAction:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def align_signal_and_recommendation(self) -> "RecommendationDTO":
        if self.signal is None:
            self.signal = self.recommendation
        elif self.recommendation != self.signal:
            raise ValueError("recommendation must match signal")
        return self


class PortfolioDTO(DomainModel):
    id: int | None = None
    user_id: int
    name: str = Field(default="Primary", min_length=1, max_length=120)
    base_currency: str = Field(default="USD", min_length=3, max_length=3)
    risk_profile: str = "balanced"
    equity: float = Field(default=0.0, ge=0.0)
    cash: float = Field(default=0.0, ge=0.0)
    positions: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("base_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


class OrderDTO(DomainModel):
    id: int | None = None
    portfolio_id: int | None = None
    symbol: str = Field(min_length=1, max_length=32)
    side: OrderSide
    quantity: float = Field(gt=0)
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.CREATED
    limit_price: float | None = Field(default=None, gt=0)
    broker: str | None = None
    audit_metadata: AuditMetadataDTO = Field(default_factory=AuditMetadataDTO)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, value: str | OrderSide) -> str | OrderSide:
        return value.upper() if isinstance(value, str) else value

    @field_validator("order_type", mode="before")
    @classmethod
    def normalize_order_type(cls, value: str | OrderType) -> str | OrderType:
        return value.lower() if isinstance(value, str) else value


class TradeDTO(DomainModel):
    id: int | None = None
    order_id: int | None = None
    symbol: str = Field(min_length=1, max_length=32)
    side: OrderSide
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    fees: float = Field(default=0.0, ge=0.0)
    signal_source: str | None = None
    attribution: dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, value: str | OrderSide) -> str | OrderSide:
        return value.upper() if isinstance(value, str) else value


class ModelVersionDTO(DomainModel):
    id: int | None = None
    model_name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)
    stage: ModelStage = ModelStage.CANDIDATE
    artifact_uri: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class DataSnapshotDTO(DomainModel):
    id: int | None = None
    snapshot_key: str = Field(min_length=1, max_length=160)
    dataset: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=80)
    source: str | None = None
    schema_hash: str = Field(min_length=16)
    row_count: int = Field(default=0, ge=0)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class AuditEventDTO(DomainModel):
    id: int | None = None
    action: str = Field(min_length=1, max_length=160)
    user_id: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    previous_hash: str = Field(min_length=16)
    current_hash: str = Field(min_length=16)
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @model_validator(mode="after")
    def validate_hash_chain(self) -> "AuditEventDTO":
        if self.previous_hash == self.current_hash:
            raise ValueError("audit hashes must advance the chain")
        return self


class PortfolioSnapshot(DomainModel):
    account_id: str
    equity: float
    cash: float
    gross_exposure: float
    net_exposure: float
    risk_score: int = Field(ge=0, le=100)


class SignalRequest(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    horizon: str = "swing"
    portfolio_context: dict | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class RecommendationResponse(DomainModel):
    symbol: str
    recommendation: RecommendationAction
    confidence: float = Field(ge=0.0, le=1.0)
    probability_distribution: dict[str, Any]
    rationale: list[str]
    tail_risk_summary: dict[str, Any] = Field(default_factory=dict)
    factor_exposures: dict[str, float] = Field(default_factory=dict)
    freshness_score: float = Field(default=1.0, ge=0.0, le=1.0)
    audit_metadata: AuditMetadataDTO = Field(default_factory=AuditMetadataDTO)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("recommendation", mode="before")
    @classmethod
    def normalize_recommendation(cls, value: str | RecommendationAction) -> str | RecommendationAction:
        return value.upper() if isinstance(value, str) else value

    @field_validator("probability_distribution")
    @classmethod
    def validate_probability_distribution(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_probability_map(value)


class OrderRequest(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: str = Field(pattern="^(buy|sell|BUY|SELL)$")
    quantity: float = Field(gt=0)
    order_type: str = "market"

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("side")
    @classmethod
    def normalize_side(cls, value: str) -> str:
        return value.upper()

    @field_validator("order_type")
    @classmethod
    def normalize_order_type(cls, value: str) -> str:
        return value.lower()


class BacktestRequest(DomainModel):
    strategy_id: str
    start_date: str
    end_date: str
    universe: list[str] = Field(default_factory=list)

    @field_validator("universe")
    @classmethod
    def normalize_universe(cls, value: list[str]) -> list[str]:
        return [_normalize_symbol(symbol) for symbol in value]

    @model_validator(mode="after")
    def validate_date_order(self) -> "BacktestRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date cannot be later than end_date")
        return self


class BacktestResult(DomainModel):
    strategy_id: str
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: int


class OHLCVBar(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    timestamp: datetime.datetime
    open: float = Field(ge=0)
    high: float = Field(ge=0)
    low: float = Field(ge=0)
    close: float = Field(ge=0)
    volume: float = Field(ge=0)
    adjusted_close: float | None = Field(default=None, ge=0)
    source: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("timestamp")
    @classmethod
    def ensure_timezone(cls, value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value

    @model_validator(mode="after")
    def validate_ohlc_consistency(self) -> "OHLCVBar":
        if self.high < self.low:
            raise ValueError("high cannot be less than low")
        if self.high < max(self.open, self.close):
            raise ValueError("high must be at least open and close")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be no greater than open and close")
        return self


class QuoteTick(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    timestamp: datetime.datetime
    bid: float = Field(ge=0)
    ask: float = Field(ge=0)
    bid_size: float = Field(ge=0, default=0)
    ask_size: float = Field(ge=0, default=0)
    source: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("timestamp")
    @classmethod
    def ensure_timezone(cls, value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value

    @model_validator(mode="after")
    def validate_spread(self) -> "QuoteTick":
        if self.bid and self.ask and self.ask < self.bid:
            raise ValueError("ask cannot be below bid")
        return self


class BidAskQuote(QuoteTick):
    pass


class VolumeSnapshot(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    timestamp: datetime.datetime
    volume: float = Field(ge=0)
    average_volume: float | None = Field(default=None, ge=0)
    relative_volume: float | None = Field(default=None, ge=0)
    source: str = Field(min_length=1)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("timestamp")
    @classmethod
    def ensure_timezone(cls, value: datetime.datetime) -> datetime.datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value


class CorporateActionEvent(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    effective_date: datetime.date
    action_type: str
    ratio: float | None = Field(default=None, gt=0)
    cash_amount: float | None = Field(default=None, ge=0)
    new_symbol: str | None = None
    source: str = "internal"

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("new_symbol")
    @classmethod
    def normalize_new_symbol(cls, value: str | None) -> str | None:
        return _normalize_symbol(value) if value else value

    @field_validator("action_type")
    @classmethod
    def normalize_action_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"split", "dividend", "symbol_change"}
        if normalized not in allowed:
            raise ValueError(f"unsupported corporate action type: {value}")
        return normalized

    @model_validator(mode="after")
    def validate_required_action_fields(self) -> "CorporateActionEvent":
        if self.action_type == "split" and not self.ratio:
            raise ValueError("split actions require ratio")
        if self.action_type == "dividend" and self.cash_amount is None:
            raise ValueError("dividend actions require cash_amount")
        if self.action_type == "symbol_change" and not self.new_symbol:
            raise ValueError("symbol_change actions require new_symbol")
        return self


class NormalizedEvent(DomainModel):
    source: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    symbol: str | None = None
    timestamp: datetime.datetime
    confidence: float = Field(ge=0.0, le=1.0)
    source_timestamp: datetime.datetime | None = None
    received_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str | None) -> str | None:
        return _normalize_symbol(value) if value else value

    @field_validator("timestamp", "source_timestamp", "received_at")
    @classmethod
    def ensure_timezone(cls, value: datetime.datetime | None) -> datetime.datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=datetime.timezone.utc)
        return value

    @model_validator(mode="after")
    def default_source_timestamp(self) -> "NormalizedEvent":
        if self.source_timestamp is None:
            self.source_timestamp = self.timestamp
        return self


class BrokerAccountSnapshotDTO(DomainModel):
    broker: str
    account_id: str
    mode: str = "sandbox"
    status: str = "healthy"
    equity: float = Field(ge=0)
    cash: float = Field(ge=0)
    buying_power: float = Field(ge=0)
    margin_requirement: float = Field(default=0.0, ge=0)
    last_sync_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class OperatingPositionDTO(DomainModel):
    symbol: str = Field(min_length=1, max_length=32)
    asset_type: AssetType = AssetType.EQUITY
    quantity: float
    average_cost: float = Field(gt=0)
    last_price: float = Field(gt=0)
    market_value: float
    unrealized_pnl: float
    day_pnl: float = 0.0
    sector: str = "unknown"
    factor_exposures: dict[str, float] = Field(default_factory=dict)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class MarginSnapshotDTO(DomainModel):
    broker: str
    account_id: str
    equity: float = Field(ge=0)
    buying_power: float = Field(ge=0)
    maintenance_margin: float = Field(ge=0)
    intraday_margin_requirement: float = Field(ge=0)
    intraday_margin_deficiency: float = Field(default=0.0, ge=0)
    liquidation_risk: str = "low"
    ruleset: str = "sandbox_intraday_margin"
    effective_date: datetime.date | None = None
    violations: list[str] = Field(default_factory=list)


class OperatingOrderDTO(DomainModel):
    order_id: str
    symbol: str = Field(min_length=1, max_length=32)
    side: OrderSide
    quantity: float = Field(gt=0)
    order_type: str = "market"
    status: str = "working"
    broker: str = "alpaca"
    time_in_force: str = "day"
    extended_hours: bool = False
    limit_price: float | None = Field(default=None, gt=0)
    stop_price: float | None = Field(default=None, gt=0)
    parent_order_id: str | None = None
    blocked_reason: str | None = None
    routing_decision: dict[str, Any] = Field(default_factory=dict)
    audit_id: str = Field(default_factory=lambda: f"audit-{datetime.datetime.utcnow().timestamp():.0f}")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, value: str | OrderSide) -> str | OrderSide:
        return value.upper() if isinstance(value, str) else value


class FillQualityDTO(DomainModel):
    fill_id: str
    order_id: str
    symbol: str
    venue: str
    arrival_price: float = Field(gt=0)
    fill_price: float = Field(gt=0)
    spread_at_arrival_bps: float
    slippage_bps: float
    price_improvement_bps: float
    execution_speed_ms: int = Field(ge=0)
    routed_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class OptionContractDTO(DomainModel):
    option_symbol: str
    underlying: str
    expiration: datetime.date
    strike: float = Field(gt=0)
    option_type: str = Field(pattern="^(call|put)$")
    bid: float = Field(ge=0)
    ask: float = Field(ge=0)
    volume: int = Field(ge=0)
    open_interest: int = Field(ge=0)
    implied_volatility: float = Field(ge=0)
    delta: float
    gamma: float
    theta: float
    vega: float


class CatalystEventDTO(DomainModel):
    event_id: str
    symbol: str | None = None
    event_type: str
    title: str
    starts_at: datetime.datetime
    impact: str = "medium"
    linked_risks: list[str] = Field(default_factory=list)
    source: str = "internal"


class WatchlistDTO(DomainModel):
    watchlist_id: str
    name: str
    symbols: list[str] = Field(default_factory=list)
    criteria: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str]) -> list[str]:
        return [_normalize_symbol(symbol) for symbol in value]


class DisclosureAttestationDTO(DomainModel):
    disclosure_id: str
    title: str
    status: str = "required"
    acknowledged_at: datetime.datetime | None = None
    required_for: list[str] = Field(default_factory=list)


class BasketTradeDTO(DomainModel):
    basket_id: str
    name: str
    target_weights: dict[str, float] = Field(default_factory=dict)
    account_allocations: dict[str, float] = Field(default_factory=dict)
    status: str = "draft"
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("target_weights")
    @classmethod
    def validate_target_weights(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("target_weights must include at least one symbol")
        normalized = {_normalize_symbol(symbol): float(weight) for symbol, weight in value.items()}
        total = sum(normalized.values())
        if total <= 0 or total > 1.25:
            raise ValueError("target_weights must have a positive realistic total")
        return normalized


class PreTradeCheckDTO(DomainModel):
    check_id: str
    scope: str = "order"
    status: str = "blocked"
    allowed: bool = False
    checks: list[dict[str, Any]] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    audit_id: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class TaxLotDecisionDTO(DomainModel):
    decision_id: str
    symbol: str
    recommended_method: str
    lots: list[dict[str, Any]] = Field(default_factory=list)
    wash_sale_risk: str = "low"
    after_tax_estimate: float = 0.0
    audit_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class BorrowLocateDTO(DomainModel):
    locate_id: str
    symbol: str
    status: str = "review"
    borrow_fee_rate: float = Field(ge=0)
    hard_to_borrow: bool = False
    recall_risk: str = "medium"
    short_sale_restriction: bool = False
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class PortfolioModelDTO(DomainModel):
    model_id: str
    name: str
    objective: str
    target_allocations: dict[str, float] = Field(default_factory=dict)
    risk_budget: dict[str, float] = Field(default_factory=dict)
    expected_volatility: float = Field(ge=0)
    tax_aware: bool = True


class MarketDepthSnapshotDTO(DomainModel):
    symbol: str
    nbbo: dict[str, float]
    depth: list[dict[str, Any]] = Field(default_factory=list)
    liquidity_score: float = Field(ge=0, le=1)
    estimated_impact_bps: float = Field(ge=0)
    captured_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class StagedOrderDTO(DomainModel):
    stage_id: str
    symbol: str
    side: OrderSide
    quantity: float = Field(gt=0)
    status: str = "draft"
    approvals: list[dict[str, Any]] = Field(default_factory=list)
    compliance_holds: list[str] = Field(default_factory=list)
    audit_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, value: str | OrderSide) -> str | OrderSide:
        return value.upper() if isinstance(value, str) else value


class DataQualityScoreDTO(DomainModel):
    source: str
    status: str
    freshness_score: float = Field(ge=0, le=1)
    completeness_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    impacted_signals: list[str] = Field(default_factory=list)


class StrategyDefinitionDTO(DomainModel):
    strategy_id: str
    name: str
    universe: list[str] = Field(default_factory=list)
    rules: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "research"

    @field_validator("universe")
    @classmethod
    def normalize_universe(cls, value: list[str]) -> list[str]:
        return [_normalize_symbol(symbol) for symbol in value]


class RiskConstitutionRuleDTO(DomainModel):
    rule_id: str
    rule_type: str
    threshold: float | str | bool
    enforcement: str = "never_override"
    enabled: bool = True


class CommunicationArchiveRecordDTO(DomainModel):
    archive_id: str
    record_type: str
    title: str
    audit_id: str
    source_refs: list[str] = Field(default_factory=list)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class EmergencyActionDTO(DomainModel):
    action_id: str
    action_type: str
    status: str = "requested"
    actor: str = "user"
    audit_id: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class FundingAccountDTO(DomainModel):
    funding_account_id: str
    account_type: str
    institution_name: str
    status: str = "pending_verification"
    verification_status: str = "sandbox_only"
    live_transfer_enabled: bool = False
    audit_id: str


class CashTransferDTO(DomainModel):
    transfer_id: str
    direction: str
    method: str
    amount: float = Field(gt=0)
    status: str = "pending"
    settlement_date: datetime.date | None = None
    audit_id: str


class CashLedgerEntryDTO(DomainModel):
    ledger_id: str
    entry_type: str
    amount: float
    settled: bool = False
    description: str
    audit_id: str
    posted_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class SettlementLotDTO(DomainModel):
    settlement_id: str
    symbol: str
    quantity: float = Field(gt=0)
    trade_date: datetime.date
    settlement_date: datetime.date
    status: str = "pending"

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class ChartTradingLayoutDTO(DomainModel):
    layout_id: str
    symbol: str
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)
    risk_reward: float = Field(ge=0)
    audit_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class CorporateActionDTO(DomainModel):
    action_id: str
    symbol: str
    action_type: str
    status: str = "announced"
    election_required: bool = False
    deadline: datetime.datetime | None = None
    audit_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class AccountDocumentDTO(DomainModel):
    document_id: str
    document_type: str
    period: str
    status: str = "available"
    formats: list[str] = Field(default_factory=lambda: ["html", "pdf", "csv"])
    audit_id: str


class AdminReviewDTO(DomainModel):
    review_id: str
    review_type: str
    status: str = "open"
    severity: str = "review"
    subject_ref: str
    audit_id: str


class SurveillanceAlertDTO(DomainModel):
    alert_id: str
    alert_type: str
    severity: str = "review"
    status: str = "open"
    evidence: dict[str, Any] = Field(default_factory=dict)
    audit_id: str


class MarketDataEntitlementDTO(DomainModel):
    entitlement_id: str
    user_id: str
    data_type: str
    access_level: str = "delayed"
    status: str = "active"
    vendor: str = "sandbox"
    audit_id: str


class DataUsageMeterDTO(DomainModel):
    usage_id: str
    data_type: str
    vendor: str
    units: int = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    audit_id: str


class RecurringInvestmentPlanDTO(DomainModel):
    plan_id: str
    symbol: str
    dollar_amount: float = Field(gt=0)
    cadence: str = "monthly"
    status: str = "pending_precheck"
    audit_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class ConditionalOrderDTO(DomainModel):
    conditional_order_id: str
    symbol: str
    side: OrderSide
    quantity: float = Field(gt=0)
    triggers: list[dict[str, Any]] = Field(default_factory=list)
    do_not_execute_if: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "simulated"
    audit_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)

    @field_validator("side", mode="before")
    @classmethod
    def normalize_side(cls, value: str | OrderSide) -> str | OrderSide:
        return value.upper() if isinstance(value, str) else value


class PortfolioReviewPackDTO(DomainModel):
    report_id: str
    title: str
    status: str = "generated"
    formats: list[str] = Field(default_factory=lambda: ["html", "pdf", "csv"])
    archive_id: str
    audit_id: str


class MobileDeviceDTO(DomainModel):
    device_id: str
    platform: str
    push_enabled: bool = False
    biometric_approval_supported: bool = False
    status: str = "registered"
    audit_id: str


class SupportCaseDTO(DomainModel):
    case_id: str
    category: str
    status: str = "open"
    subject: str
    audit_id: str


class AuditRequestDTO(DomainModel):
    request_id: str
    request_type: str
    status: str = "queued"
    scope: dict[str, Any] = Field(default_factory=dict)
    audit_id: str


class TerminalQuoteDTO(DomainModel):
    quote_id: str
    symbol: str
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    last: float = Field(gt=0)
    entitlement_level: str = "delayed"
    source_confidence: float = Field(default=1.0, ge=0, le=1)
    audit_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class LevelIIBookDTO(DomainModel):
    book_id: str
    symbol: str
    bids: list[dict[str, Any]] = Field(default_factory=list)
    asks: list[dict[str, Any]] = Field(default_factory=list)
    entitlement_status: str = "blocked"
    audit_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class TimeAndSalesPrintDTO(DomainModel):
    print_id: str
    symbol: str
    price: float = Field(gt=0)
    size: int = Field(gt=0)
    venue: str = "sandbox"
    printed_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class OptionFlowEventDTO(DomainModel):
    flow_id: str
    underlying: str
    contract: str
    side: str
    premium: float = Field(ge=0)
    unusual_score: float = Field(default=0.0, ge=0, le=1)
    audit_id: str

    @field_validator("underlying")
    @classmethod
    def normalize_underlying(cls, value: str) -> str:
        return _normalize_symbol(value)


class ResearchSnapshotDTO(DomainModel):
    snapshot_id: str
    symbol: str
    summary: str
    valuation: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)
    audit_id: str

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return _normalize_symbol(value)


class BrokerConnectionDTO(DomainModel):
    connection_id: str
    broker: str
    account_id: str
    status: str = "paper_connected"
    live_enabled: bool = False
    permissions: list[str] = Field(default_factory=list)
    audit_id: str


class ACATSTransferDTO(DomainModel):
    transfer_id: str
    direction: str
    status: str = "initiated"
    delivering_firm: str
    receiving_firm: str
    audit_id: str


class AccountTypeRuleDTO(DomainModel):
    rule_id: str
    account_type: str
    rule_type: str
    status: str = "active"
    constraints: dict[str, Any] = Field(default_factory=dict)
    audit_id: str


class PortfolioAnalyticsSnapshotDTO(DomainModel):
    analytics_id: str
    account_id: str
    performance: dict[str, Any] = Field(default_factory=dict)
    attribution: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] = Field(default_factory=dict)
    audit_id: str


class AlertRuleDTO(DomainModel):
    alert_rule_id: str
    name: str
    event_type: str
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    destinations: list[str] = Field(default_factory=list)
    status: str = "active"
    audit_id: str


class AutomationPolicyDTO(DomainModel):
    policy_id: str
    name: str
    policy_type: str
    guardrails: list[str] = Field(default_factory=list)
    status: str = "simulation"
    audit_id: str


class StrategyMarketplaceListingDTO(DomainModel):
    listing_id: str
    name: str
    strategy_type: str
    status: str = "listed"
    performance_summary: dict[str, Any] = Field(default_factory=dict)
    audit_id: str


class DocumentAISummaryDTO(DomainModel):
    summary_id: str
    document_type: str
    title: str
    impact_summary: str
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    audit_id: str


class CoachingPlanDTO(DomainModel):
    plan_id: str
    user_id: str
    focus_area: str
    goals: list[str] = Field(default_factory=list)
    status: str = "active"
    audit_id: str


class CollaborationSpaceDTO(DomainModel):
    space_id: str
    name: str
    privacy: str = "private"
    members: list[str] = Field(default_factory=list)
    audit_id: str


class FeeYieldRecordDTO(DomainModel):
    record_id: str
    account_id: str
    category: str
    amount: float
    annualized_rate: float | None = None
    audit_id: str


class TrustSecurityEventDTO(DomainModel):
    event_id: str
    event_type: str
    status: str = "open"
    severity: str = "review"
    audit_id: str


class NotificationPolicyDTO(DomainModel):
    policy_id: str
    channel: str
    category: str
    enabled: bool = True
    quiet_hours: dict[str, Any] = Field(default_factory=dict)
    audit_id: str


class NotificationDeliveryLogDTO(DomainModel):
    delivery_id: str
    channel: str
    status: str
    destination: str
    audit_id: str


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)  # encrypted in DB
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    risk_profile_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    # In User class add:
    email_hash = Column(String, unique=True, index=True, nullable=False)
    # The email field will be the encrypted email.

    risk_profile = relationship("RiskProfile", uselist=False, back_populates="user")
    accounts = relationship("PaperAccount", back_populates="user")


class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    investment_experience = Column(String)  # beginner, intermediate, advanced
    risk_tolerance = Column(String)  # low, medium, high
    annual_income = Column(String)
    net_worth = Column(String)
    investment_horizon = Column(String)
    loss_tolerance_percent = Column(Float)
    questionnaire_answers = Column(JSON)  # raw answers
    risk_score = Column(Integer)  # computed score
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="risk_profile")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String)
    previous_hash = Column(String, nullable=False)
    current_hash = Column(String, nullable=False, unique=True)
    # The hash chain ensures immutability


class SecretRecord(Base):
    __tablename__ = "secret_records"

    id = Column(Integer, primary_key=True)
    name_hash = Column(String, index=True, nullable=False)
    version = Column(Integer, nullable=False)
    ciphertext = Column(Text, nullable=False)
    key_id = Column(String, nullable=True)
    active = Column(Boolean, default=True, index=True)
    secret_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (Index("idx_secret_records_name_version", "name_hash", "version", unique=True),)


class PrivacyRecordModel(Base):
    __tablename__ = "privacy_records"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    email_hash = Column(String, nullable=False)
    consent = Column(JSON, nullable=False, default=dict)
    deletion_requested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    asset_type = Column(String, default=AssetType.EQUITY.value, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    listing_date = Column(Date, nullable=True)
    delisting_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    instrument_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SecurityMaster(Base):
    __tablename__ = "security_master"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    name = Column(String)
    exchange = Column(String)
    asset_type = Column(String)  # stock, etf, etc.
    listing_date = Column(Date, nullable=True)
    delisting_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    adjusted_close = Column(Float, nullable=True)
    source = Column(String)  # provider name
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (Index("idx_market_data_symbol_date", "symbol", "date"),)


class CorporateAction(Base):
    __tablename__ = "corporate_actions"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    date = Column(Date, nullable=False)
    action_type = Column(String)  # split, dividend, etc.
    description = Column(Text)
    ratio = Column(Float, nullable=True)  # for splits
    value = Column(Float, nullable=True)  # for dividends
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    source = Column(String)
    title = Column(Text)
    url = Column(Text)
    published_at = Column(DateTime)
    content = Column(Text)
    symbols = Column(JSON)  # list of related tickers
    sentiment = Column(Float, nullable=True)  # to be computed later
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EconomicIndicator(Base):
    __tablename__ = "economic_indicators"

    id = Column(Integer, primary_key=True)
    indicator_name = Column(String, index=True)
    date = Column(Date, index=True)
    value = Column(Float)
    source = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String)
    sector = Column(String)
    last_price = Column(Float)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal = Column(String)  # BUY, SELL, HOLD
    confidence = Column(Float)
    fundamentals_score = Column(Float)
    sentiment_score = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    probability_distribution = Column(
        JSON
    )  # {"win": 0.65, "loss": 0.35, "expected_return": 0.05}
    explanation = Column(JSON)  # feature contributions
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("paper_accounts.id"), index=True, nullable=True)
    symbol = Column(String)
    action = Column(String)  # BUY, SELL
    quantity = Column(Integer)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="filled")  # filled, pending
    pnl = Column(Float, nullable=True)
    account = relationship("PaperAccount", back_populates="trades")


class PaperAccount(Base):
    __tablename__ = "paper_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Float, default=100000)
    user = relationship("User", back_populates="accounts")
    trades = relationship("PaperTrade", back_populates="account")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    name = Column(String, nullable=False, default="Primary")
    base_currency = Column(String, default="USD")
    risk_profile = Column(String, default="balanced")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), index=True, nullable=False)
    symbol = Column(String, index=True, nullable=False)
    asset_type = Column(String, default="equity")
    quantity = Column(Float, nullable=False)
    average_cost = Column(Float, nullable=False)
    market_value = Column(Float, nullable=False, default=0.0)
    factor_exposures = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    recommendation = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    probability_distribution = Column(JSON, nullable=False)
    rationale = Column(JSON, nullable=False)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True)
    data_snapshot_id = Column(Integer, ForeignKey("data_snapshots.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), index=True, nullable=True)
    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    order_type = Column(String, default="market")
    status = Column(String, default="created")
    broker = Column(String, nullable=True)
    broker_order_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), index=True, nullable=True)
    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)
    signal_source = Column(String, nullable=True)
    attribution = Column(JSON, nullable=True)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, index=True, nullable=False)
    version = Column(String, nullable=False)
    stage = Column(String, default="candidate")
    artifact_uri = Column(String, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DataSnapshot(Base):
    __tablename__ = "data_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_key = Column(String, unique=True, index=True, nullable=False)
    dataset = Column(String, index=True, nullable=False)
    version = Column(String, nullable=False)
    source = Column(String, nullable=True)
    schema_hash = Column(String, nullable=False)
    row_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class TaxLot(Base):
    __tablename__ = "tax_lots"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    symbol = Column(String)
    quantity = Column(Float)
    cost_per_share = Column(Float)
    acquisition_date = Column(Date)
    active = Column(Boolean, default=True)
    account_id = Column(String, nullable=True)
    wash_sale_blocked_until = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class StressScenario(Base):
    __tablename__ = "stress_scenarios"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    label = Column(String)
    shocks = Column(JSON, nullable=False)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class TradeImpact(Base):
    __tablename__ = "trade_impacts"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    expected_execution_price = Column(Float, nullable=False)
    impact_cost_bps = Column(Float, nullable=False)
    permanent_impact_bps = Column(Float, nullable=False)
    temporary_impact_bps = Column(Float, nullable=False)
    model_name = Column(String, default="almgren_chriss")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class BrokerAccountModel(Base):
    __tablename__ = "broker_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    broker = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    mode = Column(String, default="sandbox", nullable=False)
    status = Column(String, default="healthy", nullable=False)
    equity = Column(Float, default=0.0)
    cash = Column(Float, default=0.0)
    buying_power = Column(Float, default=0.0)
    margin_requirement = Column(Float, default=0.0)
    account_metadata = Column("metadata", JSON, nullable=True)
    last_sync_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (Index("idx_broker_account_unique", "broker", "account_id", "mode", unique=True),)


class MarginSnapshotModel(Base):
    __tablename__ = "margin_snapshots"

    id = Column(Integer, primary_key=True)
    broker = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    equity = Column(Float, default=0.0)
    buying_power = Column(Float, default=0.0)
    maintenance_margin = Column(Float, default=0.0)
    intraday_margin_requirement = Column(Float, default=0.0)
    intraday_margin_deficiency = Column(Float, default=0.0)
    liquidation_risk = Column(String, default="low")
    ruleset = Column(String, default="sandbox_intraday_margin")
    effective_date = Column(Date, nullable=True)
    violations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class OptionContractModel(Base):
    __tablename__ = "option_contracts"

    id = Column(Integer, primary_key=True)
    option_symbol = Column(String, unique=True, nullable=False, index=True)
    underlying = Column(String, nullable=False, index=True)
    expiration = Column(Date, nullable=False, index=True)
    strike = Column(Float, nullable=False)
    option_type = Column(String, nullable=False)
    bid = Column(Float, default=0.0)
    ask = Column(Float, default=0.0)
    volume = Column(Integer, default=0)
    open_interest = Column(Integer, default=0)
    implied_volatility = Column(Float, default=0.0)
    delta = Column(Float, default=0.0)
    gamma = Column(Float, default=0.0)
    theta = Column(Float, default=0.0)
    vega = Column(Float, default=0.0)
    source = Column(String, default="sandbox")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CatalystEventModel(Base):
    __tablename__ = "catalyst_events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    starts_at = Column(DateTime, nullable=False, index=True)
    impact = Column(String, default="medium")
    linked_risks = Column(JSON, nullable=True)
    source = Column(String, default="internal")
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class WatchlistModel(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    watchlist_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    symbols = Column(JSON, nullable=False, default=list)
    criteria = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class TradeJournalEntryV2Model(Base):
    __tablename__ = "trade_journal_entries_v2"

    id = Column(Integer, primary_key=True)
    journal_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    setup = Column(String, nullable=False)
    pre_trade_plan = Column(Text, nullable=True)
    thesis = Column(Text, nullable=True)
    confidence_tag = Column(String, nullable=True)
    emotion_tag = Column(String, nullable=True)
    rule_checklist = Column(JSON, nullable=True)
    mae = Column(Float, default=0.0)
    mfe = Column(Float, default=0.0)
    expectancy = Column(Float, default=0.0)
    setup_quality = Column(Integer, default=0)
    ai_post_trade_review = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DisclosureAttestationModel(Base):
    __tablename__ = "disclosure_attestations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    disclosure_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    status = Column(String, default="required", nullable=False)
    required_for = Column(JSON, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (Index("idx_disclosure_user_unique", "user_id", "disclosure_id", unique=True),)


class BrokerReconciliationRecordModel(Base):
    __tablename__ = "broker_reconciliation_records"

    id = Column(Integer, primary_key=True)
    broker = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)
    checks = Column(JSON, nullable=False, default=list)
    alerts = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class BasketTradeModel(Base):
    __tablename__ = "basket_trades"

    id = Column(Integer, primary_key=True)
    basket_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    target_weights = Column(JSON, nullable=False, default=dict)
    account_allocations = Column(JSON, nullable=True)
    rebalance_orders = Column(JSON, nullable=True)
    impact_preview = Column(JSON, nullable=True)
    status = Column(String, default="draft", nullable=False, index=True)
    audit_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class PreTradeCheckModel(Base):
    __tablename__ = "pre_trade_checks"

    id = Column(Integer, primary_key=True)
    check_id = Column(String, unique=True, nullable=False, index=True)
    scope = Column(String, default="order", nullable=False, index=True)
    status = Column(String, default="blocked", nullable=False, index=True)
    allowed = Column(Boolean, default=False, nullable=False)
    checks = Column(JSON, nullable=False, default=list)
    violations = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class TaxLotDecisionModel(Base):
    __tablename__ = "tax_lot_decisions"

    id = Column(Integer, primary_key=True)
    decision_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    recommended_method = Column(String, nullable=False)
    lots = Column(JSON, nullable=False, default=list)
    wash_sale_risk = Column(String, default="low")
    after_tax_estimate = Column(Float, default=0.0)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class BorrowLocateModel(Base):
    __tablename__ = "borrow_locates"

    id = Column(Integer, primary_key=True)
    locate_id = Column(String, unique=True, nullable=False, index=True)
    broker = Column(String, default="alpaca", nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    status = Column(String, default="review", nullable=False, index=True)
    borrow_fee_rate = Column(Float, default=0.0)
    hard_to_borrow = Column(Boolean, default=False)
    recall_risk = Column(String, default="medium")
    short_sale_restriction = Column(Boolean, default=False)
    locate_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PortfolioConstructionModel(Base):
    __tablename__ = "portfolio_models"

    id = Column(Integer, primary_key=True)
    model_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    objective = Column(String, nullable=False)
    target_allocations = Column(JSON, nullable=False, default=dict)
    risk_budget = Column(JSON, nullable=True)
    constraints = Column(JSON, nullable=True)
    expected_volatility = Column(Float, default=0.0)
    tax_aware = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class MarketDepthSnapshotModel(Base):
    __tablename__ = "market_depth_snapshots"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    nbbo = Column(JSON, nullable=False, default=dict)
    depth = Column(JSON, nullable=False, default=list)
    liquidity_score = Column(Float, default=0.0)
    estimated_impact_bps = Column(Float, default=0.0)
    route_visibility = Column(JSON, nullable=True)
    captured_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class StagedOrderModel(Base):
    __tablename__ = "staged_orders"

    id = Column(Integer, primary_key=True)
    stage_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    status = Column(String, default="draft", nullable=False, index=True)
    approvals = Column(JSON, nullable=False, default=list)
    compliance_holds = Column(JSON, nullable=True)
    allocations = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class DataQualityScoreModel(Base):
    __tablename__ = "data_quality_scores"

    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    freshness_score = Column(Float, default=0.0)
    completeness_score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    issues = Column(JSON, nullable=True)
    impacted_signals = Column(JSON, nullable=True)
    captured_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class StrategyDefinitionModel(Base):
    __tablename__ = "strategy_definitions"

    id = Column(Integer, primary_key=True)
    strategy_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    universe = Column(JSON, nullable=False, default=list)
    rules = Column(JSON, nullable=False, default=list)
    walk_forward_report = Column(JSON, nullable=True)
    paper_deploy_status = Column(String, default="research", nullable=False, index=True)
    drift_monitor = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class RiskConstitutionRuleModel(Base):
    __tablename__ = "risk_constitution_rules"

    id = Column(Integer, primary_key=True)
    rule_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    rule_type = Column(String, nullable=False, index=True)
    threshold = Column(JSON, nullable=False)
    enforcement = Column(String, default="never_override", nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CommunicationArchiveRecordModel(Base):
    __tablename__ = "communication_archive_records"

    id = Column(Integer, primary_key=True)
    archive_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    record_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    content_summary = Column(Text, nullable=True)
    source_refs = Column(JSON, nullable=True)
    model_version = Column(String, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    retention_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class EmergencyActionModel(Base):
    __tablename__ = "emergency_actions"

    id = Column(Integer, primary_key=True)
    action_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action_type = Column(String, nullable=False, index=True)
    status = Column(String, default="requested", nullable=False, index=True)
    actor = Column(String, default="user", nullable=False)
    payload = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class FundingAccountModel(Base):
    __tablename__ = "funding_accounts"

    id = Column(Integer, primary_key=True)
    funding_account_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    account_type = Column(String, nullable=False, index=True)
    institution_name = Column(String, nullable=False)
    masked_account = Column(String, nullable=True)
    status = Column(String, default="pending_verification", nullable=False, index=True)
    verification_status = Column(String, default="sandbox_only", nullable=False)
    live_transfer_enabled = Column(Boolean, default=False, nullable=False)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class CashTransferModel(Base):
    __tablename__ = "cash_transfers"

    id = Column(Integer, primary_key=True)
    transfer_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    funding_account_id = Column(String, nullable=True, index=True)
    direction = Column(String, nullable=False, index=True)
    method = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending", nullable=False, index=True)
    settlement_date = Column(Date, nullable=True, index=True)
    blocked_reason = Column(Text, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class CashLedgerEntryModel(Base):
    __tablename__ = "cash_ledger_entries"

    id = Column(Integer, primary_key=True)
    ledger_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    entry_type = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    settled = Column(Boolean, default=False, nullable=False)
    description = Column(Text, nullable=False)
    audit_id = Column(String, nullable=False, index=True)
    posted_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class SettlementLotModel(Base):
    __tablename__ = "settlement_lots"

    id = Column(Integer, primary_key=True)
    settlement_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    trade_date = Column(Date, nullable=False, index=True)
    settlement_date = Column(Date, nullable=False, index=True)
    cash_effect = Column(Float, default=0.0)
    status = Column(String, default="pending", nullable=False, index=True)


class ChartTradingLayoutModel(Base):
    __tablename__ = "chart_trading_layouts"

    id = Column(Integer, primary_key=True)
    layout_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    entry = Column(Float, nullable=False)
    stop = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    risk_reward = Column(Float, default=0.0)
    bracket_payload = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class CorporateActionModel(Base):
    __tablename__ = "brokerage_corporate_actions"

    id = Column(Integer, primary_key=True)
    action_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    action_type = Column(String, nullable=False, index=True)
    status = Column(String, default="announced", nullable=False, index=True)
    election_required = Column(Boolean, default=False, nullable=False)
    deadline = Column(DateTime, nullable=True, index=True)
    impact_payload = Column(JSON, nullable=True)
    user_elections = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AccountDocumentModel(Base):
    __tablename__ = "account_documents"

    id = Column(Integer, primary_key=True)
    document_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    document_type = Column(String, nullable=False, index=True)
    period = Column(String, nullable=False, index=True)
    status = Column(String, default="available", nullable=False, index=True)
    formats = Column(JSON, nullable=False, default=list)
    document_payload = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AdminReviewModel(Base):
    __tablename__ = "admin_reviews"

    id = Column(Integer, primary_key=True)
    review_id = Column(String, unique=True, nullable=False, index=True)
    review_type = Column(String, nullable=False, index=True)
    status = Column(String, default="open", nullable=False, index=True)
    severity = Column(String, default="review", nullable=False, index=True)
    subject_ref = Column(String, nullable=False, index=True)
    reviewer = Column(String, nullable=True)
    payload = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class SurveillanceAlertModel(Base):
    __tablename__ = "surveillance_alerts"

    id = Column(Integer, primary_key=True)
    alert_id = Column(String, unique=True, nullable=False, index=True)
    alert_type = Column(String, nullable=False, index=True)
    severity = Column(String, default="review", nullable=False, index=True)
    status = Column(String, default="open", nullable=False, index=True)
    evidence = Column(JSON, nullable=False, default=dict)
    case_id = Column(String, nullable=True, index=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class MarketDataEntitlementModel(Base):
    __tablename__ = "market_data_entitlements"

    id = Column(Integer, primary_key=True)
    entitlement_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    data_type = Column(String, nullable=False, index=True)
    access_level = Column(String, default="delayed", nullable=False, index=True)
    status = Column(String, default="active", nullable=False, index=True)
    vendor = Column(String, default="sandbox", nullable=False)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class DataUsageMeterModel(Base):
    __tablename__ = "data_usage_meters"

    id = Column(Integer, primary_key=True)
    usage_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    data_type = Column(String, nullable=False, index=True)
    vendor = Column(String, nullable=False, index=True)
    units = Column(Integer, default=0, nullable=False)
    estimated_cost = Column(Float, default=0.0)
    audit_id = Column(String, nullable=False, index=True)
    measured_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class RecurringInvestmentPlanModel(Base):
    __tablename__ = "recurring_investment_plans"

    id = Column(Integer, primary_key=True)
    plan_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    dollar_amount = Column(Float, nullable=False)
    cadence = Column(String, default="monthly", nullable=False, index=True)
    status = Column(String, default="pending_precheck", nullable=False, index=True)
    rules = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class ConditionalOrderModel(Base):
    __tablename__ = "conditional_orders"

    id = Column(Integer, primary_key=True)
    conditional_order_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    triggers = Column(JSON, nullable=False, default=list)
    do_not_execute_if = Column(JSON, nullable=True)
    status = Column(String, default="simulated", nullable=False, index=True)
    simulation_result = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class PortfolioReviewPackModel(Base):
    __tablename__ = "portfolio_review_packs"

    id = Column(Integer, primary_key=True)
    report_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, default="generated", nullable=False, index=True)
    formats = Column(JSON, nullable=False, default=list)
    report_payload = Column(JSON, nullable=False, default=dict)
    archive_id = Column(String, nullable=False, index=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class MobileDeviceModel(Base):
    __tablename__ = "mobile_devices"

    id = Column(Integer, primary_key=True)
    device_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    platform = Column(String, nullable=False, index=True)
    push_enabled = Column(Boolean, default=False, nullable=False)
    biometric_approval_supported = Column(Boolean, default=False, nullable=False)
    status = Column(String, default="registered", nullable=False, index=True)
    audit_id = Column(String, nullable=False, index=True)
    registered_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class SupportCaseModel(Base):
    __tablename__ = "support_cases"

    id = Column(Integer, primary_key=True)
    case_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    category = Column(String, nullable=False, index=True)
    status = Column(String, default="open", nullable=False, index=True)
    subject = Column(String, nullable=False)
    messages = Column(JSON, nullable=False, default=list)
    evidence_refs = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AuditRequestModel(Base):
    __tablename__ = "audit_requests"

    id = Column(Integer, primary_key=True)
    request_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    request_type = Column(String, nullable=False, index=True)
    status = Column(String, default="queued", nullable=False, index=True)
    scope = Column(JSON, nullable=False, default=dict)
    export_refs = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class TerminalQuoteModel(Base):
    __tablename__ = "one_stop_terminal_quotes"

    id = Column(Integer, primary_key=True)
    quote_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    bid = Column(Float, nullable=False)
    ask = Column(Float, nullable=False)
    last = Column(Float, nullable=False)
    entitlement_level = Column(String, default="delayed", nullable=False, index=True)
    source_confidence = Column(Float, default=1.0)
    stale = Column(Boolean, default=False, nullable=False)
    audit_id = Column(String, nullable=False, index=True)
    captured_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class LevelIIBookModel(Base):
    __tablename__ = "one_stop_level_ii_books"

    id = Column(Integer, primary_key=True)
    book_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    bids = Column(JSON, nullable=False, default=list)
    asks = Column(JSON, nullable=False, default=list)
    entitlement_status = Column(String, default="blocked", nullable=False, index=True)
    audit_id = Column(String, nullable=False, index=True)
    captured_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class TimeAndSalesPrintModel(Base):
    __tablename__ = "one_stop_time_sales_prints"

    id = Column(Integer, primary_key=True)
    print_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    size = Column(Integer, nullable=False)
    venue = Column(String, default="sandbox", nullable=False, index=True)
    sale_conditions = Column(JSON, nullable=True)
    printed_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class OptionFlowEventModel(Base):
    __tablename__ = "one_stop_option_flow_events"

    id = Column(Integer, primary_key=True)
    flow_id = Column(String, unique=True, nullable=False, index=True)
    underlying = Column(String, nullable=False, index=True)
    contract = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)
    premium = Column(Float, default=0.0)
    unusual_score = Column(Float, default=0.0)
    event_payload = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    captured_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class ResearchSnapshotModel(Base):
    __tablename__ = "one_stop_research_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String, unique=True, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    valuation = Column(JSON, nullable=True)
    financials = Column(JSON, nullable=True)
    source_refs = Column(JSON, nullable=True)
    model_version = Column(String, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class BrokerConnectionModel(Base):
    __tablename__ = "one_stop_broker_connections"

    id = Column(Integer, primary_key=True)
    connection_id = Column(String, unique=True, nullable=False, index=True)
    broker = Column(String, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    status = Column(String, default="paper_connected", nullable=False, index=True)
    live_enabled = Column(Boolean, default=False, nullable=False)
    permissions = Column(JSON, nullable=False, default=list)
    capability_matrix = Column(JSON, nullable=True)
    token_expires_at = Column(DateTime, nullable=True, index=True)
    audit_id = Column(String, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ACATSTransferModel(Base):
    __tablename__ = "one_stop_acats_transfers"

    id = Column(Integer, primary_key=True)
    transfer_id = Column(String, unique=True, nullable=False, index=True)
    direction = Column(String, nullable=False, index=True)
    status = Column(String, default="initiated", nullable=False, index=True)
    delivering_firm = Column(String, nullable=False)
    receiving_firm = Column(String, nullable=False)
    assets = Column(JSON, nullable=True)
    rejected_assets = Column(JSON, nullable=True)
    cost_basis_status = Column(String, default="pending", nullable=False)
    checklist = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class AccountTypeRuleModel(Base):
    __tablename__ = "one_stop_account_type_rules"

    id = Column(Integer, primary_key=True)
    rule_id = Column(String, unique=True, nullable=False, index=True)
    account_type = Column(String, nullable=False, index=True)
    rule_type = Column(String, nullable=False, index=True)
    status = Column(String, default="active", nullable=False)
    constraints = Column(JSON, nullable=False, default=dict)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class PortfolioAnalyticsSnapshotModel(Base):
    __tablename__ = "one_stop_portfolio_analytics"

    id = Column(Integer, primary_key=True)
    analytics_id = Column(String, unique=True, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    performance = Column(JSON, nullable=False, default=dict)
    attribution = Column(JSON, nullable=True)
    risk = Column(JSON, nullable=True)
    income_projection = Column(JSON, nullable=True)
    tax_drag = Column(Float, default=0.0)
    audit_id = Column(String, nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AlertRuleModel(Base):
    __tablename__ = "one_stop_alert_rules"

    id = Column(Integer, primary_key=True)
    alert_rule_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    event_type = Column(String, nullable=False, index=True)
    conditions = Column(JSON, nullable=False, default=list)
    destinations = Column(JSON, nullable=False, default=list)
    status = Column(String, default="active", nullable=False, index=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AutomationPolicyModel(Base):
    __tablename__ = "one_stop_automation_policies"

    id = Column(Integer, primary_key=True)
    policy_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    policy_type = Column(String, nullable=False, index=True)
    guardrails = Column(JSON, nullable=False, default=list)
    simulation_result = Column(JSON, nullable=True)
    status = Column(String, default="simulation", nullable=False, index=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class StrategyMarketplaceListingModel(Base):
    __tablename__ = "one_stop_strategy_marketplace_listings"

    id = Column(Integer, primary_key=True)
    listing_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    strategy_type = Column(String, nullable=False, index=True)
    status = Column(String, default="listed", nullable=False, index=True)
    performance_summary = Column(JSON, nullable=True)
    risk_summary = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class DocumentAISummaryModel(Base):
    __tablename__ = "one_stop_document_ai_summaries"

    id = Column(Integer, primary_key=True)
    summary_id = Column(String, unique=True, nullable=False, index=True)
    document_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    impact_summary = Column(Text, nullable=False)
    source_refs = Column(JSON, nullable=True)
    confidence = Column(Float, default=0.0)
    recommendation_boundary = Column(Text, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class CoachingPlanModel(Base):
    __tablename__ = "one_stop_coaching_plans"

    id = Column(Integer, primary_key=True)
    plan_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    focus_area = Column(String, nullable=False, index=True)
    goals = Column(JSON, nullable=False, default=list)
    status = Column(String, default="active", nullable=False, index=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class CollaborationSpaceModel(Base):
    __tablename__ = "one_stop_collaboration_spaces"

    id = Column(Integer, primary_key=True)
    space_id = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    privacy = Column(String, default="private", nullable=False, index=True)
    members = Column(JSON, nullable=False, default=list)
    shared_assets = Column(JSON, nullable=True)
    moderation_status = Column(String, default="active", nullable=False)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class FeeYieldRecordModel(Base):
    __tablename__ = "one_stop_fee_yield_records"

    id = Column(Integer, primary_key=True)
    record_id = Column(String, unique=True, nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    annualized_rate = Column(Float, nullable=True)
    broker = Column(String, nullable=True, index=True)
    disclosure = Column(Text, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class TrustSecurityEventModel(Base):
    __tablename__ = "one_stop_trust_security_events"

    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    status = Column(String, default="open", nullable=False, index=True)
    severity = Column(String, default="review", nullable=False, index=True)
    payload = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class NotificationPolicyModel(Base):
    __tablename__ = "one_stop_notification_policies"

    id = Column(Integer, primary_key=True)
    policy_id = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    channel = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    quiet_hours = Column(JSON, nullable=True)
    escalation_rules = Column(JSON, nullable=True)
    audit_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class NotificationDeliveryLogModel(Base):
    __tablename__ = "one_stop_notification_delivery_logs"

    id = Column(Integer, primary_key=True)
    delivery_id = Column(String, unique=True, nullable=False, index=True)
    policy_id = Column(String, nullable=True, index=True)
    channel = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    destination = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    audit_id = Column(String, nullable=False, index=True)
    delivered_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
