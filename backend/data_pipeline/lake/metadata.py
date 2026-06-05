import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        if hasattr(row, "model_dump"):
            normalized.append(row.model_dump(mode="json"))
        else:
            normalized.append(dict(row))
    return normalized


def schema_hash(rows: list[dict[str, Any]]) -> str:
    fields = sorted(
        {
            key: type(value).__name__
            for row in normalize_rows(rows)
            for key, value in row.items()
        }.items()
    )
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def content_hash(rows: list[dict[str, Any]]) -> str:
    payload = json.dumps(normalize_rows(rows), default=str, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def dataset_manifest(
    *,
    name: str,
    layer: str,
    rows: list[dict[str, Any]],
    version: str,
    source: str,
    asset_type: str,
    timestamp_field: str,
) -> dict[str, Any]:
    normalized = normalize_rows(rows)
    schema = schema_hash(normalized)
    content = content_hash(normalized)
    written_at = datetime.now(timezone.utc).isoformat()
    return {
        "dataset": name,
        "layer": layer,
        "asset_type": asset_type,
        "version": version,
        "source": source,
        "schema_hash": schema,
        "content_hash": content,
        "row_count": len(normalized),
        timestamp_field: written_at,
        "manifest": {
            "dataset_id": f"{layer}:{asset_type}:{name}:{version}:{schema[:12]}:{content[:12]}",
            "schema_hash": schema,
            "content_hash": content,
            "created_at": written_at,
            "source": source,
            "version": version,
            "lineage": {
                "source": source,
                "layer": layer,
                "upstream_dataset_id": source if ":" in source else None,
                "content_hash": content,
            },
        },
    }
