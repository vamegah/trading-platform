const agents = [
  { id: "options-edge", name: "Options Edge", assetTypes: "Options", rating: "4.8" },
  { id: "crypto-flow", name: "Crypto Flow", assetTypes: "Crypto", rating: "4.6" },
];

function AgentStore() {
  return (
    <section className="panel">
      <header>
        <div>
          <span>Marketplace</span>
          <strong>Agent Store</strong>
        </div>
      </header>
      {agents.map((agent) => (
        <div className="row" key={agent.id}>
          <span>{agent.name}</span>
          <strong>{agent.assetTypes} · {agent.rating}</strong>
        </div>
      ))}
    </section>
  );
}

export default AgentStore;

