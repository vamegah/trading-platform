#!/usr/bin/env bash
set -euo pipefail

BUCKET="$1"
SHA="$2"
# This script lives in .github/scripts/ci/, so the repo root is three levels up.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

upload() {
  local local_path="$1"
  local s3_key="$2"
  if [[ ! -f "$local_path" ]]; then
    echo "Missing artifact: $local_path" >&2
    exit 1
  fi
  echo "Uploading $local_path -> s3://$BUCKET/$s3_key"
  aws s3 cp "$local_path" "s3://$BUCKET/$s3_key" \
    --metadata "git-sha=$SHA" \
    --no-progress
}

# Local paths match build_one_lambda.sh and the Terraform stacks.
upload "$ROOT/backend/services/agents/portfolio_planner/planner_lambda.zip"         "planner/planner_lambda.zip"
upload "$ROOT/backend/services/agents/instrument_tagger/tagger_lambda.zip"          "tagger/tagger_lambda.zip"
upload "$ROOT/backend/services/agents/report_writer/reporter_lambda.zip"            "reporter/reporter_lambda.zip"
upload "$ROOT/backend/services/agents/chart_maker/charter_lambda.zip"               "charter/charter_lambda.zip"
upload "$ROOT/backend/services/agents/retirement_specialist/retirement_lambda.zip"  "retirement/retirement_lambda.zip"
upload "$ROOT/backend/services/scheduler/lambda_function.zip"                       "scheduler/lambda_function.zip"
upload "$ROOT/backend/services/knowledge_base/ingestion/lambda_function.zip"        "ingest/lambda_function.zip"
upload "$ROOT/backend/api_gateway/api_lambda.zip"                                   "api/api_lambda.zip"

echo "All artifacts uploaded for $SHA"
