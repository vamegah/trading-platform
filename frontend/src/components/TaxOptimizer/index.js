import { useEffect, useState } from "react";
import { findTaxHarvests } from "../../services/api";

function TaxOptimizer() {
  const [plan, setPlan] = useState(null);

  useEffect(() => {
    findTaxHarvests({
      lots: [
        { lot_id: "loss-msft", symbol: "MSFT", quantity: 10, cost_per_share: 140, acquisition_date: "2024-01-01" },
        { lot_id: "gain-aapl", symbol: "AAPL", quantity: 8, cost_per_share: 80, acquisition_date: "2020-01-01" },
      ],
      current_prices: { MSFT: 100, AAPL: 120 },
      minimum_loss: 100,
    })
      .then(setPlan)
      .catch(() => undefined);
  }, []);

  return (
    <section className="panel">
      <header>
        <div>
          <span>Tax optimizer</span>
          <strong>After-tax Plan</strong>
        </div>
      </header>
      <div className="row">
        <span>Wash-sale window</span>
        <strong>30 days</strong>
      </div>
      <div className="row">
        <span>Lot method</span>
        <strong>Tax-aware</strong>
      </div>
      <div className="row">
        <span>Harvest candidates</span>
        <strong>{plan?.count ?? "pending"}</strong>
      </div>
      {(plan?.opportunities || []).slice(0, 2).map((opportunity) => (
        <div className="row" key={opportunity.lot_id}>
          <span>{opportunity.symbol}</span>
          <strong>${opportunity.unrealized_loss}</strong>
        </div>
      ))}
    </section>
  );
}

export default TaxOptimizer;
