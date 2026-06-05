# Release Candidate Checklist

Live trading is disabled until every item below is complete and signed off.

## Required Evidence

| Area | Command or Artifact | Owner |
| --- | --- | --- |
| Backend tests | `pytest -q` | Engineering |
| Frontend build | `npm run build` | Engineering |
| Python compile | `python -m compileall backend scripts migrations` | Engineering |
| Migration rollback | `pytest -q backend/tests/integration/test_m9_migrations.py` | Engineering |
| Persistent controls | `pytest -q backend/tests/integration/test_m9_persistent_controls.py` | Engineering |
| Smoke test | `python scripts/smoke_test.py <base_url>` | Release manager |
| Load test | `python scripts/run_load_test.py --users 10000 --instruments 5000 --duration-minutes 240 --environment staging --distributed-evidence --fail-invalid` plus cloud report | SRE |
| DR drill | `python scripts/run_dr_drill.py --evidence <dr-evidence.json> --fail-invalid` plus environment evidence | SRE |
| Security assessment | `python scripts/security_assessment.py --validate <security-assessment.json> --fail-invalid` plus scan reports | Security |
| Legal/compliance | Counsel-approved disclosures and trading approvals | Compliance |
| Final readiness review | `python scripts/release_candidate_review.py --fail-open` | Release manager |
| Evidence manifest | `python scripts/evidence_manifest.py --manifest release_evidence.json --fail-invalid` | Release manager |
| Evidence acceptance | `python scripts/accept_evidence.py --manifest release_evidence.json --key <key> --artifact <artifact.json> --owner <team> --notes <summary>` | Release manager |
| Evidence bundle acceptance | `python scripts/accept_evidence_bundle.py --manifest release_evidence.json --evidence-dir release-artifacts/<candidate> --release-candidate <candidate> --live-requested --fail-invalid` | Release manager |
| Go-live gate | `python scripts/go_live_gate.py --environment production --env-file config/prod.env --evidence-manifest release_evidence.json --live-requested --fail-closed` | Release manager |
| Model validation | `python scripts/model_validation_report.py --validate <model-validation.json>` | ML |
| Provider certification | `python scripts/provider_certification.py --validate <provider-report.json>` | Data platform |
| Broker certification | `python scripts/broker_certification.py --validate <broker-report.json>` | Execution |
| Persistent controls restore | `python scripts/persistent_controls_restore.py --evidence <persistent-controls-evidence.json> --fail-invalid` plus KMS/Vault evidence | Platform |
| Cloud infrastructure plan | `python scripts/cloud_infrastructure_plan.py --evidence <cloud-apply-evidence.json> --fail-invalid` plus Terraform plan/apply evidence | SRE |
| Paper trading validation | `python scripts/paper_trading_validation.py --trades <trades.json> --days 30` | Trading operations |

## Release Gates

1. Staging deployment succeeds from the `Deploy` workflow.
2. Smoke tests pass against staging.
3. Production Terraform plan is reviewed and archived.
4. Security has no unresolved critical or high findings without formal risk acceptance.
5. DR evidence satisfies approved RTO and RPO.
6. Extended paper trading report is accepted.
7. Legal/compliance signs live-trading terms and jurisdiction policy.
8. Operations confirms runbooks, on-call rotation, and rollback owner.
9. `release_evidence.json` validates against the required M9 evidence manifest.

## Go-Live Rule

`LIVE_TRADING_ENABLED` remains `false` until the release-candidate readiness review is approved and recorded. Do not mark `release_evidence.json` records as accepted until the category validator passes and the artifact is reviewed by the listed owner. The final manifest must explicitly set `release.live_trading_requested=true` for production before the go-live gate can allow live trading.
