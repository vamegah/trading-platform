import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, status

from backend.shared.config import settings

try:
    from jose import JWTError, jwt
except Exception:
    JWTError = Exception
    jwt = None

try:
    from passlib.context import CryptContext
except Exception:
    CryptContext = None

try:
    from cryptography.fernet import Fernet
except Exception:
    Fernet = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") if CryptContext else None


class Role(str, Enum):
    USER = "user"
    ANALYST = "analyst"
    ADMIN = "admin"
    SERVICE = "service"


class Permission(str, Enum):
    READ_SIGNALS = "read:signals"
    TRADE_ONE_CLICK = "trade:one_click"
    TRADE_AUTOMATED = "trade:automated"
    MANAGE_USERS = "manage:users"
    MANAGE_MODELS = "manage:models"
    MANAGE_SECRETS = "manage:secrets"
    VIEW_AUDIT = "view:audit"
    SERVICE_INTERNAL = "service:internal"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.USER: {Permission.READ_SIGNALS, Permission.TRADE_ONE_CLICK},
    Role.ANALYST: {Permission.READ_SIGNALS, Permission.VIEW_AUDIT},
    Role.ADMIN: {
        Permission.READ_SIGNALS,
        Permission.TRADE_ONE_CLICK,
        Permission.TRADE_AUTOMATED,
        Permission.MANAGE_USERS,
        Permission.MANAGE_MODELS,
        Permission.MANAGE_SECRETS,
        Permission.VIEW_AUDIT,
    },
    Role.SERVICE: {Permission.SERVICE_INTERNAL, Permission.READ_SIGNALS, Permission.MANAGE_MODELS},
}


def _sign(value: str) -> str:
    return hmac.new(settings.secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def hash_password(password: str) -> str:
    if pwd_context:
        return pwd_context.hash(password)
    digest = _sign(password)
    return f"sha256${digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if pwd_context and not hashed_password.startswith("sha256$"):
        return pwd_context.verify(plain_password, hashed_password)
    return hmac.compare_digest(hash_password(plain_password), hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    now = datetime.utcnow()
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload.update(
        {
            "exp": expire.timestamp(),
            "iat": now.timestamp(),
            "iss": settings.token_issuer,
            "jti": payload.get("jti") or str(uuid4()),
            "token_type": payload.get("token_type", "access"),
        }
    )
    if jwt:
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"{encoded}.{_sign(encoded)}"


def create_refresh_token(data: dict) -> str:
    claims = data.copy()
    claims["token_type"] = "refresh"
    return create_access_token(
        claims,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def create_service_token(service_name: str, permissions_scope: str = "internal") -> str:
    return create_access_token(
        {
            "sub": service_name,
            "roles": [Role.SERVICE.value],
            "scope": permissions_scope,
            "token_type": "service",
        },
        expires_delta=timedelta(minutes=min(settings.access_token_expire_minutes, 15)),
    )


def decode_token(token: str) -> dict:
    if jwt:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            if payload.get("iss") != settings.token_issuer:
                return {}
            return payload
        except JWTError:
            return {}
    try:
        encoded, signature = token.rsplit(".", 1)
        if not hmac.compare_digest(_sign(encoded), signature):
            return {}
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode()).decode())
        if payload.get("iss") != settings.token_issuer:
            return {}
        if payload.get("exp") and datetime.utcnow().timestamp() > float(payload["exp"]):
            return {}
        return payload
    except Exception:
        return {}


def _fernet():
    if not Fernet:
        return None
    try:
        return Fernet(settings.encryption_key.encode())
    except Exception:
        return None


def encrypt_data(plaintext: str) -> str:
    fernet = _fernet()
    if fernet:
        return fernet.encrypt(plaintext.encode()).decode()
    return base64.urlsafe_b64encode(plaintext.encode()).decode()


def decrypt_data(ciphertext: str) -> str:
    fernet = _fernet()
    if fernet:
        return fernet.decrypt(ciphertext.encode()).decode()
    return base64.urlsafe_b64decode(ciphertext.encode()).decode()


def hash_lookup(value: str) -> str:
    return _sign(value.lower().strip())


def permissions_for_roles(roles: list[str] | tuple[str, ...] | None) -> set[Permission]:
    resolved: set[Permission] = set()
    for role in roles or [Role.USER.value]:
        try:
            resolved.update(ROLE_PERMISSIONS[Role(role)])
        except ValueError:
            continue
    return resolved


def has_permission(roles: list[str] | tuple[str, ...] | None, permission: Permission | str) -> bool:
    try:
        requested = Permission(permission)
    except ValueError:
        return False
    return requested in permissions_for_roles(roles)


def permission_report(roles: list[str] | tuple[str, ...] | None) -> dict[str, object]:
    permissions = sorted(permission.value for permission in permissions_for_roles(roles))
    return {
        "roles": list(roles or [Role.USER.value]),
        "permissions": permissions,
        "role_count": len(roles or [Role.USER.value]),
    }


def require_permission_from_claims(claims: dict, permission: Permission | str) -> None:
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if claims.get("token_type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Refresh tokens cannot authorize API actions",
        )
    roles = claims.get("roles") or [claims.get("role", Role.USER.value)]
    requested = Permission(permission)
    if requested == Permission.SERVICE_INTERNAL and claims.get("token_type") != "service":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Service permission requires a service token",
        )
    if not has_permission(roles, requested):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {requested.value}",
        )


def sanitize_for_log(payload: dict) -> dict:
    return {
        key: _sanitize_value(key, value)
        for key, value in payload.items()
    }


def _sanitize_value(key: str, value):
    sensitive = {
        "password",
        "token",
        "api_key",
        "apikey",
        "secret",
        "authorization",
        "access_token",
        "refresh_token",
        "credential",
        "private_key",
    }
    lowered = key.lower()
    if any(marker in lowered for marker in sensitive):
        return "[REDACTED]"
    if isinstance(value, dict):
        return sanitize_for_log(value)
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    return value
