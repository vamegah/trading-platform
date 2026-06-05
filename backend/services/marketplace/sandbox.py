ALLOWED_TOOLS = {"market_data", "fundamentals", "feature_store", "model_inference"}
BLOCKED_SANDBOX_ACTIONS = {
    "host_network": "deny network namespace escape",
    "cpu_exhaustion": "terminate after quota breach",
    "host_filesystem": "deny host filesystem mount",
    "unauthorized_external_api": "egress only to orchestrator proxy",
}


def build_sandbox_policy(agent_id: str, requested_tools: list[str]) -> dict[str, object]:
    allowed = sorted(set(requested_tools) & ALLOWED_TOOLS)
    denied = sorted(set(requested_tools) - ALLOWED_TOOLS)
    return {
        "agent_id": agent_id,
        "allowed_tools": allowed,
        "denied_tools": denied,
        "network": "deny_by_default",
        "execution_timeout_seconds": 30,
    }


async def run_in_sandbox(agent_id: str, payload: dict) -> dict[str, object]:
    return {"agent_id": agent_id, "status": "queued", "payload_keys": sorted(payload.keys())}


def evaluate_sandbox_violation(action: str) -> dict[str, object]:
    return {
        "action": action,
        "blocked": action in BLOCKED_SANDBOX_ACTIONS,
        "control": BLOCKED_SANDBOX_ACTIONS.get(action, "not_applicable"),
    }
