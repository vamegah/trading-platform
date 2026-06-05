# Provider Integration Requirements

Production market-data and execution integrations require contracted provider access, sandbox certification where available, and documented service levels before live trading.

## Market Data Providers

| Provider | Required Use | Credential | Expected SLA Evidence | Failover Role |
| --- | --- | --- | --- | --- |
| Polygon.io | Real-time and historical equities OHLCV and NBBO quote data | `POLYGON_API_KEY` | Contract tier, rate limits, market-hours latency, outage notification policy | Primary equities market-data source |
| Financial Modeling Prep | Fundamentals, statements, ratios, and historical bars | `FMP_API_KEY` | Statement coverage, redistribution rights, stale-data rules | Fundamentals and tertiary price source |
| Twelve Data | Historical bars and technical indicators | `TWELVE_DATA_API_KEY` | Indicator definitions, latency, rate limits | Technical-analysis source |
| Alpha Vantage | Historical daily bars and quote fallback | `ALPHA_VANTAGE_API_KEY` | Rate limits, throttling behavior, delayed-data disclosure | Secondary/fallback source |
| Finnhub / NewsCatcher | News, sentiment, and company event feeds | `FINNHUB_API_KEY`, `NEWSCATCHER_API_KEY` | Source timestamp availability, redistribution rights, event latency | Non-price event enrichment |
| Reddit / Twitter/X | Social sentiment and trend feeds | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `TWITTER_BEARER_TOKEN` | Terms of service, retention limits, moderation controls | Social sentiment enrichment |
| IVolatility / Amberdata / CoinAPI / CryptoQuant | Options chains, derivatives, crypto market data, and on-chain metrics | Provider-specific API keys | Asset coverage, refresh intervals, historical retention | Multi-asset enrichment |
| EagleView / ONESOURCE ESG / Facteus | Satellite, ESG, and transaction-derived alternative data | Provider-specific API keys | Redistribution rights, privacy review, sampling bias controls | Alternative-data enrichment |

## Platform APIs

The runtime catalog is exposed at `GET /integrations` and powers the frontend Integrations tab. It reports configured credentials, self-hosted services, and live-trading gaps without exposing secret values.

## Certification Checklist

1. Store credentials through the approved secret manager.
2. Run provider sandbox or contracted test endpoint checks.
3. Record latency, rate-limit, failover, and stale-data behavior.
4. Verify data quality checks block missing, stale, outlier, and look-ahead-biased data.
5. Confirm redistribution and user-display rights with legal/compliance.
6. Record provider status-page URL and escalation contacts in the operations handbook.

## Runtime Behavior

- Providers with configured API keys use authenticated HTTP calls.
- Providers without configured API keys fall back to deterministic local samples for development only.
- Production runtime validation requires real provider credentials before live integrations are enabled.
- `MarketDataManager` tries providers in order and records `last_used_provider` after successful retrieval.
