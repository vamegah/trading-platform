"""
Alex Researcher Service — Investment research agent HTTP API.

Endpoints:
    GET  /                → service identity
    GET  /health          → liveness probe
    GET  /ready           → readiness probe (checks deps)
    POST /research        → run agent on a topic/ticker/sector/macro
    GET  /research/auto   → scheduled run (agent picks topic)
    GET  /test-bedrock    → model connectivity diagnostic (guarded)

Design notes:
- Uses the multi-server research_lifespan (Playwright + news feed).
- Parses and validates the agent's structured JSON brief before returning.
- Bounded concurrency (Playwright is expensive; don't fan out unbounded).
- Optional API-key auth via RESEARCHER_API_KEY.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from agents import Agent, RunConfig, RunHooks, Runner
from agents.extensions.models.litellm_model import LitellmModel

from backend.services.agents.researcher_agent.context import (
    DEFAULT_RESEARCH_PROMPT,
    MACRO_EVENT_PROMPT,
    SECTOR_SCAN_PROMPT,
    TICKER_DEEP_DIVE_PROMPT,
    get_agent_instructions,
)
from backend.services.agents.researcher_agent.mcp_servers import (
    MCP_LOGGING_ENABLED,
    research_lifespan,
    select_servers_by_tag,
)
from backend.services.agents.researcher_agent.tools import ingest_financial_document


# ---------------------------------------------------------------------------
# BOOTSTRAP
# ---------------------------------------------------------------------------

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


RESEARCHER_MODEL = os.getenv("RESEARCHER_MODEL", "bedrock/global.openai.gpt-oss-120b-1:0")
RESEARCHER_MAX_TURNS = int(os.getenv("RESEARCHER_MAX_TURNS", "15"))
RESEARCHER_RUN_TIMEOUT = float(os.getenv("RESEARCHER_RUN_TIMEOUT", "600"))
RESEARCHER_MAX_CONCURRENCY = int(os.getenv("RESEARCHER_MAX_CONCURRENCY", "4"))
RESEARCHER_API_KEY = os.getenv("RESEARCHER_API_KEY", "").strip()
ENABLE_DIAGNOSTICS = _env_bool("RESEARCHER_ENABLE_DIAGNOSTICS", default=False)
APP_VERSION = os.getenv("RESEARCHER_VERSION", "2.0.0")


def _set_aws_region_env() -> str:
    """Set AWS region once at import time (avoid per-request env races)."""
    region = os.getenv("BEDROCK_REGION", "us-west-2")
    os.environ.setdefault("AWS_REGION_NAME", region)
    os.environ.setdefault("AWS_REGION", region)
    os.environ.setdefault("AWS_DEFAULT_REGION", region)
    return region


AWS_REGION = _set_aws_region_env()

# Bounded concurrency for Playwright + LLM runs
_run_semaphore = asyncio.Semaphore(RESEARCHER_MAX_CONCURRENCY)


# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

ResearchMode = Literal["auto", "ticker", "sector", "macro", "topic"]


class ResearchRequest(BaseModel):
    topic: Optional[str] = Field(
        default=None,
        description="Free-form topic if mode='topic' (or leave unset for auto).",
    )
    tickers: list[str] = Field(
        default_factory=list,
        description="Tickers to focus on (mode='ticker').",
    )
    sector: Optional[str] = Field(
        default=None, description="Sector label (mode='sector').",
    )
    mode: ResearchMode = Field(
        default="auto",
        description="Which research workflow to run.",
    )
    window: str = Field(default="24h", description="News window: 24h | 7d | custom.")
    ingest: bool = Field(
        default=True,
        description="Whether the agent should persist the brief via ingest_financial_document.",
    )


class SourceRef(BaseModel):
    name: str
    url: str
    published_at: Optional[str] = None
    tier: Optional[int] = None


class NewsItem(BaseModel):
    headline: str
    event_type: str
    tickers: list[str] = Field(default_factory=list)
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL", "MIXED"]
    magnitude: Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
    time_horizon: Literal["INTRADAY", "DAYS", "WEEKS", "MONTHS"]
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    status: Literal["FACT", "RUMOR", "OPINION"]
    key_numbers: dict[str, Any] = Field(default_factory=dict)
    summary: str
    sources: list[SourceRef] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    stale: bool = False


class TopSignal(BaseModel):
    ticker: str
    direction: str
    rationale: str


class SignalBrief(BaseModel):
    generated_at_utc: str
    window: str
    universe: list[str] = Field(default_factory=list)
    items: list[NewsItem] = Field(default_factory=list)
    top_signal: Optional[TopSignal] = None
    risks_and_caveats: list[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    run_id: str
    mode: ResearchMode
    brief: Optional[SignalBrief] = None
    raw_output: str
    parse_ok: bool
    duration_ms: int
    timestamp: str


# ---------------------------------------------------------------------------
# LOGGING HOOKS
# ---------------------------------------------------------------------------

def _trim_for_log(value: Any, max_length: int = 1500) -> str:
    text = str(value)
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}... [trimmed {len(text) - max_length} chars]"


class ResearchLoggingHooks(RunHooks):
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id

    async def on_tool_start(self, context, agent, tool) -> None:
        if MCP_LOGGING_ENABLED:
            logger.info(
                "[run=%s][tool:start] name=%s type=%s",
                self.run_id,
                getattr(tool, "name", type(tool).__name__),
                type(tool).__name__,
            )

    async def on_tool_end(self, context, agent, tool, result) -> None:
        if MCP_LOGGING_ENABLED:
            logger.info(
                "[run=%s][tool:end] name=%s result=%s",
                self.run_id,
                getattr(tool, "name", type(tool).__name__),
                _trim_for_log(result),
            )


# ---------------------------------------------------------------------------
# AUTH (optional)
# ---------------------------------------------------------------------------

async def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Require the internal shared key whenever one is configured."""
    if not RESEARCHER_API_KEY:
        return
    if not x_api_key or x_api_key != RESEARCHER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )


