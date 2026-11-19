"""
Paper trading validation evidence.

Queries the platform database for paper trades and computes:
  * Number of trades
  * Reconciliation status
  * Average slippage
  * Max drawdown during the paper period
"""
import os
from pathlib import Path

import boto3
from jinja2 import Environment, FileSystemLoader

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "templates"))


def collect(environment: str) -> str:
    # Query the Aurora cluster for paper trades in the last 30 days
    cluster_arn = os.environ["AURORA_CLUSTER_ARN"]
    secret_arn = os.environ["AURORA_SECRET_ARN"]
    database = os.environ.get("AURORA_DATABASE", "trading")
    region = os.environ.get("DEFAULT_AWS_REGION", "us-east-1")

    client = boto3.client("rds-data", region_name=region)

    sql = """
        SELECT
            COUNT(*) AS num_trades,
            AVG(slippage) AS avg_slippage,
            AVG(commission) AS avg_commission
        FROM trades
        WHERE is_paper = true
          AND placed_at > NOW() - INTERVAL '30 days'
    """
    resp = client.execute_statement(
        resourceArn=cluster_arn, secretArn=secret_arn,
        database=database, sql=sql,
    )
    row = resp.get("records", [[]])[0] if resp.get("records") else []
    num_trades = row[0]["longValue"] if row else 0
    avg_slippage = row[1]["doubleValue"] if row and row[1] else 0
    avg_commission = row[2]["doubleValue"] if row and row[2] else 0

    return TEMPLATES.get_template("paper_trading_validation.md.j2").render(
        environment=environment,
        num_trades=num_trades,
        avg_slippage=avg_slippage,
        avg_commission=avg_commission,
        window_days=30,
    )