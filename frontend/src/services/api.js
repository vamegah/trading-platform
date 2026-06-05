function resolveApiBaseUrl() {
  const configured = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  if (typeof window === "undefined") {
    return configured.replace(/\/$/, "");
  }

  try {
    const url = new URL(configured, window.location.origin);
    const browserHost = window.location.hostname;
    const configuredHost = url.hostname;
    const loopbackHosts = new Set(["localhost", "127.0.0.1"]);
    if (loopbackHosts.has(configuredHost) && loopbackHosts.has(browserHost)) {
      url.hostname = browserHost;
    }
    return url.toString().replace(/\/$/, "");
  } catch {
    return configured.replace(/\/$/, "");
  }
}

const API_BASE_URL = resolveApiBaseUrl();

export function getStoredSession() {
  try {
    return JSON.parse(window.localStorage.getItem("trading-session") || "null");
  } catch {
    return null;
  }
}

async function request(path, options = {}) {
  const session = getStoredSession();
  const authorization =
    options.auth === false || !session?.accessToken
      ? {}
      : { Authorization: `Bearer ${session.accessToken}` };
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...authorization, ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed: ${path}`;
    try {
      const payload = await response.json();
      detail = typeof payload.detail === "string" ? payload.detail : detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function login(username, password) {
  return request("/api/auth/login", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ username, password }),
  });
}

export async function createAccount(email, password) {
  return request("/api/auth/signup", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ email, password }),
  });
}

export async function createDemoSession() {
  return request("/api/auth/demo", { method: "POST", auth: false });
}

export async function refreshSession(refreshToken) {
  return request("/api/auth/refresh", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function getSession(accessToken) {
  return request("/api/auth/session", {
    method: "GET",
    auth: false,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  });
}

export async function getPortfolioSummary() {
  return request("/portfolio/summary");
}

export async function evaluateSignal(payload) {
  return request("/signals/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runWalkForwardBacktest(payload) {
  return request("/backtest/walk-forward", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function executePaperSignal(symbol) {
  return request(`/paper/execute/${symbol}`, { method: "POST" });
}

export async function getTradeJournal() {
  return request("/paper/journal");
}

export async function getBrokerCapabilities(mode = "sandbox") {
  return request(`/execution/brokers?mode=${mode}`);
}

export async function smartRouteOrder(payload) {
  return request("/execution/smart-route", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function precheckExecution(payload) {
  return request("/execution/precheck", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function validateChampionChallenger(payload) {
  return request("/validation/champion-challenger", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function monitorModel(payload) {
  return request("/validation/monitor", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runDiscoveryScanner(payload) {
  return request("/signals/scanner", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAlerts(userId = "demo") {
  const [alerts, preferences] = await Promise.all([
    request(`/alerts?user_id=${userId}`),
    request(`/alerts/preferences/${userId}`),
  ]);
  return { alerts, preferences };
}

export async function saveAlertPreferences(preferences) {
  return request("/alerts/preferences", {
    method: "POST",
    body: JSON.stringify(preferences),
  });
}

export async function getNudges(userId = "demo") {
  return request(`/nudges/history?user_id=${userId}`);
}

export async function dismissNudge(eventType, userId = "demo") {
  return request(`/nudges/dismiss/${eventType}?user_id=${userId}`, { method: "POST" });
}

export async function runStressTest(scenarioName, portfolio = []) {
  const defaultPortfolio = [
    { symbol: "SPY", market_value: 50000, factor_betas: { market: 1.0 } },
    { symbol: "QQQ", market_value: 35000, factor_betas: { market: 1.15, growth: 0.4 } },
  ];
  return request(`/stress-test/run/${scenarioName}`, {
    method: "POST",
    body: JSON.stringify(portfolio.length ? portfolio : defaultPortfolio),
  });
}

export async function getStressTestScenarios() {
  return request("/stress-test/scenarios");
}

export async function runCustomStressTest(payload) {
  return request("/stress-test/custom", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function estimateTaxOptimization(payload) {
  return request("/portfolio/tax/optimize", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function findTaxHarvests(payload) {
  return request("/portfolio/tax/harvest", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getSafetyStatus() {
  return request("/safety/status");
}

export async function monitorSafety(payload) {
  return request("/safety/monitor", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function evaluateSuitability(payload) {
  return request("/api/profile/suitability/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function calculatePositionSize(payload) {
  return request("/portfolio/position-size", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function evaluatePortfolioRisk(payload) {
  return request("/portfolio/risk/live", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function optimizePortfolioTrade(payload) {
  return request("/portfolio/trade-impact", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function evaluateSignalFreshness(signal) {
  return request("/signals/freshness", {
    method: "POST",
    body: JSON.stringify(signal),
  });
}

export async function getExternalIntegrations(category = "") {
  const suffix = category ? `?category=${encodeURIComponent(category)}` : "";
  return request(`/integrations${suffix}`);
}

export async function getTraderCommandCenter() {
  return request("/trader-os/command-center");
}

export async function getTraderOrderBlotter() {
  return request("/trader-os/orders");
}

export async function submitTraderOrder(payload) {
  return request("/trader-os/orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function cancelTraderOrder(orderId) {
  return request(`/trader-os/orders/${orderId}/cancel`, { method: "POST" });
}

export async function replaceTraderOrder(orderId, payload) {
  return request(`/trader-os/orders/${orderId}/replace`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getOptionsSuite(symbol) {
  return request(`/trader-os/options/${encodeURIComponent(symbol)}`);
}

export async function submitOptionsApproval(payload) {
  return request("/trader-os/options/approval", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function evaluateTraderMargin(payload) {
  return request("/trader-os/margin", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getExecutionQuality() {
  return request("/trader-os/execution-quality");
}

export async function getMarketReplay(symbol) {
  return request(`/trader-os/replay/${encodeURIComponent(symbol)}`);
}

export async function submitReplayTrade(payload) {
  return request("/trader-os/replay/trades", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getTraderWatchlists() {
  return request("/trader-os/watchlists");
}

export async function getEventCalendar() {
  return request("/trader-os/events");
}

export async function getTradeJournalV2() {
  return request("/trader-os/journal");
}

export async function addTradeJournalPlan(payload) {
  return request("/trader-os/journal", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function askTraderCopilot(question) {
  return request("/trader-os/copilot", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export async function getComplianceCenter() {
  return request("/trader-os/compliance-center");
}

export async function getBrokerReconciliation() {
  return request("/trader-os/reconciliation");
}

export async function getWorkstationOverview() {
  return request("/workstation/overview");
}

export async function getBasketWorkbench() {
  return request("/workstation/basket");
}

export async function previewBasket(payload) {
  return request("/workstation/basket/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function submitBasket(payload) {
  return request("/workstation/basket/submit", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runPreTradeControl(payload) {
  return request("/workstation/pre-trade/check", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getTaxLotDecision(symbol) {
  return request(`/workstation/tax-lots/${encodeURIComponent(symbol)}`);
}

export async function saveTaxLotDecision(symbol, payload) {
  return request(`/workstation/tax-lots/${encodeURIComponent(symbol)}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getBorrowDesk(symbol) {
  return request(`/workstation/borrow/${encodeURIComponent(symbol)}`);
}

export async function requestBorrowLocate(payload) {
  return request("/workstation/borrow/locate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function constructPortfolio(payload) {
  return request("/workstation/portfolio-lab/construct", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMarketMicrostructure(symbol, quantity = 250) {
  return request(`/workstation/microstructure/${encodeURIComponent(symbol)}?quantity=${encodeURIComponent(quantity)}`);
}

export async function getTradeStaging() {
  return request("/workstation/staging");
}

export async function stageWorkstationOrder(payload) {
  return request("/workstation/staging/orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function approveStagedOrder(stageId, payload = {}) {
  return request(`/workstation/staging/${encodeURIComponent(stageId)}/approve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function releaseStagedOrder(stageId, payload = {}) {
  return request(`/workstation/staging/${encodeURIComponent(stageId)}/release`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getDataQualityDashboard() {
  return request("/workstation/data-quality");
}

export async function researchStrategy(payload) {
  return request("/workstation/strategy/research", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deployStrategy(payload) {
  return request("/workstation/strategy/deploy", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getRiskConstitution() {
  return request("/workstation/risk-constitution");
}

export async function saveRiskConstitutionRule(payload) {
  return request("/workstation/risk-constitution", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function evaluateRiskConstitution(payload) {
  return request("/workstation/risk-constitution/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getDisclosureArchive(query = "") {
  const suffix = query ? `?query=${encodeURIComponent(query)}` : "";
  return request(`/workstation/disclosure-archive${suffix}`);
}

export async function getEmergencyControls() {
  return request("/workstation/emergency");
}

export async function pauseTradingEmergency(payload = {}) {
  return request("/workstation/emergency/pause", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function cancelAllEmergencyOrders(payload = {}) {
  return request("/workstation/emergency/cancel-all", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function decideEmergencyStagedOrder(stageId, payload) {
  return request(`/workstation/emergency/staged/${encodeURIComponent(stageId)}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getBrokerageOpsOverview() {
  return request("/brokerage-ops/overview");
}

export async function getCashSettlementCenter() {
  return request("/brokerage-ops/cash-settlement");
}

export async function createCashTransfer(payload) {
  return request("/brokerage-ops/cash-settlement/transfers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getChartTradingWorkspace(symbol) {
  return request(`/brokerage-ops/chart-trading/${encodeURIComponent(symbol)}`);
}

export async function previewChartOrder(payload) {
  return request("/brokerage-ops/chart-trading/order-preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCorporateActionsCenter() {
  return request("/brokerage-ops/corporate-actions");
}

export async function recordCorporateActionElection(actionId, payload) {
  return request(`/brokerage-ops/corporate-actions/${encodeURIComponent(actionId)}/election`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAccountDocumentsCenter() {
  return request("/brokerage-ops/account-documents");
}

export async function getAccountDocument(documentId) {
  return request(`/brokerage-ops/account-documents/${encodeURIComponent(documentId)}`);
}

export async function getBrokerageAdminConsole() {
  return request("/brokerage-ops/admin");
}

export async function createAdminOverride(payload) {
  return request("/brokerage-ops/admin/overrides", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getSurveillanceDashboard() {
  return request("/brokerage-ops/surveillance");
}

export async function evaluateSurveillance(payload) {
  return request("/brokerage-ops/surveillance/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMarketDataEntitlements() {
  return request("/brokerage-ops/entitlements");
}

export async function checkMarketDataEntitlement(payload) {
  return request("/brokerage-ops/entitlements/check", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getRecurringInvestments() {
  return request("/brokerage-ops/recurring-investments");
}

export async function createRecurringInvestmentPlan(payload) {
  return request("/brokerage-ops/recurring-investments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function simulateConditionalOrder(payload) {
  return request("/brokerage-ops/conditional-orders/simulate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createConditionalOrder(payload) {
  return request("/brokerage-ops/conditional-orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function generatePortfolioReviewPack(payload = {}) {
  return request("/brokerage-ops/reports/portfolio-review", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMobileCompanion() {
  return request("/brokerage-ops/mobile");
}

export async function pauseTradingFromMobile(payload = {}) {
  return request("/brokerage-ops/mobile/emergency-pause", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getSupportCenter() {
  return request("/brokerage-ops/support");
}

export async function createSupportCase(payload) {
  return request("/brokerage-ops/support/cases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getOneStopOverview() {
  return request("/one-stop/overview");
}

export async function getMarketTerminal(symbol) {
  return request(`/one-stop/terminal/${encodeURIComponent(symbol)}`);
}

export async function getResearchLab(symbol) {
  return request(`/one-stop/research/${encodeURIComponent(symbol)}`);
}

export async function generateResearchBrief(payload) {
  return request("/one-stop/research/brief", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getBrokerConnectivityHub() {
  return request("/one-stop/brokers");
}

export async function refreshBrokerConnection(payload) {
  return request("/one-stop/brokers/refresh", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAccountTransferCenter() {
  return request("/one-stop/transfers");
}

export async function createAcatsTransfer(payload) {
  return request("/one-stop/transfers/acats", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAccountTypeRules() {
  return request("/one-stop/account-rules");
}

export async function evaluateAccountTypeRule(payload) {
  return request("/one-stop/account-rules/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getPortfolioAnalyticsPro() {
  return request("/one-stop/analytics/portfolio");
}

export async function getAlertBuilder() {
  return request("/one-stop/alerts");
}

export async function createOneStopAlertRule(payload) {
  return request("/one-stop/alerts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function testOneStopAlert(payload) {
  return request("/one-stop/alerts/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getAutomationStudio() {
  return request("/one-stop/automation");
}

export async function simulateAutomation(payload) {
  return request("/one-stop/automation/simulate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getBacktestMarketplace() {
  return request("/one-stop/backtest-marketplace");
}

export async function compareMarketplaceStrategies(payload) {
  return request("/one-stop/backtest-marketplace/compare", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function readDocumentAi(payload) {
  return request("/one-stop/document-ai/read", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCoachingCenter() {
  return request("/one-stop/coaching");
}

export async function getCollaborationLayer() {
  return request("/one-stop/collaboration");
}

export async function createCollaborationSpace(payload) {
  return request("/one-stop/collaboration/spaces", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getFeeYieldCenter() {
  return request("/one-stop/fees-yield");
}

export async function getTrustCenter() {
  return request("/one-stop/trust");
}

export async function lockAccountTrust(payload) {
  return request("/one-stop/trust/lock", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getNotificationSystem() {
  return request("/one-stop/notifications");
}

export async function testNotificationDelivery(payload) {
  return request("/one-stop/notifications/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
