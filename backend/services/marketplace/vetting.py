REQUIRED_MANIFEST_FIELDS = {"id", "name", "publisher_id", "asset_types", "description"}


def vet_agent_manifest(manifest: dict) -> dict[str, object]:
    missing = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
    risky_permissions = [
        permission
        for permission in manifest.get("permissions", [])
        if permission in {"unrestricted_network", "filesystem_write", "live_trading"}
    ]
    return {
        "approved": not missing and not risky_permissions,
        "missing_fields": missing,
        "manual_review_required": bool(risky_permissions),
        "risky_permissions": risky_permissions,
    }

