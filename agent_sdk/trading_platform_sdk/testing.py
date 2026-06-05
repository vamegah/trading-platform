import asyncio

from trading_platform_sdk.agent import Agent, AgentContext, AgentResult


def run_agent_once(agent: Agent, symbol: str, context: AgentContext | None = None) -> AgentResult:
    async def _run() -> AgentResult:
        return await agent.analyze(symbol, context or AgentContext(user_id="test-user"))

    return asyncio.run(_run())
