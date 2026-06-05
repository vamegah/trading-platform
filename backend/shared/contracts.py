from typing import Generic, TypeVar

from pydantic import BaseModel, Field

API_VERSION = "v1"
T = TypeVar("T")


class ApiEnvelope(BaseModel, Generic[T]):
    api_version: str = API_VERSION
    request_id: str | None = None
    data: T


class ErrorEnvelope(BaseModel):
    api_version: str = API_VERSION
    request_id: str | None = None
    error: str
    detail: str | None = None


class HealthResponse(BaseModel):
    service: str
    status: str = "healthy"
    api_version: str = API_VERSION


class ReadyResponse(BaseModel):
    service: str
    ready: bool
    dependencies: dict[str, str] = Field(default_factory=dict)

