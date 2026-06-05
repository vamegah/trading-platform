# Broker Certification Requirements

Broker integrations must be certified in paper or sandbox environments before live trading is enabled.

## Broker Matrix

| Broker | Asset Classes | Required Credentials | Certification Evidence |
| --- | --- | --- | --- |
| Alpaca | Equities, ETFs | `ALPACA_API_KEY`, `ALPACA_API_SECRET` | Sandbox submit, cancel, replace, position sync, balance sync, fills reconciliation |
| Interactive Brokers | Equities, ETFs, options, futures, forex | `IBKR_ACCOUNT_ID` and gateway/session credentials | Paper account submit, cancel, fills, account sync, margin rejection behavior |
| TradeStation | Futures and multi-asset routing | Provider credentials | Sandbox lifecycle and reconciliation report |
| Deribit/Binance Futures | Crypto options/futures | Provider credentials | Testnet lifecycle, liquidation-risk checks, position reconciliation |

## Runtime Rules

- Sandbox mode may simulate fills for local development and paper workflows.
- Live mode must never simulate fills or mutate positions before broker confirmation.
- Live mode fails closed unless credentials and certification flags are present.
- Broker fills must reconcile into the trade journal and audit trail before customer reporting.
- TD Ameritrade remains deferred because the API migrated to Schwab; a successor connector requires new provider access.

## Certification Checklist

1. Place market, limit, stop, TWAP, VWAP, and iceberg orders where supported.
2. Cancel and replace open orders.
3. Sync positions, cash, buying power, margin, and restrictions.
4. Reconcile partial fills and rejected orders.
5. Confirm broker outage handling and retry/idempotency behavior.
6. Record sandbox evidence before setting `certified_live=true`.
