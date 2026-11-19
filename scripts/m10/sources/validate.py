#!/usr/bin/env python3
"""
M10 evidence validator.

Reads release_evidence.json and:
  * Confirms every required category is present.
  * Re-hashes every evidence file and compares to the stored sha256.
  * Applies category-specific rules.
  * Refuses to accept a category if any rule fails.
"""
import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

from .schemas import EvidenceManifest, REQUIRED_CATEGORIES, Status

logger = logging.getLogger("m10.validate")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _check_provider(path: Path, content: str) -> list[str]:
    problems = []
    if "missing key" in content:
        problems.append("provider missing API key")
    if "error:" in content:
        problems.append("provider sandbox call failed")
    return problems


def _check_broker(path: Path, content: str) -> list[str]:
    problems = []
    for broker in ("alpaca", "ibkr"):
        if f"{broker}" in content and "live_approved | false" in content.lower():
            problems.append(f"{broker} live not approved")
    return problems


def _check_model(path: Path, content: str) -> list[str]:
    if "missing" in content and "approved" not in content.lower():
        return ["model validation missing approvals"]
    return []


def _check_persistent(path: Path, content: str) -> list[str]:
    if "pending" in content.lower():
        return ["persistent controls restore pending"]
    if "unknown" in content.lower():
        return ["audit chain integrity unknown"]
    return []


def _check_infra(path: Path, content: str) -> list[str]:
    if "pending" in content.lower():
        return ["DR region not verified"]
    return []


def _check_load(path: Path, content: str) -> list[str]:
    if "n/a" in content.lower():
        return ["load test report missing"]
    return []


def _check_security(path: Path, content: str) -> list[str]:
    if "| Critical | " in content and "| 0 |" not in content:
        return ["critical findings not remediated"]
    if "| High | " in content and "| 0 |" not in content:
        return ["high findings not remediated"]
    return []


def _check_dr(path: Path, content: str) -> list[str]:
    if "pending" in content.lower():
        return ["DR drill incomplete"]
    return []


def _check_legal(path: Path, content: str) -> list[str]:
    if "| False |" in content:
        return ["one or more legal documents missing"]
    return []


def _check_paper(path: Path, content: str) -> list[str]:
    if "**0**" in content:
        return ["no paper trades recorded"]
    return []


CHECKERS = {
    "provider_certification": _check_provider,
    "broker_certification": _check_broker,
    "model_validation": _check_model,
    "persistent_controls_restore": _check_persistent,
    "cloud_infrastructure_plan": _check_infra,
    "load_soak_test": _check_load,
    "security_assessment": _check_security,
    "dr_outage_drill": _check_dr,
    "legal_compliance_review": _check_legal,
    "paper_trading_validation": _check_paper,
}


def validate(manifest_path: Path) -> int:
    raw = json.loads(manifest_path.read_text())
    manifest = EvidenceManifest(**raw)

    failures: list[str] = []

    for name in REQUIRED_CATEGORIES:
        category = getattr(manifest, name)
        if category.status != Status.submitted:
            failures.append(f"{name}: not submitted")
            continue

        path = Path(category.path)
        if not path.exists():
            failures.append(f"{name}: evidence file missing")
            continue

        digest = _sha256(path)
        if category.sha256 and digest != category.sha256:
            failures.append(f"{name}: hash mismatch")
            continue

        check = CHECKERS.get(name)
        if check:
            content = path.read_text()
            for problem in check(path, content):
                failures.append(f"{name}: {problem}")

        # Update the manifest with the recomputed hash
        setattr(
            manifest,
            name,
            category.model_copy(update={"sha256": digest}),
        )

    manifest_path.write_text(manifest.model_dump_json(indent=2))

    if failures:
        logger.error("Validation failed:")
        for f in failures:
            logger.error("  - %s", f)
        return 1

    logger.info("All categories validated.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="release_evidence.json")
    args = parser.parse_args()
    sys.exit(validate(Path(args.manifest)))


if __name__ == "__main__":
    main()