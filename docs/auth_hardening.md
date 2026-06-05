# Authentication Hardening

Production authentication must use a reviewed identity provider or the hardened local JWT issuer with equivalent controls.

## Token Policy

- Access tokens include issuer, issued-at, expiry, JWT ID, roles, and `token_type=access`.
- Refresh tokens include `token_type=refresh` and cannot authorize API actions.
- Service-to-service tokens include `token_type=service` and are the only tokens accepted for `service:internal` permissions.
- Production deployments must rotate signing keys through the approved secret manager.
- Admin accounts require MFA through the identity provider before production access is granted.

## RBAC Policy

- Users can read signals and perform approved one-click trading.
- Automated trading requires explicit suitability, consent, risk, and execution preflight checks.
- Admins can manage users, models, secrets, and audit review.
- Service accounts are scoped to internal APIs and must not be used by humans.

## Release Gate

Live trading remains disabled until identity-provider configuration, MFA enforcement, service-account inventory, key rotation, and protected-route tests are reviewed by security.
