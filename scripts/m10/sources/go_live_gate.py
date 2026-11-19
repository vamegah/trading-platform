#!/usr/bin/env python3
"""
M10 go-live gate.

Refuses to release unless every required category is accepted, hashes
match, and the environment matches the requested release.

Usage:
    python -m scripts.m10.go_live_gate \
      --environment production \
      --evidence-manifest release_evidence.json \
      --live-requested \
      --fail-closed
"""
import argparse
import hashlib
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from .schemas import EvidenceManifest, REQUIRED_CATEGORIES, Status

logger = logging.getLogger("m10.gate")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def gate(manifest_path: Path, environment: str, fail_closed: bool) -> int:
    if not manifest_path.exists():
        logger.error("Evidence manifest not found")
        return 1 if fail_closed else 0

    manifest = EvidenceManifest(**json.loads(manifest_path.read_text()))

    if manifest.environment != environment:
        logger.error(
            "Manifest environment mismatch: %s != %s",
            manifest.environment, environment,
        )
        return 1

    problems: list[str] = []
    for name in REQUIRED_CATEGORIES:
        category = getattr(manifest, name)
        if category.status != Status.accepted:
            problems.append(f"{name}: status={category.status}")
            continue
        if not category.sha256:
            problems.append(f"{name}: missing hash")
            continue
        path = Path(category.path)
        if not path.exists():
            problems.append(f"{name}: evidence file missing")
            continue
        if _sha256(path) != category.sha256:
            problems.append(f"{name}: hash mismatch")
        if not category.accepted_by:
            problems.append(f"{name}: no acceptor")

    if problems:
        logger.error("Go-live gate FAILED:")
        for p in problems:
            logger.error("  - %s", p)
        return 1

    logger.info("Go-live gate PASSED at %s", datetime.now(UTC).isoformat())
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True)
    parser.add_argument("--evidence-manifest", default="release_evidence.json")
    parser.add_argument("--live-requested", action="store_true")
    parser.add_argument("--fail-closed", action="store_true")
    args = parser.parse_args()
    sys.exit(gate(Path(args.evidence_manifest), args.environment, args.fail_closed))


if __name__ == "__main__":
    main()