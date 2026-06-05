def issue_partner_token(partner_id: str, scopes: list[str]) -> dict[str, object]:
    return {
        "partner_id": partner_id,
        "access_token": f"partner-dev-token-{partner_id}",
        "token_type": "bearer",
        "scopes": scopes,
    }

