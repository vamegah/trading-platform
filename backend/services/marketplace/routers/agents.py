from fastapi import APIRouter

from backend.services.marketplace.models import MarketplaceAgent
from backend.services.marketplace.vetting import vet_agent_manifest

router = APIRouter()

_AGENTS: dict[str, MarketplaceAgent] = {}


@router.post("")
async def publish_agent(agent: MarketplaceAgent) -> dict[str, object]:
    vetting = vet_agent_manifest(agent.__dict__)
    agent.status = "approved" if vetting["approved"] else "pending_review"
    _AGENTS[agent.id] = agent
    return {"agent": agent, "vetting": vetting}


@router.get("")
async def list_agents(asset_type: str | None = None) -> list[MarketplaceAgent]:
    agents = list(_AGENTS.values())
    if asset_type:
        return [agent for agent in agents if asset_type in agent.asset_types]
    return agents


@router.get("/search")
async def search_agents(query: str) -> list[MarketplaceAgent]:
    needle = query.lower()
    return [
        agent
        for agent in _AGENTS.values()
        if needle in agent.name.lower() or needle in agent.description.lower()
    ]

