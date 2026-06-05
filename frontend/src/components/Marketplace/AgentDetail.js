function AgentDetail({ agentName = "Options Edge" }) {
  return (
    <section className="panel">
      <header>
        <div>
          <span>Agent detail</span>
          <strong>{agentName}</strong>
        </div>
        <span className="badge review">vetting</span>
      </header>
      <p>Performance, permissions, supported assets, reviews, and sandbox status appear here.</p>
    </section>
  );
}

export default AgentDetail;

