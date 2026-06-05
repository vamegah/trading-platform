function resolveApiBaseUrl() {
  const configured = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  if (typeof window === "undefined") {
    return configured.replace(/\/$/, "");
  }

  try {
    const url = new URL(configured, window.location.origin);
    const loopbackHosts = new Set(["localhost", "127.0.0.1"]);
    if (loopbackHosts.has(url.hostname) && loopbackHosts.has(window.location.hostname)) {
      url.hostname = window.location.hostname;
    }
    return url.toString().replace(/\/$/, "");
  } catch {
    return configured.replace(/\/$/, "");
  }
}

const API_BASE_URL = resolveApiBaseUrl();

export async function getPartnerSignal(symbol) {
  const response = await fetch(`${API_BASE_URL}/api/partner/signals/${symbol}`);
  if (!response.ok) {
    throw new Error("Unable to load partner signal");
  }
  return response.json();
}
