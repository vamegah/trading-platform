import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.shared.config import Settings  # noqa: E402
from scripts.evidence_manifest import load_manifest, validate_manifest  # noqa: E402
from scripts.release_candidate_review import build_review  # noqa: E402


def _default_env_file(environment: str) -> Path:
    normalized = environment.lower()
    if normalized in {"prod", "production"}:
        return Path("config/prod.env")
    return Path(f"config/{normalized}.env")


def build_gate(
    environment: str,
    evidence_manifest: Path,
    live_requested: bool = False,
    env_file: Path | None = None,
) -> dict[str, object]:
    normalized_environment = environment.lower()
    runtime_env_file = env_file or _default_env_file(environment)
    settings = Settings(
        _env_file=runtime_env_file if runtime_env_file.exists() else ".env",
        environment=environment,
        require_live_integrations=live_requested,
    )
    runtime_issues = settings.production_readiness_issues()
    evidence = validate_manifest(evidence_manifest)
    manifest = load_manifest(evidence_manifest)
    release_intent_matches = _release_intent_matches(manifest, normalized_environment, live_requested)
    release = build_review(evidence_manifest)
    blocking_reasons = []
    if normalized_environment not in {"prod", "production"}:
        blocking_reasons.append("environment_not_production")
    if not live_requested:
        blocking_reasons.append("live_request_not_confirmed")
    if runtime_issues:
        blocking_reasons.append("runtime_configuration_invalid")
    if not evidence.valid:
        blocking_reasons.append("evidence_manifest_invalid")
    if not release["release_candidate_approved"]:
        blocking_reasons.append("release_candidate_not_approved")
    if not release_intent_matches:
        blocking_reasons.append("manifest_release_intent_mismatch")
    allowed = (
        normalized_environment in {"prod", "production"}
        and live_requested
        and not runtime_issues
        and evidence.valid
        and release_intent_matches
        and release["release_candidate_approved"] is True
    )
    return {
        "environment": environment,
        "env_file": str(runtime_env_file),
        "live_requested": live_requested,
        "runtime_issues": runtime_issues,
        "evidence_valid": evidence.valid,
        "release_intent_matches": release_intent_matches,
        "release_candidate_approved": release["release_candidate_approved"],
        "open_tasks": release["open_tasks"],
        "blocking_reasons": blocking_reasons,
        "go_live_allowed": allowed,
    }


def _release_intent_matches(manifest: dict[str, object], environment: str, live_requested: bool) -> bool:
    if not live_requested:
        return True
    release = manifest.get("release", {})
    if not isinstance(release, dict):
        return False
    manifest_environment = str(release.get("environment", "")).lower()
    return (
        environment in {"prod", "production"}
        and manifest_environment in {"prod", "production"}
        and release.get("live_trading_requested") is True
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Final live-trading go-live gate.")
    parser.add_argument("--environment", default="production")
    parser.add_argument("--evidence-manifest", default="release_evidence.json")
    parser.add_argument("--env-file")
    parser.add_argument("--live-requested", action="store_true")
    parser.add_argument("--fail-closed", action="store_true")
    args = parser.parse_args()

    gate = build_gate(
        args.environment,
        Path(args.evidence_manifest),
        args.live_requested,
        Path(args.env_file) if args.env_file else None,
    )
    print(json.dumps(gate, indent=2, sort_keys=True))
    if args.fail_closed and not gate["go_live_allowed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
