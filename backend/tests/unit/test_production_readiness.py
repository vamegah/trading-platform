import pytest

from backend.shared.config import Settings
from scripts.migrate_db import preflight


def test_production_rejects_placeholder_runtime_configuration() -> None:
    settings = Settings(
        environment="prod",
        database_url="postgresql+psycopg://trading:change-me@postgres:5432/trading",
        redis_url="",
        secret_key="change-me",
        encryption_key="change-me",
        create_tables_on_startup=True,
    )

    issues = settings.production_readiness_issues()

    assert "DATABASE_URL must be set to a non-placeholder production value" in issues
    assert "REDIS_URL must be set to a non-placeholder production value" in issues
    assert "SECRET_KEY must be set to a non-placeholder production value" in issues
    assert "ENCRYPTION_KEY must be set to a non-placeholder production value" in issues
    assert "CREATE_TABLES_ON_STARTUP must be false in production" in issues
    with pytest.raises(RuntimeError):
        settings.validate_runtime()


def test_development_allows_local_defaults() -> None:
    settings = Settings(environment="development", secret_key="change-me", encryption_key="change-me")

    assert settings.production_readiness_issues() == []
    settings.validate_runtime()


def test_live_integrations_require_provider_and_broker_credentials() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://trading:strong-pass@postgres:5432/trading",
        redis_url="redis://redis:6379/0",
        secret_key="prod-secret-that-is-not-default",
        encryption_key="prod-fernet-key-that-is-not-default",
        kms_key_id="kms-prod-key",
        audit_store_url="postgresql+psycopg://audit:strong-pass@postgres:5432/audit",
        secret_store_url="vault://trading-platform/prod",
        live_trading_enabled=True,
    )

    issues = settings.production_readiness_issues()

    assert "POLYGON_API_KEY is required before live integrations are enabled" in issues
    assert "ALPACA_API_KEY is required before live integrations are enabled" in issues
    assert "ALPACA_API_SECRET is required before live integrations are enabled" in issues
    assert "IBKR_ACCOUNT_ID is required before live integrations are enabled" in issues
    assert "BROKER_ENCRYPTION_KEY_ID is required before live integrations are enabled" in issues


def test_migration_preflight_uses_runtime_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    invalid = Settings(environment="prod", database_url="", secret_key="change-me")
    monkeypatch.setattr("scripts.migrate_db.settings", invalid)

    with pytest.raises(RuntimeError):
        preflight()
