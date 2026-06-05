import { useEffect, useState } from "react";

export function useMarketOverview() {
  const [overview, setOverview] = useState({ status: "idle", data: null });

  useEffect(() => {
    setOverview({
      status: "ready",
      data: {
        regime: "balanced",
        volatility: "normal",
      },
    });
  }, []);

  return overview;
}

