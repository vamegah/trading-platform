from typing import Any

from backend.data_pipeline.cleaning.data_quality import quality_gate_or_raise
from backend.data_pipeline.lake.metadata import dataset_manifest


def write_processed_dataset(
    name: str,
    rows: list[dict[str, Any]],
    asset_type: str = "equity",
    version: str = "dev",
    source: str = "raw_pipeline",
    enforce_quality: bool = True,
) -> dict[str, Any]:
    quality_report = quality_gate_or_raise(rows) if enforce_quality else None
    manifest = dataset_manifest(
        name=name,
        layer="processed",
        rows=rows,
        version=version,
        source=source,
        asset_type=asset_type,
        timestamp_field="processed_at",
    )
    return {**manifest, "rows_processed": manifest["row_count"], "quality": quality_report}
