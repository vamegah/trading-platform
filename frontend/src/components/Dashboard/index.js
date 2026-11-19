import React, { useCallback, useEffect, useState } from "react";
import {
  getAlexAccounts,
  getAlexJobs,
  getAlexPositions,
  getAlexUser,
  updateAlexUser,
} from "../../services/api";

// ─── helpers ─────────────────────────────────────────────────────────────────

function fmt(n, decimals = 2) {
  return Number(n).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v));
}

// Simple bar showing a percentage split between two categories
function SplitBar({ labelA, valA, labelB, valB, colorA = "#209DD7", colorB = "#753991" }) {
  return (
    <div style={{ marginTop: "0.5rem" }}>
      <div
        style={{
          display: "flex",
          height: 10,
          borderRadius: 6,
          overflow: "hidden",
          background: colorB,
        }}
      >
        <div style={{ width: `${valA}%`, background: colorA }} />
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.78em",
          opacity: 0.75,
          marginTop: 3,
        }}
      >
        <span>
          {labelA}: {valA}%
        </span>
        <span>
          {labelB}: {valB}%
        </span>
      </div>
    </div>
  );
}

// ─── main component ───────────────────────────────────────────────────────────

function Dashboard() {
  // ── data state ──────────────────────────────────────────────────────────────
  const [user, setUser] = useState(null);
  const [portfolioValue, setPortfolioValue] = useState(0);
  const [accountCount, setAccountCount] = useState(0);
  const [lastAnalysisDate, setLastAnalysisDate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ── form state ──────────────────────────────────────────────────────────────
  const [displayName, setDisplayName] = useState("");
  const [yearsUntilRetirement, setYearsUntilRetirement] = useState(20);
  const [targetRetirementIncome, setTargetRetirementIncome] = useState(0);
  const [equityTarget, setEquityTarget] = useState(70);
  const [fixedIncomeTarget, setFixedIncomeTarget] = useState(30);
  const [northAmericaTarget, setNorthAmericaTarget] = useState(60);
  const [internationalTarget, setInternationalTarget] = useState(40);
  const [saving, setSaving] = useState(false);
  const [saveNotice, setSaveNotice] = useState(null);

  // ── load ─────────────────────────────────────────────────────────────────────

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [userData, rawAccounts, jobsData] = await Promise.all([
        getAlexUser(),
        getAlexAccounts().catch(() => []),
        getAlexJobs().catch(() => ({ jobs: [] })),
      ]);

      const u = userData?.user ?? userData;
      setUser(u);
      setDisplayName(u?.display_name ?? "");
      setYearsUntilRetirement(u?.years_until_retirement ?? 20);
      const income = Number(u?.target_retirement_income ?? 0);
      setTargetRetirementIncome(income);
      setEquityTarget(u?.asset_class_targets?.equity ?? 70);
      setFixedIncomeTarget(u?.asset_class_targets?.fixed_income ?? 30);
      setNorthAmericaTarget(u?.region_targets?.north_america ?? 60);
      setInternationalTarget(u?.region_targets?.international ?? 40);

      const accounts = Array.isArray(rawAccounts)
        ? rawAccounts
        : rawAccounts?.accounts ?? [];
      setAccountCount(accounts.length);

      // Compute total portfolio value: cash + position values
      let total = 0;
      await Promise.all(
        accounts.map(async (acc) => {
          total += Number(acc.cash_balance ?? 0);
          try {
            const posData = await getAlexPositions(acc.id);
            for (const p of posData?.positions ?? []) {
              total += Number(p.quantity) * (Number(p.current_price) || 0);
            }
          } catch {
            // position fetch failure is non-fatal
          }
        })
      );
      setPortfolioValue(total);

      const jobs = jobsData?.jobs ?? [];
      const lastDone = jobs.find((j) => j.status === "completed");
      if (lastDone) {
        setLastAnalysisDate(lastDone.completed_at ?? lastDone.created_at);
      }
    } catch (err) {
      setError(err?.message ?? "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Refresh after an analysis completes (fired by Portfolio Advisor tab)
  useEffect(() => {
    const handler = () => loadData();
    window.addEventListener("analysis:completed", handler);
    return () => window.removeEventListener("analysis:completed", handler);
  }, [loadData]);

  // ── save settings ────────────────────────────────────────────────────────────

  const handleSave = async (e) => {
    e.preventDefault();
    if (!displayName.trim()) {
      setSaveNotice({ type: "error", text: "Display name is required." });
      return;
    }
    if (Math.abs(equityTarget + fixedIncomeTarget - 100) > 0.5) {
      setSaveNotice({ type: "error", text: "Equity + Fixed Income must total 100%." });
      return;
    }
    if (Math.abs(northAmericaTarget + internationalTarget - 100) > 0.5) {
      setSaveNotice({ type: "error", text: "North America + International must total 100%." });
      return;
    }

    setSaving(true);
    setSaveNotice(null);
    try {
      await updateAlexUser({
        display_name: displayName.trim(),
        years_until_retirement: yearsUntilRetirement,
        target_retirement_income: targetRetirementIncome,
        asset_class_targets: { equity: equityTarget, fixed_income: fixedIncomeTarget },
        region_targets: { north_america: northAmericaTarget, international: internationalTarget },
      });
      setSaveNotice({ type: "ok", text: "Settings saved." });
      setTimeout(() => setSaveNotice(null), 3000);
    } catch (err) {
      setSaveNotice({ type: "error", text: err?.message ?? "Failed to save settings." });
    } finally {
      setSaving(false);
    }
  };

  // ── linked sliders (A + B = 100) ─────────────────────────────────────────────

  const onEquityChange = (v) => {
    const val = clamp(Number(v), 0, 100);
    setEquityTarget(val);
    setFixedIncomeTarget(100 - val);
  };
  const onNorthAmericaChange = (v) => {
    const val = clamp(Number(v), 0, 100);
    setNorthAmericaTarget(val);
    setInternationalTarget(100 - val);
  };

  // ── loading / error ──────────────────────────────────────────────────────────

  if (loading) {
    return (
      <section className="operating-stack">
        <div className="panel" role="status">
          Loading dashboard…
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="operating-stack">
        <div className="panel">
          <p className="advisor-error">{error}</p>
          <button type="button" onClick={loadData}>
            Retry
          </button>
        </div>
      </section>
    );
  }

  // ── render ───────────────────────────────────────────────────────────────────

  return (
    <section className="operating-stack">
      {/* ── summary metrics ── */}
      <section className="metrics advisor-metrics">
        <article className="metric">
          <span>Total portfolio value</span>
          <strong>${fmt(portfolioValue)}</strong>
        </article>
        <article className="metric">
          <span>Accounts</span>
          <strong>{accountCount}</strong>
        </article>
        <article className="metric">
          <span>Last analysis</span>
          <strong>
            {lastAnalysisDate
              ? new Date(lastAnalysisDate).toLocaleDateString()
              : "Never"}
          </strong>
        </article>
        {user?.years_until_retirement != null && (
          <article className="metric">
            <span>Years to retirement</span>
            <strong>{user.years_until_retirement}</strong>
          </article>
        )}
      </section>

      {/* ── user settings form ── */}
      <form className="panel" onSubmit={handleSave}>
        <header>
          <div>
            <span>Profile</span>
            <h2>Planning settings</h2>
          </div>
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </header>

        {saveNotice && (
          <p
            className={saveNotice.type === "error" ? "advisor-error" : "operating-note"}
            role={saveNotice.type === "error" ? "alert" : "status"}
          >
            {saveNotice.text}
          </p>
        )}

        <div className="advisor-form-grid">
          {/* Display name */}
          <label>
            Display name
            <input
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </label>

          {/* Target retirement income */}
          <label>
            Target retirement income (annual $)
            <input
              type="number"
              min="0"
              step="1000"
              value={targetRetirementIncome || ""}
              onChange={(e) =>
                setTargetRetirementIncome(Math.max(0, Number(e.target.value)))
              }
              placeholder="e.g. 80000"
            />
          </label>
        </div>

        {/* Years until retirement slider */}
        <label style={{ display: "block", marginTop: "1rem" }}>
          Years until retirement: <strong>{yearsUntilRetirement}</strong>
          <input
            type="range"
            min="0"
            max="50"
            value={yearsUntilRetirement}
            style={{ width: "100%", marginTop: "0.4rem" }}
            onChange={(e) => setYearsUntilRetirement(Number(e.target.value))}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.75em",
              opacity: 0.6,
            }}
          >
            {[0, 10, 20, 30, 40, 50].map((v) => (
              <span key={v}>{v}</span>
            ))}
          </div>
        </label>

        {/* Asset class targets */}
        <div style={{ marginTop: "1.25rem" }}>
          <h3 style={{ fontSize: "0.9em", fontWeight: 600, marginBottom: "0.5rem" }}>
            Target asset-class allocation
          </h3>
          <div className="advisor-form-grid">
            <label>
              Equity: <strong>{equityTarget}%</strong>
              <input
                type="range"
                min="0"
                max="100"
                value={equityTarget}
                onChange={(e) => onEquityChange(e.target.value)}
              />
            </label>
            <label>
              Fixed income: <strong>{fixedIncomeTarget}%</strong>
              <input
                type="range"
                min="0"
                max="100"
                value={fixedIncomeTarget}
                onChange={(e) => {
                  const val = clamp(Number(e.target.value), 0, 100);
                  setFixedIncomeTarget(val);
                  setEquityTarget(100 - val);
                }}
              />
            </label>
          </div>
          <SplitBar
            labelA="Equity"
            valA={equityTarget}
            labelB="Fixed income"
            valB={fixedIncomeTarget}
            colorA="#209DD7"
            colorB="#753991"
          />
        </div>

        {/* Regional targets */}
        <div style={{ marginTop: "1.25rem" }}>
          <h3 style={{ fontSize: "0.9em", fontWeight: 600, marginBottom: "0.5rem" }}>
            Target regional allocation
          </h3>
          <div className="advisor-form-grid">
            <label>
              North America: <strong>{northAmericaTarget}%</strong>
              <input
                type="range"
                min="0"
                max="100"
                value={northAmericaTarget}
                onChange={(e) => onNorthAmericaChange(e.target.value)}
              />
            </label>
            <label>
              International: <strong>{internationalTarget}%</strong>
              <input
                type="range"
                min="0"
                max="100"
                value={internationalTarget}
                onChange={(e) => {
                  const val = clamp(Number(e.target.value), 0, 100);
                  setInternationalTarget(val);
                  setNorthAmericaTarget(100 - val);
                }}
              />
            </label>
          </div>
          <SplitBar
            labelA="North America"
            valA={northAmericaTarget}
            labelB="International"
            valB={internationalTarget}
            colorA="#FFB707"
            colorB="#062147"
          />
        </div>
      </form>
    </section>
  );
}

export default Dashboard;
