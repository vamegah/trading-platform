# scripts/m10/accept.py
#!/usr/bin/env python3
"""
Accept a category in the manifest.

Usage:
    python -m scripts.m10.accept --manifest release_evidence.json \
      --category provider_certification --by "release-manager"
"""
import argparse
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("m10.accept")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="release_evidence.json")
    parser.add_argument("--category", required=True)
    parser.add_argument("--by", required=True)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text())

    if args.category not in manifest:
        logger.error("Unknown category %s", args.category)
        raise SystemExit(1)

    category = manifest[args.category]
    path = Path(category["path"])
    if not path.exists():
        logger.error("Evidence file missing: %s", path)
        raise SystemExit(1)

    category["status"] = "accepted"
    category["sha256"] = _sha256(path)
    category["accepted_at"] = datetime.now(UTC).isoformat()
    category["accepted_by"] = args.by
    if args.notes:
        category["notes"] = args.notes

    manifest_path.write_text(json.dumps(manifest, indent=2))
    logger.info("Accepted %s", args.category)


if __name__ == "__main__":
    main()