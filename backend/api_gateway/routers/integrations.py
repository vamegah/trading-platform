from fastapi import APIRouter

from backend.shared.external_apis import list_external_api_status, missing_live_integrations

router = APIRouter()


@router.get("")
async def integrations(category: str | None = None) -> dict[str, object]:
    providers = list_external_api_status(category)
    return {
        "providers": providers,
        "configured": sum(1 for provider in providers if provider["configured"]),
        "total": len(providers),
        "missing_live_integrations": missing_live_integrations(),
    }
