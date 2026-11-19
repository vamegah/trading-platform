"""
LangFuse/Logfire observability context manager.
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
    if not os.getenv("LANGFUSE_SECRET_KEY"):
        yield None
        return

    client = None
    try:
        import logfire
        from langfuse import get_client

        logfire.configure(service_name="trading_retirement_specialist", send_to_logfire=False)
        logfire.instrument_openai_agents()
        client = get_client()
        try:
            client.auth_check()
        except Exception:
            logger.warning("Observability: auth check failed; continuing")
    except ImportError as exc:
        logger.error("Observability: missing package %s", exc)
        client = None
    except Exception:
        logger.exception("Observability: setup failed")
        client = None

    try:
        yield client
    finally:
        if client:
            try:
                client.flush()
                client.shutdown()
                if FLUSH_WAIT_SECONDS > 0:
                    time.sleep(FLUSH_WAIT_SECONDS)
            except Exception:
                logger.exception("Observability: flush failed")