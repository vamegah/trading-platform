-- ============================================================================
-- Migration 002: briefs, brief_items, signals
--
-- Purpose: native storage for Alex research agent output (SignalBrief schema).
-- Complements S3 Vectors (which is for semantic search) with relational
-- storage suited for backtesting, joins, and dedupe.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- briefs: one row per research run that produced a validated SignalBrief
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS briefs (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id            VARCHAR(32)  NOT NULL,          -- from server.py uuid4().hex[:12]
    generated_at      TIMESTAMPTZ  NOT NULL,          -- parsed from generated_at_utc
    window            VARCHAR(16)  NOT NULL,          -- '24h' | '7d' | 'custom'
    universe          TEXT[]       NOT NULL DEFAULT '{}',
    mode              VARCHAR(16),                    -- 'auto'|'ticker'|'sector'|'macro'|'topic'
    parse_ok          BOOLEAN      NOT NULL DEFAULT TRUE,
    dedupe_key        VARCHAR(64),                    -- sha256[:32] from tools.py
    top_signal_ticker VARCHAR(20),                    -- denormalized for quick filter
    top_signal_dir    VARCHAR(16),                    -- 'BULLISH'|'BEARISH'|...
    top_signal_rationale TEXT,
    risks_and_caveats TEXT[]       NOT NULL DEFAULT '{}',
    raw_output        TEXT,                           -- full agent text (fallback / audit)
    source_hash       CHAR(64),                       -- sha256 of canonical brief JSON
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT briefs_window_chk CHECK (window IN ('24h', '7d', 'custom')),
    CONSTRAINT briefs_mode_chk CHECK (
        mode IS NULL OR mode IN ('auto', 'ticker', 'sector', 'macro', 'topic')
    ),
    CONSTRAINT briefs_top_dir_chk CHECK (
        top_signal_dir IS NULL OR top_signal_dir IN ('BULLISH','BEARISH','NEUTRAL','MIXED')
    )
);

-- Idempotency: same dedupe_key from same run → one row
CREATE UNIQUE INDEX IF NOT EXISTS uq_briefs_dedupe_key
    ON briefs(dedupe_key) WHERE dedupe_key IS NOT NULL;

-- Most common query pattern: "latest briefs for NVDA in the last 24h"
CREATE INDEX IF NOT EXISTS idx_briefs_generated_at
    ON briefs(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_briefs_universe_gin
    ON briefs USING GIN (universe);
CREATE INDEX IF NOT EXISTS idx_briefs_top_ticker_time
    ON briefs(top_signal_ticker, generated_at DESC)
    WHERE top_signal_ticker IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_briefs_run_id
    ON briefs(run_id);

-- ---------------------------------------------------------------------------
-- brief_items: one row per NewsItem inside a brief
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS brief_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brief_id        UUID NOT NULL REFERENCES briefs(id) ON DELETE CASCADE,
    item_index      INTEGER NOT NULL,                 -- preserves order in the brief
    headline        TEXT NOT NULL,
    event_type      VARCHAR(64) NOT NULL,
    tickers         TEXT[] NOT NULL DEFAULT '{}',
    direction       VARCHAR(16) NOT NULL,
    magnitude       VARCHAR(16) NOT NULL,
    time_horizon    VARCHAR(16) NOT NULL,
    confidence      VARCHAR(16) NOT NULL,
    status          VARCHAR(16) NOT NULL,
    summary         TEXT NOT NULL,
    key_numbers     JSONB NOT NULL DEFAULT '{}',
    sources         JSONB NOT NULL DEFAULT '[]',      -- [{name,url,published_at,tier}]
    conflicts       TEXT[] NOT NULL DEFAULT '{}',
    stale           BOOLEAN NOT NULL DEFAULT FALSE,
    item_dedupe_key VARCHAR(64),                      -- per-item dedupe within a day
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT brief_items_direction_chk CHECK (
        direction IN ('BULLISH','BEARISH','NEUTRAL','MIXED')
    ),
    CONSTRAINT brief_items_magnitude_chk CHECK (
        magnitude IN ('LOW','MEDIUM','HIGH','EXTREME')
    ),
    CONSTRAINT brief_items_horizon_chk CHECK (
        time_horizon IN ('INTRADAY','DAYS','WEEKS','MONTHS')
    ),
    CONSTRAINT brief_items_confidence_chk CHECK (
        confidence IN ('LOW','MEDIUM','HIGH')
    ),
    CONSTRAINT brief_items_status_chk CHECK (
        status IN ('FACT','RUMOR','OPINION')
    ),
    CONSTRAINT brief_items_unique_per_brief UNIQUE (brief_id, item_index)
);

