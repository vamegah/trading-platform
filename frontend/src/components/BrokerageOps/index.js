import { useEffect, useState } from "react";
import {
  checkMarketDataEntitlement,
  createAdminOverride,
  createCashTransfer,
  createConditionalOrder,
  createRecurringInvestmentPlan,
  createSupportCase,
  evaluateSurveillance,
  generatePortfolioReviewPack,
  getAccountDocument,
  getAccountDocumentsCenter,
  getBrokerageAdminConsole,
  getBrokerageOpsOverview,
  getCashSettlementCenter,
  getChartTradingWorkspace,
  getCorporateActionsCenter,
  getMarketDataEntitlements,
  getMobileCompanion,
  getRecurringInvestments,
  getSupportCenter,
  getSurveillanceDashboard,
  pauseTradingFromMobile,
  previewChartOrder,
  recordCorporateActionElection,
  simulateConditionalOrder,
} from "../../services/api";
import { formatCurrency } from "../../utils/format";

function money(value = 0) {
  return formatCurrency(Number(value || 0));
}

function percent(value = 0) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function Badge({ status = "ready" }) {
  const normalized = String(status).toLowerCase();
  const className =
    normalized.includes("active") ||
    normalized.includes("ready") ||
    normalized.includes("available") ||
    normalized.includes("allowed") ||
    normalized.includes("generated")
      ? "badge healthy"
      : normalized.includes("block") ||
          normalized.includes("review") ||
          normalized.includes("required") ||
          normalized.includes("degraded") ||
          normalized.includes("pending")
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

function Row({ label, value }) {
  return (
    <div className="row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MiniRows({ rows = [], labelKey = "label", valueKey = "status" }) {
  if (!rows.length) return <p className="operating-note">No records available.</p>;
  return rows.slice(0, 4).map((row, index) => (
    <div className="row" key={row.id || row.action_id || row.document_id || row.case_id || row.alert_id || row.plan_id || index}>
      <span>{row[labelKey] || row.symbol || row.document_type || row.category || row.alert_type || row.data_type}</span>
      <strong>{row[valueKey] || row.status || row.severity || row.amount}</strong>
    </div>
  ));
}

export default function BrokerageOps({ symbol = "MSFT" }) {
  const [overview, setOverview] = useState(null);
  const [cash, setCash] = useState(null);
  const [chart, setChart] = useState(null);
  const [corporateActions, setCorporateActions] = useState(null);
  const [documents, setDocuments] = useState(null);
  const [admin, setAdmin] = useState(null);
  const [surveillance, setSurveillance] = useState(null);
  const [entitlements, setEntitlements] = useState(null);
  const [recurring, setRecurring] = useState(null);
  const [mobile, setMobile] = useState(null);
  const [support, setSupport] = useState(null);
  const [report, setReport] = useState(null);
  const [actionStatus, setActionStatus] = useState("loading");

  const load = async () => {
    setActionStatus("loading");
    try {
      const [
        overviewData,
        cashData,
        chartData,
        corporateData,
        documentData,
        adminData,
        surveillanceData,
        entitlementData,
        recurringData,
        mobileData,
        supportData,
      ] = await Promise.all([
        getBrokerageOpsOverview(),
        getCashSettlementCenter(),
        getChartTradingWorkspace(symbol),
        getCorporateActionsCenter(),
        getAccountDocumentsCenter(),
        getBrokerageAdminConsole(),
        getSurveillanceDashboard(),
        getMarketDataEntitlements(),
        getRecurringInvestments(),
        getMobileCompanion(),
        getSupportCenter(),
      ]);
      setOverview(overviewData);
      setCash(cashData);
      setChart(chartData);
      setCorporateActions(corporateData);
      setDocuments(documentData);
      setAdmin(adminData);
      setSurveillance(surveillanceData);
      setEntitlements(entitlementData);
      setRecurring(recurringData);
      setMobile(mobileData);
      setSupport(supportData);
      setActionStatus("ready");
    } catch {
      setActionStatus("error");
    }
  };

  useEffect(() => {
    load();
  }, [symbol]);

  const requestSandboxTransfer = async () => {
    setActionStatus("transfer");
    const result = await createCashTransfer({ direction: "deposit", method: "ach", amount: 2500 });
    setCash((current) => ({ ...(current || {}), transfer_statuses: [result, ...((current || {}).transfer_statuses || [])] }));
    setActionStatus(result.status);
  };

  const testLiveTransferGate = async () => {
    setActionStatus("checking gate");
    const result = await createCashTransfer({ direction: "withdrawal", method: "wire", amount: 1000, live: true });
    setCash((current) => ({ ...(current || {}), latest_transfer_gate: result }));
    setActionStatus(result.status);
  };

  const previewTradeFromChart = async () => {
    setActionStatus("previewing chart order");
    const result = await previewChartOrder({
      symbol,
      side: "BUY",
      quantity: 10,
      entry: chart?.levels?.entry,
      stop: chart?.levels?.stop,
      target: chart?.levels?.target,
    });
    setChart((current) => ({ ...(current || {}), latest_order_preview: result }));
    setActionStatus(result.status);
  };

  const submitElection = async () => {
    const action = (corporateActions?.actions || []).find((item) => item.election_required) || corporateActions?.actions?.[0];
    if (!action) return;
    setActionStatus("recording election");
    const result = await recordCorporateActionElection(action.action_id, { election: "hold_and_receive_cash", lot_selection: "specific_lot" });
    setCorporateActions((current) => ({ ...(current || {}), elections: [result, ...((current || {}).elections || [])] }));
    setActionStatus(result.status);
  };

  const previewDocument = async () => {
    const document = documents?.documents?.[0];
    if (!document) return;
    setActionStatus("opening document");
    const result = await getAccountDocument(document.document_id);
    setDocuments((current) => ({ ...(current || {}), selected_document: result }));
    setActionStatus(result.status || "available");
  };

  const queueAdminReview = async () => {
    setActionStatus("queueing review");
    const result = await createAdminOverride({
      confirmed: true,
      reason: "Sandbox supervisory review of blocked chart-trade release.",
      subject_ref: "chart-order-preview",
    });
    setAdmin((current) => ({ ...(current || {}), risk_overrides: [result, ...((current || {}).risk_overrides || [])] }));
    setActionStatus(result.status);
  };

  const runSurveillanceCheck = async () => {
    setActionStatus("surveillance");
    const result = await evaluateSurveillance({ symbol: "JPM", cancellations: 42, submitted: 90, event_blackout: true });
    setSurveillance((current) => ({ ...(current || {}), latest_evaluation: result, alerts: [...(result.alerts || []), ...((current || {}).alerts || [])] }));
    setActionStatus(result.status);
  };

  const checkLevelTwo = async () => {
    setActionStatus("entitlement");
    const result = await checkMarketDataEntitlement({ data_type: "level_ii", required_level: "real_time" });
    setEntitlements((current) => ({ ...(current || {}), latest_check: result }));
    setActionStatus(result.status);
  };

  const addRecurringPlan = async () => {
    setActionStatus("recurring");
    const result = await createRecurringInvestmentPlan({ symbol, dollar_amount: 250, cadence: "weekly", dividend_reinvestment: true });
    setRecurring((current) => ({ ...(current || {}), plans: [result, ...((current || {}).plans || [])] }));
    setActionStatus(result.status);
  };

  const armConditionalOrder = async () => {
    setActionStatus("conditional");
    const simulation = await simulateConditionalOrder({
      symbol,
      side: "BUY",
      quantity: 10,
      triggers: [{ field: "price", operator: "<=", value: chart?.levels?.entry || 420 }],
    });
    const order = await createConditionalOrder({ ...simulation, symbol, side: "BUY", quantity: 10, confirmed: true });
    setChart((current) => ({ ...(current || {}), conditional_order: order }));
    setActionStatus(order.status);
  };

  const buildReport = async () => {
    setActionStatus("reporting");
    const result = await generatePortfolioReviewPack({ title: `${symbol} portfolio review` });
    setReport(result);
    setActionStatus(result.status);
  };

  const pauseMobile = async () => {
    setActionStatus("mobile pause");
    const result = await pauseTradingFromMobile({ reason: "mobile companion test" });
    const refreshed = await getMobileCompanion();
    setMobile({ ...refreshed, latest_pause: result });
    setActionStatus(result.status);
  };

  const openSupportCase = async () => {
    setActionStatus("support");
    const result = await createSupportCase({
      category: "order_rejection",
      subject: "Why was this order rejected?",
      message: "Please attach the pre-trade and entitlement audit trail.",
      evidence_refs: [chart?.latest_order_preview?.audit_id].filter(Boolean),
    });
    setSupport((current) => ({ ...(current || {}), cases: [result, ...((current || {}).cases || [])] }));
    setActionStatus(result.status);
  };

  return (
    <section className="operating-stack brokerage-ops-stack">
      <section className="metrics">
        <Metric label="Operations" value={actionStatus} />
        <Metric label="Settled cash" value={money(cash?.cash_summary?.settled_cash)} />
        <Metric label="Unsettled" value={money(cash?.cash_summary?.unsettled_cash)} />
        <Metric label="Modules" value={overview?.modules?.length || 0} />
      </section>

      <section className="analysis-grid ops-grid">
        <article className="panel">
          <header>
            <div>
              <span>Cash and settlement</span>
              <strong>{money(cash?.cash_summary?.buying_power_after_pending)}</strong>
            </div>
            <Badge status={cash?.live_transfer_gate?.enabled ? "live" : "sandbox"} />
          </header>
          <Row label="Withdrawable" value={money(cash?.cash_summary?.cash_available_to_withdraw)} />
          <Row label="Pending transfers" value={cash?.transfer_statuses?.length || 0} />
          <Row label="Settlement warnings" value={cash?.warnings?.length || 0} />
          {cash?.latest_transfer_gate && <Row label="Live gate" value={cash.latest_transfer_gate.status} />}
          <div className="ops-action-row">
            <button type="button" onClick={requestSandboxTransfer}>Schedule ACH</button>
            <button type="button" className="ghost-button" onClick={testLiveTransferGate}>Test live gate</button>
          </div>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Chart trading</span>
              <strong>{chart?.symbol || symbol}</strong>
            </div>
            <Badge status={chart?.latest_order_preview?.status || chart?.pre_trade?.status || "precheck"} />
          </header>
          <div className="chart-level-grid">
            <div><span>Entry</span><strong>{money(chart?.levels?.entry)}</strong></div>
            <div><span>Stop</span><strong>{money(chart?.levels?.stop)}</strong></div>
            <div><span>Target</span><strong>{money(chart?.levels?.target)}</strong></div>
          </div>
          <Row label="Risk/reward" value={`${chart?.risk_reward?.ratio || 0}:1`} />
          <Row label="VWAP" value={money(chart?.vwap)} />
          <div className="ops-action-row">
            <button type="button" onClick={previewTradeFromChart}>Preview Buy</button>
            <button type="button" className="ghost-button" onClick={armConditionalOrder}>Arm conditional</button>
          </div>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Corporate actions</span>
              <strong>{corporateActions?.actions?.length || 0} events</strong>
            </div>
            <Badge status={(corporateActions?.actions || []).some((item) => item.election_required) ? "election required" : "ready"} />
          </header>
          <MiniRows rows={corporateActions?.actions || []} labelKey="symbol" valueKey="action_type" />
          <Row label="Recorded elections" value={corporateActions?.elections?.length || 0} />
          <button type="button" onClick={submitElection}>Record election</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Statements and tax docs</span>
              <strong>{documents?.documents?.length || 0} files</strong>
            </div>
            <Badge status={documents?.selected_document?.status || "available"} />
          </header>
          <MiniRows rows={documents?.documents || []} labelKey="document_type" valueKey="period" />
          {documents?.selected_document && <Row label="Preview" value={documents.selected_document.preview?.title} />}
          <button type="button" onClick={previewDocument}>Open statement</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Supervisory console</span>
              <strong>{admin?.role_gate?.current_mode || "role gated"}</strong>
            </div>
            <Badge status={admin?.role_gate?.required_role || "supervisor"} />
          </header>
          <Row label="Accounts" value={admin?.accounts?.length || 0} />
          <Row label="Risk reviews" value={admin?.risk_overrides?.length || 0} />
          <Row label="Broker outages" value={admin?.broker_outages?.length || 0} />
          <button type="button" onClick={queueAdminReview}>Queue review</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Surveillance</span>
              <strong>{surveillance?.alerts?.length || 0} alerts</strong>
            </div>
            <Badge status={surveillance?.latest_evaluation?.status || "monitoring"} />
          </header>
          <MiniRows rows={surveillance?.alerts || []} labelKey="alert_type" valueKey="severity" />
          <Row label="Release allowed" value={String(surveillance?.latest_evaluation?.release_allowed ?? true)} />
          <button type="button" onClick={runSurveillanceCheck}>Run check</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Market data entitlements</span>
              <strong>{money(entitlements?.cost_controls?.current_spend)}</strong>
            </div>
            <Badge status={entitlements?.latest_check?.status || "enforcing"} />
          </header>
          <MiniRows rows={entitlements?.entitlements || []} labelKey="data_type" valueKey="access_level" />
          {entitlements?.latest_check && <Row label="Level II" value={entitlements.latest_check.blocked_reason || "allowed"} />}
          <button type="button" onClick={checkLevelTwo}>Check Level II</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Recurring investing</span>
              <strong>{recurring?.plans?.length || 0} plans</strong>
            </div>
            <Badge status={recurring?.cash_sweep?.status || "sandbox"} />
          </header>
          <MiniRows rows={recurring?.plans || []} labelKey="symbol" valueKey="cadence" />
          <Row label="Cash sweep target" value={recurring?.cash_sweep?.target || "SGOV"} />
          <button type="button" onClick={addRecurringPlan}>Add weekly plan</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Client reports</span>
              <strong>{report?.title || "Portfolio review"}</strong>
            </div>
            <Badge status={report?.status || "ready"} />
          </header>
          <Row label="Formats" value={(report?.formats || ["html", "pdf", "csv"]).join(", ")} />
          <Row label="YTD excess" value={percent(report?.performance?.excess_return)} />
          <Row label="Archive" value={report?.archive_id || "not generated"} />
          <button type="button" onClick={buildReport}>Generate pack</button>
        </article>

        <article className="panel emergency-panel">
          <header>
            <div>
              <span>Mobile companion</span>
              <strong>{mobile?.devices?.[0]?.platform || "mobile"}</strong>
            </div>
            <Badge status={mobile?.latest_pause?.status || "push ready"} />
          </header>
          <Row label="Push alerts" value={mobile?.alerts?.length || 0} />
          <Row label="Biometric approval" value={String(mobile?.devices?.[0]?.biometric_approval_supported || false)} />
          <Row label="Trading paused" value={String(mobile?.state?.trading_paused || false)} />
          <button type="button" onClick={pauseMobile}>Mobile pause</button>
        </article>

        <article className="panel operating-wide">
          <header>
            <div>
              <span>Support, disputes, and audit requests</span>
              <strong>{support?.cases?.length || 0} cases</strong>
            </div>
            <Badge status={support?.cases?.[0]?.status || "ready"} />
          </header>
          <section className="ops-support-grid">
            <div>
              <MiniRows rows={support?.cases || []} labelKey="subject" valueKey="status" />
            </div>
            <div>
              <MiniRows rows={support?.incident_status || []} labelKey="type" valueKey="status" />
            </div>
          </section>
          <button type="button" onClick={openSupportCase}>Open support case</button>
        </article>
      </section>
    </section>
  );
}
