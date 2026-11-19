export {
  evaluateSignal,
  runDiscoveryScanner,
  evaluateSignalFreshness,
} from "./api";

export async function getSignals(symbol?: string): Promise<any> {
  const base = (import.meta as any).env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const session = (() => {
    try { return JSON.parse(window.localStorage.getItem("trading-session") ?? "null"); } catch { return null; }
  })();
  const suffix = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
  const res = await fetch(`${base}/signals${suffix}`, {
    headers: {
      "Content-Type": "application/json",
      ...(session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {}),
    },
  });
  if (!res.ok) throw new Error(`getSignals failed: ${res.statusText}`);
  return res.json();
}