# ---------------------------------------------------------------------------
# PROMPT SELECTION
# ---------------------------------------------------------------------------

def build_query(req: ResearchRequest) -> str:
    if req.mode == "ticker":
        tickers = ", ".join(req.tickers) or "unspecified"
        return TICKER_DEEP_DIVE_PROMPT.format(ticker=tickers)
    if req.mode == "sector":
        return SECTOR_SCAN_PROMPT.format(sector=req.sector or "unspecified")
    if req.mode == "macro":
        return MACRO_EVENT_PROMPT
    if req.mode == "topic" and req.topic:
        return (
            f"Research this investment topic: {req.topic}\n"
            f"Window: {req.window}. Follow the 7-step workflow."
        )
    return DEFAULT_RESEARCH_PROMPT.format(
        universe=req.sector or "broad_market",
        window=req.window,
        tickers=", ".join(req.tickers) or "n/a",
    )


# ---------------------------------------------------------------------------
# STRUCTURED OUTPUT PARSER
# ---------------------------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_signal_brief(raw_output: str) -> tuple[Optional[SignalBrief], bool]:
    """
    Try to pull the JSON block out of the agent output and validate it.

    Returns (brief, parse_ok). parse_ok=False means we couldn't validate,
    but the raw text is still returned to the caller.
    """
    if not raw_output:
        return None, False

    match = _JSON_BLOCK_RE.search(raw_output)
    candidates: list[str] = []
    if match:
        candidates.append(match.group(1))

    # Fallback: last { ... } region
    first, last = raw_output.find("{"), raw_output.rfind("}")
    if first != -1 and last > first:
        candidates.append(raw_output[first : last + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            return SignalBrief.model_validate(parsed), True
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Brief parse attempt failed: %s", exc)
            continue

    return None, False


# ---------------------------------------------------------------------------
# AGENT RUNNER
# ---------------------------------------------------------------------------

async def run_research_agent(req: ResearchRequest) -> ResearchResponse:
    """Execute one research run and return the structured result."""
    import uuid

    run_id = uuid.uuid4().hex[:12]
    started = datetime.now(UTC)
    query = build_query(req)

    if MCP_LOGGING_ENABLED:
        logger.info(
            "[run=%s] mode=%s window=%s tickers=%s sector=%s query=%s",
            run_id,
            req.mode,
            req.window,
            req.tickers,
            req.sector,
            _trim_for_log(query, max_length=400),
        )

    model = LitellmModel(model=RESEARCHER_MODEL)

    # Choose servers: broad scan needs news; deep dive needs playwright.
    if req.mode in {"ticker", "sector", "topic"}:
        server_names = select_servers_by_tag("broad_scan", "browser")
    else:
        server_names = select_servers_by_tag("broad_scan", "browser")

    async with _run_semaphore:
        async with research_lifespan(servers=server_names) as servers:
            mcp_list = list(servers.values())
            if MCP_LOGGING_ENABLED:
                logger.info(
                    "[run=%s] MCP servers active: %s",
                    run_id,
                    list(servers.keys()),
                )

            agent = Agent(
                name="Alex Investment Researcher",
                instructions=get_agent_instructions(allow_ingest=req.ingest),
                model=model,
                tools=[ingest_financial_document] if req.ingest else [],
                mcp_servers=mcp_list,
            )

            try:
                result = await asyncio.wait_for(
                    Runner.run(
                        agent,
                        input=query,
                        max_turns=RESEARCHER_MAX_TURNS,
                        run_config=RunConfig(tracing_disabled=True),
                        hooks=ResearchLoggingHooks(run_id)
                        if MCP_LOGGING_ENABLED
                        else None,
                    ),
                    timeout=RESEARCHER_RUN_TIMEOUT,
                )
            except asyncio.TimeoutError as exc:
                logger.exception("[run=%s] agent timed out", run_id)
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Research run exceeded {RESEARCHER_RUN_TIMEOUT}s",
                ) from exc
            except Exception:
                logger.exception("[run=%s] agent run failed", run_id)
                raise

    raw_output = result.final_output or ""
    brief, parse_ok = extract_signal_brief(raw_output)

    duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)

    if MCP_LOGGING_ENABLED:
        logger.info(
            "[run=%s] completed in %sms parse_ok=%s items=%s",
            run_id,
            duration_ms,
            parse_ok,
            len(brief.items) if brief else 0,
        )

    return ResearchResponse(
        run_id=run_id,
        mode=req.mode,
        brief=brief,
        raw_output=raw_output,
        parse_ok=parse_ok,
        duration_ms=duration_ms,
        timestamp=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# APP LIFESPAN
# ---------------------------------------------------------------------------

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info(
        "Alex Researcher starting | version=%s model=%s region=%s "
        "max_concurrency=%s run_timeout=%ss auth=%s",
        APP_VERSION,
        RESEARCHER_MODEL,
        AWS_REGION,
        RESEARCHER_MAX_CONCURRENCY,
        RESEARCHER_RUN_TIMEOUT,
        "enabled" if RESEARCHER_API_KEY else "disabled",
    )
    yield
    logger.info("Alex Researcher shutting down")


app = FastAPI(title="Alex Researcher Service", version=APP_VERSION, lifespan=app_lifespan)


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "service": "Alex Researcher",
        "version": APP_VERSION,
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    """Liveness probe — cheap, no dependency calls."""
    return {
        "service": "Alex Researcher",
        "version": APP_VERSION,
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/ready")
async def ready() -> JSONResponse:
    """Readiness probe — checks configuration, not network calls."""
    issues: list[str] = []
    if not RESEARCHER_MODEL:
        issues.append("RESEARCHER_MODEL not set")
    if not os.getenv("AWS_DEFAULT_REGION"):
        issues.append("AWS_DEFAULT_REGION not set")

    ready_state = not issues
    return JSONResponse(
        status_code=200 if ready_state else 503,
        content={
            "ready": ready_state,
            "issues": issues,
            "region": AWS_REGION,
            "model": RESEARCHER_MODEL,
            "mcp_logging_enabled": MCP_LOGGING_ENABLED,
            "auth_enabled": bool(RESEARCHER_API_KEY),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.post(
    "/research",
    response_model=ResearchResponse,
    dependencies=[Depends(require_api_key)],
)
async def research(request: ResearchRequest) -> ResearchResponse:
    """
    Run the Alex research agent.

    Returns the structured SignalBrief (when parseable) plus the raw output.
    Downstream trading logic should consume `brief` and fall back to
    `raw_output` only for human review when `parse_ok=False`.
    """
    try:
        return await run_research_agent(request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Research endpoint failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/research/auto",
    response_model=ResearchResponse,
    dependencies=[Depends(require_api_key)],
)
async def research_auto() -> ResearchResponse:
    """Automated run for scheduled jobs (EventBridge etc.)."""
    return await research(ResearchRequest(mode="auto"))


@app.get(
    "/test-bedrock",
    dependencies=[Depends(require_api_key)],
)
async def test_bedrock() -> dict[str, Any]:
    """Model connectivity diagnostic. Disabled unless RESEARCHER_ENABLE_DIAGNOSTICS=true."""
    if not ENABLE_DIAGNOSTICS:
        raise HTTPException(status_code=404, detail="Diagnostics disabled")

    try:
        import boto3

        session = boto3.Session()
        client = boto3.client("bedrock-runtime", region_name=AWS_REGION)  # noqa: F841

        try:
            bedrock_client = boto3.client("bedrock", region_name=AWS_REGION)
            models = bedrock_client.list_foundation_models()
            openai_models = [
                m["modelId"]
                for m in models["modelSummaries"]
                if "openai" in m["modelId"].lower()
            ]
        except Exception as list_error:
            openai_models = f"Error listing: {list_error}"

        model = LitellmModel(model=RESEARCHER_MODEL)
        agent = Agent(
            name="Test Agent",
            instructions="You are a helpful assistant. Be very brief.",
            model=model,
        )
        result = await Runner.run(agent, input="Say hello in 5 words or less", max_turns=1)

        return {
            "status": "success",
            "model": str(model.model),
            "region": session.region_name,
            "response": result.final_output,
            "available_openai_models": openai_models,
        }
    except Exception as exc:
        logger.exception("Bedrock diagnostic failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )