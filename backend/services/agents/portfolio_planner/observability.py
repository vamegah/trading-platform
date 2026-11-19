"""
LangFuse observability context manager.

Wraps the OpenAI Agents SDK with Logfire instrumentation and flushes
LangFuse traces on exit. Configuration is opt-in via environment.
"""
import logging
import os
import time
from contextlib import contextmanager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

FLUSH_WAIT_SECONDS = float(os.getenv("LANGFUSE_FLUSH_WAIT_SECONDS", "2"))


@contextmanager
def observe():
    """Set up and flush LangFuse traces around a code block."""
    has_langfuse = bool(os.getenv("LANGFUSE_SECRET_KEY"))
    if not has_langfuse:
        logger.debug("Observability: LangFuse not configured; skipping")
        yield
        return

    langfuse_client = None
    try:
        import logfire
        from langfuse import get_client

        logfire.configure(service_name="trading_planner", send_to_logfire=False)
        logfire.instrument_openai_agents()

        langfuse_client = get_client()
        try:
            langfuse_client.auth_check()
        except Exception:
            logger.warning("LangFuse auth check failed; continuing")

        logger.info("Observability: LangFuse ready")
    except ImportError as exc:
        logger.error("Observability: missing package: %s", exc)
    except Exception:
        logger.exception("Observability: setup failed")

    try:
        yield
    finally:
        if langfuse_client:
            try:
                logger.info("Observability: flushing")
                langfuse_client.flush()
                langfuse_client.shutdown()
                if FLUSH_WAIT_SECONDS > 0:
                    time.sleep(FLUSH_WAIT_SECONDS)
            except Exception:
                logger.exception("Observability: flush failed")