import { useEffect, useState } from "react";
import { getSafetyStatus, monitorSafety } from "../../services/api";

function BlackSwanBreaker() {
  const [status, setStatus] = useState(null);
  const [monitorStatus, setMonitorStatus] = useState("idle");

  useEffect(() => {
    getSafetyStatus().then(setStatus).catch(() => undefined);
  }, []);

  const runMonitor = async () => {
    setMonitorStatus("checking");
    try {
      const response = await monitorSafety({
        volatility_zscore: 1.2,
        correlation_spike: 0.4,
        liquidity_drop: 0.1,
      });
      setStatus({ trading_allowed: response.trading_allowed, reason: response.reason });
      setMonitorStatus(response.triggered ? "review" : "checked");
    } catch {
      setMonitorStatus("error");
    }
  };

  return (
    <section className="panel">
      <header>
        <div>
          <span>Safety</span>
          <strong>Black Swan Breaker</strong>
        </div>
        <span className={status?.trading_allowed === false ? "badge review" : "badge healthy"}>
          {status?.trading_allowed === false ? "halted" : "ready"}
        </span>
      </header>
      <div className="row">
        <span>Manual pause</span>
        <strong>{status?.reason || "Ready"}</strong>
      </div>
      <div className="row">
        <span>Auto detection</span>
        <strong>{monitorStatus === "idle" ? "Monitoring" : monitorStatus}</strong>
      </div>
      <button
        type="button"
        className="ghost-button"
        disabled={monitorStatus === "checking"}
        onClick={runMonitor}
      >
        {monitorStatus === "checking" ? "Checking" : "Check market stress"}
      </button>
    </section>
  );
}

export default BlackSwanBreaker;
