"""
Clean up the S3 Vectors financial-research index.

Usage:
    python cleanup_vectors.py                     # interactive confirm
    python cleanup_vectors.py --dry-run           # list what would be deleted
    python cleanup_vectors.py --force             # no prompt (CI-friendly)
    python cleanup_vectors.py --filter ticker=NVDA
    python cleanup_vectors.py --filter tag=test --force

Exit codes:
    0 — success (deleted or already empty)
    1 — configuration error
    2 — user cancelled
    3 — partial failure (some vectors could not be deleted)

Design notes:
- Uses list_vectors (paged) when available — this is a real scan, not a
  similarity search, so it actually covers the whole index.
- Falls back to metadata-filtered listing if the SDK supports it.
- Batched deletes (up to MAX_BATCH) with retry on throttling.
- Dry-run mode prints target keys without mutating anything.
- Non-interactive mode for CI/CD.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

# Load env from project root (adjust if your layout differs)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env", override=True)

VECTOR_BUCKET = os.getenv("VECTOR_BUCKET")
INDEX_NAME = os.getenv("INDEX_NAME", "financial-research")
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-west-2"

MAX_BATCH = int(os.getenv("CLEANUP_BATCH_SIZE", "100"))
MAX_PAGES = int(os.getenv("CLEANUP_MAX_PAGES", "10000"))  # hard safety cap
DELETE_RETRIES = int(os.getenv("CLEANUP_DELETE_RETRIES", "3"))
BACKOFF_BASE = float(os.getenv("CLEANUP_BACKOFF_BASE", "0.5"))


# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("cleanup-vectors")


# ---------------------------------------------------------------------------
# AWS
# ---------------------------------------------------------------------------

_boto_cfg = Config(
    retries={"max_attempts": 5, "mode": "standard"},
    connect_timeout=5,
    read_timeout=30,
    region_name=AWS_REGION,
)

s3_vectors = boto3.client("s3vectors", config=_boto_cfg)


# ---------------------------------------------------------------------------
# FILTER PARSING
# ---------------------------------------------------------------------------

@dataclass
class Filter:
    """Simple key=value filter applied against vector metadata."""
    key: str
    value: str

    def matches(self, metadata: dict[str, Any]) -> bool:
        v = metadata.get(self.key)
        if v is None:
            return False
        if isinstance(v, list):
            return self.value in [str(x) for x in v]
        return str(v) == self.value


def _parse_filters(raw: Optional[list[str]]) -> list[Filter]:
    out: list[Filter] = []
    for item in raw or []:
        if "=" not in item:
            raise argparse.ArgumentTypeError(
                f"Invalid --filter '{item}', expected key=value"
            )
        k, v = item.split("=", 1)
        out.append(Filter(key=k.strip(), value=v.strip()))
    return out


# ---------------------------------------------------------------------------
# LISTING (real scan, not similarity search)
# ---------------------------------------------------------------------------

def _list_vectors_page(
    next_token: Optional[str],
    max_results: int,
) -> tuple[list[dict[str, Any]], Optional[str]]:
    """
    One page of list_vectors. Returns (vectors, next_token).
    Assumes the backend supports list_vectors — the correct primitive for
    enumeration. Falls back to query-based scan if not available.
    """
    kwargs: dict[str, Any] = {
        "vectorBucketName": VECTOR_BUCKET,
        "indexName": INDEX_NAME,
        "maxResults": max_results,
        "returnMetadata": True,
    }
    if next_token:
        kwargs["nextToken"] = next_token

    try:
        resp = s3_vectors.list_vectors(**kwargs)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"ValidationException", "InvalidAction", "MethodNotAllowed"}:
            raise NotImplementedError("list_vectors unsupported") from exc
        raise

    vectors = resp.get("vectors", [])
    return vectors, resp.get("nextToken")


def iter_vectors() -> Iterable[dict[str, Any]]:
    """Yield every vector in the index (paginated)."""
    token: Optional[str] = None
    pages = 0
    while True:
        pages += 1
        if pages > MAX_PAGES:
            logger.error(
                "Reached MAX_PAGES=%s; aborting enumeration for safety", MAX_PAGES
            )
            return
        batch, token = _list_vectors_page(token, MAX_BATCH)
        if not batch:
            return
        for v in batch:
            yield v
        if not token:
            return


# ---------------------------------------------------------------------------
# DELETION
# ---------------------------------------------------------------------------

_RETRYABLE_CODES = {"ThrottlingException", "ServiceUnavailable", "InternalServerError"}


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        return code in _RETRYABLE_CODES or status in {429, 500, 502, 503, 504}
    return isinstance(exc, (ConnectionError, TimeoutError))


def delete_batch(keys: list[str]) -> tuple[int, list[tuple[str, str]]]:
    """
    Delete a batch of vector keys. Returns (deleted_count, failures).
    Failures is a list of (key, error_message).
    """
    if not keys:
        return 0, []

    for attempt in range(1, DELETE_RETRIES + 1):
        try:
            s3_vectors.delete_vectors(
                vectorBucketName=VECTOR_BUCKET,
                indexName=INDEX_NAME,
                keys=keys,
            )
            return len(keys), []
        except Exception as exc:  # noqa: BLE001
            if not _is_retryable(exc) or attempt == DELETE_RETRIES:
                # Try to narrow down which key failed by retrying one-by-one.
                deleted = 0
                failures: list[tuple[str, str]] = []
                for k in keys:
                    try:
                        s3_vectors.delete_vectors(
                            vectorBucketName=VECTOR_BUCKET,
                            indexName=INDEX_NAME,
                            keys=[k],
                        )
                        deleted += 1
                    except Exception as inner:  # noqa: BLE001
                        failures.append((k, str(inner)))
                return deleted, failures
            sleep_s = BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(
                "delete batch failed (attempt %s/%s), retrying in %.1fs: %s",
                attempt, DELETE_RETRIES, sleep_s, exc,
            )
            time.sleep(sleep_s)

    return 0, [(k, "exhausted retries") for k in keys]


# ---------------------------------------------------------------------------
# MAIN FLOW
# ---------------------------------------------------------------------------

def run(dry_run: bool, filters: list[Filter]) -> int:
    if not VECTOR_BUCKET:
        logger.error("VECTOR_BUCKET not set in environment / .env")
        return 1

    logger.info("Bucket: %s", VECTOR_BUCKET)
    logger.info("Index:  %s", INDEX_NAME)
    logger.info("Region: %s", AWS_REGION)
    if filters:
        logger.info(
            "Filters: %s", ", ".join(f"{f.key}={f.value}" for f in filters)
        )
    if dry_run:
        logger.info("Mode:   DRY RUN (nothing will be deleted)")
    else:
        logger.info("Mode:   LIVE DELETE")
    print()

    matched_keys: list[str] = []
    scanned = 0
    matched = 0

    try:
        for v in iter_vectors():
            scanned += 1
            meta = v.get("metadata") or {}
            if filters and not all(f.matches(meta) for f in filters):
                continue
            matched += 1
            matched_keys.append(v["key"])
            if dry_run:
                logger.info("  [would delete] key=%s topic=%s",
                            v["key"], meta.get("topic"))
    except NotImplementedError:
        logger.error(
            "Backend does not support list_vectors. Use the metadata-filtered "
            "path or a DynamoDB index of keys instead. Aborting rather than "
            "falling back to an unreliable similarity-search sweep."
        )
        return 1

    logger.info("Scanned %s vectors; matched %s", scanned, matched)
    print()

    if not matched_keys:
        logger.info("Nothing to delete.")
        return 0

    if dry_run:
        logger.info("Dry run complete — %s vector(s) would be deleted.", matched)
        return 0

    # Batched deletion
    total_deleted = 0
    all_failures: list[tuple[str, str]] = []
    for i in range(0, len(matched_keys), MAX_BATCH):
        batch = matched_keys[i : i + MAX_BATCH]
        deleted, failures = delete_batch(batch)
        total_deleted += deleted
        all_failures.extend(failures)
        logger.info(
            "Batch %s: deleted=%s failed=%s (running total: %s)",
            i // MAX_BATCH + 1, deleted, len(failures), total_deleted,
        )

    print()
    if all_failures:
        logger.warning(
            "Completed with failures: deleted=%s, failed=%s",
            total_deleted, len(all_failures),
        )
        for k, err in all_failures[:10]:
            logger.warning("  key=%s error=%s", k, err)
        if len(all_failures) > 10:
            logger.warning("  ... and %s more", len(all_failures) - 10)
        return 3

    logger.info("Successfully deleted %s vector(s).", total_deleted)
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Delete vectors from the S3 Vectors index.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be deleted without deleting anything.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Skip the interactive confirmation prompt (CI-friendly).",
    )
    p.add_argument(
        "--filter",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Only delete vectors whose metadata matches. "
            "Repeatable, e.g. --filter ticker=NVDA --filter tag=test"
        ),
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        filters = _parse_filters(args.filter)
    except argparse.ArgumentTypeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("=" * 60)
    print("S3 Vectors Cleanup")
    print("=" * 60)
    print()

    if not args.dry_run and not args.force:
        scope = (
            "ALL vectors"
            if not filters
            else f"vectors matching {', '.join(f'{f.key}={f.value}' for f in filters)}"
        )
        resp = input(f"⚠️  This will DELETE {scope}. Continue? (yes/no): ")
        if resp.strip().lower() != "yes":
            print("Cleanup cancelled.")
            return 2

    return run(dry_run=args.dry_run, filters=filters)


if __name__ == "__main__":
    sys.exit(main())