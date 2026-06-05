import { useEffect, useState } from "react";
import {
  addTradeJournalPlan,
  askTraderCopilot,
  cancelTraderOrder,
  evaluateTraderMargin,
  getBrokerReconciliation,
  getComplianceCenter,
  getEventCalendar,
  getExecutionQuality,
  getMarketReplay,
  getOptionsSuite,
  getTradeJournalV2,
  getTraderCommandCenter,
  getTraderOrderBlotter,
  getTraderWatchlists,
  replaceTraderOrder,
  submitOptionsApproval,
  submitReplayTrade,
  submitTraderOrder,
} from "../../services/api";
import { formatCurrency } from "../../utils/format";

function percent(value = 0) {
  return `${Math.round(Number(value) * 100)}%`;
}

function metricValue(value, fallback = "pending") {
  return value || value === 0 ? value : fallback;
}

function StatusBadge({ status = "ready" }) {
  const normalized = String(status).toLowerCase();
  const className =
    normalized.includes("healthy") || normalized.includes("passed") || normalized.includes("allowed") || normalized.includes("filled")
      ? "badge healthy"
      : normalized.includes("review") || normalized.includes("attention") || normalized.includes("blocked") || normalized.includes("rejected")
        ? "badge review"
        : "badge hold";
  return <span className={className}>{status}</span>;
}

