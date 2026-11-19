import { useEffect, useState } from "react";
import { getStoredSession } from "../services/api";

interface ResearcherEvent {
  event_id: string;
  event_type: string;
  symbol?: string;
  summary?: string;
  created_at: string;
  [key: string]: any;
}

const BASE = (import.meta as any).env.VITE_API_BASE_URL ?? "http://localhost:8000";
const POLL_MS = 5000;

async function fetchEvents(symbol?: string): Promise<ResearcherEvent[]> {
  const session = getStoredSession();
  const suffix = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
  const res = await fetch(`${BASE}/researcher/events${suffix}`, {
    headers: {
      "Content-Type": "application/json",
      ...(session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {}),
    },
  });
  if (!res.ok) throw new Error(`Researcher events fetch failed: ${res.statusText}`);
  return res.json();
}

export function useResearcherEvents(symbol?: string) {
  const [events, setEvents] = useState<ResearcherEvent[]>([]);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const data = await fetchEvents(symbol);
        if (active) { setEvents(data); setLoading(false); }
      } catch (err: any) {
        if (active) { setError(err.message ?? "Failed to load researcher events."); setLoading(false); }
      }
    };

    load();
    const interval = window.setInterval(load, POLL_MS);
    return () => { active = false; window.clearInterval(interval); };
  }, [symbol]);

  return { events, error, loading };
}
