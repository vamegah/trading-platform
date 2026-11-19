"""
Model validation evidence.

Scans the model registry manifest produced by ML training:
  * Trained artifact hash
  * Calibration summary
  * Drift evaluation
  * SHAP explanation sample
  * Human review approval
"""
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent.parent / "templates"))

REGISTRY_MANIFEST = Path("evidence/models/registry_manifest.json")


def collect(environment: str) -> str:
    manifest = json.loads(REGISTRY_MANIFEST.read_text()) if REGISTRY_MANIFEST.exists() else {}
    models = manifest.get("models", [])
    if not models:
        models = [
            {"name": "fundamentals_agent", "status": "missing"},
            {"name": "technical_agent", "status": "missing"},
            {"name": "news_sentiment_agent", "status": "missing"},
            {"name": "retirement_specialist", "status": "missing"},
        ]
    return TEMPLATES.get_template("model_validation.md.j2").render(
        environment=environment, models=models
    )