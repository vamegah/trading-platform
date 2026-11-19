from fastapi import APIRouter

from backend.shared.database import SessionLocal
from backend.shared.redis_client import redis_client

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, object]:
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception:
        pass

    redis_ok = False
    try:
        redis_client.get("__health__")
        redis_ok = True
    except Exception:
        pass

    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "dependencies": {
            "database": "ok" if db_ok else "unavailable",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }
