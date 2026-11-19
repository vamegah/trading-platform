import React, { useState } from "react";
import {
  deleteAlexPosition,
  upsertAlexPosition,
} from "../../services/api";

interface Position {
  id: string;
  symbol: string;
  quantity: number;
  current_price?: number;
  instrument?: {
    name?: string;
    instrument_type?: string;
  };
}

interface Props {
  accountId: string;
  positions: Position[];
  onRefresh: () => void;
}

function fmt(n: number, decimals = 2) {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function PositionTable({ accountId, positions, onRefresh }: Props) {
  const [adding, setAdding] = useState(false);
  const [newSymbol, setNewSymbol] = useState("");
  const [newQty, setNewQty] = useState("");
  const [saving, setSaving] = useState(false);
  const [deletingSymbol, setDeletingSymbol] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async () => {
    const symbol = newSymbol.trim().toUpperCase();
    const quantity = parseFloat(newQty);
    if (!symbol) { setError("Symbol is required."); return; }
    if (!Number.isFinite(quantity) || quantity <= 0) { setError("Quantity must be a positive number."); return; }

    setSaving(true);
    setError(null);
    try {
      await upsertAlexPosition(accountId, { symbol, quantity });
      setNewSymbol("");
      setNewQty("");
      setAdding(false);
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save position.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (symbol: string) => {
    setDeletingSymbol(symbol);
    setError(null);
    try {
      await deleteAlexPosition(accountId, symbol);
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete position.");
    } finally {
      setDeletingSymbol(null);
    }
  };

  const positionValue = (p: Position) =>
    Number(p.quantity) * (Number(p.current_price) || 0);

  const totalValue = positions.reduce((sum, p) => sum + positionValue(p), 0);

  return (
    <div className="panel" style={{ marginTop: "0.5rem" }}>
      <header>
        <div>
          <span>Positions</span>
          <h2>Holdings</h2>
        </div>
        <button
          className="ghost-button"
          type="button"
          onClick={() => { setAdding((v) => !v); setError(null); }}
        >
          {adding ? "Cancel" : "+ Add"}
        </button>
      </header>

      {error && <p className="advisor-error" role="alert">{error}</p>}

      {adding && (
        <div className="advisor-form-grid" style={{ marginBottom: "1rem" }}>
          <label>
            Symbol
            <input
              placeholder="e.g. VTI"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
            />
          </label>
          <label>
            Quantity
            <input
              type="number"
              min="0.00000001"
              step="any"
              placeholder="e.g. 10"
              value={newQty}
              onChange={(e) => setNewQty(e.target.value)}
            />
          </label>
          <button type="button" disabled={saving} onClick={handleAdd}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      )}

      {positions.length === 0 ? (
        <p className="operating-note">No positions yet. Use "+ Add" to add one.</p>
      ) : (
        <>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "0.4rem 0.6rem" }}>Symbol</th>
                <th style={{ textAlign: "left", padding: "0.4rem 0.6rem" }}>Name</th>
                <th style={{ textAlign: "right", padding: "0.4rem 0.6rem" }}>Qty</th>
                <th style={{ textAlign: "right", padding: "0.4rem 0.6rem" }}>Price</th>
                <th style={{ textAlign: "right", padding: "0.4rem 0.6rem" }}>Value</th>
                <th style={{ padding: "0.4rem 0.6rem" }} />
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.symbol}>
                  <td style={{ padding: "0.4rem 0.6rem", fontWeight: 600 }}>{p.symbol}</td>
                  <td style={{ padding: "0.4rem 0.6rem", opacity: 0.7, fontSize: "0.85em" }}>
                    {p.instrument?.name ?? "—"}
                  </td>
                  <td style={{ textAlign: "right", padding: "0.4rem 0.6rem" }}>
                    {fmt(Number(p.quantity), 4)}
                  </td>
                  <td style={{ textAlign: "right", padding: "0.4rem 0.6rem" }}>
                    {p.current_price ? `$${fmt(Number(p.current_price))}` : "—"}
                  </td>
                  <td style={{ textAlign: "right", padding: "0.4rem 0.6rem", fontWeight: 600 }}>
                    {p.current_price ? `$${fmt(positionValue(p))}` : "—"}
                  </td>
                  <td style={{ textAlign: "center", padding: "0.4rem 0.6rem" }}>
                    <button
                      className="ghost-button"
                      type="button"
                      disabled={deletingSymbol === p.symbol}
                      onClick={() => handleDelete(p.symbol)}
                      aria-label={`Delete ${p.symbol}`}
                    >
                      {deletingSymbol === p.symbol ? "…" : "✕"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {totalValue > 0 && (
            <p className="operating-note" style={{ textAlign: "right", marginTop: "0.4rem" }}>
              Total positions value: <strong>${fmt(totalValue)}</strong>
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default PositionTable;
