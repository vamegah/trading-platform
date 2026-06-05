from typing import Any

from backend.data_pipeline.cleaning.data_quality import quality_gate_or_raise
from backend.data_pipeline.lake.metadata import dataset_manifest


def publish_features(
    name: str,
    features: list[dict[str, Any]],
    asset_type: str = "equity",
    version: str = "dev",
    source: str = "feature_pipeline",
    quality_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if quality_report and quality_report.get("blocked"):
        raise ValueError(f"quality gate blocked feature publication: {quality_report}")
    manifest = dataset_manifest(
        name=name,
        layer="feature",
        rows=features,
        version=version,
        source=source,
        asset_type=asset_type,
        timestamp_field="published_at",
    )
    return {**manifest, "feature_set": name, "rows_published": manifest["row_count"]}


def publish_features_with_quality_gate(
    name: str,
    features: list[dict[str, Any]],
    asset_type: str = "equity",
    version: str = "dev",
    source: str = "feature_pipeline",
) -> dict[str, Any]:
    quality_report = quality_gate_or_raise(features)
    return publish_features(
        name=name,
        features=features,
        asset_type=asset_type,
        version=version,
        source=source,
        quality_report=quality_report,
    )


def publish_asset_features(asset_type: str, name: str, features: list[dict[str, Any]]) -> dict[str, Any]:
    return publish_features(name=name, features=features, asset_type=asset_type)
