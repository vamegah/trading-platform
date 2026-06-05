import { useState } from "react";
import { dismissNudge } from "../../services/api";

const messages = {
  PANIC_SELL: "Review your plan before selling into a sharp drawdown.",
  FOMO_BUY: "Multiple quick buys can increase concentration risk.",
};

function BehavioralNudges({ nudges = [] }) {
  const [dismissed, setDismissed] = useState([]);
  const visible = nudges.filter((nudge) => !dismissed.includes(nudge.event_type));
  const rows = visible.length
    ? visible
    : [
        {
          event_type: "PLAN_CHECK",
          severity: "info",
          user_id: "demo",
          message: "No active behavior flags. Stay aligned with the written trade plan.",
        },
      ];

  const handleDismiss = async (eventType) => {
    setDismissed((current) => [...current, eventType]);
    await dismissNudge(eventType).catch(() => undefined);
  };

  return (
    <section className="nudge-list" aria-label="Behavioral nudges">
      {rows.map((nudge) => (
        <article className="panel nudge" key={nudge.event_type}>
          <span>Behavioral nudge</span>
          <strong>{nudge.event_type.replaceAll("_", " ")}</strong>
          <p>{nudge.message || messages[nudge.event_type] || "Review your trading plan and risk limits."}</p>
          <small>Severity: {nudge.severity}</small>
          {nudge.evidence && (
            <small>
              Evidence: {Object.entries(nudge.evidence).map(([key, value]) => `${key.replaceAll("_", " ")} ${value}`).join(", ")}
            </small>
          )}
          {nudge.event_type !== "PLAN_CHECK" && nudge.dismissible !== false && (
            <button type="button" className="ghost-button" onClick={() => handleDismiss(nudge.event_type)}>
              Dismiss
            </button>
          )}
        </article>
      ))}
    </section>
  );
}

export default BehavioralNudges;
