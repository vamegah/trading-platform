CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_positions_account ON positions(account_id);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE INDEX IF NOT EXISTS idx_signals_user ON trading_signals(clerk_user_id, status);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trading_signals(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_symbol ON researcher_events(symbol, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_status ON researcher_events(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(clerk_user_id, placed_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_broker_order ON trades(broker_order_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON trading_audit(clerk_user_id, event_time DESC);