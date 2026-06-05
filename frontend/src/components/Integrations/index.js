import React, { useEffect, useMemo, useState } from "react";
import { getExternalIntegrations } from "../../services/api";

function IntegrationsPanel() {
  const [payload, setPayload] = useState({ providers: [], configured: 0, total: 0, missing_live_integrations: [] });
  const [category, setCategory] = useState("");

  useEffect(() => {
    getExternalIntegrations(category).then(setPayload).catch(() => setPayload({ providers: [], configured: 0, total: 0, missing_live_integrations: [] }));
  }, [category]);

  const categories = useMemo(
    () => Array.from(new Set(payload.providers.map((provider) => provider.category))).sort(),
    [payload.providers],
  );

  return (
    <section className="panel">
      <header>
        <div>
          <p className="eyebrow">Operations</p>
          <h2>External APIs</h2>
        </div>
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="">All categories</option>
          {categories.map((item) => (
            <option key={item} value={item}>
              {item.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </header>

      <section className="metrics integrations-summary">
        <article className="metric">
          <span>Configured</span>
          <strong>{payload.configured}</strong>
        </article>
        <article className="metric">
          <span>Total</span>
          <strong>{payload.total}</strong>
        </article>
        <article className="metric">
          <span>Live gaps</span>
          <strong>{payload.missing_live_integrations.length}</strong>
        </article>
      </section>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Provider</th>
              <th>Category</th>
              <th>Phase</th>
              <th>Status</th>
              <th>Purpose</th>
            </tr>
          </thead>
          <tbody>
            {payload.providers.map((provider) => (
              <tr key={provider.name}>
                <td>{provider.name}</td>
                <td>{provider.category.replaceAll("_", " ")}</td>
                <td>{provider.phase.replaceAll("_", " ")}</td>
                <td>{provider.configured ? "configured" : provider.self_hosted ? "self-hosted" : "missing key"}</td>
                <td>{provider.purpose}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default IntegrationsPanel;