CREATE INDEX IF NOT EXISTS idx_brief_items_brief_id
    ON brief_items(brief_id);
CREATE INDEX IF NOT EXISTS idx_brief_items_tickers_gin
    ON brief_items USING GIN (tickers);
CREATE INDEX IF NOT EXISTS idx_brief_items_event_mag
    ON brief_items(event_type, magnitude, direction);
CREATE INDEX IF NOT EXISTS idx_brief_items_high_mag
    ON brief_items(generated_at)
    WHERE magnitude IN ('HIGH','EXTREME');  -- requires the column below

-- Denormalize generated_at so the partial index above works without a join
ALTER TABLE brief_items
    ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ;

-- Backfill from parent (safe on re-run)
UPDATE brief_items bi
SET generated_at = b.generated_at
FROM briefs b
WHERE bi.brief_id = b.id AND bi.generated_at IS NULL;

-- Now create the partial index
CREATE INDEX IF NOT EXISTS idx_brief_items_high_mag_time
    ON brief_items(generated_at DESC)
    WHERE magnitude IN ('HIGH','EXTREME');

-- ---------------------------------------------------------------------------
-- signals: one row per top_signal — the tradeable output
--
-- Kept separate from brief_items because:
--   1. It's the primary unit for backtesting against price action.
--   2. It has a narrower, more stable shape that downstream consumers
--      (portfolio engine, alerts) can rely on.
--   3. Signals can be manually edited/reviewed without touching the brief.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS signals (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brief_id      UUID REFERENCES briefs(id) ON DELETE SET NULL,
    brief_item_id UUID REFERENCES brief_items(id) ON DELETE SET NULL,
    run_id        VARCHAR(32),
    ticker        VARCHAR(20) NOT NULL,
    direction     VARCHAR(16) NOT NULL,
    confidence    VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    magnitude     VARCHAR(16) NOT NULL DEFAULT 'MEDIUM',
    time_horizon  VARCHAR(16) NOT NULL DEFAULT 'DAYS',
    rationale     TEXT NOT NULL,
    event_type    VARCHAR(64),
    recorded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generated_at  TIMESTAMPTZ NOT NULL,              -- when the brief was generated
    -- Backtest bookkeeping
    price_at_signal  NUMERIC(20,6),
    price_checked_at TIMESTAMPTZ,
    outcome_pct      NUMERIC(10,4),                  -- filled later by a pricer job
    outcome_label    VARCHAR(16),                    -- 'WIN'|'LOSS'|'FLAT'|NULL

    CONSTRAINT signals_direction_chk CHECK (
        direction IN ('BULLISH','BEARISH','NEUTRAL','MIXED')
    ),
    CONSTRAINT signals_confidence_chk CHECK (
        confidence IN ('LOW','MEDIUM','HIGH')
    ),
    CONSTRAINT signals_magnitude_chk CHECK (
        magnitude IN ('LOW','MEDIUM','HIGH','EXTREME')
    ),
    CONSTRAINT signals_horizon_chk CHECK (
        time_horizon IN ('INTRADAY','DAYS','WEEKS','MONTHS')
    ),
    CONSTRAINT signals_outcome_label_chk CHECK (
        outcome_label IS NULL OR outcome_label IN ('WIN','LOSS','FLAT')
    )
);

CREATE TABLE IF NOT EXISTS trading_profiles (
    clerk_user_id VARCHAR(255) PRIMARY KEY REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    risk_tolerance VARCHAR(20) NOT NULL,
    investment_experience VARCHAR(20),
    income_bracket VARCHAR(20),
    max_drawdown_pct DECIMAL(5,2) DEFAULT 20.0,
    kyc_status VARCHAR(20) DEFAULT 'pending',
    kyc_provider_ref VARCHAR(255),
    jurisdiction VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trading_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id VARCHAR(255) REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    symbol VARCHAR(20) REFERENCES instruments(symbol),
    direction VARCHAR(10) NOT NULL,
    confidence DECIMAL(4,3) NOT NULL,
    horizon VARCHAR(10),
    entry_price DECIMAL(12,4),
    stop_loss DECIMAL(12,4),
    take_profit DECIMAL(12,4),
    rationale TEXT,
    source VARCHAR(50),
    researcher_event_id UUID,
    status VARCHAR(20) DEFAULT 'active',
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id VARCHAR(255) REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
    signal_id UUID REFERENCES trading_signals(id),
    symbol VARCHAR(20) REFERENCES instruments(symbol),
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    filled_price DECIMAL(12,4),
    commission DECIMAL(8,4) DEFAULT 0,
    slippage DECIMAL(8,4) DEFAULT 0,
    broker VARCHAR(50),
    broker_order_id VARCHAR(255),
    is_paper BOOLEAN DEFAULT true,
    status VARCHAR(20) DEFAULT 'pending',
    placed_at TIMESTAMP DEFAULT NOW(),
    filled_at TIMESTAMP,
    idempotency_key UUID UNIQUE
);

