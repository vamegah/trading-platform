from pydantic import BaseModel, Field, field_validator, model_validator


ALLOCATION_KEYS = {"equity", "fixed_income", "real_estate", "commodities", "cash"}


class RetirementAssumptions(BaseModel):
    years_until_retirement: int = Field(ge=0, le=70)
    annual_contribution: float = Field(ge=0, le=10_000_000)
    target_annual_income: float = Field(gt=0, le=10_000_000)
    years_in_retirement: int = Field(default=30, ge=1, le=70)
    inflation_rate: float = Field(default=0.025, ge=0, le=0.2)
    allocation: dict[str, float]
    simulations: int = Field(default=1000, ge=100, le=5000)
    seed: int = Field(default=0, ge=0, le=2**32 - 1)

    @field_validator("allocation")
    @classmethod
    def validate_allocation(cls, value: dict[str, float]) -> dict[str, float]:
        if not value or set(value) - ALLOCATION_KEYS:
            raise ValueError("allocation must use supported asset classes")
        if any(weight < 0 or weight > 1 for weight in value.values()):
            raise ValueError("allocation weights must be between 0 and 1")
        if abs(sum(value.values()) - 1.0) > 0.001:
            raise ValueError("allocation weights must sum to 1")
        return value


class PortfolioAdvisorRequest(BaseModel):
    portfolio_id: int = Field(gt=0)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)
    max_market_data_age_days: int = Field(default=5, ge=0, le=365)
    use_llm: bool = False
    retirement: RetirementAssumptions | None = None

    @field_validator("idempotency_key")
    @classmethod
    def strip_idempotency_key(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @model_validator(mode="after")
    def validate_nonblank_idempotency_key(self) -> "PortfolioAdvisorRequest":
        if self.idempotency_key == "":
            raise ValueError("idempotency_key cannot be blank")
        return self