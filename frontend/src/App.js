import React, { useEffect, useMemo, useState } from "react";
import AlertCenter from "./components/Alerts/AlertCenter";
import BacktestViewer from "./components/BacktestViewer";
import BehavioralNudges from "./components/BehavioralNudges";
import { ChartFeedbackPanel } from "./components/Charts";
import DiscoveryScanner from "./components/DiscoveryScanner";
import ExplainabilityPanel from "./components/ExplainabilityPanel";
import ExecutionPanel from "./components/Execution";
import IntegrationsPanel from "./components/Integrations";
import BlackSwanBreaker from "./components/BlackSwanBreaker";
import BrokerageOps from "./components/BrokerageOps";
import OneStop from "./components/OneStop";
import PortfolioHealth from "./components/PortfolioHealth";
import SignalFreshness from "./components/SignalFreshness";
import StockDeepDive from "./components/StockDeepDive";
import StressTest from "./components/StressTest";
import TaxOptimizer from "./components/TaxOptimizer";
import {
  ComplianceCenter,
  MarketReplay,
  OptionsSuite,
  OrderBlotter,
  PortfolioCommandCenter,
  StockTradeTicket,
  TradeJournalPro,
  TraderCopilot,
} from "./components/TraderOS";
import Workstation from "./components/Workstation";
import {
  createAccount,
  createDemoSession,
  evaluateSignal,
  getNudges,
  getSession,
  login as loginApi,
  refreshSession,
} from "./services/api";
import "./index.css";

const tabs = [
  { id: "command", label: "Command" },
  { id: "trade", label: "Trade" },
  { id: "workstation", label: "Workstation" },
  { id: "operations", label: "Operations" },
  { id: "one-stop", label: "One Stop" },
  { id: "blotter", label: "Blotter" },
  { id: "options", label: "Options" },
  { id: "replay", label: "Replay" },
  { id: "journal", label: "Journal" },
  { id: "copilot", label: "Copilot" },
  { id: "compliance-center", label: "Compliance" },
  { id: "deep-dive", label: "Deep Dive" },
  { id: "scanner", label: "Scanner" },
  { id: "risk", label: "Risk" },
  { id: "validation", label: "Validation" },
  { id: "execution", label: "Execution" },
  { id: "alerts", label: "Alerts" },
  { id: "integrations", label: "Integrations" },
  { id: "nudges", label: "Nudges" },
];

function AuthGate({ onLogin }) {
  const [authMode, setAuthMode] = useState("sign-in");
  const [email, setEmail] = useState("analyst@example.com");
  const [password, setPassword] = useState("research-demo");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");

  const selectAuthMode = (nextMode) => {
    setAuthMode(nextMode);
    setMessage("");
    setConfirmPassword("");
    if (nextMode === "register" && email === "analyst@example.com") {
      setEmail("");
      setPassword("");
    }
  };

  const startSession = async (token, metadata = {}) => {
    const session = await getSession(token.access_token);
    onLogin({
      email,
      accessToken: token.access_token,
      refreshToken: token.refresh_token,
      roles: session.roles,
      permissions: session.permissions,
      ...metadata,
    });
  };

  const submit = async (event) => {
    event.preventDefault();
    setStatus("loading");
    setMessage("");
    try {
      if (authMode === "register") {
        if (password.length < 8) {
          setMessage("Use at least 8 characters.");
          return;
        }
        if (password !== confirmPassword) {
          setMessage("Passwords do not match.");
          return;
        }
        const token = await createAccount(email.trim(), password);
        await startSession(token, { mode: "registered" });
        return;
      }

      const token = await loginApi(email.trim(), password);
      await startSession(token);
    } catch (error) {
      setMessage(error?.message || "Sign-in failed.");
    } finally {
      setStatus("idle");
    }
  };

  const continueAsDemo = async () => {
    setStatus("loading");
    setMessage("");
    try {
      const token = await createDemoSession();
      await startSession(token, { mode: "demo" });
    } catch (error) {
      setMessage(error?.message || "Demo sign-in failed.");
    } finally {
      setStatus("idle");
    }
  };

  return (
    <main className="auth-screen">
      <form className="auth-panel" onSubmit={submit}>
        <p className="eyebrow">Research workspace</p>
        <h1>Trading Platform</h1>
        <div className="auth-mode" role="tablist" aria-label="Authentication mode">
          <button
            aria-selected={authMode === "sign-in"}
            className={authMode === "sign-in" ? "auth-mode__active" : ""}
            role="tab"
            type="button"
            onClick={() => selectAuthMode("sign-in")}
          >
            Sign in
          </button>
          <button
            aria-selected={authMode === "register"}
            className={authMode === "register" ? "auth-mode__active" : ""}
            role="tab"
            type="button"
            onClick={() => selectAuthMode("register")}
          >
            Register
          </button>
        </div>
        <label>
          Email
          <input
            autoComplete="email"
            required
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            autoComplete={authMode === "register" ? "new-password" : "current-password"}
            required
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {authMode === "register" && (
          <label>
            Confirm password
            <input
              autoComplete="new-password"
              required
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
            />
          </label>
        )}
        {message && <div className="auth-message">{message}</div>}
        <button type="submit" disabled={status === "loading"}>
          {status === "loading" ? "Working" : authMode === "register" ? "Create account" : "Sign in"}
        </button>
        <button type="button" className="ghost-button auth-demo-button" disabled={status === "loading"} onClick={continueAsDemo}>
          Continue as demo
        </button>
      </form>
    </main>
  );
}

