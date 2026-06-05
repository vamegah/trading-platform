from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.services.user_service.main import create_user, get_user_by_email
from backend.shared.config import settings
from backend.shared.database import get_db
from backend.shared.models import User
from backend.shared.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    permissions_for_roles,
    verify_password,
)

router = APIRouter()


class UserCreate(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class SessionResponse(BaseModel):
    authenticated: bool
    user_id: str | None = None
    roles: list[str] = []
    permissions: list[str] = []
    token_type: str | None = None


def _token_response(claims: dict) -> dict[str, str]:
    return {
        "access_token": create_access_token(data=claims),
        "refresh_token": create_refresh_token(data=claims),
    }


def _claims_to_session(claims: dict) -> SessionResponse:
    if not claims or claims.get("token_type") == "refresh":
        return SessionResponse(authenticated=False)
    roles = claims.get("roles") or ["user"]
    permissions = sorted(permission.value for permission in permissions_for_roles(roles))
    return SessionResponse(
        authenticated=True,
        user_id=str(claims.get("sub")),
        roles=list(roles),
        permissions=permissions,
        token_type=claims.get("token_type"),
    )


@router.post("/signup", response_model=Token)
def signup(user_data: UserCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    email = user_data.email.lower()
    if "@" not in email:
        raise HTTPException(status_code=422, detail="email must contain @")
    existing = get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = create_user(db, email=email, password=user_data.password)
    claims = {"sub": str(user.id), "roles": ["user"]}
    return _token_response(claims)


@router.post("/login", response_model=Token)
def login(
    form_data: LoginRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    roles = ["admin"] if user.is_superuser else ["user"]
    claims = {"sub": str(user.id), "roles": roles}
    return _token_response(claims)


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: RefreshRequest | None = None,
    refresh_token: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    token = request.refresh_token if request else refresh_token
    payload = decode_token(token or "")
    if not payload.get("sub") or payload.get("token_type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if payload["sub"] == "demo" and not settings.is_production:
        return _token_response({"sub": "demo", "roles": payload.get("roles") or ["analyst"]})
    user = db.query(User).get(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    roles = payload.get("roles") or (["admin"] if user.is_superuser else ["user"])
    claims = {"sub": str(user.id), "roles": roles}
    return _token_response(claims)


@router.get("/session", response_model=SessionResponse)
def session(authorization: str | None = Header(default=None)) -> SessionResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        return SessionResponse(authenticated=False)
    return _claims_to_session(decode_token(authorization.split(" ", 1)[1]))


@router.post("/demo", response_model=Token)
def demo_session() -> dict[str, str]:
    if settings.is_production:
        raise HTTPException(status_code=403, detail="Demo sessions are disabled in production")
    return _token_response({"sub": "demo", "roles": ["analyst"]})
