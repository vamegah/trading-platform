# Production Evidence Manifest

Release approval requires `release_evidence.json` with accepted evidence for each externally validated M9 item.

Generate a template:

```bash
python scripts/evidence_manifest.py --template > release_evidence.json
```

Validate it:

```bash
python scripts/evidence_manifest.py --manifest release_evidence.json --fail-invalid
```

Accept a reviewed artifact into the manifest only after its category validator passes:

```bash
python scripts/accept_evidence.py \
  --manifest release_evidence.json \
  --key provider_certification \
  --artifact provider-certification.json \
  --owner data-platform \
  --notes "Provider contracts, credentials, SLA, data rights, and failover reviewed"
```

Accept a complete M10 evidence bundle atomically:

```bash
python scripts/accept_evidence_bundle.py \
  --manifest release_evidence.json \
  --evidence-dir release-artifacts/rc-YYYYMMDD \
  --release-candidate rc-YYYYMMDD \
  --live-requested \
  --fail-invalid
```

The bundle directory must contain one validated JSON artifact per required evidence key, using the filenames emitted by `scripts/accept_evidence_bundle.py`.

## Required Evidence Keys

| M9 Task | Evidence Key |
| --- | --- |
| M9-01 | `provider_certification` |
| M9-02 | `broker_certification` |
| M9-03 | `model_validation` |
| M9-06 | `persistent_controls_restore` |
| M9-08 | `cloud_infrastructure_plan` |
| M9-10 | `load_soak_test` |
| M9-11 | `security_assessment` |
| M9-12 | `dr_outage_drill` |
| M9-13 | `legal_compliance_review` |
| M9-14 | `paper_trading_validation` |

Each evidence record must include `accepted=true`, an artifact URI, owner, review timestamp, and notes. Use `scripts/accept_evidence.py` so the artifact is validated before the manifest is updated. The go-live gate remains blocked while required evidence is missing, invalid, or not accepted.

For production live trading, the release section must also record explicit intent:

```json
{
  "release": {
    "environment": "production",
    "candidate": "rc-YYYYMMDD",
    "live_trading_requested": true
  }
}
```

The go-live gate treats a missing or false `live_trading_requested` value as a blocker even when all evidence records are accepted.
