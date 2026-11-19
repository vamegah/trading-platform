#!/usr/bin/env python3
"""
Migration runner for the trading platform database.

Reads migrations/*.sql in sorted order, records applied versions in
schema_migrations, and skips migrations that are already applied.
"""
import glob
import logging
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("migrate")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

CLUSTER_ARN = os.environ.get("AURORA_CLUSTER_ARN")
SECRET_ARN = os.environ.get("AURORA_SECRET_ARN")
DATABASE = os.environ.get("AURORA_DATABASE", "trading")
REGION = os.environ.get("DEFAULT_AWS_REGION", "us-east-1")

if not CLUSTER_ARN or not SECRET_ARN:
    raise SystemExit("AURORA_CLUSTER_ARN and AURORA_SECRET_ARN are required")

client = boto3.client("rds-data", region_name=REGION)


def _execute(sql: str) -> None:
    client.execute_statement(
        resourceArn=CLUSTER_ARN,
        secretArn=SECRET_ARN,
        database=DATABASE,
        sql=sql,
    )


def _ensure_tracking_table() -> None:
    _execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)


def _applied_versions() -> set[str]:
    response = client.execute_statement(
        resourceArn=CLUSTER_ARN,
        secretArn=SECRET_ARN,
        database=DATABASE,
        sql="SELECT version FROM schema_migrations",
    )
    return {
        rec[0]["stringValue"]
        for rec in response.get("records", [])
    }


def _split_statements(sql: str) -> list[str]:
    """
    Split a migration file into executable statements.

    Handles dollar-quoted blocks ($$ ... $$) used by PL/pgSQL.
    """
    statements: list[str] = []
    buffer: list[str] = []
    in_dollar = False

    for line in sql.splitlines():
        if line.count("$$") % 2 == 1:
            in_dollar = not in_dollar

        buffer.append(line)

        if not in_dollar and line.rstrip().endswith(";"):
            statement = "\n".join(buffer).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            buffer = []

    if buffer:
        statement = "\n".join(buffer).strip()
        if statement:
            statements.append(statement)

    return statements


def _apply_file(path: Path) -> None:
    logger.info("Applying %s", path.name)
    sql = path.read_text()
    for i, stmt in enumerate(_split_statements(sql), 1):
        try:
            _execute(stmt)
        except ClientError as exc:
            msg = exc.response.get("Error", {}).get("Message", "")
            if "already exists" in msg.lower():
                logger.warning("  [%d] already exists, skipping", i)
                continue
            logger.error("  [%d] failed: %s", i, msg[:200])
            raise

    _execute(f"INSERT INTO schema_migrations (version) VALUES ('{path.name}')")
    logger.info("Applied %s", path.name)


def main() -> None:
    _ensure_tracking_table()
    applied = _applied_versions()

    files = sorted(glob.glob(str(MIGRATIONS_DIR / "*.sql")))
    if not files:
        logger.warning("No migration files found in %s", MIGRATIONS_DIR)
        return

    for f in files:
        name = Path(f).name
        if name in applied:
            logger.info("Skipping %s (already applied)", name)
            continue
        _apply_file(Path(f))

    logger.info("Migrations complete.")


if __name__ == "__main__":
    sys.exit(main())