function Metric({ label, value }) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function CompactTable({ columns, rows, emptyText = "No records available." }) {
  return (
    <div className="table-wrap operating-table">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row, index) => (
              <tr key={row.id || row.order_id || row.symbol || row.event_id || index}>
                {columns.map((column) => (
                  <td key={column.key}>{column.render ? column.render(row) : metricValue(row[column.key])}</td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td className="table-empty" colSpan={columns.length}>
                {emptyText}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export function PortfolioCommandCenter({ symbol = "MSFT" }) {
  const [command, setCommand] = useState(null);
  const [watchlists, setWatchlists] = useState(null);
  const [events, setEvents] = useState(null);
  const [quality, setQuality] = useState(null);
  const [reconciliation, setReconciliation] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    let active = true;
    setStatus("loading");
    Promise.all([
      getTraderCommandCenter(),
      getTraderWatchlists(),
      getEventCalendar(),
      getExecutionQuality(),
      getBrokerReconciliation(),
    ])
      .then(([commandData, watchlistData, eventData, qualityData, reconciliationData]) => {
        if (!active) return;
        setCommand(commandData);
        setWatchlists(watchlistData);
        setEvents(eventData);
        setQuality(qualityData);
        setReconciliation(reconciliationData);
        setStatus("ready");
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [symbol]);

  const totals = command?.totals || {};
  const exposure = command?.exposure || {};

  return (
    <section className="operating-stack">
      <section className="metrics">
        <Metric label="Equity" value={formatCurrency(totals.equity || 0)} />
        <Metric label="Cash" value={formatCurrency(totals.cash || 0)} />
        <Metric label="Buying power" value={formatCurrency(totals.buying_power || 0)} />
        <Metric label="Day P&L" value={formatCurrency(totals.day_pnl || 0)} />
      </section>

      <section className="analysis-grid">
        <article className="panel">
          <header>
            <div>
              <span>Command center</span>
              <strong>Portfolio operating view</strong>
            </div>
            <StatusBadge status={status} />
          </header>
          <CompactTable
            columns={[
              { key: "symbol", label: "Symbol" },
              { key: "quantity", label: "Qty" },
              { key: "last_price", label: "Last", render: (row) => formatCurrency(row.last_price) },
              { key: "market_value", label: "Value", render: (row) => formatCurrency(row.market_value) },
              { key: "unrealized_pnl", label: "Unrealized", render: (row) => formatCurrency(row.unrealized_pnl) },
              { key: "sector", label: "Sector" },
            ]}
            rows={command?.positions || []}
          />
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Exposure</span>
              <strong>Factor and sector load</strong>
            </div>
          </header>
          {Object.entries(exposure.sectors || {}).map(([name, value]) => (
            <div className="row" key={name}>
              <span>{name.replaceAll("_", " ")}</span>
              <strong>{percent(value)}</strong>
            </div>
          ))}
          {Object.entries(exposure.factors || {})
            .slice(0, 5)
            .map(([name, value]) => (
              <div className="row" key={name}>
                <span>{name.replaceAll("_", " ")}</span>
                <strong>{percent(value)}</strong>
              </div>
            ))}
        </article>
      </section>

      <section className="analysis-grid">
        <article className="panel">
          <header>
            <div>
              <span>Open orders</span>
              <strong>Blotter preview</strong>
            </div>
          </header>
          {(command?.open_orders || []).map((order) => (
            <div className="row" key={order.order_id}>
              <span>{order.symbol} {order.side} {order.quantity}</span>
              <strong>{order.status}</strong>
            </div>
          ))}
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Broker health</span>
              <strong>Reconciliation</strong>
            </div>
          </header>
          {(reconciliation?.connections || command?.broker_health || []).map((connection) => (
            <div className="row" key={connection.broker}>
              <span>{connection.broker}</span>
              <strong>{connection.status}</strong>
            </div>
          ))}
          {(reconciliation?.alerts || []).map((alert) => (
            <p className="operating-note" key={alert.title}>{alert.detail}</p>
          ))}
        </article>
      </section>

      <section className="analysis-grid">
        <article className="panel">
          <header>
            <div>
              <span>Watchlists</span>
              <strong>Screeners and heat maps</strong>
            </div>
          </header>
          {(watchlists?.watchlists || []).map((watchlist) => (
            <div className="row" key={watchlist.watchlist_id}>
              <span>{watchlist.name}</span>
              <strong>{watchlist.symbols.join(", ")}</strong>
            </div>
          ))}
          {(watchlists?.why_moving || []).map((item) => (
            <p className="operating-note" key={item.symbol}>{item.symbol}: {item.reason}</p>
          ))}
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Events</span>
              <strong>Catalyst risk</strong>
            </div>
          </header>
          {(events?.events || []).slice(0, 4).map((event) => (
            <div className="row" key={event.event_id}>
              <span>{event.title}</span>
              <strong>{event.impact}</strong>
            </div>
          ))}
          <div className="row">
            <span>Avg slippage</span>
            <strong>{quality?.summary ? `${quality.summary.average_slippage_bps} bps` : "pending"}</strong>
          </div>
        </article>
      </section>
    </section>
  );
}

export function StockTradeTicket({ symbol = "MSFT" }) {
  const [ticket, setTicket] = useState({
    symbol,
    quantity: 10,
    order_type: "limit",
    limit_price: 420,
    current_price: 420,
    broker: "alpaca",
    time_in_force: "day",
    extended_hours: false,
  });
  const [status, setStatus] = useState("ready");
  const [precheck, setPrecheck] = useState(null);
  const [lastOrder, setLastOrder] = useState(null);

  useEffect(() => {
    setTicket((current) => ({ ...current, symbol }));
  }, [symbol]);

  const updateTicket = (key, value) => setTicket((current) => ({ ...current, [key]: value }));

  const submitSide = async (side) => {
    setStatus(`checking ${side.toLowerCase()}`);
    const payload = {
      ...ticket,
      side,
      symbol: ticket.symbol || symbol,
      quantity: Number(ticket.quantity),
      limit_price: Number(ticket.limit_price),
      current_price: Number(ticket.current_price || ticket.limit_price),
      asset_type: "equity",
      options_approved: true,
    };
    try {
      const check = await evaluateTraderMargin(payload);
      setPrecheck(check);
      if (!check.allowed) {
        setStatus("blocked");
        return;
      }
      setStatus(`submitting ${side.toLowerCase()}`);
      const order = await submitTraderOrder(payload);
      setLastOrder(order.order);
      setStatus(order.status);
    } catch {
      setStatus("error");
    }
  };

  const notional = Number(ticket.quantity || 0) * Number(ticket.limit_price || 0);

  return (
    <section className="analysis-grid">
      <article className="panel trade-ticket-wide">
        <header>
          <div>
            <span>Trade</span>
            <strong>Buy or sell stock</strong>
          </div>
          <StatusBadge status={status} />
        </header>
        <div className="ticket-grid">
          <label>
            Symbol
            <input value={ticket.symbol} onChange={(event) => updateTicket("symbol", event.target.value.toUpperCase())} />
          </label>
          <label>
            Quantity
            <input min="1" type="number" value={ticket.quantity} onChange={(event) => updateTicket("quantity", Number(event.target.value))} />
          </label>
          <label>
            Order type
            <select value={ticket.order_type} onChange={(event) => updateTicket("order_type", event.target.value)}>
              <option value="market">Market</option>
              <option value="limit">Limit</option>
              <option value="stop">Stop</option>
              <option value="TWAP">TWAP</option>
              <option value="VWAP">VWAP</option>
            </select>
          </label>
          <label>
            Limit price
            <input min="0" step="0.01" type="number" value={ticket.limit_price} onChange={(event) => updateTicket("limit_price", Number(event.target.value))} />
          </label>
          <label>
            Time in force
            <select value={ticket.time_in_force} onChange={(event) => updateTicket("time_in_force", event.target.value)}>
              <option value="day">DAY</option>
              <option value="gtc">GTC</option>
              <option value="ioc">IOC</option>
            </select>
          </label>
          <label>
            Broker
            <select value={ticket.broker} onChange={(event) => updateTicket("broker", event.target.value)}>
              <option value="alpaca">Alpaca</option>
              <option value="ibkr">IBKR</option>
            </select>
          </label>
        </div>
        <label className="check-row">
          <input checked={ticket.extended_hours} type="checkbox" onChange={() => updateTicket("extended_hours", !ticket.extended_hours)} />
          Extended-hours eligible
        </label>
        <div className="row">
          <span>Estimated notional</span>
          <strong>{formatCurrency(notional)}</strong>
        </div>
        <div className="row">
          <span>Pre-trade status</span>
          <strong>{precheck ? (precheck.allowed ? "Allowed" : precheck.violations.join(", ")) : "pending"}</strong>
        </div>
        <div className="trade-side-buttons">
          <button type="button" className="buy-button" disabled={status.includes("checking") || status.includes("submitting")} onClick={() => submitSide("BUY")}>
            Buy {ticket.symbol || symbol}
          </button>
          <button type="button" className="sell-button" disabled={status.includes("checking") || status.includes("submitting")} onClick={() => submitSide("SELL")}>
            Sell {ticket.symbol || symbol}
          </button>
        </div>
      </article>

      <article className="panel">
        <header>
          <div>
            <span>Last order</span>
            <strong>{lastOrder ? lastOrder.order_id : "No order submitted"}</strong>
          </div>
        </header>
        <div className="row">
          <span>Side</span>
          <strong>{lastOrder?.side || "pending"}</strong>
        </div>
        <div className="row">
          <span>Status</span>
          <strong>{lastOrder?.status || "pending"}</strong>
        </div>
        <div className="row">
          <span>Quantity</span>
          <strong>{lastOrder?.quantity || ticket.quantity}</strong>
        </div>
        <div className="row">
          <span>Audit</span>
          <strong>{lastOrder?.audit_id || "pending"}</strong>
        </div>
      </article>
    </section>
  );
}

export function OrderBlotter({ symbol = "MSFT" }) {
  const [data, setData] = useState(null);
  const [ticket, setTicket] = useState({
    symbol,
    side: "BUY",
    quantity: 25,
    order_type: "limit",
    limit_price: 420,
    current_price: 420,
    broker: "alpaca",
    time_in_force: "day",
    extended_hours: false,
  });
  const [margin, setMargin] = useState(null);
  const [actionStatus, setActionStatus] = useState("idle");

  const load = () => getTraderOrderBlotter().then(setData).catch(() => setData(null));

  useEffect(() => {
    load();
  }, []);

  const updateTicket = (key, value) => setTicket((current) => ({ ...current, [key]: value }));

  const runMargin = async () => {
    setActionStatus("checking");
    try {
      const result = await evaluateTraderMargin(ticket);
      setMargin(result);
      setActionStatus(result.allowed ? "allowed" : "blocked");
    } catch {
      setActionStatus("error");
    }
  };

  const submit = async () => {
    setActionStatus("submitting");
    try {
      const result = await submitTraderOrder(ticket);
      setMargin(result.precheck);
      setActionStatus(result.status);
      await load();
    } catch {
      setActionStatus("error");
    }
  };

  const cancelFirst = async () => {
    const orderId = data?.open_orders?.[0]?.order_id;
    if (!orderId) return;
    setActionStatus("canceling");
    await cancelTraderOrder(orderId).catch(() => undefined);
    await load();
    setActionStatus("canceled");
  };

  const replaceFirst = async () => {
    const orderId = data?.open_orders?.[0]?.order_id;
    if (!orderId) return;
    setActionStatus("replacing");
    await replaceTraderOrder(orderId, { quantity: Number(ticket.quantity), limit_price: Number(ticket.limit_price) }).catch(() => undefined);
    await load();
    setActionStatus("replaced");
  };

  return (
    <section className="analysis-grid">
      <article className="panel">
        <header>
          <div>
            <span>Order ticket</span>
            <strong>Advanced sandbox routing</strong>
          </div>
          <StatusBadge status={actionStatus} />
        </header>
        <div className="ticket-grid">
          <label>
            Symbol
            <input value={ticket.symbol} onChange={(event) => updateTicket("symbol", event.target.value.toUpperCase())} />
          </label>
          <label>
            Side
            <select value={ticket.side} onChange={(event) => updateTicket("side", event.target.value)}>
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </label>
          <label>
            Quantity
            <input type="number" value={ticket.quantity} onChange={(event) => updateTicket("quantity", Number(event.target.value))} />
          </label>
          <label>
            Type
            <select value={ticket.order_type} onChange={(event) => updateTicket("order_type", event.target.value)}>
              <option value="market">Market</option>
              <option value="limit">Limit</option>
              <option value="stop">Stop</option>
              <option value="bracket">Bracket</option>
              <option value="oco">OCO</option>
              <option value="trailing_stop">Trailing stop</option>
              <option value="TWAP">TWAP</option>
              <option value="VWAP">VWAP</option>
            </select>
          </label>
          <label>
            Limit
            <input type="number" value={ticket.limit_price} onChange={(event) => updateTicket("limit_price", Number(event.target.value))} />
          </label>
          <label>
            TIF
            <select value={ticket.time_in_force} onChange={(event) => updateTicket("time_in_force", event.target.value)}>
              <option value="day">DAY</option>
              <option value="gtc">GTC</option>
              <option value="ioc">IOC</option>
            </select>
          </label>
        </div>
        <label className="check-row">
          <input checked={ticket.extended_hours} type="checkbox" onChange={() => updateTicket("extended_hours", !ticket.extended_hours)} />
          Extended-hours eligible
        </label>
        <div className="row">
          <span>Margin status</span>
          <strong>{margin ? (margin.allowed ? "Allowed" : margin.violations.join(", ")) : "pending"}</strong>
        </div>
        <div className="row">
          <span>Intraday requirement</span>
          <strong>{margin ? formatCurrency(margin.intraday_margin_requirement) : "pending"}</strong>
        </div>
        <button type="button" className="ghost-button" disabled={actionStatus === "checking"} onClick={runMargin}>
          {actionStatus === "checking" ? "Checking" : "Check margin"}
        </button>
        <button type="button" disabled={actionStatus === "submitting"} onClick={submit}>
          {actionStatus === "submitting" ? "Submitting" : "Submit sandbox order"}
        </button>
        <button type="button" className="ghost-button" onClick={replaceFirst}>Replace first order</button>
        <button type="button" className="ghost-button" onClick={cancelFirst}>Cancel first order</button>
      </article>

      <article className="panel">
        <header>
          <div>
            <span>Order blotter</span>
            <strong>Open orders and fills</strong>
          </div>
        </header>
        <CompactTable
          columns={[
            { key: "symbol", label: "Symbol" },
            { key: "side", label: "Side" },
            { key: "quantity", label: "Qty" },
            { key: "order_type", label: "Type" },
            { key: "status", label: "Status" },
            { key: "broker", label: "Broker" },
          ]}
          rows={data?.open_orders || []}
        />
      </article>
    </section>
  );
}

export function OptionsSuite({ symbol = "MSFT" }) {
  const [data, setData] = useState(null);
  const [approval, setApproval] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    setStatus("loading");
    getOptionsSuite(symbol)
      .then((result) => {
        setData(result);
        setApproval(result.approval);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, [symbol]);

  const requestApproval = async () => {
    setStatus("requesting");
    try {
      const result = await submitOptionsApproval({
        experience: "advanced",
        objective: "hedging",
        risk_disclosure_acknowledged: true,
      });
      setApproval(result);
      setStatus("approved");
    } catch {
      setStatus("error");
    }
  };

  return (
    <section className="analysis-grid">
      <article className="panel">
        <header>
          <div>
            <span>Options suite</span>
            <strong>{data?.underlying?.symbol || symbol}</strong>
          </div>
          <StatusBadge status={status} />
        </header>
        <div className="row">
          <span>Last price</span>
          <strong>{formatCurrency(data?.underlying?.last_price || 0)}</strong>
        </div>
        <div className="row">
          <span>IV rank</span>
          <strong>{data?.underlying?.iv_rank || "pending"}</strong>
        </div>
        <div className="row">
          <span>Options level</span>
          <strong>{approval?.options_level ?? "pending"}</strong>
        </div>
        <div className="row">
          <span>Allowed</span>
          <strong>{approval?.allowed_strategies?.join(", ") || "none"}</strong>
        </div>
        <button type="button" onClick={requestApproval}>Request sandbox approval</button>
      </article>

      <article className="panel">
        <header>
          <div>
            <span>Strategy builder</span>
            <strong>Payoff and risk</strong>
          </div>
        </header>
        {(data?.strategy_builder || []).map((strategy) => (
          <div className="row" key={strategy.strategy}>
            <span>{strategy.strategy.replaceAll("_", " ")}</span>
            <strong>{strategy.probability_of_profit ? percent(strategy.probability_of_profit) : formatCurrency(strategy.max_gain)}</strong>
          </div>
        ))}
      </article>

      <article className="panel operating-wide">
        <header>
          <div>
            <span>Options chain</span>
            <strong>Greeks and liquidity</strong>
          </div>
        </header>
        <CompactTable
          columns={[
            { key: "option_symbol", label: "Contract" },
            { key: "strike", label: "Strike" },
            { key: "option_type", label: "Type" },
            { key: "bid", label: "Bid" },
            { key: "ask", label: "Ask" },
            { key: "implied_volatility", label: "IV", render: (row) => percent(row.implied_volatility) },
            { key: "delta", label: "Delta" },
            { key: "open_interest", label: "OI" },
          ]}
          rows={(data?.chain || []).slice(0, 8)}
        />
      </article>
    </section>
  );
}

export function MarketReplay({ symbol = "MSFT" }) {
  const [replay, setReplay] = useState(null);
  const [trade, setTrade] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    setStatus("loading");
    getMarketReplay(symbol)
      .then((result) => {
        setReplay(result);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, [symbol]);

  const bars = replay?.bars || [];
  const finalBar = bars[bars.length - 1];

  const simulate = async () => {
    setStatus("simulating");
    try {
      const result = await submitReplayTrade({
        symbol,
        side: "BUY",
        quantity: 15,
        price: finalBar?.close || 100,
      });
      setTrade(result);
      setStatus("simulated");
    } catch {
      setStatus("error");
    }
  };

  return (
    <section className="analysis-grid">
      <article className="panel">
        <header>
          <div>
            <span>Market replay</span>
            <strong>{replay?.session_date || "session"}</strong>
          </div>
          <StatusBadge status={status} />
        </header>
        <div className="row">
          <span>Signal at start</span>
          <strong>{replay?.ai_signal_at_start?.signal || "pending"}</strong>
        </div>
        <div className="row">
          <span>Confidence</span>
          <strong>{replay?.ai_signal_at_start ? percent(replay.ai_signal_at_start.confidence) : "pending"}</strong>
        </div>
        <div className="row">
          <span>Replay bars</span>
          <strong>{bars.length}</strong>
        </div>
        <div className="row">
          <span>Simulated trade</span>
          <strong>{trade ? `${trade.side} ${trade.quantity}` : "none"}</strong>
        </div>
        <button type="button" onClick={simulate}>{status === "simulating" ? "Simulating" : "Place replay trade"}</button>
      </article>

      <article className="panel">
        <header>
          <div>
            <span>Replay tape</span>
            <strong>Candle sequence</strong>
          </div>
        </header>
        <CompactTable
          columns={[
            { key: "time", label: "Time", render: (row) => row.time.slice(11, 16) },
            { key: "open", label: "Open" },
            { key: "high", label: "High" },
            { key: "low", label: "Low" },
            { key: "close", label: "Close" },
            { key: "volume", label: "Volume" },
          ]}
          rows={bars.slice(0, 10)}
        />
      </article>
    </section>
  );
}

export function TradeJournalPro({ symbol = "MSFT" }) {
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");

  const load = () => getTradeJournalV2().then(setData).catch(() => setData(null));

  useEffect(() => {
    load().finally(() => setStatus("ready"));
  }, []);

  const addPlan = async () => {
    setStatus("saving");
    await addTradeJournalPlan({
      symbol,
      setup: "breakout retest",
      pre_trade_plan: "Enter only after signal freshness remains above 70%.",
      thesis: "Momentum continuation with defined stop and event-risk check.",
      confidence_tag: "medium",
      emotion_tag: "focused",
      setup_quality: 78,
    }).catch(() => undefined);
    await load();
    setStatus("saved");
  };

  return (
    <section className="analysis-grid">
      <article className="panel">
        <header>
          <div>
            <span>Trade Journal 2.0</span>
            <strong>Plan, review, improve</strong>
          </div>
          <StatusBadge status={status} />
        </header>
        <div className="row">
          <span>Expectancy</span>
          <strong>{data?.analytics?.expectancy ?? "pending"}</strong>
        </div>
        <div className="row">
          <span>Setup quality</span>
          <strong>{data?.analytics?.average_setup_quality ?? "pending"}</strong>
        </div>
        <button type="button" onClick={addPlan}>{status === "saving" ? "Saving" : "Add pre-trade plan"}</button>
      </article>
      <article className="panel">
        <header>
          <div>
            <span>Recent reviews</span>
            <strong>AI post-trade notes</strong>
          </div>
        </header>
        {(data?.entries || []).map((entry) => (
          <div className="journal-entry" key={entry.journal_id}>
            <strong>{entry.symbol} - {entry.setup}</strong>
            <p>{entry.ai_post_trade_review}</p>
          </div>
        ))}
      </article>
    </section>
  );
}

export function TraderCopilot() {
  const [question, setQuestion] = useState("Why is MSFT a hold today?");
  const [response, setResponse] = useState(null);
  const [status, setStatus] = useState("idle");

  const ask = async () => {
    setStatus("thinking");
    try {
      const result = await askTraderCopilot(question);
      setResponse(result);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  return (
    <section className="analysis-grid">
      <article className="panel">
        <header>
          <div>
            <span>AI copilot</span>
            <strong>Guardrailed assistant</strong>
          </div>
          <StatusBadge status={status} />
        </header>
        <label>
          Question
          <textarea rows="4" value={question} onChange={(event) => setQuestion(event.target.value)} />
        </label>
        <button type="button" onClick={ask}>{status === "thinking" ? "Thinking" : "Ask copilot"}</button>
      </article>
      <article className="panel">
        <header>
          <div>
            <span>Response</span>
            <strong>Audited context</strong>
          </div>
        </header>
        <p>{response?.answer || "Ask a portfolio, signal, risk, replay, or disclosure question."}</p>
        {(response?.citations || []).map((citation) => (
          <div className="row" key={citation}>
            <span>Source</span>
            <strong>{citation}</strong>
          </div>
        ))}
        <div className="row">
          <span>Trade action</span>
          <strong>{response?.guardrails?.can_place_trade ? "available" : "confirmation required"}</strong>
        </div>
      </article>
    </section>
  );
}

export function ComplianceCenter() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getComplianceCenter().then(setData).catch(() => setData(null));
  }, []);

  return (
    <section className="analysis-grid">
      <article className="panel">
        <header>
          <div>
            <span>Compliance</span>
            <strong>Disclosure center</strong>
          </div>
          <StatusBadge status={data?.risk_profile_fit?.status || "loading"} />
        </header>
        {(data?.recommendation_basis || []).map((item) => (
          <div className="row" key={item}>
            <span>{item.replaceAll("_", " ")}</span>
            <strong>included</strong>
          </div>
        ))}
      </article>
      <article className="panel">
        <header>
          <div>
            <span>Attestations</span>
            <strong>Required acknowledgements</strong>
          </div>
        </header>
        {(data?.attestations || []).map((attestation) => (
          <div className="row" key={attestation.disclosure_id}>
            <span>{attestation.title}</span>
            <strong>{attestation.status}</strong>
          </div>
        ))}
        {(data?.fees_and_conflicts || []).map((item) => (
          <p className="operating-note" key={item}>{item}</p>
        ))}
      </article>
    </section>
  );
}

export default PortfolioCommandCenter;
