#!/usr/bin/env bash
# Build one Lambda zip in its source folder.
#
# Usage: build_one_lambda.sh <source dir relative to backend/> <artifact name>
#
# Each Lambda's zip is written once, inside its own source folder, under the
# name its packager produces. The Terraform stacks, upload_artifacts.sh and
# scripts/deploy.py all reference these same paths:
#
#   planner    backend/services/agents/portfolio_planner/planner_lambda.zip
#   tagger     backend/services/agents/instrument_tagger/tagger_lambda.zip
#   reporter   backend/services/agents/report_writer/reporter_lambda.zip
#   charter    backend/services/agents/chart_maker/charter_lambda.zip
#   retirement backend/services/agents/retirement_specialist/retirement_lambda.zip
#   scheduler  backend/services/scheduler/lambda_function.zip
#   ingest     backend/services/knowledge_base/ingestion/lambda_function.zip
#   api        backend/api_gateway/api_lambda.zip
#
# The researcher Lambda is an image-based function (4_researcher uses
# image_uri), so it has no zip here.
set -euo pipefail

SERVICE_REL="$1"     # e.g. services/agents/portfolio_planner
ARTIFACT_NAME="$2"   # e.g. planner

# This script lives in .github/scripts/ci/, so the repo root is three levels up.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SERVICE_DIR="$ROOT/backend/$SERVICE_REL"

case "$ARTIFACT_NAME" in
  planner|tagger|reporter|charter|retirement|api) ZIP_NAME="${ARTIFACT_NAME}_lambda.zip" ;;
  scheduler|ingest)                               ZIP_NAME="lambda_function.zip" ;;
  *)
    echo "Unknown artifact name: $ARTIFACT_NAME" >&2
    exit 1
    ;;
esac
ZIP_PATH="$SERVICE_DIR/$ZIP_NAME"

if [[ ! -d "$SERVICE_DIR" ]]; then
  echo "Missing service directory: $SERVICE_DIR" >&2
  exit 1
fi

echo "Building $ARTIFACT_NAME from $SERVICE_DIR"
pushd "$SERVICE_DIR" >/dev/null

if [[ "$ARTIFACT_NAME" == "ingest" ]]; then
  # The ingest handler only needs the stdlib plus boto3/botocore, which the
  # Lambda Python runtime provides, so the zip holds just the handler module.
  rm -f "$ZIP_NAME"
  uv run --no-project python - "$ZIP_NAME" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write("ingest_s3Vector.py", "ingest_s3Vector.py")
PY
else
  # Sync a project environment only where the folder defines one.
  if [[ -f pyproject.toml ]]; then
    uv sync --frozen || uv sync
  fi

  if [[ -f package_docker.py ]]; then
    # Uses Docker to install dependencies for linux/amd64
    uv run package_docker.py
  elif [[ -f package.py ]]; then
    uv run package.py
  else
    echo "No packager (package_docker.py or package.py) in $SERVICE_DIR" >&2
    exit 1
  fi
fi

popd >/dev/null

if [[ ! -f "$ZIP_PATH" ]]; then
  echo "Expected artifact not produced: $ZIP_PATH" >&2
  exit 1
fi

echo "Build complete: $ARTIFACT_NAME -> ${ZIP_PATH#"$ROOT"/}"
