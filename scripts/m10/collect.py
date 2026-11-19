#!/usr/bin/env python3
"""
M10 evidence collector.

Runs each source module in sequence, writes the evidence file to
evidence/, computes its SHA256, and assembles release_evidence.json.

Usage:
    python -m scripts.m10.collect --environment prod --out release_evidence.json
"""
import argparse
import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from . import sources
from .schemas import EvidenceCategory, EvidenceManifest, Status

logger = logging.getLogger("m10.collect")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

EVIDENCE_DIR = Path("evidence")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_evidence(name: str, content: str) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE_DIR / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    return path


def run_sources(environment: str) -> dict[str, EvidenceCategory]:
    categories: dict[str, EvidenceCategory] = {}

    for module_name in sources.__all__:
        module = getattr(sources, module_name)
        logger.info("Running %s", module_name)
        try:
            content = module.collect(environment)
            path = write_evidence(module_name, content)
            categories[module_name] = EvidenceCategory(
                status=Status.submitted,
                path=str(path),
                sha256=sha256_of(path),
            )
        except Exception as exc:
            logger.exception("Source %s failed", module_name)
            categories[module_name] = EvidenceCategory(
                status=Status.missing,
                path="",
                notes=f"collector error: {exc}",
            )
    return categories


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True, choices=["dev", "staging", "prod"])
    parser.add_argument("--out", default="release_evidence.json")
    parser.add_argument("--build-sha", default=os.getenv("GITHUB_SHA", "local"))
    args = parser.parse_args()

    categories = run_sources(args.environment)

    manifest = EvidenceManifest(
        generated_at=datetime.now(UTC).isoformat(),
        build_sha=args.build_sha,
        environment=args.environment,
        **categories,
    )

    Path(args.out).write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Wrote %s", args.out)


if __name__ == "__main__":
    main()