const metrics = [
  { label: "Portfolio equity", value: "$125,000" },
  { label: "Net exposure", value: "48%" },
  { label: "Signal confidence", value: "70%" },
  { label: "Drawdown guard", value: "14.2%" },
];

function Dashboard() {
  return (
    <section id="dashboard" className="metrics" aria-label="Portfolio metrics">
      {metrics.map((metric) => (
        <article className="metric" key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
        </article>
      ))}
    </section>
  );
}

export default Dashboard;

