import json
from datetime import datetime, timezone


def build_stop_report() -> dict[str, object]:
    return {
        "action": "chaos_stop",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "safe_local_actions": [
            "disable chaos_mode feature flag",
            "clear local simulation state",
            "leave real network and broker connections untouched",
        ],
        "staging_actions": [
            "kubectl delete chaosengine,networkchaos,podchaos,stresschaos -n chaos --all",
            "reset toxiproxy routes to healthy upstreams",
            "remove Redis poison keys matching chaos:*",
            "restart api-orchestrator pods if health checks fail",
        ],
        "status": "ready",
    }


if __name__ == "__main__":
    print(json.dumps(build_stop_report(), indent=2))