CREATE TABLE IF NOT EXISTS researcher_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(64) UNIQUE NOT NULL,
    symbol VARCHAR(20),
    event_type VARCHAR(50),
    direction VARCHAR(10),
    confidence DECIMAL(4,3),
    horizon VARCHAR(10),
    summary TEXT,
    source_urls TEXT[],
    extracted_facts JSONB,
    discovered_at TIMESTAMP,
    expires_at TIMESTAMP,
    raw_article_hash VARCHAR(100),
    status VARCHAR(20) DEFAULT 'candidate',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trading_audit (
    id BIGSERIAL PRIMARY KEY,
    event_time TIMESTAMP NOT NULL DEFAULT NOW(),
    clerk_user_id VARCHAR(255),
    actor VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    payload JSONB,
    prev_hash VARCHAR(64),
    this_hash VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_ticker_time
    ON signals(ticker, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_run_id
    ON signals(run_id);
CREATE INDEX IF NOT EXISTS idx_signals_pending_outcome
    ON signals(generated_at)
    WHERE outcome_pct IS NULL;
CREATE INDEX IF NOT EXISTS idx_signals_strong
    ON signals(ticker, generated_at DESC)
    WHERE magnitude IN ('HIGH','EXTREME')
      AND confidence = 'HIGH';

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS update_briefs_updated_at ON briefs;
CREATE TRIGGER update_briefs_updated_at
    BEFORE UPDATE ON briefs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Utility: idempotent brief upsert
--
-- Returns the brief id either way. If the dedupe_key already exists, returns
-- the existing id and does NOT overwrite content (avoids clobbering manual
-- edits). Callers can pass force:=true to update instead.
-- ============================================================================
CREATE OR REPLACE FUNCTION upsert_brief(
    p_run_id              VARCHAR,
    p_generated_at        TIMESTAMPTZ,
    p_window              VARCHAR,
    p_universe            TEXT[],
    p_mode                VARCHAR,
    p_dedupe_key          VARCHAR,
    p_top_ticker          VARCHAR,
    p_top_dir             VARCHAR,
    p_top_rationale       TEXT,
    p_risks               TEXT[],
    p_raw_output          TEXT,
    p_source_hash         CHAR(64),
    force                 BOOLEAN DEFAULT FALSE
) RETURNS UUID
LANGUAGE plpgsql AS $$
DECLARE
    v_id UUID;
BEGIN
    IF p_dedupe_key IS NOT NULL THEN
        SELECT id INTO v_id FROM briefs WHERE dedupe_key = p_dedupe_key;
        IF v_id IS NOT NULL AND NOT force THEN
            RETURN v_id;
        END IF;
    END IF;

    IF v_id IS NOT NULL THEN
        UPDATE briefs SET
            run_id = p_run_id,
            generated_at = p_generated_at,
            window = p_window,
            universe = p_universe,
            mode = p_mode,
            top_signal_ticker = p_top_ticker,
            top_signal_dir = p_top_dir,
            top_signal_rationale = p_top_rationale,
            risks_and_caveats = p_risks,
            raw_output = p_raw_output,
            source_hash = p_source_hash,
            updated_at = NOW()
        WHERE id = v_id;
        RETURN v_id;
    END IF;

    INSERT INTO briefs (
        run_id, generated_at, window, universe, mode,
        dedupe_key, top_signal_ticker, top_signal_dir, top_signal_rationale,
        risks_and_caveats, raw_output, source_hash
    ) VALUES (
        p_run_id, p_generated_at, p_window, p_universe, p_mode,
        p_dedupe_key, p_top_ticker, p_top_dir, p_top_rationale,
        p_risks, p_raw_output, p_source_hash
    ) RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;