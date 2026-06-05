import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.shared.config import settings
from backend.shared.redis_client import redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/ready", "/metrics"}:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        minute = int(time.time() // 60)
        key = f"rate:{client_ip}:{minute}"
        try:
            count = int(redis_client.incr(key))
            if count == 1 and hasattr(redis_client, "expire"):
                redis_client.expire(key, 120)
        except Exception:
            return await call_next(request)

        if count > settings.api_rate_limit_per_minute:
            return JSONResponse(
                {"detail": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
