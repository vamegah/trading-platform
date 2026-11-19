#!/usr/bin/env bash
set -euo pipefail

SERVICE_REL="$1"     # e.g. portfolio_planner
ARTIFACT_NAME="$2"   # e.g. planner

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_DIR="$ROOT/backend/services/$SERVICE_REL"

if [[ ! -d "$SERVICE_DIR" ]]; then
  echo "Missing service directory: $SERVICE_DIR" >&2
  exit 1
fi

echo "Building $ARTIFACT_NAME from $SERVICE_DIR"
pushd "$SERVICE_DIR" >/dev/null

# Ensure isolated environment for build
uv sync --frozen || uv sync

# Run the packager (uses Docker to install for linux/amd64)
uv run package_docker.py

popd >/dev/null

# Normalise output name
case "$ARTIFACT_NAME" in
  planner)    [[ -f "$SERVICE_DIR/planner_lambda.zip" ]]    && mv "$SERVICE_DIR/planner_lambda.zip"    "$SERVICE_DIR/planner.zip" ;;
  tagger)     [[ -f "$SERVICE_DIR/tagger_lambda.zip" ]]     && mv "$SERVICE_DIR/tagger_lambda.zip"     "$SERVICE_DIR/tagger.zip" ;;
  reporter)   [[ -f "$SERVICE_DIR/reporter_lambda.zip" ]]   && mv "$SERVICE_DIR/reporter_lambda.zip"   "$SERVICE_DIR/reporter.zip" ;;
  charter)    [[ -f "$SERVICE_DIR/charter_lambda.zip" ]]    && mv "$SERVICE_DIR/charter_lambda.zip"    "$SERVICE_DIR/charter.zip" ;;
  retirement) [[ -f "$SERVICE_DIR/retirement_lambda.zip" ]] && mv "$SERVICE_DIR/retirement_lambda.zip" "$SERVICE_DIR/retirement.zip" ;;
  researcher) [[ -f "$SERVICE_DIR/researcher.zip" ]]        && true ;;
  scheduler)  [[ -f "$SERVICE_DIR/scheduler.zip" ]]         && true ;;
  knowledge_base)
    # Both ingest and search share the same zip
    [[ -f "$SERVICE_DIR/lambda_function.zip" ]] && cp "$SERVICE_DIR/lambda_function.zip" "$SERVICE_DIR/knowledge_base.zip"
    ;;
  api)        [[ -f "$SERVICE_DIR/api_lambda.zip" ]]        && mv "$SERVICE_DIR/api_lambda.zip"        "$SERVICE_DIR/api.zip" ;;
esac

echo "Build complete: $ARTIFACT_NAME"