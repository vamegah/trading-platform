import { useEffect, useState } from "react";
import {
  compareMarketplaceStrategies,
  createAcatsTransfer,
  createCollaborationSpace,
  createOneStopAlertRule,
  evaluateAccountTypeRule,
  generateResearchBrief,
  getAccountTransferCenter,
  getAccountTypeRules,
  getAlertBuilder,
  getAutomationStudio,
  getBacktestMarketplace,
  getBrokerConnectivityHub,
  getCoachingCenter,
  getCollaborationLayer,
  getFeeYieldCenter,
  getMarketTerminal,
  getNotificationSystem,
  getOneStopOverview,
  getPortfolioAnalyticsPro,
  getResearchLab,
  getTrustCenter,
  lockAccountTrust,
  readDocumentAi,
  refreshBrokerConnection,
  simulateAutomation,
  testNotificationDelivery,
  testOneStopAlert,
} from "../../services/api";
import { formatCurrency } from "../../utils/format";

function money(value = 0) {
  return formatCurrency(Number(value || 0));
}

function pct(value = 0) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function Badge({ status = "ready" }) {
  const normalized = String(status).toLowerCase();
  const className =
    normalized.includes("ready") ||
    normalized.includes("active") ||
    normalized.includes("healthy") ||
    normalized.includes("sent") ||
    normalized.includes("allowed")
      ? "badge healthy"
      : normalized.includes("block") ||
          normalized.includes("degraded") ||
          normalized.includes("required") ||
          normalized.includes("review") ||
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

function MiniRows({ rows = [], labelKey = "name", valueKey = "status" }) {
  if (!rows.length) return <p className="operating-note">No records available.</p>;
  return rows.slice(0, 4).map((row, index) => (
    <div className="row" key={row.id || row[labelKey] || row.alert_rule_id || row.connection_id || row.transfer_id || row.listing_id || index}>
      <span>{row[labelKey] || row.symbol || row.title || row.category || row.event_type}</span>
      <strong>{row[valueKey] ?? row.status ?? row.change_pct ?? ""}</strong>
    </div>
  ));
}

export default function OneStop({ symbol = "MSFT" }) {
  const [overview, setOverview] = useState(null);
  const [terminal, setTerminal] = useState(null);
  const [research, setResearch] = useState(null);
  const [brokers, setBrokers] = useState(null);
  const [transfers, setTransfers] = useState(null);
  const [rules, setRules] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [automation, setAutomation] = useState(null);
  const [marketplace, setMarketplace] = useState(null);
  const [documentAi, setDocumentAi] = useState(null);
  const [coaching, setCoaching] = useState(null);
  const [collaboration, setCollaboration] = useState(null);
  const [fees, setFees] = useState(null);
  const [trust, setTrust] = useState(null);
  const [notifications, setNotifications] = useState(null);
  const [actionStatus, setActionStatus] = useState("loading");

  const load = async () => {
    setActionStatus("loading");
    try {
      const [
        overviewData,
        terminalData,
        researchData,
        brokerData,
        transferData,
        rulesData,
        analyticsData,
        alertData,
        automationData,
        marketplaceData,
        docData,
        coachingData,
        collaborationData,
        feeData,
        trustData,
        notificationData,
      ] = await Promise.all([
        getOneStopOverview(),
        getMarketTerminal(symbol),
        getResearchLab(symbol),
        getBrokerConnectivityHub(),
        getAccountTransferCenter(),
        getAccountTypeRules(),
        getPortfolioAnalyticsPro(),
        getAlertBuilder(),
        getAutomationStudio(),
        getBacktestMarketplace(),
        readDocumentAi({ symbol, document_type: "10-Q" }),
        getCoachingCenter(),
        getCollaborationLayer(),
        getFeeYieldCenter(),
        getTrustCenter(),
        getNotificationSystem(),
      ]);
      setOverview(overviewData);
      setTerminal(terminalData);
      setResearch(researchData);
      setBrokers(brokerData);
      setTransfers(transferData);
      setRules(rulesData);
      setAnalytics(analyticsData);
      setAlerts(alertData);
      setAutomation(automationData);
      setMarketplace(marketplaceData);
      setDocumentAi(docData);
      setCoaching(coachingData);
      setCollaboration(collaborationData);
      setFees(feeData);
      setTrust(trustData);
      setNotifications(notificationData);
      setActionStatus("ready");
    } catch {
      setActionStatus("error");
    }
  };

  useEffect(() => {
    load();
  }, [symbol]);

  const refreshBroker = async () => {
    setActionStatus("broker refresh");
    const result = await refreshBrokerConnection({ connection_id: brokers?.connections?.[0]?.connection_id || "broker-alpaca-paper" });
    setBrokers((current) => ({ ...(current || {}), latest_refresh: result }));
    setActionStatus(result.status);
  };

  const startTransfer = async () => {
    setActionStatus("acats");
    const result = await createAcatsTransfer({
      confirmed: true,
      direction: "incoming",
      assets: [{ symbol, quantity: 10 }],
    });
    setTransfers((current) => ({ ...(current || {}), transfers: [result, ...((current || {}).transfers || [])] }));
    setActionStatus(result.status);
  };

  const testIraRule = async () => {
    setActionStatus("account rules");
    const result = await evaluateAccountTypeRule({ account_type: "traditional_ira", action: "short_sale" });
    setRules((current) => ({ ...(current || {}), latest_evaluation: result }));
    setActionStatus(result.status);
  };

  const createAlert = async () => {
    setActionStatus("alert");
    const rule = await createOneStopAlertRule({ name: `${symbol} IV spike`, event_type: "options_iv", destinations: ["in_app", "push"] });
    const delivery = await testOneStopAlert({ channels: ["in_app", "push"], destination: "demo-user" });
    setAlerts((current) => ({ ...(current || {}), rules: [rule, ...((current || {}).rules || [])], latest_delivery: delivery }));
    setActionStatus(delivery.status);
  };

  const runAutomation = async () => {
    setActionStatus("automation");
    const result = await simulateAutomation({ symbol, policy_id: "auto-vol-pause", volatility: 0.22, approval_required: true });
    setAutomation((current) => ({ ...(current || {}), latest_simulation: result }));
    setActionStatus(result.status);
  };

  const compareStrategies = async () => {
    setActionStatus("backtest compare");
    const result = await compareMarketplaceStrategies({ listing_ids: ["strat-quality-pullback", "strat-ai-momentum"], universe: [symbol, "NVDA", "JPM"] });
    setMarketplace((current) => ({ ...(current || {}), latest_comparison: result }));
    setActionStatus(result.paper_deploy_eligible ? "paper eligible" : "research only");
  };

  const buildBrief = async () => {
    setActionStatus("research brief");
    const brief = await generateResearchBrief({ symbol, revenue_growth: 0.12, operating_margin: 0.43 });
    const doc = await readDocumentAi({ symbol, document_type: "earnings_call", title: `${symbol} earnings transcript` });
    setResearch(brief);
    setDocumentAi(doc);
    setActionStatus("brief ready");
  };

  const createSpace = async () => {
    setActionStatus("collaboration");
    const result = await createCollaborationSpace({ name: `${symbol} review room`, privacy: "private", members: ["analyst@example.com"] });
    setCollaboration((current) => ({ ...(current || {}), spaces: [result, ...((current || {}).spaces || [])] }));
    setActionStatus(result.status || "active");
  };

  const lockTrust = async () => {
    setActionStatus("trust lock");
    const result = await lockAccountTrust({ confirmed: true, reason: "manual security test" });
    setTrust((current) => ({ ...(current || {}), latest_lock: result }));
    setActionStatus(result.status);
  };

  const sendNotification = async () => {
    setActionStatus("notification");
    const result = await testNotificationDelivery({ channel: "push", destination: "demo-user" });
    setNotifications((current) => ({ ...(current || {}), delivery_logs: [result, ...((current || {}).delivery_logs || [])] }));
    setActionStatus(result.status);
  };

  return (
    <section className="operating-stack one-stop-stack">
      <section className="metrics">
        <Metric label="One-stop" value={actionStatus} />
        <Metric label="Terminal" value={terminal?.quote?.entitlement_level || "loading"} />
        <Metric label="After-fee return" value={pct(analytics?.performance?.after_fee_return)} />
        <Metric label="Modules" value={overview?.modules?.length || 0} />
      </section>

      <section className="analysis-grid ops-grid">
        <article className="panel">
          <header>
            <div>
              <span>Market data terminal</span>
              <strong>{terminal?.symbol || symbol}</strong>
            </div>
            <Badge status={terminal?.source_health?.market_data || "loading"} />
          </header>
          <section className="chart-level-grid">
            <div><span>Bid</span><strong>{money(terminal?.quote?.bid)}</strong></div>
            <div><span>Ask</span><strong>{money(terminal?.quote?.ask)}</strong></div>
            <div><span>Last</span><strong>{money(terminal?.quote?.last)}</strong></div>
          </section>
          <Row label="Level II" value={terminal?.level_ii?.blocked_reason || "available"} />
          <MiniRows rows={terminal?.option_flow || []} labelKey="contract" valueKey="unusual_score" />
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Research lab</span>
              <strong>{research?.symbol || symbol}</strong>
            </div>
            <Badge status="source linked" />
          </header>
          <Row label="DCF fair value" value={money(research?.valuation?.dcf_fair_value)} />
          <Row label="Revenue growth" value={pct(research?.financials?.revenue_growth)} />
          <Row label="Ownership change" value={pct(research?.institutional_ownership?.net_13f_change_pct)} />
          <button type="button" onClick={buildBrief}>Generate brief</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Broker connectivity</span>
              <strong>{brokers?.connections?.length || 0} links</strong>
            </div>
            <Badge status={brokers?.latest_refresh?.status || brokers?.connections?.[1]?.status || "monitoring"} />
          </header>
          <MiniRows rows={brokers?.connections || []} labelKey="broker" valueKey="status" />
          <Row label="Live gate" value={brokers?.live_status_gate?.enabled ? "enabled" : "blocked"} />
          <button type="button" onClick={refreshBroker}>Refresh broker</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>ACATS transfers</span>
              <strong>{transfers?.transfers?.length || 0} transfers</strong>
            </div>
            <Badge status={transfers?.transfers?.[0]?.status || "sandbox"} />
          </header>
          <MiniRows rows={transfers?.transfers || []} labelKey="transfer_id" valueKey="status" />
          <Row label="Support cases" value={transfers?.support_links?.length || 0} />
          <button type="button" onClick={startTransfer}>Start ACATS</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Account-type rules</span>
              <strong>{rules?.supported_account_types?.length || 0} types</strong>
            </div>
            <Badge status={rules?.latest_evaluation?.status || "enforcing"} />
          </header>
          <MiniRows rows={rules?.rules || []} labelKey="account_type" valueKey="rule_type" />
          {rules?.latest_evaluation && <Row label="Latest" value={rules.latest_evaluation.violations?.[0] || "allowed"} />}
          <button type="button" onClick={testIraRule}>Test IRA short</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Portfolio analytics pro</span>
              <strong>{pct(analytics?.performance?.ytd_return)}</strong>
            </div>
            <Badge status="exportable" />
          </header>
          <Row label="Benchmark" value={pct(analytics?.performance?.benchmark_return)} />
          <Row label="Rolling Sharpe" value={analytics?.risk?.rolling_sharpe_90d || 0} />
          <Row label="Tax drag" value={pct(Math.abs(analytics?.attribution?.tax_drag || 0))} />
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Alert builder</span>
              <strong>{alerts?.rules?.length || 0} rules</strong>
            </div>
            <Badge status={alerts?.latest_delivery?.status || "armed"} />
          </header>
          <MiniRows rows={alerts?.rules || []} labelKey="name" valueKey="event_type" />
          <Row label="Channels" value={(alerts?.delivery_channels || []).length} />
          <button type="button" onClick={createAlert}>Create + test</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Automation studio</span>
              <strong>{automation?.policies?.length || 0} policies</strong>
            </div>
            <Badge status={automation?.latest_simulation?.status || "simulation"} />
          </header>
          <MiniRows rows={automation?.policies || []} labelKey="name" valueKey="status" />
          <Row label="Guardrails" value={(automation?.guardrail_catalog || []).length} />
          <button type="button" onClick={runAutomation}>Simulate</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Backtest marketplace</span>
              <strong>{marketplace?.listings?.length || 0} listings</strong>
            </div>
            <Badge status={marketplace?.latest_comparison ? "compared" : "ready"} />
          </header>
          <MiniRows rows={marketplace?.listings || []} labelKey="name" valueKey="strategy_type" />
          <Row label="Walk-forward" value={marketplace?.latest_comparison?.walk_forward?.windows || "not run"} />
          <button type="button" onClick={compareStrategies}>Compare</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Document AI + coaching</span>
              <strong>{documentAi?.document_type || "reader"}</strong>
            </div>
            <Badge status="education" />
          </header>
          <Row label="Confidence" value={pct(documentAi?.confidence)} />
          <Row label="Coaching plans" value={coaching?.plans?.length || 0} />
          <p className="operating-note">{documentAi?.impact_summary}</p>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Collaboration</span>
              <strong>{collaboration?.spaces?.length || 0} spaces</strong>
            </div>
            <Badge status={collaboration?.spaces?.[0]?.privacy || "private"} />
          </header>
          <MiniRows rows={collaboration?.spaces || []} labelKey="name" valueKey="privacy" />
          <Row label="Team approvals" value={collaboration?.team_approvals?.length || 0} />
          <button type="button" onClick={createSpace}>Create room</button>
        </article>

        <article className="panel">
          <header>
            <div>
              <span>Fee, yield, trust, notifications</span>
              <strong>{money(fees?.net_yield_after_fees)}</strong>
            </div>
            <Badge status={trust?.latest_lock?.status || "armed"} />
          </header>
          <Row label="After-fee return" value={pct(fees?.after_fee_performance?.after_fee_return)} />
          <Row label="Devices" value={trust?.devices?.length || 0} />
          <Row label="Delivery logs" value={notifications?.delivery_logs?.length || 0} />
          <div className="ops-action-row">
            <button type="button" onClick={sendNotification}>Test push</button>
            <button type="button" className="ghost-button" onClick={lockTrust}>Lock account</button>
          </div>
        </article>
      </section>
    </section>
  );
}
