import json
import logging
import time
from collections import defaultdict
from contextvars import ContextVar
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_metrics = defaultdict(int)
_latency_ms = defaultdict(float)
_LOG_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__)


def _record_request_metrics(route_key: str, latency: float, status_code: int, failed: bool) -> None:
    _metrics[f"requests_total:{route_key}"] += 1
    _metrics[f"responses_total:{status_code}"] += 1
    if failed:
        _metrics[f"errors_total:{route_key}"] += 1
    _latency_ms[route_key] = latency


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "timestamp": self.formatTime(record, self.datefmt),
        }
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _LOG_RECORD_FIELDS and not key.startswith("_")
        }
        payload.update(extras)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        token = request_id_var.set(request_id)
        started_at = time.perf_counter()
        route_key = f"{request.method} {request.url.path}"
        logger = logging.getLogger("http.request")
        try:
            response = await call_next(request)
        except Exception:
            latency = (time.perf_counter() - started_at) * 1000
            _record_request_metrics(route_key, latency, 500, failed=True)
            logger.exception(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "latency_ms": round(latency, 2),
                },
            )
            raise
        else:
            latency = (time.perf_counter() - started_at) * 1000
            _record_request_metrics(route_key, latency, response.status_code, failed=False)
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency_ms": round(latency, 2),
                },
            )
            response.headers["x-request-id"] = request_id
            return response
        finally:
            request_id_var.reset(token)


def configure_json_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def metrics_snapshot() -> dict[str, object]:
    return {
        "counters": dict(_metrics),
        "latency_ms": {key: round(value, 2) for key, value in _latency_ms.items()},
    }


def add_observability_routes(app: FastAPI, service_name: str, dependencies: dict[str, str] | None = None) -> None:
    @app.get("/ready")
    async def ready() -> dict[str, object]:
        return {"service": service_name, "ready": True, "dependencies": dependencies or {}}

    @app.get("/metrics")
    async def metrics() -> dict[str, object]:
        return metrics_snapshot()


def instrument_app(app: FastAPI, service_name: str, dependencies: dict[str, str] | None = None) -> FastAPI:
    app.add_middleware(RequestContextMiddleware)
    add_observability_routes(app, service_name, dependencies)
    return app