function App() {
  const [session, setSession] = useState(() => {
    const stored = window.localStorage.getItem("trading-session");
    return stored ? JSON.parse(stored) : null;
  });
  const [activeTab, setActiveTab] = useState("command");
  const [symbol, setSymbol] = useState("MSFT");
  const [signal, setSignal] = useState(null);
  const [nudges, setNudges] = useState([]);
  const [status, setStatus] = useState("idle");

  useEffect(() => {
    if (!session) return;
    window.localStorage.setItem("trading-session", JSON.stringify(session));
  }, [session]);

  useEffect(() => {
    if (!session?.accessToken) return;
    getSession(session.accessToken)
      .then((current) => {
        if (!current.authenticated && session.refreshToken) {
          return refreshSession(session.refreshToken).then((token) =>
            getSession(token.access_token).then((refreshed) => {
              setSession((existing) => ({
                ...(existing || {}),
                accessToken: token.access_token,
                refreshToken: token.refresh_token,
                roles: refreshed.roles,
                permissions: refreshed.permissions,
              }));
            })
          );
        }
        if (!current.authenticated) {
          signOut();
        }
        return undefined;
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!session) return;
    setStatus("loading");
    evaluateSignal({ symbol, portfolio_context: { factor_load: { quality: 0.4 } } })
      .then((data) => {
        setSignal(data);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
    getNudges("demo").then(setNudges).catch(() => setNudges([]));
  }, [session, symbol]);

  const confidence = useMemo(() => Math.round((signal?.confidence || 0) * 100), [signal]);

  const signOut = () => {
    window.localStorage.removeItem("trading-session");
    setSession(null);
  };

  if (!session) {
    return <AuthGate onLogin={setSession} />;
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark">TP</div>
        <nav aria-label="Primary">
          {tabs.map((tab) => (
            <button
              className={activeTab === tab.id ? "nav-active" : ""}
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Protected research workspace</p>
            <h1>{symbol} Research</h1>
            <span className="session-line">{(session.roles || ["user"]).join(", ")}</span>
          </div>
          <div className="symbol-tools">
            <input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} />
            <button type="button" onClick={signOut}>
              Sign out
            </button>
          </div>
        </header>

        <section className="metrics">
          <article className="metric">
            <span>Recommendation</span>
            <strong>{signal?.signal || status}</strong>
          </article>
          <article className="metric">
            <span>Confidence</span>
            <strong>{confidence}%</strong>
          </article>
          <article className="metric">
            <span>Tail risk</span>
            <strong>{Math.round((signal?.probability_distribution?.tail_loss_8pct_20d || 0) * 100)}%</strong>
          </article>
          <article className="metric">
            <span>Freshness</span>
            <strong>{Math.round((signal?.freshness_score || 0) * 100)}%</strong>
          </article>
        </section>

        {activeTab === "command" && <PortfolioCommandCenter symbol={symbol} />}
        {activeTab === "trade" && <StockTradeTicket symbol={symbol} />}
        {activeTab === "workstation" && <Workstation symbol={symbol} />}
        {activeTab === "operations" && <BrokerageOps symbol={symbol} />}
        {activeTab === "one-stop" && <OneStop symbol={symbol} />}
        {activeTab === "blotter" && <OrderBlotter symbol={symbol} />}
        {activeTab === "options" && <OptionsSuite symbol={symbol} />}
        {activeTab === "replay" && <MarketReplay symbol={symbol} />}
        {activeTab === "journal" && <TradeJournalPro symbol={symbol} />}
        {activeTab === "copilot" && <TraderCopilot />}
        {activeTab === "compliance-center" && <ComplianceCenter />}
        {activeTab === "deep-dive" && (
          <section className="analysis-grid deep-dive-grid">
            <div className="deep-dive-primary">
              <StockDeepDive signal={signal} symbol={symbol} />
            </div>
            <div className="deep-dive-sidebar">
              <ExplainabilityPanel signal={signal} />
              <SignalFreshness score={signal?.freshness_score || 0} signal={signal} />
            </div>
          </section>
        )}
        {activeTab === "scanner" && <DiscoveryScanner />}
        {activeTab === "risk" && (
          <section className="analysis-grid">
            <PortfolioHealth />
            <StressTest />
            <TaxOptimizer />
            <BlackSwanBreaker />
          </section>
        )}
        {activeTab === "validation" && <BacktestViewer symbol={symbol} />}
        {activeTab === "execution" && <ExecutionPanel symbol={symbol} />}
        {activeTab === "alerts" && <AlertCenter />}
        {activeTab === "integrations" && <IntegrationsPanel />}
        {activeTab === "nudges" && <BehavioralNudges nudges={nudges} />}
        <ChartFeedbackPanel context={activeTab} />
      </section>
    </main>
  );
}

export default App;
