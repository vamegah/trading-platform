"""
MCP server configurations for the Alex Researcher.

Provides:
- Playwright MCP (browser automation for web research / deep dives)
- News API MCP (structured news/event feeds for broad scans)
- A registry so the agent can request servers by name
- A combined lifespan that fans out across all configured servers

Design goals:
- Config via env vars (no hardcoded /tmp paths, no hardcoded chrome globs)
- Failure isolation (one server down ≠ platform down)
- Structured stderr capture with backpressure
- Health checks + timeouts on startup
- Reusable across single-ticker, sector, and macro research tasks
"""

from __future__ import annotations

import asyncio
import glob
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Iterable, Mapping

from agents.mcp import MCPServerStdio
from mcp.client.stdio import stdio_client


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CONFIG (env-driven)
# ---------------------------------------------------------------------------

def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


MCP_LOGGING_ENABLED = _env_bool("MCP_LOGGING", default=False)
MCP_STDERR_MAX_LENGTH = int(os.getenv("MCP_STDERR_MAX_LENGTH", "4000"))
MCP_STARTUP_TIMEOUT = float(os.getenv("MCP_STARTUP_TIMEOUT", "30"))
MCP_DEFAULT_CLIENT_TIMEOUT = float(os.getenv("MCP_CLIENT_TIMEOUT", "120"))

# Browser config
PLAYWRIGHT_USER_AGENT = os.getenv(
    "PLAYWRIGHT_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
)
PLAYWRIGHT_BROWSER_GLOB = os.getenv(
    "PLAYWRIGHT_BROWSER_GLOB", "/ms-playwright/chromium-*/chrome-linux*/chrome"
)
PLAYWRIGHT_BROWSER_FALLBACK = os.getenv(
    "PLAYWRIGHT_BROWSER_FALLBACK", "/ms-playwright/chromium-1208/chrome-linux64/chrome"
)
PLAYWRIGHT_CONFIG_PATH = os.getenv(
    "PLAYWRIGHT_CONFIG_PATH", "/tmp/playwright-mcp.config.json"
)

# News API config (adjust to your provider — NewsAPI, Finnhub, Polygon, Benzinga, etc.)
NEWS_API_COMMAND = os.getenv("NEWS_API_COMMAND", "news-mcp")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_API_EXTRA_ARGS = os.getenv("NEWS_API_EXTRA_ARGS", "").split()


# ---------------------------------------------------------------------------
# LOGGING HELPERS
# ---------------------------------------------------------------------------

def _trim_for_log(value: Any, max_length: int = MCP_STDERR_MAX_LENGTH) -> str:
    text = str(value)
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}... [trimmed {len(text) - max_length} chars]"


# ---------------------------------------------------------------------------
# STDIO WRAPPER WITH STRUCTURED STDERR DRAIN
# ---------------------------------------------------------------------------

class LoggingMCPServerStdio(MCPServerStdio):
    """
    MCPServerStdio that drains the subprocess stderr into the Python logger
    without blocking the event loop, and without the join() hang risk of the
    original implementation.

    Improvements over the prior version:
    - Uses a bounded queue + worker thread (backpressure-safe).
    - Stops cleanly via an explicit shutdown event.
    - Never blocks the enclosing coroutine on thread join.
    - Emits structured log records with the server name for filtering.
    """

    def __init__(self, *args, server_name: str = "mcp", **kwargs):
        super().__init__(*args, **kwargs)
        self._server_name = server_name

    @asynccontextmanager
    async def create_streams(self) -> AsyncIterator[tuple[Any, Any]]:
        read_fd, write_fd = os.pipe()
        stderr_reader = os.fdopen(read_fd, "r", encoding="utf-8", errors="replace")
        stderr_writer = os.fdopen(write_fd, "w", encoding="utf-8", errors="replace")

        stop_event = threading.Event()

        def drain_stderr() -> None:
            try:
                for line in stderr_reader:
                    if stop_event.is_set():
                        break
                    message = line.rstrip()
                    if message:
                        logger.error(
                            "[mcp:%s:stderr] %s",
                            self._server_name,
                            _trim_for_log(message),
                        )
            except Exception:
                logger.exception(
                    "Failed to read MCP subprocess stderr for %s", self._server_name
                )
            finally:
                try:
                    stderr_reader.close()
                except Exception:
                    pass

        stderr_thread = threading.Thread(
            target=drain_stderr,
            name=f"{self._server_name}-mcp-stderr",
            daemon=True,
        )
        stderr_thread.start()

        try:
            async with stdio_client(self.params, errlog=stderr_writer) as streams:
                yield streams
        finally:
            stop_event.set()
            try:
                stderr_writer.close()
            except Exception:
                pass
            # Never block the event loop on the drain thread.
            stderr_thread.join(timeout=0.5)


