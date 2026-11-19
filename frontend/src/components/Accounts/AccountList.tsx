import React, { useCallback, useEffect, useState } from "react";
import {
  deleteAlexAccount,
  getAlexAccounts,
  getAlexPositions,
  populateAlexTestData,
  resetAlexAccounts,
} from "../../services/api";
import AccountForm from "./AccountForm";
import PositionTable from "./PositionTable";

interface Position {
  id: string;
  symbol: string;
  quantity: number;
  current_price?: number;
  instrument?: { name?: string; instrument_type?: string };
}

interface Account {
  id: string;
  account_name: string;
  account_purpose: string;
  cash_balance: number;
  positions?: Position[];
}

function fmt(n: number, decimals = 2) {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function AccountList() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // ── data loading ──────────────────────────────────────────────────────────

  const loadAccounts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const raw: Account[] = await getAlexAccounts();
      // Load positions for every account in parallel
      const withPositions = await Promise.all(
        raw.map(async (account) => {
          if (!account.id) return { ...account, positions: [] };
          try {
            const data = await getAlexPositions(account.id);
            return { ...account, positions: data.positions ?? [] };
          } catch {
            return { ...account, positions: [] };
          }
        })
      );
      setAccounts(withPositions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load accounts.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAccounts(); }, [loadAccounts]);

  // Refresh on analysis completion events fired by the Portfolio Advisor tab
  useEffect(() => {
    const handler = () => loadAccounts();
    window.addEventListener("analysis:completed", handler);
    return () => window.removeEventListener("analysis:completed", handler);
  }, [loadAccounts]);

  // ── helpers ───────────────────────────────────────────────────────────────

  const flash = (msg: string) => {
    setNotice(msg);
    setTimeout(() => setNotice(null), 4000);
  };

  const accountTotal = (account: Account) => {
    const posValue = (account.positions ?? []).reduce(
      (sum, p) => sum + Number(p.quantity) * (Number(p.current_price) || 0),
      0
    );
    return Number(account.cash_balance) + posValue;
  };

  const portfolioTotal = accounts.reduce((sum, a) => sum + accountTotal(a), 0);
  const totalPositions = accounts.reduce((sum, a) => sum + (a.positions?.length ?? 0), 0);

  // ── actions ───────────────────────────────────────────────────────────────

  const handleDelete = async (accountId: string) => {
    setBusy(true);
    setError(null);
    try {
      await deleteAlexAccount(accountId);
      if (expandedId === accountId) setExpandedId(null);
      await loadAccounts();
      flash("Account deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete account.");
    } finally {
      setBusy(false);
    }
  };

  const handlePopulate = async () => {
    setBusy(true);
    setError(null);
    try {
      const data = await populateAlexTestData();
      await loadAccounts();
      flash(data?.message ?? "Test data populated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to populate test data.");
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm("Delete all accounts and positions? This cannot be undone.")) return;
    setBusy(true);
    setError(null);
    try {
      await resetAlexAccounts();
      setExpandedId(null);
      await loadAccounts();
      flash("All accounts reset.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset accounts.");
    } finally {
      setBusy(false);
    }
  };

  // ── render ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <section className="operating-stack">
        <div className="panel" role="status">Loading accounts…</div>
      </section>
    );
  }

  return (
    <section className="operating-stack">
      {/* Header panel */}
      <div className="panel">
        <header>
          <div>
            <span>Portfolio management</span>
            <h2>Investment accounts</h2>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              type="button"
              onClick={() => { setShowForm((v) => !v); setError(null); }}
              disabled={busy}
            >
              {showForm ? "Cancel" : "+ Add account"}
            </button>
            {accounts.length === 0 && !loading && (
              <button
                type="button"
                className="ghost-button"
                onClick={handlePopulate}
                disabled={busy}
              >
                {busy ? "Working…" : "Populate test data"}
              </button>
            )}
            {accounts.length > 0 && (
              <button
                type="button"
                className="ghost-button"
                onClick={handleReset}
                disabled={busy}
              >
                Reset all
              </button>
            )}
          </div>
        </header>

        {error && <p className="advisor-error" role="alert">{error}</p>}
        {notice && <p className="operating-note" role="status">{notice}</p>}

        {/* Portfolio summary metrics */}
        {accounts.length > 0 && (
          <section className="metrics advisor-metrics">
            <article className="metric">
              <span>Total value</span>
              <strong>${fmt(portfolioTotal)}</strong>
            </article>
            <article className="metric">
              <span>Accounts</span>
              <strong>{accounts.length}</strong>
            </article>
            <article className="metric">
              <span>Positions</span>
              <strong>{totalPositions}</strong>
            </article>
          </section>
        )}
      </div>

      {/* New-account form */}
      {showForm && (
        <AccountForm
          onCreated={async () => {
            setShowForm(false);
            await loadAccounts();
            flash("Account created.");
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Empty state */}
      {accounts.length === 0 && !showForm && (
        <div className="panel">
          <p className="operating-note">
            No accounts found. Add an account or use "Populate test data" to get started.
          </p>
        </div>
      )}

      {/* Account rows */}
      {accounts.map((account) => {
        const isExpanded = expandedId === account.id;
        const total = accountTotal(account);
        const positionsValue = total - Number(account.cash_balance);

        return (
          <div key={account.id} className="panel">
            {/* Account header row */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                cursor: "pointer",
              }}
              role="button"
              tabIndex={0}
              onClick={() => setExpandedId(isExpanded ? null : account.id)}
              onKeyDown={(e) => e.key === "Enter" && setExpandedId(isExpanded ? null : account.id)}
            >
              <div>
                <strong>{account.account_name}</strong>
                <span style={{ marginLeft: "0.75rem", opacity: 0.6, fontSize: "0.85em" }}>
                  {account.account_purpose}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
                <span style={{ fontSize: "0.85em", opacity: 0.7 }}>
                  {account.positions?.length ?? 0} positions
                  {positionsValue > 0 && ` · $${fmt(positionsValue, 0)}`}
                </span>
                <span style={{ fontSize: "0.85em", opacity: 0.7 }}>
                  cash ${fmt(Number(account.cash_balance))}
                </span>
                <strong>${fmt(total)}</strong>
                <button
                  type="button"
                  className="ghost-button"
                  onClick={(e) => { e.stopPropagation(); handleDelete(account.id); }}
                  disabled={busy}
                  aria-label={`Delete ${account.account_name}`}
                >
                  ✕
                </button>
                <span aria-hidden="true">{isExpanded ? "▲" : "▼"}</span>
              </div>
            </div>

            {/* Expanded: positions */}
            {isExpanded && (
              <PositionTable
                accountId={account.id}
                positions={account.positions ?? []}
                onRefresh={loadAccounts}
              />
            )}
          </div>
        );
      })}

      <p className="advisor-disclosure">
        Account data is for planning and research purposes only.
        Figures do not constitute a real brokerage statement.
      </p>
    </section>
  );
}

export default AccountList;
