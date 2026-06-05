import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


PRODUCTION_ENVIRONMENTS = {"prod", "production"}
PLACEHOLDER_VALUES = {
    "",
    "change-me",
    "changeme",
    "your-secret-key-change-in-production",
    "your-fernet-key-here-change-in-production",
    "__required__",
    "__required_database_url__",
    "__required_redis_url__",
    "__required_secret_key__",
    "__required_encryption_key__",
}


class Settings(BaseSettings):
    database_url: str = (
        "postgresql://trading_user:strong_password@localhost:5432/trading_db"
    )
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    token_issuer: str = "trading-platform"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    encryption_key: str = "change-me"  # Fernet key

    # API keys
    alpha_vantage_api_key: Optional[str] = None
    marketstack_key: str = os.getenv("MARKETSTACK_API_KEY", "")
    openai_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: Optional[str] = None
    sentiment_model: str = "vader"  # or "finbert"
    news_api_key: Optional[str] = None
    fred_api_key: Optional[str] = None
    risk_free_rate: float = 0.04
    max_position_pct: float = 0.2
    backtest_default_days: int = 365

    # Phase 4: tax optimization, market impact, stress testing, safety
    short_term_cap_gains_rate: float = 0.37
    long_term_cap_gains_rate: float = 0.20
    wash_sale_window_days: int = 30
    market_impact_eta: float = 0.08
    market_impact_gamma: float = 0.12
    market_impact_beta: float = 0.65
    market_impact_default_daily_volume: float = 1000000
    market_impact_default_volatility: float = 0.025
    signal_half_life_minutes: float = 60
    signal_auto_cancel_threshold: float = 0.25
    black_swan_volatility_zscore: float = 3.0
    black_swan_correlation_threshold: float = 0.85
    black_swan_liquidity_drop_threshold: float = 0.5
    stress_test_default_scenario: str = "2008_financial_crisis"
    redis_cluster_enabled: bool = False
    hpa_min_replicas: int = 2
    hpa_max_replicas: int = 10
    create_tables_on_startup: bool = False

    environment: str = "development"
    log_level: str = "INFO"

    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,"
        "http://127.0.0.1:3000,http://127.0.0.1:5173"
    )
    api_rate_limit_per_minute: int = 600
    live_trading_enabled: bool = False
    require_live_integrations: bool = False

    # Production external integrations. These stay optional in local/dev, but
    # production validation fails closed when live integrations are required.
    polygon_api_key: Optional[str] = None
    fmp_api_key: Optional[str] = None
    twelve_data_api_key: Optional[str] = None
    eodhd_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    newscatcher_api_key: Optional[str] = None
    databento_api_key: Optional[str] = None
    macro_calendar_api_key: Optional[str] = None
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    twitter_bearer_token: Optional[str] = None
    ivolatility_api_key: Optional[str] = None
    amberdata_api_key: Optional[str] = None
    coinapi_key: Optional[str] = None
    cryptoquant_api_key: Optional[str] = None
    finfeedapi_key: Optional[str] = None
    eagleview_api_key: Optional[str] = None
    onesource_esg_api_key: Optional[str] = None
    facteus_api_key: Optional[str] = None
    auth0_domain: Optional[str] = None
    auth0_audience: Optional[str] = None
    smarsh_api_key: Optional[str] = None
    proofpoint_api_key: Optional[str] = None
    sentry_dsn: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None
    sendgrid_api_key: Optional[str] = None
    stripe_api_key: Optional[str] = None
    launchdarkly_sdk_key: Optional[str] = None
    microblink_api_key: Optional[str] = None
    alpaca_api_key: Optional[str] = None
    alpaca_api_secret: Optional[str] = None
    ibkr_account_id: Optional[str] = None
    ibkr_host: Optional[str] = None
    ibkr_port: Optional[int] = None
    tradestation_api_key: Optional[str] = None
    deribit_client_id: Optional[str] = None
    deribit_client_secret: Optional[str] = None
    binance_futures_api_key: Optional[str] = None
    binance_futures_api_secret: Optional[str] = None
    broker_encryption_key_id: Optional[str] = None
    kms_key_id: Optional[str] = None
    audit_store_url: Optional[str] = None
    secret_store_url: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in PRODUCTION_ENVIRONMENTS

    def production_readiness_issues(self) -> list[str]:
        issues: list[str] = []
        if not self.is_production:
            return issues

        required_settings = {
            "DATABASE_URL": self.database_url,
            "REDIS_URL": self.redis_url,
            "SECRET_KEY": self.secret_key,
            "ENCRYPTION_KEY": self.encryption_key,
            "KMS_KEY_ID": self.kms_key_id,
            "AUDIT_STORE_URL": self.audit_store_url,
            "SECRET_STORE_URL": self.secret_store_url,
        }
        for name, value in required_settings.items():
            if _is_placeholder(value):
                issues.append(f"{name} must be set to a non-placeholder production value")

        if _is_local_database_url(self.database_url):
            issues.append("DATABASE_URL must point to a production database, not localhost or SQLite")

        if _is_local_redis_url(self.redis_url):
            issues.append("REDIS_URL must point to a production Redis endpoint, not localhost")

        if not _has_minimum_secret_strength(self.secret_key):
            issues.append("SECRET_KEY must be at least 32 characters in production")

        if not _has_minimum_secret_strength(self.encryption_key):
            issues.append("ENCRYPTION_KEY must be at least 32 characters in production")

        if self.create_tables_on_startup:
            issues.append("CREATE_TABLES_ON_STARTUP must be false in production")

        if self.live_trading_enabled or self.require_live_integrations:
            live_requirements = {
                "POLYGON_API_KEY": self.polygon_api_key or self.alpha_vantage_api_key,
                "FMP_API_KEY": self.fmp_api_key,
                "TWELVE_DATA_API_KEY": self.twelve_data_api_key,
                "FINNHUB_API_KEY": self.finnhub_api_key,
                "SENTRY_DSN": self.sentry_dsn,
                "AUTH0_DOMAIN": self.auth0_domain,
                "AUTH0_AUDIENCE": self.auth0_audience,
                "ALPACA_API_KEY": self.alpaca_api_key,
                "ALPACA_API_SECRET": self.alpaca_api_secret,
                "IBKR_ACCOUNT_ID": self.ibkr_account_id,
                "BROKER_ENCRYPTION_KEY_ID": self.broker_encryption_key_id,
            }
            for name, value in live_requirements.items():
                if _is_placeholder(value):
                    issues.append(f"{name} is required before live integrations are enabled")

        return issues

    def validate_runtime(self) -> None:
        issues = self.production_readiness_issues()
        if issues:
            joined = "; ".join(issues)
            raise RuntimeError(f"Production readiness validation failed: {joined}")


def _is_placeholder(value: Optional[str]) -> bool:
    normalized = (value or "").strip()
    lowered = normalized.lower()
    return (
        lowered in PLACEHOLDER_VALUES
        or lowered.startswith("__required")
        or "change-me" in lowered
    )


def _is_local_database_url(value: Optional[str]) -> bool:
    lowered = (value or "").strip().lower()
    return lowered.startswith("sqlite:") or "localhost" in lowered or "127.0.0.1" in lowered


def _is_local_redis_url(value: Optional[str]) -> bool:
    lowered = (value or "").strip().lower()
    return "localhost" in lowered or "127.0.0.1" in lowered


def _has_minimum_secret_strength(value: Optional[str]) -> bool:
    normalized = (value or "").strip()
    return len(normalized) >= 32 and not _is_placeholder(normalized)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
