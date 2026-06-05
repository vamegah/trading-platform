from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend.shared.security import decode_token


class IdentityPropagationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        claims = {}
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            claims = decode_token(auth_header.split(" ", 1)[1])

        user_id = claims.get("sub") or request.headers.get("x-user-id")
        roles = claims.get("roles") or request.headers.get("x-roles")
        request.state.identity = {
            "user_id": user_id,
            "roles": roles or [],
            "token_type": claims.get("token_type"),
        }

        response = await call_next(request)
        if user_id:
            response.headers["x-user-id"] = str(user_id)
        if roles:
            response.headers["x-roles"] = ",".join(roles) if isinstance(roles, list) else str(roles)
        return response
