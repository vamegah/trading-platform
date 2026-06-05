from typing import Any

from backend.data_pipeline.lake.metadata import dataset_manifest


def write_raw_dataset(
    name: str,
    rows: list[dict[str, Any]],
    asset_type: str = "equity",
    version: str = "dev",
    source: str = "unknown",
) -> dict[str, Any]:
    manifest = dataset_manifest(
        name=name,
        layer="raw",
        rows=rows,
        version=version,
        source=source,
        asset_type=asset_type,
        timestamp_field="written_at",
    )
    return {**manifest, "rows_written": manifest["row_count"]}


def write_raw_asset_dataset(asset_type: str, name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return write_raw_dataset(name=name, rows=rows, asset_type=asset_type)
