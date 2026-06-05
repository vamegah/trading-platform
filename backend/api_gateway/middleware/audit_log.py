import logging
from datetime import timezone, datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend.shared.database import SessionLocal
from backend.shared.models import AuditLog
from backend.shared.audit import audit_chain, compute_audit_hash
from backend.shared.security import decode_token, sanitize_for_log

logger = logging.getLogger(__name__)


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        response = await call_next(request)
        if not path.startswith("/api") or path == "/api/health":
            return response

        db = SessionLocal()
        try:
            user_id = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                payload = decode_token(auth_header.split(" ", 1)[1])
                user_id = payload.get("sub")

            details = {
                "method": request.method,
                "path": path,
                "query_params": str(request.query_params),
                "status_code": response.status_code,
                "client_ip": request.client.host if request.client else "unknown",
            }
            details = sanitize_for_log(details)
            last_log = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
            previous_hash = last_log.current_hash if last_log else "0" * 64
            action = f"{details['method']} {details['path']}"
            timestamp = datetime.now(timezone.utc)
            timestamp_text = timestamp.isoformat()
            current_hash = compute_audit_hash(previous_hash, action, details, user_id, timestamp_text)
            db.add(
                AuditLog(
                    user_id=int(user_id) if user_id else None,
                    action=action,
                    details=details,
                    ip_address=details["client_ip"],
                    timestamp=timestamp.replace(tzinfo=None),
                    previous_hash=previous_hash,
                    current_hash=current_hash,
                )
            )
            audit_chain.append(action, details, user_id)
            db.commit()
        except Exception:
            logger.exception("audit_log_write_failed path=%s", path)
        finally:
            db.close()
        return response