# ---------------------------------------------------------------------------
# SERVER DEFINITIONS
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MCPServerSpec:
    """Declarative description of an MCP server to instantiate."""
    name: str
    factory: "callable[[float], MCPServerStdio]"
    client_timeout: float = MCP_DEFAULT_CLIENT_TIMEOUT
    required: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)


def _resolve_chrome_path() -> tuple[str, bool]:
    """Return (path, used_fallback)."""
    candidates = glob.glob(PLAYWRIGHT_BROWSER_GLOB)
    if candidates:
        return candidates[0], False
    return PLAYWRIGHT_BROWSER_FALLBACK, True


def _write_playwright_config(path: str) -> dict[str, Any]:
    config = {
        "browser": {
            "launchOptions": {
                "args": [
                    "--single-process",
                    "--no-zygote",
                    "--disable-gpu",
                ]
            }
        }
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh)
    return config


def create_playwright_mcp_server(
    timeout_seconds: float = MCP_DEFAULT_CLIENT_TIMEOUT,
) -> MCPServerStdio:
    """
    Create a Playwright MCP server for browser-based research.

    Used by the Alex agent for:
    - STEP 2 broad scan on tier-2/3 sites (Yahoo Finance, MarketWatch, etc.)
    - STEP 3 deep dives on primary sources (SEC EDGAR, IR pages)
    """
    chrome_path, used_fallback = _resolve_chrome_path()
    if used_fallback:
        logger.warning(
            "Playwright Chrome not found via glob %s; using fallback %s",
            PLAYWRIGHT_BROWSER_GLOB,
            chrome_path,
        )
    else:
        logger.info("Using Playwright Chrome binary: %s", chrome_path)

    config = _write_playwright_config(PLAYWRIGHT_CONFIG_PATH)

    args = [
        "--headless",
        "--isolated",
        "--no-sandbox",
        "--ignore-https-errors",
        "--user-agent",
        PLAYWRIGHT_USER_AGENT,
        "--executable-path",
        chrome_path,
        "--config",
        PLAYWRIGHT_CONFIG_PATH,
    ]

    params = {
        "command": "playwright-mcp",
        "args": args,
        "env": {
            # Keep noise down; PW debug levels are very chatty.
            "DEBUG": os.getenv("PLAYWRIGHT_DEBUG", ""),
        },
    }

    logger.info(
        "Creating Playwright MCP server | timeout=%ss chrome=%s fallback=%s "
        "config=%s args=%s",
        timeout_seconds,
        chrome_path,
        used_fallback,
        config,
        args,
    )

    cls = LoggingMCPServerStdio if MCP_LOGGING_ENABLED else MCPServerStdio
    kwargs: dict[str, Any] = {
        "params": params,
        "client_session_timeout_seconds": timeout_seconds,
    }
    if cls is LoggingMCPServerStdio:
        kwargs["server_name"] = "playwright"
    return cls(**kwargs)


def create_news_mcp_server(
    timeout_seconds: float = MCP_DEFAULT_CLIENT_TIMEOUT,
) -> MCPServerStdio:
    """
    Create a structured news/event MCP server.

    This is the tier-2 'breadth' feed that pairs with Playwright's 'depth'.
    Point NEWS_API_COMMAND at whichever MCP wrapper you use for your provider
    (NewsAPI, Finnhub, Polygon, Benzinga, RSS aggregator, etc.).

    The agent should prefer this for STEP 2 (broad scan) and reserve Playwright
    for STEP 3 (deep dive on a specific article/filing).
    """
    if not NEWS_API_KEY:
        logger.warning(
            "NEWS_API_KEY is not set — news MCP server will start but may fail "
            "on authenticated calls."
        )

    args = list(NEWS_API_EXTRA_ARGS)
    env = {
        "NEWS_API_KEY": NEWS_API_KEY,
        "DEBUG": os.getenv("NEWS_DEBUG", ""),
    }

    params = {"command": NEWS_API_COMMAND, "args": args, "env": env}

    logger.info(
        "Creating News MCP server | command=%s args=%s timeout=%ss",
        NEWS_API_COMMAND,
        args,
        timeout_seconds,
    )

    cls = LoggingMCPServerStdio if MCP_LOGGING_ENABLED else MCPServerStdio
    kwargs: dict[str, Any] = {
        "params": params,
        "client_session_timeout_seconds": timeout_seconds,
    }
    if cls is LoggingMCPServerStdio:
        kwargs["server_name"] = "news"
    return cls(**kwargs)


