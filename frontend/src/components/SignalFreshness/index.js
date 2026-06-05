function SignalFreshness({ score = 0.84, signal }) {
  const freshnessDetails = signal?.signal_freshness || {};
  const freshness = freshnessDetails.score ?? signal?.freshness_score ?? score;
  const percent = Math.round(freshness * 100);
  const status = signal?.auto_cancel ? "auto-canceled" : freshness < 0.25 ? "stale" : "fresh";
  const halfLife = freshnessDetails.half_life_minutes || 60;
  const staleAction = freshnessDetails.stale_order_action || (signal?.auto_cancel ? "cancel_pending_orders" : "keep_active");
  const triggers = freshnessDetails.invalidation_triggers || [
    "price_breaks_stop_loss",
    "thesis_change",
    "event_risk",
  ];

  return (
    <section className="panel">
      <header>
        <div>
          <span>Signal freshness</span>
          <strong>{percent}%</strong>
        </div>
        <span className={status === "fresh" ? "badge healthy" : "badge review"}>
          {status}
        </span>
      </header>
      <div className="bar" aria-label="Signal freshness score">
        <i style={{ width: `${percent}%` }} />
      </div>
      <div className="freshness-grid">
        <div>
          <span>Half-life</span>
          <strong>{halfLife} min</strong>
        </div>
        <div>
          <span>Order status</span>
          <strong>{staleAction === "cancel_pending_orders" ? "Cancel pending" : "Eligible"}</strong>
        </div>
        <div>
          <span>Invalidation triggers</span>
          <strong>{triggers.map((trigger) => trigger.replaceAll("_", " ")).join(", ")}</strong>
        </div>
      </div>
    </section>
  );
}

export default SignalFreshness;
