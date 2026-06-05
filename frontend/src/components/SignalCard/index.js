function SignalCard({ signal }) {
  return (
    <article className="signal-card">
      <header>
        <div>
          <span>{signal.symbol}</span>
          <strong>{signal.confidence}%</strong>
        </div>
        <span className={`badge ${signal.rating}`}>{signal.rating}</span>
      </header>
      <div className="row">
        <span>Session move</span>
        <strong>{signal.move}</strong>
      </div>
      <div className="bar" aria-label={`${signal.symbol} confidence`}>
        <i style={{ width: `${signal.confidence}%` }} />
      </div>
    </article>
  );
}

export default SignalCard;