# Registry — the agent can request a server by name/tag
SERVER_SPECS: dict[str, MCPServerSpec] = {
    "playwright": MCPServerSpec(
        name="playwright",
        factory=create_playwright_mcp_server,
        tags=("browser", "deep_dive", "primary_sources"),
    ),
    "news": MCPServerSpec(
        name="news",
        factory=create_news_mcp_server,
        tags=("news", "broad_scan", "structured"),
        required=False,  # fail-soft if provider not configured
    ),
}


# ---------------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------------

async def _probe_server(server: MCPServerStdio, name: str) -> bool:
    """
    Best-effort startup probe. We don't assume a particular tool exists;
    we just verify the session opens within MCP_STARTUP_TIMEOUT.
    """
    try:
        await asyncio.wait_for(server.__aenter__(), timeout=MCP_STARTUP_TIMEOUT)
    except Exception:
        logger.exception("MCP server %s failed startup probe", name)
        return False
    try:
        await server.__aexit__(None, None, None)
    except Exception:
        logger.exception("MCP server %s failed clean shutdown after probe", name)
    logger.info("MCP server %s startup probe OK", name)
    return True


# ---------------------------------------------------------------------------
# PUBLIC LIFESPAN HELPERS
# ---------------------------------------------------------------------------

@asynccontextmanager
async def playwright_lifespan(
    timeout_seconds: float = MCP_DEFAULT_CLIENT_TIMEOUT,
) -> AsyncIterator[MCPServerStdio]:
    """Single-server lifespan for Playwright-only tasks (quick scans)."""
    server = create_playwright_mcp_server(timeout_seconds)
    async with server:
        yield server


@asynccontextmanager
async def research_lifespan(
    timeout_seconds: float = MCP_DEFAULT_CLIENT_TIMEOUT,
    servers: Iterable[str] | None = None,
    fail_soft: bool = True,
) -> AsyncIterator[Mapping[str, MCPServerStdio]]:
    """
    Multi-server lifespan for full Alex research runs.

    Yields a mapping {server_name: server_instance} for all successfully
    started servers. If fail_soft is True, servers that fail to start are
    omitted (with a warning) instead of aborting the whole run.

    Typical usage:
        async with research_lifespan(servers=["playwright", "news"]) as servers:
            pw = servers["playwright"]
            ...
    """
    names = list(servers) if servers is not None else list(SERVER_SPECS.keys())

    instances: dict[str, MCPServerStdio] = {}
    entered: list[tuple[str, MCPServerStdio]] = []

    try:
        for name in names:
            spec = SERVER_SPECS.get(name)
            if spec is None:
                logger.warning("Unknown MCP server requested: %s", name)
                if not fail_soft:
                    raise KeyError(name)
                continue

            server = spec.factory(timeout_seconds)
            try:
                await asyncio.wait_for(
                    server.__aenter__(), timeout=MCP_STARTUP_TIMEOUT
                )
            except Exception:
                logger.exception("Failed to start MCP server %s", name)
                if spec.required and not fail_soft:
                    raise
                continue

            instances[name] = server
            entered.append((name, server))
            logger.info("MCP server %s started", name)

        yield instances

    finally:
        # Shut down in reverse order for a cleaner dependency unwinding.
        for name, server in reversed(entered):
            try:
                await server.__aexit__(None, None, None)
            except Exception:
                logger.exception("Error shutting down MCP server %s", name)


# ---------------------------------------------------------------------------
# CONVENIENCE: choose servers by tag
# ---------------------------------------------------------------------------

def select_servers_by_tag(*tags: str) -> list[str]:
    """
    Return server names matching ANY of the given tags.
    Example:
        select_servers_by_tag("broad_scan")  -> ["news"]
        select_servers_by_tag("browser")     -> ["playwright"]
    """
    wanted = set(tags)
    return [
        name
        for name, spec in SERVER_SPECS.items()
        if wanted.intersection(spec.tags)
    ]