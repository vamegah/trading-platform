import { useEffect, useState } from "react";
import { getAlerts, saveAlertPreferences } from "../../services/api";

function AlertCenter() {
  const [alerts, setAlerts] = useState([]);
  const [preferences, setPreferences] = useState({
    user_id: "demo",
    push_enabled: true,
    email_enabled: false,
    high_conviction_threshold: 0.7,
    stop_loss_alerts: true,
    thesis_change_alerts: true,
  });
  const [status, setStatus] = useState("idle");

  useEffect(() => {
    getAlerts("demo")
      .then((data) => {
        setAlerts(data.alerts || []);
        setPreferences(data.preferences || preferences);
      })
      .catch(() => setStatus("offline"));
  }, []);

  const togglePreference = (key) => {
    setPreferences((current) => ({ ...current, [key]: !current[key] }));
  };

  const save = async () => {
    setStatus("saving");
    try {
      const saved = await saveAlertPreferences(preferences);
      setPreferences(saved);
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  };

  return (
    <section className="analysis-grid">
      <article className="panel">
        <header>
          <div>
            <span>Alert center</span>
            <strong>Live notifications</strong>
          </div>
          <span className="badge hold">{status}</span>
        </header>
        {alerts.map((alert) => (
          <div className="row" key={`${alert.type}-${alert.symbol}`}>
            <span>{alert.type.replaceAll("_", " ")}</span>
            <strong>
              {alert.symbol} {Math.round((alert.confidence || 0) * 100)}%
            </strong>
          </div>
        ))}
      </article>
      <article className="panel">
        <header>
          <div>
            <span>Notification preferences</span>
            <strong>Delivery rules</strong>
          </div>
          <button type="button" disabled={status === "saving"} onClick={save}>
            {status === "saving" ? "Saving" : "Save"}
          </button>
        </header>
        <label className="check-row">
          <input
            checked={preferences.push_enabled}
            type="checkbox"
            onChange={() => togglePreference("push_enabled")}
          />
          Push alerts
        </label>
        <label className="check-row">
          <input
            checked={preferences.email_enabled}
            type="checkbox"
            onChange={() => togglePreference("email_enabled")}
          />
          Email alerts
        </label>
        <label className="check-row">
          <input
            checked={preferences.stop_loss_alerts}
            type="checkbox"
            onChange={() => togglePreference("stop_loss_alerts")}
          />
          Stop-loss breaches
        </label>
        <label className="check-row">
          <input
            checked={preferences.thesis_change_alerts}
            type="checkbox"
            onChange={() => togglePreference("thesis_change_alerts")}
          />
          Thesis changes
        </label>
        <label>
          High-conviction threshold
          <input
            max="0.95"
            min="0.2"
            step="0.05"
            type="number"
            value={preferences.high_conviction_threshold}
            onChange={(event) =>
              setPreferences((current) => ({
                ...current,
                high_conviction_threshold: Number(event.target.value),
              }))
            }
          />
        </label>
      </article>
    </section>
  );
}

export default AlertCenter;
