"""
InstrumentTagger Agent.

Classifies financial instruments (stocks, ETFs, bond funds) into the
platform's canonical allocation schema. Uses the OpenAI Agents SDK with
Bedrock Claude via LiteLLM for structured classification.
"""
import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.database.src.schemas import AssetClassType, InstrumentCreate, RegionType, SectorType
from .templates import CLASSIFICATION_PROMPT, TAGGER_INSTRUCTIONS

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

logger = logging.getLogger()

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")


# ------------------------------------------------------- structured output

class AllocationBreakdown(BaseModel):
    """Asset-class allocation. Must sum to 100."""
    model_config = ConfigDict(extra="forbid")

    equity: float = Field(default=0.0, ge=0, le=100)
    fixed_income: float = Field(default=0.0, ge=0, le=100)
    real_estate: float = Field(default=0.0, ge=0, le=100)
    commodities: float = Field(default=0.0, ge=0, le=100)
    cash: float = Field(default=0.0, ge=0, le=100)
    alternatives: float = Field(default=0.0, ge=0, le=100)


class RegionAllocation(BaseModel):
    """Region allocation. Must sum to 100."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    north_america: float = Field(default=0.0, ge=0, le=100)
    europe: float = Field(default=0.0, ge=0, le=100)
    asia: float = Field(default=0.0, ge=0, le=100)
    latin_america: float = Field(default=0.0, ge=0, le=100)
    africa: float = Field(default=0.0, ge=0, le=100)
    middle_east: float = Field(default=0.0, ge=0, le=100)
    oceania: float = Field(default=0.0, ge=0, le=100)
    global_: float = Field(default=0.0, ge=0, le=100, alias="global")
    international: float = Field(default=0.0, ge=0, le=100)


class SectorAllocation(BaseModel):
    """Sector allocation. Must sum to 100."""
    model_config = ConfigDict(extra="forbid")

    technology: float = Field(default=0.0, ge=0, le=100)
    healthcare: float = Field(default=0.0, ge=0, le=100)
    financials: float = Field(default=0.0, ge=0, le=100)
    consumer_discretionary: float = Field(default=0.0, ge=0, le=100)
    consumer_staples: float = Field(default=0.0, ge=0, le=100)
    industrials: float = Field(default=0.0, ge=0, le=100)
    materials: float = Field(default=0.0, ge=0, le=100)
    energy: float = Field(default=0.0, ge=0, le=100)
    utilities: float = Field(default=0.0, ge=0, le=100)
    real_estate: float = Field(default=0.0, ge=0, le=100)
    communication: float = Field(default=0.0, ge=0, le=100)
    treasury: float = Field(default=0.0, ge=0, le=100)
    corporate: float = Field(default=0.0, ge=0, le=100)
    mortgage: float = Field(default=0.0, ge=0, le=100)
    government_related: float = Field(default=0.0, ge=0, le=100)
    commodities: float = Field(default=0.0, ge=0, le=100)
    diversified: float = Field(default=0.0, ge=0, le=100)
    other: float = Field(default=0.0, ge=0, le=100)


class InstrumentClassification(BaseModel):
    """Full structured classification returned by the LLM."""
    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str
    instrument_type: str
    current_price: float = Field(gt=0)

    allocation_asset_class: AllocationBreakdown
    allocation_regions: RegionAllocation
    allocation_sectors: SectorAllocation

    @field_validator("allocation_asset_class")
    def _asset_sum(cls, v):
        total = v.equity + v.fixed_income + v.real_estate + v.commodities + v.cash + v.alternatives
        if abs(total - 100) > 3:
            raise ValueError(f"Asset class allocations must sum to 100, got {total}")
        return v

    @field_validator("allocation_regions")
    def _region_sum(cls, v):
        total = (
            v.north_america + v.europe + v.asia + v.latin_america
            + v.africa + v.middle_east + v.oceania + v.global_ + v.international
        )
        if abs(total - 100) > 3:
            raise ValueError(f"Region allocations must sum to 100, got {total}")
        return v

    @field_validator("allocation_sectors")
    def _sector_sum(cls, v):
        total = (
            v.technology + v.healthcare + v.financials + v.consumer_discretionary
            + v.consumer_staples + v.industrials + v.materials + v.energy
            + v.utilities + v.real_estate + v.communication + v.treasury
            + v.corporate + v.mortgage + v.government_related + v.commodities
            + v.diversified + v.other
        )
        if abs(total - 100) > 3:
            raise ValueError(f"Sector allocations must sum to 100, got {total}")
        return v


# ------------------------------------------------------- classification

async def classify_instrument(
    symbol: str,
    name: str,
    instrument_type: str = "etf",
    *,
    model_id: Optional[str] = None,
    region: Optional[str] = None,
) -> InstrumentClassification:
    """Classify a single instrument via the LLM."""
    try:
        from agents import Agent, RunConfig, Runner  # type: ignore[import]
        from agents.extensions.models.litellm_model import LitellmModel  # type: ignore[import]
        from litellm.exceptions import RateLimitError as _RateLimitError  # type: ignore[import]  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "openai-agents and litellm packages are required for instrument classification. "
            "Install with: pip install openai-agents litellm"
        ) from exc
    selected_region = region or BEDROCK_REGION
    selected_model = model_id or BEDROCK_MODEL_ID
    os.environ["AWS_REGION_NAME"] = selected_region
    model_route = selected_model if selected_model.startswith("bedrock/") else f"bedrock/converse/{selected_model}"
    model = LitellmModel(model=model_route)

    task = CLASSIFICATION_PROMPT.format(
        symbol=symbol, name=name, instrument_type=instrument_type
    )

    agent = Agent(
        name="InstrumentTagger",
        instructions=TAGGER_INSTRUCTIONS,
        model=model,
        tools=[],
        output_type=InstrumentClassification,
    )
    result = await Runner.run(
        agent,
        input=task,
        max_turns=5,
        run_config=RunConfig(tracing_disabled=True),
    )
    return result.final_output_as(InstrumentClassification)


async def tag_instruments(
    instruments: List[Dict[str, Any]],
    *,
    model_id: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Optional[InstrumentClassification]]:
    """Classify a batch of instruments sequentially with pacing."""
    import asyncio

    results: List[Optional[InstrumentClassification]] = []
    for i, inst in enumerate(instruments):
        if i > 0:
            await asyncio.sleep(0.5)
        try:
            classification = await classify_instrument(
                symbol=inst["symbol"],
                name=inst.get("name") or "",
                instrument_type=inst.get("instrument_type") or "etf",
                model_id=model_id,
                region=region,
            )
            logger.info("Tagger: classified %s", inst["symbol"])
            results.append(classification)
        except Exception:
            logger.exception("Tagger: failed %s", inst.get("symbol"))
            results.append(None)
    return results


# ---------------------------------------------------------- conversion

def classification_to_db_format(classification: InstrumentClassification) -> InstrumentCreate:
    """Convert a classification into the platform's InstrumentCreate schema."""
    asset_classes: Dict[AssetClassType, float] = {
        k: v for k, v in {
            "equity": classification.allocation_asset_class.equity,
            "fixed_income": classification.allocation_asset_class.fixed_income,
            "real_estate": classification.allocation_asset_class.real_estate,
            "commodities": classification.allocation_asset_class.commodities,
            "cash": classification.allocation_asset_class.cash,
            "alternatives": classification.allocation_asset_class.alternatives,
        }.items() if v > 0
    }

    regions: Dict[RegionType, float] = {
        k: v for k, v in {
            "north_america": classification.allocation_regions.north_america,
            "europe": classification.allocation_regions.europe,
            "asia": classification.allocation_regions.asia,
            "latin_america": classification.allocation_regions.latin_america,
            "africa": classification.allocation_regions.africa,
            "middle_east": classification.allocation_regions.middle_east,
            "oceania": classification.allocation_regions.oceania,
            "global": classification.allocation_regions.global_,
            "international": classification.allocation_regions.international,
        }.items() if v > 0
    }

    sectors: Dict[SectorType, float] = {
        k: v for k, v in {
            "technology": classification.allocation_sectors.technology,
            "healthcare": classification.allocation_sectors.healthcare,
            "financials": classification.allocation_sectors.financials,
            "consumer_discretionary": classification.allocation_sectors.consumer_discretionary,
            "consumer_staples": classification.allocation_sectors.consumer_staples,
            "industrials": classification.allocation_sectors.industrials,
            "materials": classification.allocation_sectors.materials,
            "energy": classification.allocation_sectors.energy,
            "utilities": classification.allocation_sectors.utilities,
            "real_estate": classification.allocation_sectors.real_estate,
            "communication": classification.allocation_sectors.communication,
            "treasury": classification.allocation_sectors.treasury,
            "corporate": classification.allocation_sectors.corporate,
            "mortgage": classification.allocation_sectors.mortgage,
            "government_related": classification.allocation_sectors.government_related,
            "commodities": classification.allocation_sectors.commodities,
            "diversified": classification.allocation_sectors.diversified,
            "other": classification.allocation_sectors.other,
        }.items() if v > 0
    }

    return InstrumentCreate(
        symbol=classification.symbol,
        name=classification.name,
        instrument_type=classification.instrument_type,
        current_price=Decimal(str(classification.current_price)),
        allocation_asset_class=asset_classes,
        allocation_regions=regions,
        allocation_sectors=sectors,
        source="instrument_tagger",
    )