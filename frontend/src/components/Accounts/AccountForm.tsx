import React, { useState } from "react";
import { createAlexAccount } from "../../services/api";

interface Props {
  onCreated: () => void;
  onCancel: () => void;
}

function AccountForm({ onCreated, onCancel }: Props) {
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [cashBalance, setCashBalance] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) { setError("Account name is required."); return; }

    const cash = parseFloat(cashBalance.replace(/,/g, "")) || 0;
    if (cash < 0) { setError("Cash balance cannot be negative."); return; }

    setSaving(true);
    setError(null);
    try {
      await createAlexAccount({
        account_name: trimmedName,
        account_purpose: purpose.trim() || "Investment Account",
        cash_balance: cash,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create account.");
    } finally {
      setSaving(false);
    }
  };

  const formatCash = (raw: string) => {
    const digits = raw.replace(/[^0-9.]/g, "");
    const parts = digits.split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    return parts.slice(0, 2).join(".");
  };

  return (
    <form className="panel" onSubmit={handleSubmit} style={{ maxWidth: 480 }}>
      <header>
        <div>
          <span>Portfolio</span>
          <h2>New account</h2>
        </div>
      </header>

      {error && <p className="advisor-error" role="alert">{error}</p>}

      <div className="advisor-form-grid">
        <label>
          Account name *
          <input
            required
            placeholder="e.g. 401k, Roth IRA"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>

        <label>
          Purpose
          <input
            placeholder="e.g. Long-term retirement savings"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
          />
        </label>

        <label>
          Initial cash balance ($)
          <input
            inputMode="decimal"
            placeholder="0.00"
            value={cashBalance}
            onChange={(e) => setCashBalance(formatCash(e.target.value))}
          />
        </label>
      </div>

      <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
        <button type="submit" disabled={saving}>
          {saving ? "Creating…" : "Create account"}
        </button>
        <button type="button" className="ghost-button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export default AccountForm;
