"""Smoke tests for the API gateway."""
import json
from unittest.mock import patch

from fastapi.testclient import TestClient


def _client():
    from api.main import app
    return TestClient(app)


def test_health():
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@patch("api.main.db")
@patch("api.main.clerk_guard")
def test_list_signals_requires_auth(mock_guard, mock_db):
    client = _client()
    resp = client.get("/api/signals")
    # FastAPI returns 401/403 when the dependency cannot authenticate
    assert resp.status_code in (401, 403)