import { useEffect, useState } from "react";
import { getBrokerCapabilities, precheckExecution, smartRouteOrder } from "../../services/api";

function ExecutionPanel({ symbol = "MSFT" }) {
  const [brokers, setBrokers] = useState([]);
  const [broker, setBroker] = useState("ibkr");
  const [mode, setMode] = useState("one_click");
  const [oneClickAck, setOneClickAck] = useState(false);
  const [automationConsent, setAutomationConsent] = useState(false);
  const [automationSigned, setAutomationSigned] = useState(false);
  const [liveAck, setLiveAck] = useState(false);
  const [liveSigned, setLiveSigned] = useState(false);
  const [route, setRoute] = useState(null);
  const [precheck, setPrecheck] = useState(null);
  const [precheckStatus, setPrecheckStatus] = useState("idle");
  const [routeStatus, setRouteStatus] = useState("idle");

  useEffect(() => {
    getBrokerCapabilities("sandbox").then(setBrokers).catch(() => setBrokers([]));
  }, []);

  const buildPayload = () => ({
      mode,
      suitability_completed: true,
      risk_breach: false,
      stale_signal: false,
      kill_switch_active: false,
      one_click_acknowledged: oneClickAck,
      automation_consent: automationConsent,
      automation_acknowledgement_signed: automationSigned,
      live_trading_acknowledged: liveAck,
      live_trading_agreement_signed: liveSigned,
      roles: ["user"],
    });

  const runPrecheck = async () => {
    setPrecheckStatus("loading");
    const payload = buildPayload();
    try {
      const result = await precheckExecution(payload);
      setPrecheck(result);
      setPrecheckStatus(result.allowed ? "allowed" : "blocked");
      return result;
    } catch {
      setPrecheck(null);
      setPrecheckStatus("error");
    }
    return null;
  };

  const routeOrder = async () => {
    setRouteStatus("loading");
    try {
      const result = await smartRouteOrder({
        ...buildPayload(),
        broker,
        broker_mode: "sandbox",
        symbol,
        side: "BUY",
        quantity: 2500,
        current_price: 100,
        daily_volume: 25000,
        urgency: "normal",
        order_type: "MARKET",
      });
      setRoute(result);
      setPrecheck(result.precheck || precheck);
      setRouteStatus(result.status || "routed");
    } catch {
      setRoute(null);
      setRouteStatus("error");
    }
  };

  return (
    <section className="analysis-grid">
      <article className="panel">
        <header>
          <div>
            <span>Execution</span>
            <strong>Broker routing</strong>
          </div>
          <span className={route?.status === "routed" ? "badge healthy" : "badge hold"}>
            {route?.status || "ready"}
          </span>
        </header>
        <label>
          Mode
          <select value={mode} onChange={(event) => setMode(event.target.value)}>
            <option value="one_click">One-click</option>
            <option value="automated">Automated</option>
            <option value="live">Live</option>
          </select>
        </label>
        <label>
          Broker
          <select value={broker} onChange={(event) => setBroker(event.target.value)}>
            {brokers
              .filter((item) => item.status !== "deferred")
              .map((item) => (
                <option value={item.broker} key={item.broker}>
                  {item.broker}
                </option>
              ))}
          </select>
        </label>
        <label className="check-row">
          <input checked={oneClickAck} type="checkbox" onChange={() => setOneClickAck((value) => !value)} />
          One-click acknowledgement
        </label>
        <label className="check-row">
          <input checked={automationConsent} type="checkbox" onChange={() => setAutomationConsent((value) => !value)} />
          Automated trading consent
        </label>
        <label className="check-row">
          <input checked={automationSigned} type="checkbox" onChange={() => setAutomationSigned((value) => !value)} />
          Automation acknowledgement signed
        </label>
        <label className="check-row">
          <input checked={liveAck} type="checkbox" onChange={() => setLiveAck((value) => !value)} />
          Live trading acknowledgement
        </label>
        <label className="check-row">
          <input checked={liveSigned} type="checkbox" onChange={() => setLiveSigned((value) => !value)} />
          Live agreement signed
        </label>
        <div className="row">
          <span>Precheck</span>
          <strong>
            {precheck
              ? precheck.allowed
                ? "Allowed"
                : precheck.violations.join(", ")
              : precheckStatus === "error"
                ? "request failed"
                : "pending"}
          </strong>
        </div>
        <div className="row">
          <span>Strategy</span>
          <strong>{route?.strategy || "pending"}</strong>
        </div>
        <div className="row">
          <span>Route ID</span>
          <strong>{route?.route_id || "pending"}</strong>
        </div>
        <div className="row">
          <span>Action status</span>
          <strong>{routeStatus !== "idle" ? routeStatus : precheckStatus}</strong>
        </div>
        <button
          type="button"
          className="ghost-button"
          disabled={precheckStatus === "loading"}
          onClick={runPrecheck}
        >
          {precheckStatus === "loading" ? "Checking" : "Run precheck"}
        </button>
        <button type="button" disabled={routeStatus === "loading"} onClick={routeOrder}>
          {routeStatus === "loading" ? "Routing" : "Route sandbox order"}
        </button>
      </article>
      <article className="panel">
        <header>
          <div>
            <span>Brokers</span>
            <strong>Capabilities</strong>
          </div>
        </header>
        {brokers.map((broker) => (
          <div className="row" key={broker.broker}>
            <span>{broker.broker}</span>
            <strong>{broker.asset_classes?.join(", ") || broker.status}</strong>
          </div>
        ))}
      </article>
    </section>
  );
}

export default ExecutionPanel;
