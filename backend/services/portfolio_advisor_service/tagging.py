from __future__ import annotations

import asyncio
import os
from typing import Any

from pydantic import BaseModel, ConfigDict

from backend.services.agents.instrument_tagger.agent import (
    AllocationBreakdown,
    RegionAllocation,
    SectorAllocation,
)


TAGGER_INSTRUCTIONS = """Classify a named financial instrument's asset-class, region, and sector allocations.
Use only well-established instrument composition knowledge. Do not return any price or valuation.
If the instrument is not identifiable from its symbol and provided name/type, state that classification
is unknown rather than guessing. Every allocation must validate to 100 percent. These classifications
are research metadata only and must never be interpreted as trade instructions."""


class InstrumentAllocationClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    allocation_asset_class: AllocationBreakdown
    allocation_regions: RegionAllocation
    allocation_sectors: SectorAllocation


def _model_route(model_id: str) -> str:
    if model_id.startswith("bedrock/"):
        return model_id
    return f"bedrock/converse/{model_id}"


async def classify_missing_instruments(
    instruments: list[dict[str, str]],
    *,
    model_id: str,
    region: str,
) -> list[dict[str, Any]]:
    if not instruments:
        return []
    try:
        from agents import Agent, RunConfig, Runner  # type: ignore[import]
        from agents.extensions.models.litellm_model import LitellmModel  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "openai-agents package is required for instrument tagging. "
            "Install it with: pip install openai-agents"
        ) from exc
    os.environ["AWS_REGION_NAME"] = region
    model = LitellmModel(model=_model_route(model_id))
    agent = Agent(
        name="Instrument Allocation Tagger",
        instructions=TAGGER_INSTRUCTIONS,
        model=model,
        output_type=InstrumentAllocationClassification,
    )
    results = []
    for instrument in instruments:
        prompt = (
            f"Classify allocations for symbol {instrument['symbol']}, "
            f"name {instrument['name']}, type {instrument['instrument_type']}. "
            "Return only the validated allocation fields. Do not estimate its current price."
        )
        try:
            run = await Runner.run(
                agent,
                input=prompt,
                max_turns=2,
                run_config=RunConfig(tracing_disabled=True),
            )
            classification = run.final_output_as(InstrumentAllocationClassification)
            if classification.symbol.strip().upper() != instrument["symbol"].upper():
                continue
            results.append(classification.model_dump(mode="json", by_alias=True))
        except Exception:
            continue
    return results


def classify_missing_instruments_sync(
    instruments: list[dict[str, str]], *, model_id: str, region: str
) -> list[dict[str, Any]]:
    return asyncio.run(classify_missing_instruments(instruments, model_id=model_id, region=region))