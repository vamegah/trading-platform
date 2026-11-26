import pytest
from sqlalchemy.engine import make_url

from backend.shared.database import resolve_database_url


def test_bare_postgresql_url_is_pinned_to_psycopg2() -> None:
    resolved = resolve_database_url("postgresql://trading_user:trading_password@localhost:5432/trading_test")

    assert resolved == "postgresql+psycopg2://trading_user:trading_password@localhost:5432/trading_test"


def test_pinning_preserves_encoded_password_and_query() -> None:
    original = "postgresql://user:p%40ss%2Fw0rd@db.internal:5432/trading?sslmode=require"

    resolved = make_url(resolve_database_url(original))

    assert resolved.drivername == "postgresql+psycopg2"
    assert resolved.password == "p@ss/w0rd"
    assert resolved.host == "db.internal"
    assert resolved.database == "trading"
    assert resolved.query == {"sslmode": "require"}


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://trading:strong-pass@db.internal:5432/trading",
        "postgresql+psycopg2://trading:strong-pass@db.internal:5432/trading",
        "postgresql+asyncpg://trading:strong-pass@db.internal:5432/trading",
        "sqlite:///./trading_platform.db",
        "sqlite://",
    ],
)
def test_explicit_driver_and_non_postgres_urls_are_unchanged(url: str) -> None:
    assert resolve_database_url(url) == url
