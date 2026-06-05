import { useEffect, useState } from "react";
import {
  approveStagedOrder,
  cancelAllEmergencyOrders,
  constructPortfolio,
  deployStrategy,
  evaluateRiskConstitution,
  getBasketWorkbench,
  getBorrowDesk,
  getDataQualityDashboard,
  getDisclosureArchive,
  getEmergencyControls,
  getMarketMicrostructure,
  getRiskConstitution,
  getTaxLotDecision,
  getTradeStaging,
  getWorkstationOverview,
  pauseTradingEmergency,
  previewBasket,
  releaseStagedOrder,
  requestBorrowLocate,
  researchStrategy,
  runPreTradeControl,
  saveRiskConstitutionRule,
  stageWorkstationOrder,
  submitBasket,
} from "../../services/api";
import { formatCurrency } from "../../utils/format";

function percent(value = 0) {
  return `${Math.round(Number(value) * 100)}%`;
}

function money(value = 0) {
  return formatCurrency(Number(value || 0));
}

function Badge({ status = "ready" }) {
  const normalized = String(status).toLowerCase();
  const className =
    normalized.includes("pass") || normalized.includes("ready") || normalized.includes("approved") || normalized.includes("allowed")
      ? "badge healthy"
      : normalized.includes("block") || normalized.includes("pause") || normalized.includes("degraded") || normalized.includes("required")
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

function Rows({ rows, render }) {
  if (!rows?.length) return <p className="operating-note">No records available.</p>;
  return rows.map(render);
}

function WeightRows({ weights = {} }) {
  return Object.entries(weights).map(([symbol, weight]) => (
    <div className="row" key={symbol}>
      <span>{symbol}</span>
      <strong>{percent(weight)}</strong>
    </div>
  ));
}

export default function Workstation({ symbol = "MSFT" }) {
  const [overview, setOverview] = useState(null);
  const [basket, setBasket] = useState(null);
  const [preTrade, setPreTrade] = useState(null);
  const [taxLots, setTaxLots] = useState(null);
  const [borrow, setBorrow] = useState(null);
  const [portfolio, setPortfolio] = useState(null);
  const [microstructure, setMicrostructure] = useState(null);
  const [staging, setStaging] = useState(null);
  const [quality, setQuality] = useState(null);
  const [strategy, setStrategy] = useState(null);
  const [risk, setRisk] = useState(null);
  const [archive, setArchive] = useState(null);
  const [emergency, setEmergency] = useState(null);
  const [actionStatus, setActionStatus] = useState("loading");

  const load = async () => {
    setActionStatus("loading");
    try {
      const [overviewData, basketData, taxData, borrowData, microData, stagingData, qualityData, strategyData, riskData, archiveData, emergencyData, portfolioData] =
        await Promise.all([
          getWorkstationOverview(),
          getBasketWorkbench(),
          getTaxLotDecision(symbol),
          getBorrowDesk(symbol),
          getMarketMicrostructure(symbol),
          getTradeStaging(),
          getDataQualityDashboard(),
          researchStrategy({ universe: [symbol, "NVDA", "JPM", "SPY"] }),
          getRiskConstitution(),
          getDisclosureArchive(),
          getEmergencyControls(),
          constructPortfolio({ objective: "balanced growth with tax awareness" }),
        ]);
      setOverview(overviewData);
      setBasket(basketData.drafts?.[0] || basketData);
      setPreTrade((basketData.drafts?.[0] || {}).pre_trade || null);
      setTaxLots(taxData);
      setBorrow(borrowData);
      setMicrostructure(microData);
      setStaging(stagingData);
      setQuality(qualityData);
      setStrategy(strategyData);
      setRisk(riskData);
      setArchive(archiveData);
      setEmergency(emergencyData);
      setPortfolio(portfolioData);
      setActionStatus("ready");
    } catch {
      setActionStatus("error");
    }
  };

  useEffect(() => {
    load();
  }, [symbol]);

  const previewCore = async () => {
    setActionStatus("previewing");
    const result = await previewBasket({
      name: "Active core rebalance",
      target_weights: { MSFT: 0.3, NVDA: 0.16, JPM: 0.2, SPY: 0.34 },
    });
    setBasket(result);
    setPreTrade(result.pre_trade);
    setActionStatus(result.status);
  };

  const submitCore = async () => {
    setActionStatus("submitting");
    const result = await submitBasket({
      basket_id: basket?.basket_id || "basket-core-rebalance",
      target_weights: basket?.target_weights || { MSFT: 0.3, NVDA: 0.16, JPM: 0.2, SPY: 0.34 },
      confirmed: true,
    });
    setActionStatus(result.status);
    await getTradeStaging().then(setStaging);
  };

  const runBlockedShortCheck = async () => {
    setActionStatus("checking");
    const result = await runPreTradeControl({
      symbol: "GME",
      side: "SELL_SHORT",
      quantity: 150,
      limit_price: 28.5,
      locate_status: "required",
      liquidity_score: 0.31,
    });
    setPreTrade(result);
    setActionStatus(result.status);
  };

  const requestLocate = async () => {
    setActionStatus("locating");
    const locate = await requestBorrowLocate({ symbol, quantity: 100 });
    setBorrow((current) => ({ ...(current || {}), locate_request: locate, locate_status: locate.status }));
    setActionStatus(locate.status);
  };

  const stageApproveRelease = async () => {
    setActionStatus("staging");
    const staged = await stageWorkstationOrder({ symbol, side: "BUY", quantity: 5, limit_price: microstructure?.nbbo?.ask || 100 });
    if (staged.status === "blocked") {
      setActionStatus("blocked");
      await getTradeStaging().then(setStaging);
      return;
    }
    await approveStagedOrder(staged.stage_id, { actor: "checker" });
    await releaseStagedOrder(staged.stage_id, { confirmed: true });
    await getTradeStaging().then(setStaging);
    setActionStatus("released");
  };

  const addRiskRule = async () => {
    setActionStatus("saving");
    await saveRiskConstitutionRule({ rule_type: "restricted_symbol", symbol: "TSLA", enforcement: "never_override" });
    const evaluation = await evaluateRiskConstitution({ symbol: "TSLA", position_pct: 0.1 });
    const rules = await getRiskConstitution();
    setRisk({ ...rules, latest_evaluation: evaluation });
    setActionStatus(evaluation.status);
  };

  const deployResearch = async () => {
    setActionStatus("deploying");
    const result = await deployStrategy({ ...(strategy || {}), confirmed: true });
    setStrategy((current) => ({ ...(current || {}), deployment: result }));
    setActionStatus(result.status);
  };

  const pauseAndCancel = async () => {
    setActionStatus("pausing");
    await pauseTradingEmergency({ reason: "manual workstation test" });
    await cancelAllEmergencyOrders({ reason: "manual workstation test" });
    const status = await getEmergencyControls();
    setEmergency(status);
    setActionStatus("emergency active");
  };

  return (
    <section className="operating-stack workstation-stack">
      <section className="metrics">
        <Metric label="Workstation" value={actionStatus} />
        <Metric label="Buying power" value={money(overview?.portfolio?.buying_power)} />
        <Metric label="Basket orders" value={basket?.orders?.length || 0} />
        <Metric label="Source confidence" value={percent((quality?.source_confidence || [])[0]?.confidence || 0)} />
      </section>

      <section className="analysis-grid">
        <article className="panel">
          <header>
            <div>
              <span>Basket workbench</span>
              <strong>{basket?.name || "Rebalance draft"}</strong>
            </div>
            <Badge status={basket?.status || actionStatus} />
          </header>
          <WeightRows weights={basket?.target_weights} />
          <div className="row">
            <span>Tax estimate</span>
            <strong>{money(basket?.impact_preview?.estimated_tax_cost)}</strong>
          </div>
          <div className="row">
            <span>Margin delta</span>
            <strong>{money(basket?.impact_preview?.estimated_margin_delta)}</strong>
          </div>
          <button type="button" className="ghost-button" onClick={previewCore}>Preview rebalance</button>
          <button type="button" onClick={submitCore}>Stage confirmed basket</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Pre-trade control</span>
              <strong>Fail-closed release gate</strong>
            </div>
            <Badge status={preTrade?.status || "pending"} />
          </header>
          <Rows
            rows={(preTrade?.checks || []).slice(0, 6)}
            render={(check) => (
              <div className="row" key={check.name}>
                <span>{check.name.replaceAll("_", " ")}</span>
                <strong>{check.status}</strong>
              </div>
            )}
          />
          <button type="button" className="ghost-button" onClick={runBlockedShortCheck}>Test short block</button>
        </article>
      </section>

      <section className="analysis-grid">
        <article className="panel">
          <header>
            <div>
              <span>Tax and lots</span>
              <strong>{taxLots?.symbol || symbol}</strong>
            </div>
            <Badge status={taxLots?.wash_sale_risk || "ready"} />
          </header>
          <Rows
            rows={taxLots?.lots}
            render={(lot) => (
              <div className="row" key={lot.lot_id}>
                <span>{lot.lot_id}</span>
                <strong>{money(lot.unrealized_gain)}</strong>
              </div>
            )}
          />
          <div className="row">
            <span>Best lot</span>
            <strong>{taxLots?.best_lot_to_sell || "pending"}</strong>
          </div>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Borrow desk</span>
              <strong>{borrow?.symbol || symbol}</strong>
            </div>
            <Badge status={borrow?.locate_status || "pending"} />
          </header>
          <div className="row">
            <span>Borrow fee</span>
            <strong>{percent(borrow?.borrow_fee_rate || 0)}</strong>
          </div>
          <div className="row">
            <span>Recall risk</span>
            <strong>{borrow?.recall_risk || "pending"}</strong>
          </div>
          <div className="row">
            <span>Squeeze risk</span>
            <strong>{borrow?.squeeze_risk || "pending"}</strong>
          </div>
          <button type="button" onClick={requestLocate}>Request sandbox locate</button>
        </article>
      </section>

      <section className="analysis-grid">
        <article className="panel">
          <header>
            <div>
              <span>Portfolio lab</span>
              <strong>{portfolio?.name || "Model portfolio"}</strong>
            </div>
          </header>
          <WeightRows weights={portfolio?.target_allocations} />
          <div className="row">
            <span>Expected volatility</span>
            <strong>{percent(portfolio?.expected_volatility || 0)}</strong>
          </div>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Microstructure</span>
              <strong>{microstructure?.symbol || symbol}</strong>
            </div>
            <Badge status={microstructure?.likely_to_move_market ? "review" : "ready"} />
          </header>
          <div className="row">
            <span>NBBO</span>
            <strong>{money(microstructure?.nbbo?.bid)} / {money(microstructure?.nbbo?.ask)}</strong>
          </div>
          <div className="row">
            <span>Liquidity</span>
            <strong>{percent(microstructure?.liquidity_score || 0)}</strong>
          </div>
          <div className="row">
            <span>Impact</span>
            <strong>{microstructure?.estimated_market_impact_bps || 0} bps</strong>
          </div>
        </article>
      </section>

      <section className="analysis-grid">
        <article className="panel">
          <header>
            <div>
              <span>Trade staging</span>
              <strong>Maker/checker release queue</strong>
            </div>
          </header>
          <Rows
            rows={(staging?.staged_orders || []).slice(0, 4)}
            render={(order) => (
              <div className="row" key={order.stage_id}>
                <span>{order.symbol} {order.side} {order.quantity}</span>
                <strong>{order.status}</strong>
              </div>
            )}
          />
          <button type="button" onClick={stageApproveRelease}>Stage, approve, release</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Data quality</span>
              <strong>Source confidence</strong>
            </div>
            <Badge status={quality?.overall_status || "pending"} />
          </header>
          <Rows
            rows={quality?.vendor_health}
            render={(source) => (
              <div className="row" key={source.source}>
                <span>{source.source}</span>
                <strong>{source.status}</strong>
              </div>
            )}
          />
        </article>
      </section>

      <section className="analysis-grid">
        <article className="panel">
          <header>
            <div>
              <span>Strategy research</span>
              <strong>{strategy?.name || "Rules workbench"}</strong>
            </div>
            <Badge status={strategy?.paper_deploy?.status || strategy?.deployment?.status || "research"} />
          </header>
          <div className="row">
            <span>Sharpe</span>
            <strong>{strategy?.walk_forward_report?.sharpe || "pending"}</strong>
          </div>
          <div className="row">
            <span>Win rate</span>
            <strong>{percent(strategy?.walk_forward_report?.win_rate || 0)}</strong>
          </div>
          <button type="button" onClick={deployResearch}>Paper deploy strategy</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Risk constitution</span>
              <strong>Hard personal rules</strong>
            </div>
            <Badge status={risk?.latest_evaluation?.status || risk?.enforcement || "ready"} />
          </header>
          <Rows
            rows={(risk?.rules || []).slice(0, 5)}
            render={(rule) => (
              <div className="row" key={rule.rule_id}>
                <span>{rule.rule_type.replaceAll("_", " ")}</span>
                <strong>{String(rule.threshold)}</strong>
              </div>
            )}
          />
          <button type="button" className="ghost-button" onClick={addRiskRule}>Add TSLA restriction</button>
        </article>
      </section>

      <section className="analysis-grid">
        <article className="panel">
          <header>
            <div>
              <span>Disclosure archive</span>
              <strong>Searchable communications</strong>
            </div>
          </header>
          <Rows
            rows={(archive?.records || []).slice(0, 4)}
            render={(record) => (
              <div className="row" key={record.archive_id}>
                <span>{record.title}</span>
                <strong>{record.record_type}</strong>
              </div>
            )}
          />
        </article>

        <article className="panel emergency-panel">
          <header>
            <div>
              <span>Mobile emergency</span>
              <strong>Pause and cancel controls</strong>
            </div>
            <Badge status={emergency?.trading_paused ? "paused" : "armed"} />
          </header>
          <div className="row">
            <span>Open orders</span>
            <strong>{emergency?.open_order_count ?? "pending"}</strong>
          </div>
          <Rows
            rows={(emergency?.critical_alerts || []).slice(0, 2)}
            render={(alert) => <p className="operating-note" key={alert.title}>{alert.detail}</p>}
          />
          <button type="button" onClick={pauseAndCancel}>Pause and cancel all</button>
        </article>
      </section>
    </section>
  );
}
