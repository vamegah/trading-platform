from dataclasses import dataclass
from typing import Optional

from backend.shared.config import settings


@dataclass(frozen=True)
class ExternalAPI:
    name: str
    category: str
    phase: str
    purpose: str
    required_for_live: bool
    credential_fields: tuple[str, ...] = ()
    self_hosted: bool = False

    def configured(self) -> bool:
        if self.self_hosted:
            return True
        return all(bool(getattr(settings, field, None)) for field in self.credential_fields)

    def status(self) -> dict[str, object]:
        return {
            "name": self.name,
            "category": self.category,
            "phase": self.phase,
            "purpose": self.purpose,
            "required_for_live": self.required_for_live,
            "configured": self.configured(),
            "credential_fields": list(self.credential_fields),
            "self_hosted": self.self_hosted,
        }


EXTERNAL_APIS: tuple[ExternalAPI, ...] = (
    ExternalAPI("polygon", "market_data", "phase_0", "Primary live equities, forex, and crypto feed", True, ("polygon_api_key",)),
    ExternalAPI("alpha_vantage", "market_data", "phase_0", "Equity and FX failover data", True, ("alpha_vantage_api_key",)),
    ExternalAPI("financial_modeling_prep", "market_data", "phase_0", "Fundamentals, statements, and historical prices", True, ("fmp_api_key",)),
    ExternalAPI("twelve_data", "market_data", "phase_0", "Historical bars and technical indicators", True, ("twelve_data_api_key",)),
    ExternalAPI("sec_edgar", "regulatory_filings", "phase_0", "Official filings and insider transactions", True, (), True),
    ExternalAPI("openai", "ai", "phase_0", "Primary LLM reasoning and synthesis", True, ("openai_key",)),
    ExternalAPI("anthropic", "ai", "phase_0", "Secondary LLM challenger reasoning", False, ("anthropic_api_key",)),
    ExternalAPI("auth0", "identity", "phase_0", "OAuth2, MFA, and partner identity", True, ("auth0_domain", "auth0_audience")),
    ExternalAPI("sentry", "observability", "phase_0", "Error tracking and APM", True, ("sentry_dsn",)),
    ExternalAPI("twilio", "notifications", "phase_0", "SMS alerts", True, ("twilio_account_sid", "twilio_auth_token", "twilio_from_number")),
    ExternalAPI("sendgrid", "notifications", "phase_0", "Transactional email", True, ("sendgrid_api_key",)),
    ExternalAPI("stripe", "billing", "phase_0", "Subscriptions and metered billing", True, ("stripe_api_key",)),
    ExternalAPI("launchdarkly", "feature_flags", "phase_0", "Canary releases and feature flags", True, ("launchdarkly_sdk_key",)),
    ExternalAPI("prometheus_grafana", "observability", "phase_0", "Metrics and dashboards", True, (), True),
    ExternalAPI("eodhd", "fundamentals", "phase_1", "Global fundamental data", False, ("eodhd_api_key",)),
    ExternalAPI("finnhub", "news_sentiment", "phase_1", "Company news and market sentiment", True, ("finnhub_api_key",)),
    ExternalAPI("newscatcher", "news_sentiment", "phase_1", "Enterprise news aggregation", False, ("newscatcher_api_key",)),
    ExternalAPI("databento", "backtesting", "phase_1", "Tick data and historical replay", True, ("databento_api_key",)),
    ExternalAPI("alpaca", "execution", "phase_2", "Equity and ETF execution", True, ("alpaca_api_key", "alpaca_api_secret")),
    ExternalAPI("ibkr", "execution", "phase_2", "Multi-asset execution", True, ("ibkr_account_id",)),
    ExternalAPI("macro_calendar", "macro", "phase_3", "Economic events and central banks", False, ("macro_calendar_api_key",)),
    ExternalAPI("world_bank", "macro", "phase_3", "Country macroeconomic indicators", False, (), True),
    ExternalAPI("reddit", "social_sentiment", "phase_3", "Financial subreddit sentiment", False, ("reddit_client_id", "reddit_client_secret")),
    ExternalAPI("twitter_x", "social_sentiment", "phase_3", "Real-time social trends", False, ("twitter_bearer_token",)),
    ExternalAPI("ivolatility", "options_data", "phase_4", "Options chains, Greeks, IV, and open interest", False, ("ivolatility_api_key",)),
    ExternalAPI("amberdata", "multi_asset_data", "phase_4", "Digital asset derivatives and on-chain data", False, ("amberdata_api_key",)),
    ExternalAPI("smarsh", "compliance_archive", "phase_4", "Recommendation and communication archiving", True, ("smarsh_api_key",)),
    ExternalAPI("proofpoint", "compliance_archive", "phase_4", "Compliance supervision and archiving", False, ("proofpoint_api_key",)),
    ExternalAPI("microblink", "kyc_aml", "phase_4", "Identity verification and liveness", True, ("microblink_api_key",)),
    ExternalAPI("coinapi", "crypto_data", "phase_5", "Unified crypto market data", False, ("coinapi_key",)),
    ExternalAPI("cryptoquant", "crypto_data", "phase_5", "On-chain institutional indicators", False, ("cryptoquant_api_key",)),
    ExternalAPI("finfeedapi", "forex_data", "phase_5", "Live and historical FX rates", False, ("finfeedapi_key",)),
    ExternalAPI("eagleview", "alternative_data", "phase_5", "Satellite and aerial imagery", False, ("eagleview_api_key",)),
    ExternalAPI("onesource_esg", "alternative_data", "phase_5", "ESG data and reporting", False, ("onesource_esg_api_key",)),
    ExternalAPI("facteus", "alternative_data", "phase_5", "Consumer spending transaction data", False, ("facteus_api_key",)),
)


def list_external_api_status(category: Optional[str] = None) -> list[dict[str, object]]:
    providers = EXTERNAL_APIS
    if category:
        providers = tuple(api for api in providers if api.category == category)
    return [api.status() for api in providers]


def missing_live_integrations() -> list[str]:
    return [api.name for api in EXTERNAL_APIS if api.required_for_live and not api.configured()]
