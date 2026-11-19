"""
Aurora Data API client for the trading platform.

Adds retry handling for transient RDS Data API failures, batch execution
for hot paths, and a lightweight ping() for readiness checks.
"""
import json
import logging
import os
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

logger = logging.getLogger(__name__)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(name: str) -> str:
    """Return `name` if it is a safe SQL identifier, else raise ValueError.

    Table, column and RETURNING names cannot be bound as parameters, so they
    are interpolated into SQL. Validating them here keeps caller-supplied dict
    keys from injecting SQL.
    """
    if not isinstance(name, str) or not _IDENTIFIER_RE.fullmatch(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name

_RETRYABLE_CODES = {
    "StatementTimeoutException",
    "DatabaseResumingException",
    "InternalServerError",
    "ThrottlingException",
    "ServiceUnavailableError",
}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, ClientError):
        return exc.response.get("Error", {}).get("Code") in _RETRYABLE_CODES
    return False


class DataAPIClient:
    """Wrapper around AWS RDS Data API for Aurora Serverless v2."""

    def __init__(
        self,
        cluster_arn: Optional[str] = None,
        secret_arn: Optional[str] = None,
        database: Optional[str] = None,
        region: Optional[str] = None,
    ) -> None:
        self.cluster_arn = cluster_arn or os.environ.get("AURORA_CLUSTER_ARN")
        self.secret_arn = secret_arn or os.environ.get("AURORA_SECRET_ARN")
        self.database = database or os.environ.get("AURORA_DATABASE", "trading")
        self.region = region or os.environ.get("DEFAULT_AWS_REGION", "us-east-1")

        if not self.cluster_arn or not self.secret_arn:
            raise ValueError(
                "Missing AURORA_CLUSTER_ARN or AURORA_SECRET_ARN. "
                "Populate them via .env or the task role."
            )

        self.client = boto3.client("rds-data", region_name=self.region)

    # ----------------------------------------------------------- retry wrapper

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def _execute_statement(self, **kwargs) -> Dict:
        return self.client.execute_statement(**kwargs)

    # ------------------------------------------------------------ public API

    def ping(self) -> bool:
        try:
            self.execute("SELECT 1")
            return True
        except Exception:
            logger.exception("Database ping failed")
            return False

    def execute(self, sql: str, parameters: Optional[List[Dict]] = None) -> Dict:
        kwargs: Dict[str, Any] = {
            "resourceArn": self.cluster_arn,
            "secretArn": self.secret_arn,
            "database": self.database,
            "sql": sql,
            "includeResultMetadata": True,
        }
        if parameters:
            kwargs["parameters"] = parameters
        try:
            return self._execute_statement(**kwargs)
        except ClientError:
            logger.error("Database error executing statement")
            raise

    def batch_execute(self, sql: str, param_sets: List[List[Dict]]) -> Dict:
        """Batch statement execution for hot paths (bulk inserts, updates)."""
        return self.client.batch_execute_statement(
            resourceArn=self.cluster_arn,
            secretArn=self.secret_arn,
            database=self.database,
            sql=sql,
            parameterSets=param_sets,
        )

    def query(self, sql: str, parameters: Optional[List[Dict]] = None) -> List[Dict]:
        response = self.execute(sql, parameters)
        if "records" not in response:
            return []
        columns = [col["name"] for col in response.get("columnMetadata", [])]
        return [
            {columns[i]: self._extract_value(record[i]) for i in range(len(columns))}
            for record in response["records"]
        ]

    def query_one(self, sql: str, parameters: Optional[List[Dict]] = None) -> Optional[Dict]:
        results = self.query(sql, parameters)
        return results[0] if results else None

    def insert(self, table: str, data: Dict, returning: Optional[str] = None) -> Optional[str]:
        table = _ident(table)
        columns = [_ident(col) for col in data]
        placeholders = []
        for col in columns:
            val = data[col]
            if isinstance(val, (dict, list)):
                placeholders.append(f":{col}::jsonb")
            elif isinstance(val, Decimal):
                placeholders.append(f":{col}::numeric")
            elif isinstance(val, datetime):
                placeholders.append(f":{col}::timestamp")
            elif isinstance(val, date):
                placeholders.append(f":{col}::date")
            else:
                placeholders.append(f":{col}")

        # Identifiers validated by _ident(); values are bound parameters.
        sql = (
            f"INSERT INTO {table} ({', '.join(columns)}) "  # nosec B608
            f"VALUES ({', '.join(placeholders)})"
        )
        if returning:
            sql += f" RETURNING {_ident(returning)}"

        response = self.execute(sql, self._build_parameters(data))
        if returning and response.get("records"):
            return self._extract_value(response["records"][0][0])
        return None

    def update(
        self,
        table: str,
        data: Dict,
        where: str,
        where_params: Optional[Dict] = None,
    ) -> int:
        table = _ident(table)
        set_parts = []
        for col, val in data.items():
            _ident(col)
            if isinstance(val, (dict, list)):
                set_parts.append(f"{col} = :{col}::jsonb")
            elif isinstance(val, Decimal):
                set_parts.append(f"{col} = :{col}::numeric")
            elif isinstance(val, datetime):
                set_parts.append(f"{col} = :{col}::timestamp")
            elif isinstance(val, date):
                set_parts.append(f"{col} = :{col}::date")
            else:
                set_parts.append(f"{col} = :{col}")

        # Identifiers validated by _ident(); `where` is an internal fragment
        # whose values are bound via where_params.
        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where}"  # nosec B608
        response = self.execute(sql, self._build_parameters({**data, **(where_params or {})}))
        return response.get("numberOfRecordsUpdated", 0)

    def delete(self, table: str, where: str, where_params: Optional[Dict] = None) -> int:
        # Table validated by _ident(); `where` values are bound via where_params.
        sql = f"DELETE FROM {_ident(table)} WHERE {where}"  # nosec B608
        response = self.execute(sql, self._build_parameters(where_params or {}))
        return response.get("numberOfRecordsUpdated", 0)

    # ------------------------------------------------------------ transactions

    def begin_transaction(self) -> str:
        response = self.client.begin_transaction(
            resourceArn=self.cluster_arn,
            secretArn=self.secret_arn,
            database=self.database,
        )
        return response["transactionId"]

    def commit_transaction(self, transaction_id: str) -> None:
        self.client.commit_transaction(
            resourceArn=self.cluster_arn,
            secretArn=self.secret_arn,
            transactionId=transaction_id,
        )

    def rollback_transaction(self, transaction_id: str) -> None:
        self.client.rollback_transaction(
            resourceArn=self.cluster_arn,
            secretArn=self.secret_arn,
            transactionId=transaction_id,
        )

    # ----------------------------------------------------------- internals

    def _build_parameters(self, data: Dict) -> List[Dict]:
        if not data:
            return []
        parameters = []
        for key, value in data.items():
            param: Dict[str, Any] = {"name": key}
            if value is None:
                param["value"] = {"isNull": True}
            elif isinstance(value, bool):
                param["value"] = {"booleanValue": value}
            elif isinstance(value, int):
                param["value"] = {"longValue": value}
            elif isinstance(value, float):
                param["value"] = {"doubleValue": value}
            elif isinstance(value, Decimal):
                param["value"] = {"stringValue": str(value)}
            elif isinstance(value, (date, datetime)):
                param["value"] = {"stringValue": value.isoformat()}
            elif isinstance(value, (dict, list)):
                param["value"] = {"stringValue": json.dumps(value)}
            else:
                param["value"] = {"stringValue": str(value)}
            parameters.append(param)
        return parameters

    def _extract_value(self, field: Dict) -> Any:
        if field.get("isNull"):
            return None
        if "booleanValue" in field:
            return field["booleanValue"]
        if "longValue" in field:
            return field["longValue"]
        if "doubleValue" in field:
            return field["doubleValue"]
        if "stringValue" in field:
            value = field["stringValue"]
            if value and value[0] in ("{", "["):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    pass
            return value
        if "blobValue" in field:
            return field["blobValue"]
        return None